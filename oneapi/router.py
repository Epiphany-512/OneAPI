"""Request router — model → provider mapping, load balancing, fallback."""

from __future__ import annotations

import logging
import random
from typing import Any

from .config import get_settings, load_routes
from .providers.base import BaseProvider, ChatResult, get_provider

logger = logging.getLogger("oneapi.router")


class Router:
    """Routes model requests to the correct provider with fallback support."""

    def __init__(self) -> None:
        self._routes = load_routes()
        self._providers: dict[str, BaseProvider] = {}
        self._init_providers()

    def _init_providers(self) -> None:
        settings = get_settings()
        provider_configs: dict[str, tuple[str, str]] = {
            "openai": (settings.openai_api_key, settings.openai_base_url),
            "anthropic": (settings.anthropic_api_key, settings.anthropic_base_url),
            "zhipu": (settings.zhipu_api_key, settings.zhipu_base_url),
            "dashscope": (settings.dashscope_api_key, settings.dashscope_base_url),
            "deepseek": (settings.deepseek_api_key, settings.deepseek_base_url),
        }
        for name, (key, url) in provider_configs.items():
            cls = get_provider(name)
            if cls and key:
                self._providers[name] = cls(api_key=key, base_url=url)
                logger.info("Provider registered: %s", name)
            elif cls and not key:
                logger.debug("Provider skipped (no key): %s", name)

    def get_provider(self, model: str) -> BaseProvider | None:
        """Resolve model to a provider, with fallback chain support."""
        route = self._routes.get(model)
        if route is None:
            # Try direct provider name
            return self._providers.get(model)

        if isinstance(route, str):
            return self._providers.get(route)

        if isinstance(route, list):
            # Fallback chain: try in order
            random.shuffle(route)  # simple load balancing
            for m in route:
                prov = self.get_provider(m)
                if prov:
                    return prov
        return None

    async def dispatch(self, model: str, **kwargs: Any) -> ChatResult:
        """Dispatch a chat request with automatic fallback."""
        route = self._routes.get(model)
        models_to_try = self._resolve_models(model, route)

        last_error: Exception | None = None
        for m in models_to_try:
            provider = self.get_provider(m) if m != model else self._resolve_direct(route)
            if provider is None:
                provider = self._resolve_direct(m)
            if provider is None:
                continue
            try:
                logger.info("Routing %s → %s (%s)", model, m, provider.name)
                result = await provider.chat(model=m, **kwargs)
                if isinstance(result, ChatResult):
                    return result
                # If streaming, return as-is
                return result  # type: ignore
            except Exception as e:
                logger.warning("Provider failed for %s: %s", m, e)
                last_error = e
                continue

        raise RuntimeError(f"All providers failed for model '{model}': {last_error}")

    async def dispatch_stream(self, model: str, **kwargs: Any):
        """Dispatch a streaming chat request with fallback."""
        kwargs["stream"] = True
        route = self._routes.get(model)
        models_to_try = self._resolve_models(model, route)

        last_error: Exception | None = None
        for m in models_to_try:
            provider = self.get_provider(m) if m != model else self._resolve_direct(route)
            if provider is None:
                provider = self._resolve_direct(m)
            if provider is None:
                continue
            try:
                logger.info("Streaming %s → %s (%s)", model, m, provider.name)
                stream = await provider.chat(model=m, **kwargs)
                async for chunk in stream:
                    yield chunk
                return
            except Exception as e:
                logger.warning("Stream failed for %s: %s", m, e)
                last_error = e
                continue

        raise RuntimeError(f"All providers failed for stream '{model}': {last_error}")

    def _resolve_models(self, model: str, route: Any) -> list[str]:
        if route is None:
            return [model]
        if isinstance(route, str):
            return [model, route]
        if isinstance(route, list):
            return [model] + route
        return [model]

    def _resolve_direct(self, route: Any) -> BaseProvider | None:
        if isinstance(route, str):
            return self._providers.get(route)
        return None

    def list_models(self) -> list[dict[str, str]]:
        """List all routed models."""
        models = []
        for model, route in self._routes.items():
            if isinstance(route, str):
                provider = route
            elif isinstance(route, list):
                provider = route[0] if route else "unknown"
            else:
                provider = "unknown"
            models.append({"id": model, "object": "model", "owned_by": provider})
        return models
