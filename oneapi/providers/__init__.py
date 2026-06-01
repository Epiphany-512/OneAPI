"""Provider package — auto-import all providers."""

from .base import BaseProvider, ChatResult, Choice, Usage, get_provider, list_providers
from .openai_compat import OpenAIProvider, DashScopeProvider, DeepSeekProvider
from .anthropic import AnthropicProvider
from .zhipu import ZhipuProvider

__all__ = [
    "BaseProvider",
    "ChatResult",
    "Choice",
    "Usage",
    "get_provider",
    "list_providers",
    "OpenAIProvider",
    "DashScopeProvider",
    "DeepSeekProvider",
    "AnthropicProvider",
    "ZhipuProvider",
]
