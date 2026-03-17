from __future__ import annotations

import json
from typing import Any

import httpx

from nanobot.config.schema import ProviderConfig
from nanobot.providers.base import (
    AuthenticationError,
    LLMProvider,
    LLMResponse,
    ProviderError,
    RateLimitError,
    ToolCallRequest,
)


class OllamaProvider(LLMProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"
        self.model = config.model or "glm-4.7-flash-32k"

    def get_default_model(self) -> str:
        return "glm-4.7-flash-32k"

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._format_messages(messages),
            "stream": False,
        }

        if tools:
            payload["tools"] = tools

        temperature = kwargs.get("temperature")
        if temperature is not None:
            payload["temperature"] = temperature

        max_tokens = kwargs.get("max_tokens")
        if max_tokens is not None:
            payload["options"] = {"num_predict": max_tokens}

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                return self._parse_response(response)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            elif e.response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            elif e.response.status_code >= 500:
                raise ProviderError(f"Server error: {e.response.status_code}")
            raise ProviderError(f"HTTP error: {e.response.status_code}")
        except httpx.ConnectError:
            raise ProviderError("Could not connect to Ollama server")
        except httpx.TimeoutException:
            raise ProviderError("Request timed out")

    def _format_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if isinstance(content, list):
                new_content = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            new_content.append({"type": "text", "text": item.get("text", "")})
                        elif item.get("type") == "image_url":
                            image_url = item.get("image_url", {})
                            url = image_url.get("url", "") if isinstance(image_url, dict) else str(image_url)
                            new_content.append({"type": "image_url", "image_url": {"url": url}})
                    elif isinstance(item, str):
                        new_content.append({"type": "text", "text": item})
                content = new_content
            elif role == "system" and isinstance(content, list):
                content = content[0].get("text", "") if content else ""

            formatted.append({"role": role, "content": content})

        return formatted

    def _parse_response(self, response: httpx.Response) -> LLMResponse:
        if response.status_code != 200:
            raise ProviderError(f"Ollama returned status {response.status_code}")

        data = response.json()
        message = data.get("message", {})
        content = message.get("content", "")
        tool_calls = self._parse_tool_calls_from_message(message)

        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            raw_response=data,
            model=data.get("model", self.model),
        )

    def _parse_tool_calls_from_message(self, message: dict[str, Any]) -> list[ToolCallRequest]:
        tool_calls = []
        raw_tool_calls = message.get("tool_calls", [])

        for tc in raw_tool_calls:
            if isinstance(tc, dict):
                func = tc.get("function", tc)
                name = func.get("name", "")
                arguments = func.get("arguments", {})

                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                tool_calls.append(
                    ToolCallRequest(
                        id=tc.get("id", ""),
                        name=name,
                        arguments=arguments,
                    )
                )

        return tool_calls
