# src/app/config/__init__.py

from .config_loader import ConfigLoader, get_config_loader, ModuleConfig, GlobalConfig

# Re-export from the parent config.py for backward compatibility
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


def get_llm_client():
    return OpenAI(api_key=OPENAI_API_KEY)


__all__ = [
    'ConfigLoader', 
    'get_config_loader', 
    'ModuleConfig', 
    'GlobalConfig',
    'OPENAI_API_KEY',
    'OPENAI_MODEL',
    'get_llm_client',
]
