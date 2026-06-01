"""OpenAI-compatible provider (covers OpenAI, DashScope, DeepSeek — they share the same API format)."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, AsyncIterator

import httpx

from .base import BaseProvider, ChatResult, Choice, Usage, register_provider


@register_provider("openai")
class OpenAIProvider(BaseProvider):
    """Works with any OpenAI-compatible API (OpenAI, DashScope, DeepSeek)."""

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
        resolved = self._resolve_model(model)
        url = f"{self.base_url}/chat/completions"
        body: dict[str, Any] = {
            "model": resolved,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            body["max_tokens"] = max_tokens
        body.update(kwargs)

        if stream:
            return self._stream(url, body)

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=body, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        return ChatResult(
            id=data.get("id", str(uuid.uuid4())),
            model=data.get("model", model),
            choices=[
                Choice(
                    index=c.get("index", 0),
                    message=c.get("message", {}),
                    finish_reason=c.get("finish_reason"),
                )
                for c in data.get("choices", [])
            ],
            usage=Usage(
                prompt_tokens=data.get("usage", {}).get("prompt_tokens", 0),
                completion_tokens=data.get("usage", {}).get("completion_tokens", 0),
                total_tokens=data.get("usage", {}).get("total_tokens", 0),
            ),
            created=data.get("created", int(time.time())),
            raw=data,
        )

    async def _stream(self, url: str, body: dict[str, Any]) -> AsyncIterator[bytes]:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, json=body, headers=self._headers()) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        yield (line + "\n\n").encode("utf-8")
                        if line.strip() == "data: [DONE]":
                            break

    async def models(self) -> list[dict[str, str]]:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(f"{self.base_url}/models", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", [])
            except Exception:
                return []

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }


@register_provider("dashscope")
class DashScopeProvider(OpenAIProvider):
    """DashScope (Qwen) — OpenAI-compatible, just different base URL & key."""
    pass


@register_provider("deepseek")
class DeepSeekProvider(OpenAIProvider):
    """DeepSeek — OpenAI-compatible, just different base URL & key."""
    pass
