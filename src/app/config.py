# import os

# from dotenv import load_dotenv

# try:
#     from openai import OpenAI
# except ImportError:
#     OpenAI = None

# load_dotenv()

# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")   # safer default


# def get_llm_client():
#     # If no API key, return None → fallback
#     if not OPENAI_API_KEY:
#         return None

#     # New OpenAI client — key auto-loaded from env
#     return OpenAI()

# # config.py

# DEFAULT_CAPEX_CWIP_RULES = {
#     "capex_intensity_high": 0.15,
#     "capex_intensity_moderate": 0.10,

#     "cwip_pct_critical": 0.40,
#     "cwip_pct_warning": 0.30,

#     "asset_turnover_critical": 0.7,
#     "asset_turnover_low": 1.0,

#     "capex_vs_revenue_gap_warning": 0.10,
#     "cwip_growth_warning": 0.25,

#     "debt_funded_capex_warning": 0.50
# }
import os
from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")   # safer default


def get_llm_client():
    # If no API key, return None → fallback
    if not OPENAI_API_KEY:
        return None
    return OpenAI()


# ======================================================
# CAPEX / CWIP RULES
# ======================================================
DEFAULT_CAPEX_CWIP_RULES = {
    "capex_intensity_high": 0.15,
    "capex_intensity_moderate": 0.10,

    "cwip_pct_critical": 0.40,
    "cwip_pct_warning": 0.30,

    "asset_turnover_critical": 0.7,
    "asset_turnover_low": 1.0,

    "capex_vs_revenue_gap_warning": 0.10,
    "cwip_growth_warning": 0.25,

    "debt_funded_capex_warning": 0.50
}


# ======================================================
# LEVERAGE & FINANCIAL RISK RULES  ✅ ADD THIS
# ======================================================
DEFAULT_LEVERAGE_FINANCIAL_RULES = {
    "de_ratio_high": 2.0,
    "de_ratio_critical": 3.0,

    "debt_ebitda_high": 4.0,
    "debt_ebitda_critical": 5.0,

    "net_debt_ebitda_warning": 4.0,
    "net_debt_ebitda_critical": 5.5,

    "icr_low": 2.0,
    "icr_critical": 1.0,

    "st_debt_ratio_warning": 0.40,
    "st_debt_ratio_critical": 0.50,

    "leverage_rising_years": 3
}
