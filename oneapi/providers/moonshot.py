"""Moonshot (Kimi) provider — OpenAI-compatible."""

from __future__ import annotations

from .openai_compat import OpenAIProvider, register_provider


@register_provider("moonshot")
class MoonshotProvider(OpenAIProvider):
    """Moonshot AI (Kimi) — OpenAI-compatible API."""

    async def models(self) -> list[dict[str, str]]:
        return [
            {"id": "moonshot-v1-8k", "object": "model", "owned_by": "moonshot"},
            {"id": "moonshot-v1-32k", "object": "model", "owned_by": "moonshot"},
            {"id": "moonshot-v1-128k", "object": "model", "owned_by": "moonshot"},
        ]
