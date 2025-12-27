# =============================================================
# src/app/llm/config.py
# LLM Configuration
# =============================================================
"""
LLM configuration from YAML or environment variables.

Environment variables:
- LLM_PROVIDER: mistral, openai, anthropic, ollama
- LLM_MODEL: Model name (provider-specific)
- MISTRAL_API_KEY: Mistral API key
- OPENAI_API_KEY: OpenAI API key
- LLM_TEMPERATURE: Temperature (0.0-2.0)
- LLM_MAX_TOKENS: Max tokens (1-32000)
"""

from typing import Dict, Any, Optional
import os
import yaml
import logging

from .provider import LLMConfig, LLMProviderType
from dotenv import load_dotenv



logger = logging.getLogger(__name__)

# Default LLM configurations by provider
DEFAULT_CONFIGS = {
    "mistral": LLMConfig(
        provider=LLMProviderType.MISTRAL,
        model="mistral-large-latest",
        temperature=0.7,
        max_tokens=1000,
    ),
    "openai": LLMConfig(
        provider=LLMProviderType.OPENAI,
        model="gpt-4o",
        temperature=0.7,
        max_tokens=1000,
    ),
}

# Agent-specific prompts
AGENT_PROMPTS = {
    "debt_analyst": """You are a senior credit analyst specializing in debt and leverage analysis.
Analyze the company's borrowing structure, debt sustainability, maturity profile,
interest rate risk, and overall leverage risks. Provide insights on refinancing
risk and debt servicing capacity. Be specific and quantitative in your analysis.""",
    
    "liquidity_analyst": """You are a liquidity analyst focused on short-term solvency.
Analyze the company's cash position, working capital adequacy, and ability to meet
near-term obligations. Identify any liquidity stress signals or strengths.""",
    
    "asset_quality_analyst": """You are an asset quality analyst focused on balance sheet analysis.
Evaluate asset turnover efficiency, intangibles concentration, CWIP trends,
and overall asset quality. Flag any concerns about asset impairment or idle capacity.""",
    
    "qoe_analyst": """You are a forensic accounting analyst evaluating earnings quality.
Analyze cash conversion, accruals, revenue recognition patterns, and identify
any red flags suggesting earnings management or unsustainable profitability.""",
    
    "working_capital_analyst": """You are a working capital efficiency analyst.
Analyze the company's DSO, DIO, DPO, and cash conversion cycle efficiency.
Identify opportunities for working capital optimization and any concerns.""",
    
    "equity_analyst": """You are a senior equity analyst evaluating shareholder value creation.
Analyze ROE sustainability, dividend policy, equity dilution, and funding mix.
Assess whether the company is creating or destroying shareholder value.""",
    
    "short_seller_critic": """You are a short-seller analyst looking for weaknesses.
Your job is to find holes in the bull case, identify hidden risks, and challenge
overly optimistic assumptions. Be skeptical and adversarial but fair.""",
    
    "judge": """You are an investment committee member making the final assessment.
Synthesize all analyst views, weigh the bull and bear cases, and provide a
balanced, actionable conclusion with clear reasoning.""",
}


def load_llm_config_from_yaml(path: str) -> Optional[LLMConfig]:
    """Load LLM configuration from a YAML file."""
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        
        llm_section = data.get("llm", {})
        if not llm_section:
            return None
        
        return LLMConfig(
            provider=llm_section.get("provider", "mistral"),
            model=llm_section.get("model", "mistral-large-latest"),
            api_key=llm_section.get("api_key"),
            temperature=llm_section.get("temperature", 0.7),
            max_tokens=llm_section.get("max_tokens", 1000),
        )
    except Exception as e:
        logger.warning(f"Failed to load LLM config from {path}: {e}")
        return None


def load_llm_config_from_env() -> LLMConfig:
    """Load LLM configuration from environment variables."""
    load_dotenv()   
    provider = os.getenv("LLM_PROVIDER", "mistral")
    
    # Get default config for this provider
    default = DEFAULT_CONFIGS.get(provider, DEFAULT_CONFIGS["mistral"])
    
    # Get model from env or use default
    model = os.getenv("LLM_MODEL", default.model)
    
    # Get API key based on provider
    api_key = None
    if provider == "mistral":
        api_key = os.getenv("MISTRAL_API_KEY")
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
    
    # Get optional overrides
    try:
        temperature = float(os.getenv("LLM_TEMPERATURE", str(default.temperature)))
    except ValueError:
        temperature = default.temperature
    
    try:
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", str(default.max_tokens)))
    except ValueError:
        max_tokens = default.max_tokens
    
    return LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_agent_prompt(agent_id: str) -> str:
    """Get the system prompt for an agent."""
    return AGENT_PROMPTS.get(agent_id, "You are a financial analyst.")
