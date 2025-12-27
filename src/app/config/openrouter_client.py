# =============================================================
# src/app/config/openrouter_client.py
# OpenRouter Client for Reasoning Model Integration
# =============================================================
"""
OpenRouter client for using reasoning models in the debate system.

Uses the deepseek-r1t-chimera model for adversarial debate reasoning.
"""

import os
import asyncio
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default model for reasoning
DEFAULT_REASONING_MODEL = "tngtech/deepseek-r1t-chimera:free"


@dataclass
class ReasoningResponse:
    """Response from the reasoning model."""
    content: str
    thinking: Optional[str] = None  # Chain of thought (if available)
    model: str = ""
    usage: Optional[Dict[str, int]] = None


class OpenRouterClient:
    """
    Client for OpenRouter API supporting streaming chat completions.
    
    Example usage:
        client = OpenRouterClient()
        response = client.chat_sync([{"role": "user", "content": "..."}])
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenRouter client.
        
        Args:
            api_key: OpenRouter API key. If not provided, reads from OPENROUTER_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not set. OpenRouter calls will fail.")
        
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of the OpenRouter client."""
        if self._client is None:
            try:
                from openrouter import OpenRouter
                self._client = OpenRouter(api_key=self.api_key)
            except ImportError:
                logger.error("openrouter package not installed. Run: pip install openrouter")
                raise ImportError("openrouter package required. Install with: pip install openrouter")
        return self._client
    
    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        model: str = DEFAULT_REASONING_MODEL,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> ReasoningResponse:
        """
        Send a chat request and get the full response (async, with streaming internally).
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            
        Returns:
            ReasoningResponse with content and optional thinking
        """
        try:
            client = self._get_client()
            
            # Use streaming to collect the response
            stream = await client.chat.send(
                model=model,
                messages=messages,
                stream=True,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            content_parts = []
            thinking_parts = []
            
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta:
                    if hasattr(delta, 'content') and delta.content:
                        content_parts.append(delta.content)
                    # Some reasoning models include thinking in a separate field
                    if hasattr(delta, 'reasoning') and delta.reasoning:
                        thinking_parts.append(delta.reasoning)
            
            return ReasoningResponse(
                content="".join(content_parts),
                thinking="".join(thinking_parts) if thinking_parts else None,
                model=model,
            )
            
        except Exception as e:
            logger.error(f"OpenRouter chat failed: {e}")
            raise
    
    def chat_sync(
        self,
        messages: List[Dict[str, str]],
        model: str = DEFAULT_REASONING_MODEL,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> ReasoningResponse:
        """
        Synchronous wrapper for chat_async.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            
        Returns:
            ReasoningResponse with content and optional thinking
        """
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, create a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.chat_async(messages, model, temperature, max_tokens)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.chat_async(messages, model, temperature, max_tokens)
                )
        except RuntimeError:
            # No event loop exists
            return asyncio.run(
                self.chat_async(messages, model, temperature, max_tokens)
            )
    
    def is_available(self) -> bool:
        """Check if the client is properly configured."""
        return bool(self.api_key)


# Module-level singleton for convenience
_openrouter_client: Optional[OpenRouterClient] = None


def get_openrouter_client() -> OpenRouterClient:
    """Get or create the singleton OpenRouter client."""
    global _openrouter_client
    if _openrouter_client is None:
        _openrouter_client = OpenRouterClient()
    return _openrouter_client
