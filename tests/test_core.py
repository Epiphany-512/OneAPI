"""Tests for OneAPI configuration and routing."""

import pytest
from oneapi.config import DEFAULT_ROUTES, Settings, get_settings, load_routes
from oneapi.providers.base import get_provider, list_providers


def test_settings_defaults():
    """Settings should load with sensible defaults."""
    s = Settings(oneapi_api_key="test-key")  # type: ignore
    assert s.oneapi_port == 8000
    assert s.oneapi_default_model == "gpt-4o"


def test_default_routes():
    """Default routes should cover major providers."""
    assert "gpt-4o" in DEFAULT_ROUTES
    assert DEFAULT_ROUTES["gpt-4o"] == "openai"
    assert "claude-sonnet-4-20250514" in DEFAULT_ROUTES
    assert DEFAULT_ROUTES["claude-sonnet-4-20250514"] == "anthropic"
    assert "deepseek-chat" in DEFAULT_ROUTES
    assert "glm-4" in DEFAULT_ROUTES
    assert "qwen-plus" in DEFAULT_ROUTES


def test_fallback_aliases():
    """Fallback aliases should map to lists of models."""
    assert isinstance(DEFAULT_ROUTES["smart"], list)
    assert "gpt-4o" in DEFAULT_ROUTES["smart"]
    assert isinstance(DEFAULT_ROUTES["fast"], list)
    assert "deepseek-chat" in DEFAULT_ROUTES["fast"]


def test_all_providers_registered():
    """All expected providers should be registered."""
    providers = list_providers()
    assert "openai" in providers
    assert "anthropic" in providers
    assert "zhipu" in providers
    assert "dashscope" in providers
    assert "deepseek" in providers


def test_get_provider():
    """get_provider should return correct class."""
    cls = get_provider("openai")
    assert cls is not None
    assert cls.name == "openai"

    cls = get_provider("anthropic")
    assert cls is not None
    assert cls.name == "anthropic"

    assert get_provider("nonexistent") is None


def test_load_routes():
    """load_routes should return at least default routes."""
    routes = load_routes()
    assert len(routes) >= len(DEFAULT_ROUTES)
    assert "gpt-4o" in routes


def test_anthropic_message_split():
    """Anthropic provider should correctly split system messages."""
    from oneapi.providers.anthropic import AnthropicProvider

    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi!"},
        {"role": "user", "content": "How are you?"},
    ]
    system, chat = AnthropicProvider._split_messages(messages)
    assert "helpful" in system
    assert len(chat) == 3
    assert chat[0]["role"] == "user"
