# =============================================================
# src/app/config/openrouter_client.py
# OpenRouter Client for Reasoning Model Integration
# =============================================================
"""
OpenRouter client for using reasoning models in the debate system.

Uses the OpenAI SDK with OpenRouter's base_url.
Uses the deepseek-r1t-chimera model for adversarial debate reasoning.
"""

import os
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
    Client for OpenRouter API using OpenAI SDK.
    
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
        """Lazy initialization of the OpenAI client with OpenRouter base_url."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=self.api_key,
                )
            except ImportError:
                logger.error("openai package not installed. Run: pip install openai")
                raise ImportError("openai package required. Install with: pip install openai")
        return self._client
    
    def chat_sync(
        self,
        messages: List[Dict[str, str]],
        model: str = DEFAULT_REASONING_MODEL,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> ReasoningResponse:
        """
        Send a chat request and get the full response (synchronous).
        
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
            
            # Use OpenAI SDK with OpenRouter
            response = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://fundamental-analysis.local",
                    "X-Title": "Fundamental Analysis Mesh",
                },
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            # Extract content from response
            content = ""
            thinking = None
            usage = None
            
            if response.choices and len(response.choices) > 0:
                choice = response.choices[0]
                if hasattr(choice, 'message') and choice.message:
                    content = choice.message.content or ""
                    # Some models include reasoning in a separate field
                    if hasattr(choice.message, 'reasoning'):
                        thinking = choice.message.reasoning
            
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
                    "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
                    "total_tokens": getattr(response.usage, 'total_tokens', 0),
                }
            
            logger.info(f"[OpenRouter] Response received: {len(content)} chars, model: {model}")
            
            return ReasoningResponse(
                content=content,
                thinking=thinking,
                model=model,
                usage=usage,
            )
            
        except Exception as e:
            logger.error(f"OpenRouter chat failed: {e}")
            raise
    
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
