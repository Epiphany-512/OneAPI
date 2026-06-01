"""Provider base and registry."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import httpx


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class Choice:
    index: int = 0
    message: dict[str, str] = field(default_factory=lambda: {"role": "assistant", "content": ""})
    finish_reason: str | None = None


@dataclass
class ChatResult:
    id: str = ""
    model: str = ""
    choices: list[Choice] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    created: int = field(default_factory=lambda: int(time.time()))
    raw: Any = None


class BaseProvider(ABC):
    """Abstract base for LLM providers."""

    name: str = ""

    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    @abstractmethod
    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 1.0,
        max_tokens: int | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> ChatResult | AsyncIterator[bytes]:
        """Send a chat completion request."""
        ...

    @abstractmethod
    async def models(self) -> list[dict[str, str]]:
        """List available models for this provider."""
        ...

    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def _resolve_model(self, model: str) -> str:
        """Map gateway model name to provider model name (override if needed)."""
        return model


# ── Registry ────────────────────────────────────────────────────────────────

_PROVIDERS: dict[str, type[BaseProvider]] = {}


def register_provider(name: str):
    """Decorator to register a provider class."""
    def wrapper(cls: type[BaseProvider]) -> type[BaseProvider]:
        cls.name = name
        _PROVIDERS[name] = cls
        return cls
    return wrapper


def get_provider(name: str) -> type[BaseProvider] | None:
    return _PROVIDERS.get(name)


def list_providers() -> list[str]:
    return list(_PROVIDERS.keys())
