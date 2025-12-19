
from .risk_metrics import compute_per_year_metrics
from .risk_trend import compute_trends
from .risk_rules import apply_rules
from .risk_llm import generate_llm_narrative


class RiskScenarioDetectionModule:
    def __init__(self):
        pass

    def run(self, inp):
        # -----------------------------
        # Deterministic layers
        # -----------------------------
        metrics = compute_per_year_metrics(inp.financials_5y)
        trends = compute_trends(metrics)
        rules = apply_rules(metrics, trends)

        # -----------------------------
        # LLM layer (✅ FIXED)
        # -----------------------------
        narrative = generate_llm_narrative(
            inp.company_id,
            trends,
            rules,   # ✅ REQUIRED ARGUMENT
        )

        latest_year = max(metrics.keys())
        m = metrics[latest_year]

        return {
            "module": "RiskScenarioDetection",
            "company": inp.company_id,

            "key_metrics": {
                "year": latest_year,
                "interest_coverage_cash": (
                    m["cfo"] / m["interest"] if m["interest"] else None
                ),
                "interest_coverage_ebit": (
                    m["ebit"] / m["interest"] if m["interest"] else None
                ),
                "net_debt": m["net_debt"],
                "cash_flow_deficit": m["cfo"] < m["interest"],
            },

            "trends": trends,

            "scenarios_detected": [
                {
                    "scenario": r.rule_name,
                    "severity": r.flag,
                    "detail": r.reason,
                }
                for r in rules
            ],

            "analysis_narrative": narrative,
            "rules": [r.dict() for r in rules],
        }
