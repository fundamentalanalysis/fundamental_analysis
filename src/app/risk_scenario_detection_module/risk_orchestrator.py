from .risk_config import load_risk_config
from .risk_metrics import compute_per_year_metrics
from .risk_trend import compute_trends
from .risk_rules import apply_rules
from .risk_llm import generate_llm_narrative


class RiskScenarioDetectionModule:
    def __init__(self):
        self.cfg = load_risk_config()

    def run(self, inp):
        metrics = compute_per_year_metrics(inp.financials_5y)
        trends = compute_trends(metrics)
        rules = apply_rules(metrics, trends, self.cfg)

        score = max(0, 100 - 10 * len(rules))
        narrative = generate_llm_narrative(inp.company_id, trends)


        latest_year = max(metrics.keys())
        m = metrics[latest_year]

        return {
            "module": "RiskScenarioDetection",
            "company": inp.company_id,

            "key_metrics": {
                "year": latest_year,
                "interest_coverage_cash": m["cfo"] / m["interest"] if m["interest"] else None,
                "interest_coverage_ebit": m["ebit"] / m["interest"] if m["interest"] else None,
                "net_debt": m["net_debt"],
                "cash_flow_deficit": m["cfo"] < m["interest"],
            },

            "trends": trends,

            "scenarios_detected": [
                {"scenario": r.rule_name, "severity": r.flag, "detail": r.reason}
                for r in rules
            ],

            "analysis_narrative": narrative,
            "rules": [r.dict() for r in rules],
        }