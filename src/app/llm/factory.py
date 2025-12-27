# =============================================================
# src/app/llm/factory.py
# LLM Provider Factory
# =============================================================
"""
Factory for creating LLM providers.

Provides a unified interface to create and manage LLM providers
based on configuration.
"""

from typing import Dict, Any, Optional
import os
import logging

from .provider import LLMProvider, LLMConfig, LLMProviderType

logger = logging.getLogger(__name__)

# Global default provider instance
_default_provider: Optional[LLMProvider] = None
_default_config: Optional[LLMConfig] = None


def create_llm_provider(config: LLMConfig) -> LLMProvider:
    """
    Create an LLM provider based on configuration.
    
    Args:
        config: LLM configuration
        
    Returns:
        LLMProvider instance
        
    Raises:
        ValueError: If provider type is not supported
        ImportError: If required package is not installed
    """
    provider_type = config.provider
    
    if provider_type == LLMProviderType.MISTRAL or provider_type == "mistral":
        from .mistral_provider import MistralProvider
        return MistralProvider(config)
    
    elif provider_type == LLMProviderType.OPENAI or provider_type == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(config)
    
    elif provider_type == LLMProviderType.ANTHROPIC or provider_type == "anthropic":
        raise NotImplementedError("Anthropic provider not yet implemented")
    
    elif provider_type == LLMProviderType.OLLAMA or provider_type == "ollama":
        raise NotImplementedError("Ollama provider not yet implemented")
    
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_type}")


def create_provider_from_env() -> LLMProvider:
    """
    Create an LLM provider from environment variables.
    
    Environment variables:
    - LLM_PROVIDER: Provider type (mistral, openai, etc.)
    - LLM_MODEL: Model name
    - MISTRAL_API_KEY: Mistral API key
    - OPENAI_API_KEY: OpenAI API key
    - LLM_TEMPERATURE: Temperature (optional)
    - LLM_MAX_TOKENS: Max tokens (optional)
    """
    provider = os.getenv("LLM_PROVIDER", "mistral")
    model = os.getenv("LLM_MODEL", "mistral-large-latest")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1000"))
    
    # Get API key based on provider
    api_key = None
    if provider == "mistral":
        api_key = os.getenv("MISTRAL_API_KEY")
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
    
    config = LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    
    return create_llm_provider(config)


def get_default_provider() -> LLMProvider:
    """
    Get the default LLM provider.
    
    Creates a provider on first call using environment variables.
    Subsequent calls return the cached instance.
    """
    global _default_provider
    
    if _default_provider is None:
        _default_provider = create_provider_from_env()
        logger.info(f"Created default LLM provider: {_default_provider.provider_type.value}")
    
    return _default_provider


def set_default_provider(provider: LLMProvider) -> None:
    """Set the default LLM provider."""
    global _default_provider
    _default_provider = provider
    logger.info(f"Set default LLM provider to: {provider.provider_type.value}")


def reset_default_provider() -> None:
    """Reset the default provider (useful for testing)."""
    global _default_provider
    _default_provider = None


def get_available_providers() -> Dict[str, bool]:
    """Check which LLM providers are available."""
    available = {}
    
    try:
        from mistralai import Mistral
        available["mistral"] = True
    except ImportError:
        available["mistral"] = False
    
    try:
        from openai import OpenAI
        available["openai"] = True
    except ImportError:
        available["openai"] = False
    
    # Future providers
    available["anthropic"] = False
    available["ollama"] = False
    
    return available
