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


# Separate provider for debate agents (uses secondary API key)
_debate_provider: Optional[LLMProvider] = None


def get_debate_provider() -> LLMProvider:
    """
    Get the debate LLM provider (uses secondary API key for parallel calls).
    
    This allows debate agents (critic, mediator) to run in parallel with
    analyst agents without hitting API rate limits.
    
    Uses MISTRAL_API_KEY_2 if available, otherwise falls back to MISTRAL_API_KEY.
    """
    global _debate_provider
    
    if _debate_provider is None:
        provider = os.getenv("LLM_PROVIDER", "mistral")
        model = os.getenv("DEBATE_LLM_MODEL", "magistral-medium-latest")  # Default to reasoning model
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.3"))  # Lower temp for reasoning
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2000"))
        
        # Use secondary API key for parallel calls
        api_key = os.getenv("MISTRAL_API_KEY_2") or os.getenv("MISTRAL_API_KEY")
        
        if not api_key:
            logger.warning("No MISTRAL_API_KEY_2 or MISTRAL_API_KEY found for debate provider")
            # Fall back to default provider
            return get_default_provider()
        
        config = LLMConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        _debate_provider = create_llm_provider(config)
        key_used = "MISTRAL_API_KEY_2" if os.getenv("MISTRAL_API_KEY_2") else "MISTRAL_API_KEY"
        logger.info(f"Created debate LLM provider: {_debate_provider.provider_type.value} (using {key_used})")
    
    return _debate_provider


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


# =============================================================================
# Concurrent LLM Pool Management
# =============================================================================
import asyncio
from typing import List
import threading

# Pool of providers for concurrent use
_provider_pool: List[LLMProvider] = []
_pool_semaphore: Optional[asyncio.Semaphore] = None
_pool_lock = threading.Lock()
_pool_initialized = False


def init_concurrent_pool(max_concurrent: int = 2) -> None:
    """
    Initialize a pool of LLM providers for concurrent use.
    
    Uses both MISTRAL_API_KEY and MISTRAL_API_KEY_2 for parallelism.
    Max concurrent is capped by the number of available API keys.
    """
    global _provider_pool, _pool_semaphore, _pool_initialized
    
    with _pool_lock:
        if _pool_initialized:
            return
        
        _provider_pool = []
        
        # Collect available API keys
        api_keys = []
        key1 = os.getenv("MISTRAL_API_KEY")
        key2 = os.getenv("MISTRAL_API_KEY_2")
        
        # Log which keys are found
        logger.info(f"Checking API keys: MISTRAL_API_KEY={'found' if key1 else 'NOT FOUND'}, MISTRAL_API_KEY_2={'found' if key2 else 'NOT FOUND'}")
        
        if key1:
            api_keys.append(("MISTRAL_API_KEY", key1))
        if key2:
            api_keys.append(("MISTRAL_API_KEY_2", key2))
        
        if not api_keys:
            logger.warning("No Mistral API keys found for concurrent pool")
            return
        
        logger.info(f"Found {len(api_keys)} API keys for concurrent pool")
        
        # Create one provider per API key
        provider_name = os.getenv("LLM_PROVIDER", "mistral")
        model = os.getenv("LLM_MODEL", "mistral-large-latest")
        
        for key_name, api_key in api_keys:
            config = LLMConfig(
                provider=provider_name,
                model=model,
                api_key=api_key,
                temperature=0.7,
                max_tokens=1000,
            )
            
            try:
                provider = create_llm_provider(config)
                _provider_pool.append(provider)
                logger.info(f"Added provider to pool using {key_name}")
            except Exception as e:
                logger.warning(f"Failed to create provider with {key_name}: {e}")
        
        # Semaphore limits concurrent calls to min(max_concurrent, num_providers)
        actual_concurrent = min(max_concurrent, len(_provider_pool))
        _pool_semaphore = asyncio.Semaphore(actual_concurrent)
        _pool_initialized = True
        
        logger.info(f"Initialized concurrent LLM pool with {len(_provider_pool)} providers, max {actual_concurrent} concurrent")


def get_pool_provider(index: int = 0) -> Optional[LLMProvider]:
    """Get a provider from the pool by index (round-robin style)."""
    if not _provider_pool:
        init_concurrent_pool()
    
    if not _provider_pool:
        return get_default_provider()  # Fallback
    
    return _provider_pool[index % len(_provider_pool)]


async def acquire_pool_slot() -> int:
    """Acquire a slot in the concurrent pool. Returns provider index."""
    global _pool_semaphore
    
    if not _pool_initialized:
        init_concurrent_pool()
    
    if _pool_semaphore:
        await _pool_semaphore.acquire()
    
    # Return index for round-robin selection
    return hash(asyncio.current_task()) % max(1, len(_provider_pool))


def release_pool_slot() -> None:
    """Release a slot back to the concurrent pool."""
    if _pool_semaphore:
        _pool_semaphore.release()


def get_pool_size() -> int:
    """Get the number of providers in the pool."""
    if not _pool_initialized:
        init_concurrent_pool()
    return len(_provider_pool)
