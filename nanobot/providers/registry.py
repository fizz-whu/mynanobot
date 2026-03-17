from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from nanobot.config.schema import ProviderConfig

if TYPE_CHECKING:
    from nanobot.providers.ollama import OllamaProvider


@dataclass
class ProviderSpec:
    name: str
    keywords: list[str]
    default_model: str
    env_key: str
    base_url: str | None
    supports_tools: bool = True
    supports_vision: bool = True
    max_tokens: int | None = None
    provider_class: str = ""


OLLAMA_SPEC = ProviderSpec(
    name="ollama",
    keywords=["glm-", "qwen", "gpt-oss", "llama", "mistral", "codestral", "phi", "mixtral"],
    default_model="glm-4.7-flash-32k",
    env_key="",
    base_url="http://localhost:11434",
    supports_tools=True,
    supports_vision=True,
    max_tokens=None,
    provider_class="nanobot.providers.ollama.OllamaProvider",
)


class ProviderRegistry:
    def __init__(self):
        self._specs: dict[str, ProviderSpec] = {}
        self._register_default_providers()

    def _register_default_providers(self):
        self.register(OLLAMA_SPEC)

    def register(self, spec: ProviderSpec):
        self._specs[spec.name] = spec

    def detect_provider(self, model: str) -> ProviderSpec | None:
        if not model:
            return self._specs.get("ollama")

        for spec in self._specs.values():
            for keyword in spec.keywords:
                if keyword in model.lower():
                    return spec
        return self._specs.get("ollama")

    def get_spec(self, name: str) -> ProviderSpec | None:
        return self._specs.get(name)

    def create_provider(
        self, config: ProviderConfig, model: str | None = None
    ) -> "OllamaProvider":
        spec = self.detect_provider(model or config.model)

        if not spec:
            spec = OLLAMA_SPEC

        provider_class_path = spec.provider_class
        module_path, class_name = provider_class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        provider_cls = getattr(module, class_name)

        return provider_cls(config)

    def list_providers(self) -> list[str]:
        return list(self._specs.keys())


_default_registry: ProviderRegistry | None = None


def get_registry() -> ProviderRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = ProviderRegistry()
    return _default_registry
