# src/app/config/__init__.py

from .config_loader import ConfigLoader, get_config_loader, ModuleConfig, GlobalConfig

# Re-export from the parent config.py for backward compatibility
import os
from dotenv import load_dotenv
from openai import OpenAI
import yaml
from pathlib import Path

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


def get_llm_client():
    return OpenAI(api_key=OPENAI_API_KEY)


# ---------------------------------------------------------
# SIMPLE CONFIG LOADING FUNCTIONS (for new GenericAgent)
# ---------------------------------------------------------

_config_cache = None

def load_agents_config() -> dict:
    """Load the full agents_config.yaml as a dictionary"""
    global _config_cache
    if _config_cache is None:
        config_path = Path(__file__).parent / "agents_config.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            _config_cache = yaml.safe_load(f)
    return _config_cache


def get_module_config(module_id: str) -> dict:
    """Get configuration for a specific module"""
    config = load_agents_config()
    return config.get("modules", {}).get(module_id, None)


def reload_config():
    """Force reload of configuration (clears cache)"""
    global _config_cache
    _config_cache = None
    return load_agents_config()


__all__ = [
    'ConfigLoader',
    'get_config_loader',
    'ModuleConfig',
    'GlobalConfig',
    'OPENAI_API_KEY',
    'OPENAI_MODEL',
    'get_llm_client',
    'load_agents_config',
    'get_module_config',
    'reload_config',
]
