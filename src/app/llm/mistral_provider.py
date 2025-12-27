# =============================================================
# src/app/llm/mistral_provider.py
# Mistral AI Provider Implementation
# =============================================================
"""
Mistral AI LLM provider implementation.

Uses the Mistral AI API for text generation.
"""

from typing import Dict, Any, List, Optional
import time
import logging
import os

from .provider import LLMProvider, LLMConfig, LLMResponse, Message, LLMProviderType

logger = logging.getLogger(__name__)

# Try to import mistralai
try:
    from mistralai import Mistral
    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False
    Mistral = None


class MistralProvider(LLMProvider):
    """
    Mistral AI LLM provider.
    
    Supported models:
    - mistral-large-latest (most capable)
    - mistral-medium-latest
    - mistral-small-latest (fastest)
    - open-mistral-7b
    - open-mixtral-8x7b
    - open-mixtral-8x22b
    """
    
    provider_type = LLMProviderType.MISTRAL
    
    # Default models by use case
    DEFAULT_MODELS = {
        "analysis": "mistral-large-latest",
        "fast": "mistral-small-latest",
        "balanced": "mistral-medium-latest",
    }
    
    def __init__(self, config: LLMConfig):
        """Initialize Mistral provider."""
        super().__init__(config)
        
        if not MISTRAL_AVAILABLE:
            raise ImportError(
                "mistralai package not installed. Run: pip install mistralai"
            )
        
        # Get API key from config or environment
        api_key = config.api_key or os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError(
                "Mistral API key not provided. Set MISTRAL_API_KEY environment variable "
                "or pass api_key in config."
            )
        
        self.client = Mistral(api_key=api_key)
        logger.info(f"Initialized Mistral provider with model: {config.model}")
    
    def complete(
        self,
        messages: List[Message],
        **kwargs,
    ) -> LLMResponse:
        """Generate completion using Mistral API."""
        start_time = time.time()
        
        try:
            # Convert messages to Mistral format
            mistral_messages = [
                {"role": m.role, "content": m.content}
                for m in messages
            ]
            
            # Merge config with kwargs
            params = {
                "model": kwargs.get("model", self.config.model),
                "messages": mistral_messages,
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "top_p": kwargs.get("top_p", self.config.top_p),
            }
            
            # Add any extra params
            params.update(self.config.extra_params)
            params.update({k: v for k, v in kwargs.items() if k not in params})
            
            # Log the call
            prompt_preview = mistral_messages[-1]["content"][:100] if mistral_messages else ""
            logger.info(f"🤖 MISTRAL CALL: model={params['model']}, prompt='{prompt_preview}...'")
            
            # Make API call
            response = self.client.chat.complete(**params)
            
            latency = (time.time() - start_time) * 1000
            
            # Extract response
            choice = response.choices[0]
            
            # Log success
            response_preview = choice.message.content[:100] if choice.message.content else ""
            logger.info(
                f"✅ MISTRAL RESPONSE: {response.usage.total_tokens} tokens, "
                f"{latency:.0f}ms, response='{response_preview}...'"
            )
            
            return LLMResponse(
                content=choice.message.content,
                model=response.model,
                provider="mistral",
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                finish_reason=choice.finish_reason,
                latency_ms=latency,
                success=True,
            )
            
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            logger.error(f"❌ MISTRAL ERROR: {e} (after {latency:.0f}ms)")
            
            return LLMResponse(
                content="",
                model=self.config.model,
                provider="mistral",
                latency_ms=latency,
                success=False,
                error_message=str(e),
            )
    
    async def acomplete(
        self,
        messages: List[Message],
        **kwargs,
    ) -> LLMResponse:
        """Async completion using Mistral API."""
        start_time = time.time()
        
        try:
            mistral_messages = [
                {"role": m.role, "content": m.content}
                for m in messages
            ]
            
            params = {
                "model": kwargs.get("model", self.config.model),
                "messages": mistral_messages,
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "top_p": kwargs.get("top_p", self.config.top_p),
            }
            
            params.update(self.config.extra_params)
            
            # Use async client
            response = await self.client.chat.complete_async(**params)
            
            latency = (time.time() - start_time) * 1000
            choice = response.choices[0]
            
            return LLMResponse(
                content=choice.message.content,
                model=response.model,
                provider="mistral",
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                finish_reason=choice.finish_reason,
                latency_ms=latency,
                success=True,
            )
            
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            logger.error(f"Mistral async API error: {e}")
            
            return LLMResponse(
                content="",
                model=self.config.model,
                provider="mistral",
                latency_ms=latency,
                success=False,
                error_message=str(e),
            )
