"""Configuration management."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Gateway settings loaded from environment / .env file."""

    # Gateway
    oneapi_api_key: str = "oneapi-secret-key"
    oneapi_host: str = "0.0.0.0"
    oneapi_port: int = 8000
    oneapi_default_model: str = "gpt-4o"
    oneapi_log_level: str = "info"

    # Provider keys
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com"
    zhipu_api_key: str = ""
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    moonshot_api_key: str = ""
    moonshot_base_url: str = "https://api.moonshot.cn/v1"

    # Routing config file
    oneapi_routes_file: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings


# ── Model routing ──────────────────────────────────────────────────────────

# Default model -> provider mapping
DEFAULT_ROUTES: dict[str, str | list[str]] = {
    # OpenAI
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    "gpt-4-turbo": "openai",
    "gpt-3.5-turbo": "openai",
    # Anthropic
    "claude-sonnet-4-20250514": "anthropic",
    "claude-3-5-sonnet-20241022": "anthropic",
    "claude-3-haiku-20240307": "anthropic",
    # Zhipu (GLM)
    "glm-4": "zhipu",
    "glm-4-plus": "zhipu",
    "glm-4-flash": "zhipu",
    # Dashscope (Qwen)
    "qwen-plus": "dashscope",
    "qwen-turbo": "dashscope",
    "qwen-max": "dashscope",
    # DeepSeek
    "deepseek-chat": "deepseek",
    "deepseek-coder": "deepseek",
    # Moonshot (Kimi)
    "moonshot-v1-8k": "moonshot",
    "moonshot-v1-32k": "moonshot",
    "moonshot-v1-128k": "moonshot",
    # Fallback aliases
    "smart": ["gpt-4o", "claude-sonnet-4-20250514", "glm-4"],
    "fast": ["deepseek-chat", "gpt-4o-mini", "glm-4-flash"],
}


def load_routes() -> dict[str, str | list[str]]:
    """Load routing config from file if configured, else use defaults."""
    settings = get_settings()
    if settings.oneapi_routes_file and Path(settings.oneapi_routes_file).exists():
        with open(settings.oneapi_routes_file, encoding="utf-8") as f:
            custom = json.load(f)
        routes = {**DEFAULT_ROUTES, **custom}
    else:
        routes = DEFAULT_ROUTES.copy()
    return routes
