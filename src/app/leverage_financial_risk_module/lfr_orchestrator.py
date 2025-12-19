# lfr_orchestrator.py

from typing import Dict, Any
import copy

from .lfr_models import (
    YearLeverageInput,
    LeverageBenchmarks,
    LeverageFinancialRiskOutput,
)
from .lfr_metrics import compute_per_year_metrics
from .lfr_trends import compute_leverage_trends
from .lfr_rules import lfr_rule_engine
from .lfr_llm import run_lfr_llm_agent   # ✅ NEW


def run_leverage_financial_risk_module(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestrator entrypoint
    Accepts RAW request dict (from FastAPI)
    """

    company = payload["company"]

    # -----------------------------
    # RAW → MODELS
    # -----------------------------
    financial_years = [
        YearLeverageInput(**fy)
        for fy in payload["financial_data"]["financial_years"]
    ]

    benchmarks = (
        LeverageBenchmarks(**payload["benchmarks"])
        if "benchmarks" in payload
        else LeverageBenchmarks()
    )

    # -----------------------------
    # METRICS (SINGLE SOURCE)
    # -----------------------------
    per_year = compute_per_year_metrics(financial_years)
    latest_year = max(per_year.keys())

    # 🚨 CRITICAL FIX:
    # Rules must NEVER mutate per_year
    per_year_for_rules = copy.deepcopy(per_year)

    metrics_for_rules = {
        "latest_year": latest_year,
        "latest": per_year_for_rules[latest_year],
        "all_years": per_year_for_rules,
    }

    # -----------------------------
    # RULES (DETERMINISTIC)
    # -----------------------------
    rules = lfr_rule_engine(metrics_for_rules, benchmarks)

    # -----------------------------
    # TRENDS (DETERMINISTIC)
    # -----------------------------
    trends = compute_leverage_trends(per_year)

    # -----------------------------
    # LLM / INTERPRETATION LAYER
    # -----------------------------
    llm_output = run_lfr_llm_agent(
        company=company,
        key_metrics=per_year[latest_year],
        trends=trends,
        rules=rules,
    )

    # -----------------------------
    # FINAL OUTPUT
    # -----------------------------
    output = LeverageFinancialRiskOutput(
        company=company,
        key_metrics=per_year[latest_year],
        trends=trends,
        analysis_narrative=llm_output["analysis_narrative"],
        positive_points=llm_output["positive_points"],
        red_flags=llm_output["red_flags"],
        rules=rules,
    )

    return output.dict()
