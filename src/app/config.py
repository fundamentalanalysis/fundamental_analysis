0# src/app/config.py

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


def get_llm_client():


    return OpenAI(api_key=OPENAI_API_KEY)

WORKING_CAPITAL_RULES = {
    "dso_high": 75,
    "dso_moderate": 60,

    "dio_high": 120,
    "dio_moderate": 90,

    "dpo_high": 90,
    "dpo_low": 30,

    "critical_ccc": 180,
    "moderate_ccc": 120,

    "nwc_revenue_critical_ratio": 0.25,
    "nwc_revenue_moderate_ratio": 0.15,

    "receivable_growth_threshold": 0.20,
    "inventory_growth_threshold": 0.20
}
