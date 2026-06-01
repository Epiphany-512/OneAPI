"""Zhipu (GLM) provider — OpenAI-compatible with JWT auth."""

from __future__ import annotations

import time
import uuid
from typing import Any, AsyncIterator

import httpx

from .openai_compat import OpenAIProvider, register_provider


@register_provider("zhipu")
class ZhipuProvider(OpenAIProvider):
    """Zhipu GLM — OpenAI-compatible API with Bearer token auth."""

    async def models(self) -> list[dict[str, str]]:
        return [
            {"id": "glm-4", "object": "model", "owned_by": "zhipu"},
            {"id": "glm-4-plus", "object": "model", "owned_by": "zhipu"},
            {"id": "glm-4-flash", "object": "model", "owned_by": "zhipu"},
        ]
