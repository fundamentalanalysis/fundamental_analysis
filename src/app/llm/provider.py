# =============================================================
# src/app/llm/provider.py
# LLM Provider Abstraction
# =============================================================
"""
Abstract base class and data models for LLM providers.

This module provides a unified interface for interacting with various
LLM providers (Mistral, OpenAI, Anthropic, etc.).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LLMProviderType(str, Enum):
    """Supported LLM providers."""
    MISTRAL = "mistral"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"  # Local models


class LLMConfig(BaseModel):
    """Configuration for an LLM provider."""
    provider: LLMProviderType = LLMProviderType.MISTRAL
    model: str = "mistral-large-latest"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=32000)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    timeout: float = Field(default=60.0, ge=1.0)
    
    # Provider-specific settings
    extra_params: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class Message(BaseModel):
    """A chat message."""
    role: str  # "system", "user", "assistant"
    content: str


class LLMResponse(BaseModel):
    """Response from an LLM provider."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = Field(default_factory=dict)
    finish_reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    
    # Metadata
    latency_ms: float = 0
    success: bool = True
    error_message: Optional[str] = None


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    Subclasses implement the actual API calls for each provider.
    """
    
    provider_type: LLMProviderType
    
    def __init__(self, config: LLMConfig):
        """Initialize the provider with configuration."""
        self.config = config
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate the configuration."""
        if not self.config.api_key:
            logger.warning(f"No API key provided for {self.provider_type.value}")
    
    @abstractmethod
    def complete(
        self,
        messages: List[Message],
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.
        
        Args:
            messages: List of chat messages
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse with the generated content
        """
        pass
    
    @abstractmethod
    async def acomplete(
        self,
        messages: List[Message],
        **kwargs,
    ) -> LLMResponse:
        """Async version of complete."""
        pass
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Simplified interface for single-turn generation.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse
        """
        messages = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        messages.append(Message(role="user", content=prompt))
        
        return self.complete(messages, **kwargs)
    
    async def agenerate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Async version of generate."""
        messages = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        messages.append(Message(role="user", content=prompt))
        
        return await self.acomplete(messages, **kwargs)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the configured model."""
        return {
            "provider": self.provider_type.value,
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
