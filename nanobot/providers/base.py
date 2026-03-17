from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

from nanobot.config.schema import ProviderConfig


class ProviderError(Exception):
    pass


class RateLimitError(ProviderError):
    pass


class AuthenticationError(ProviderError):
    pass


@dataclass
class ToolCallRequest:
    id: str
    name: str
    arguments: dict[str, Any]

    @classmethod
    def from_openai_format(cls, tool_call: dict[str, Any]) -> ToolCallRequest:
        tc = tool_call.get("function", tool_call)
        arguments = tc.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}
        return cls(
            id=tool_call.get("id", ""),
            name=tc.get("name", ""),
            arguments=arguments,
        )


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=lambda: {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    })
    raw_response: Any = None
    reasoning_content: str | None = None
    thinking_blocks: list | None = None
    model: str | None = None


class LLMProvider(ABC):
    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> LLMResponse:
        pass

    async def chat_with_retry(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_retries: int = 3,
        **kwargs,
    ) -> LLMResponse:
        delays = [1, 2, 4]
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                return await self.chat(messages, tools, **kwargs)
            except RateLimitError as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(delays[attempt])
            except AuthenticationError:
                raise
            except ProviderError as e:
                if attempt < max_retries - 1 and self._is_transient_error(e):
                    await asyncio.sleep(delays[attempt])
                else:
                    raise

        raise last_error or ProviderError("Max retries exceeded")

    def _is_transient_error(self, error: Exception) -> bool:
        if isinstance(error, httpx.HTTPStatusError):
            return error.response.status_code in (429, 500, 502, 503, 504)
        return isinstance(error, (httpx.ConnectError, httpx.TimeoutException))

    def get_default_model(self) -> str:
        return ""

    def _parse_tool_calls(self, response: Any) -> list[ToolCallRequest]:
        tool_calls = []
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                tool_calls.append(ToolCallRequest.from_openai_format(tc))
        return tool_calls

    def _build_auth_headers(self) -> dict[str, str]:
        headers = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        headers.update(self.config.extra_headers)
        return headers
