# =============================================================
# src/app/llm/__init__.py
# LLM Provider Package
# =============================================================
"""
Configurable LLM provider abstraction layer.

Supports multiple LLM providers:
- Mistral AI
- OpenAI
- Anthropic (future)
- Local models (future)
"""

from .provider import LLMProvider, LLMConfig, LLMResponse, LLMProviderType, Message
from .factory import create_llm_provider, get_default_provider, set_default_provider
from .config import (
    load_llm_config_from_env,
    load_llm_config_from_yaml,
    get_agent_prompt,
    AGENT_PROMPTS,
)

__all__ = [
    # Provider base
    "LLMProvider",
    "LLMConfig",
    "LLMResponse",
    "LLMProviderType",
    "Message",
    # Factory
    "create_llm_provider",
    "get_default_provider",
    "set_default_provider",
    # Config
    "load_llm_config_from_env",
    "load_llm_config_from_yaml",
    "get_agent_prompt",
    "AGENT_PROMPTS",
]

