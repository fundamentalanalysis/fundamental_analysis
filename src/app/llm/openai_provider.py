# =============================================================
# src/app/llm/openai_provider.py
# OpenAI Provider Implementation
# =============================================================
"""
OpenAI LLM provider implementation.

Provides fallback/alternative to Mistral.
"""

from typing import Dict, Any, List, Optional
import time
import logging
import os

from .provider import LLMProvider, LLMConfig, LLMResponse, Message, LLMProviderType

logger = logging.getLogger(__name__)

# Try to import openai
try:
    from openai import OpenAI, AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None
    AsyncOpenAI = None


class OpenAIProvider(LLMProvider):
    """
    OpenAI LLM provider.
    
    Supported models:
    - gpt-4o (latest)
    - gpt-4-turbo
    - gpt-4
    - gpt-3.5-turbo
    """
    
    provider_type = LLMProviderType.OPENAI
    
    DEFAULT_MODELS = {
        "analysis": "gpt-4o",
        "fast": "gpt-3.5-turbo",
        "balanced": "gpt-4-turbo",
    }
    
    def __init__(self, config: LLMConfig):
        """Initialize OpenAI provider."""
        super().__init__(config)
        
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package not installed. Run: pip install openai"
            )
        
        api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable "
                "or pass api_key in config."
            )
        
        self.client = OpenAI(api_key=api_key, base_url=config.base_url)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=config.base_url)
        logger.info(f"Initialized OpenAI provider with model: {config.model}")
    
    def complete(
        self,
        messages: List[Message],
        **kwargs,
    ) -> LLMResponse:
        """Generate completion using OpenAI API."""
        start_time = time.time()
        
        try:
            openai_messages = [
                {"role": m.role, "content": m.content}
                for m in messages
            ]
            
            params = {
                "model": kwargs.get("model", self.config.model),
                "messages": openai_messages,
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "top_p": kwargs.get("top_p", self.config.top_p),
            }
            
            params.update(self.config.extra_params)
            
            response = self.client.chat.completions.create(**params)
            
            latency = (time.time() - start_time) * 1000
            choice = response.choices[0]
            
            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                provider="openai",
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                finish_reason=choice.finish_reason,
                latency_ms=latency,
                success=True,
            )
            
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            logger.error(f"OpenAI API error: {e}")
            
            return LLMResponse(
                content="",
                model=self.config.model,
                provider="openai",
                latency_ms=latency,
                success=False,
                error_message=str(e),
            )
    
    async def acomplete(
        self,
        messages: List[Message],
        **kwargs,
    ) -> LLMResponse:
        """Async completion using OpenAI API."""
        start_time = time.time()
        
        try:
            openai_messages = [
                {"role": m.role, "content": m.content}
                for m in messages
            ]
            
            params = {
                "model": kwargs.get("model", self.config.model),
                "messages": openai_messages,
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "top_p": kwargs.get("top_p", self.config.top_p),
            }
            
            params.update(self.config.extra_params)
            
            response = await self.async_client.chat.completions.create(**params)
            
            latency = (time.time() - start_time) * 1000
            choice = response.choices[0]
            
            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                provider="openai",
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                finish_reason=choice.finish_reason,
                latency_ms=latency,
                success=True,
            )
            
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            logger.error(f"OpenAI async API error: {e}")
            
            return LLMResponse(
                content="",
                model=self.config.model,
                provider="openai",
                latency_ms=latency,
                success=False,
                error_message=str(e),
            )
