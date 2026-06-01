"""Anthropic (Claude) provider — translates OpenAI format to Anthropic format."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, AsyncIterator

import httpx

from .base import BaseProvider, ChatResult, Choice, Usage, register_provider


@register_provider("anthropic")
class AnthropicProvider(BaseProvider):

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
        url = f"{self.base_url}/v1/messages"

        system_msg, chat_msgs = self._split_messages(messages)

        body: dict[str, Any] = {
            "model": resolved,
            "messages": chat_msgs,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
            "stream": stream,
        }
        if system_msg:
            body["system"] = system_msg

        if stream:
            return self._stream(url, body)

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=body, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        content = "".join(
            b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
        )

        return ChatResult(
            id=data.get("id", str(uuid.uuid4())),
            model=data.get("model", model),
            choices=[
                Choice(
                    index=0,
                    message={"role": "assistant", "content": content},
                    finish_reason=data.get("stop_reason"),
                )
            ],
            usage=Usage(
                prompt_tokens=data.get("usage", {}).get("input_tokens", 0),
                completion_tokens=data.get("usage", {}).get("output_tokens", 0),
                total_tokens=(
                    data.get("usage", {}).get("input_tokens", 0)
                    + data.get("usage", {}).get("output_tokens", 0)
                ),
            ),
            created=int(time.time()),
            raw=data,
        )

    async def _stream(self, url: str, body: dict[str, Any]) -> AsyncIterator[bytes]:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, json=body, headers=self._headers()) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        raw = line[6:]
                        try:
                            evt = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        evt_type = evt.get("type", "")

                        if evt_type == "content_block_delta":
                            delta = evt.get("delta", {})
                            text = delta.get("text", "")
                            chunk = {
                                "id": evt.get("id", ""),
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": body["model"],
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {"content": text},
                                        "finish_reason": None,
                                    }
                                ],
                            }
                            yield f"data: {json.dumps(chunk)}\n\n".encode()

                        elif evt_type == "message_stop":
                            yield b"data: [DONE]\n\n"

    async def models(self) -> list[dict[str, str]]:
        return [
            {"id": "claude-sonnet-4-20250514", "object": "model", "owned_by": "anthropic"},
            {"id": "claude-3-5-sonnet-20241022", "object": "model", "owned_by": "anthropic"},
            {"id": "claude-3-haiku-20240307", "object": "model", "owned_by": "anthropic"},
        ]

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

    @staticmethod
    def _split_messages(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
        """Extract system message; separate for Anthropic API."""
        system = ""
        chat = []
        for m in messages:
            if m.get("role") == "system":
                system += m.get("content", "") + "\n"
            else:
                chat.append({"role": m["role"], "content": m.get("content", "")})
        return system.strip(), chat
