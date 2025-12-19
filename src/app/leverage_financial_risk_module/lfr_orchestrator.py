from typing import Dict, Any

from .lfr_metrics import compute_per_year_metrics
from .lfr_trends import compute_trend_output
from .lfr_llm import run_lfr_llm_agent


def run_leverage_financial_risk_module(payload: Dict[str, Any]) -> Dict[str, Any]:

    company = payload["company"]
    financials = payload["financial_data"]["financial_years"]

    # STEP 1: Metrics
    per_year_metrics = compute_per_year_metrics(financials)

    latest_year = max(per_year_metrics.keys())
    latest_metrics = per_year_metrics[latest_year]

    # STEP 2: Trends
    trends = compute_trend_output(per_year_metrics)

    # STEP 3: LLM
    llm_output = run_lfr_llm_agent(
        company=company,
        metrics={
            "latest_year": latest_year,
            "latest": latest_metrics,
            "all_years": per_year_metrics,
        },
        trends=trends,
        flags=[],
    )

    return {
        "module": "LeverageFinancialRisk",
        "company": company,
        "key_metrics": latest_metrics,
        "trends": trends,
        "analysis_narrative": llm_output.get("analysis_narrative", []),
        "red_flags": llm_output.get("red_flags", []),
        "positive_points": llm_output.get("positive_points", []),
        "rules": [],
    }
