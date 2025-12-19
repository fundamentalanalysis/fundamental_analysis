from app.risk_scenario_detection_module.risk_models import RiskScenarioInput, YearRiskFinancialInput
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

risk_engine = RiskScenarioDetectionModule()

def run_risk_scenario_detection_module(req_data):
    
    financial_years = [
            YearRiskFinancialInput(
        year=fy["year"],
        revenue=fy["revenue"],
        operating_profit=fy["operating_profit"],
        interest=fy["interest"],
        net_profit=fy["net_profit"],
        other_income=fy.get("other_income", 0.0),
        depreciation=fy.get("depreciation", 0.0),  # ✅ ADD THIS

        borrowings=fy["borrowings"],
        lease_liabilities=fy.get("lease_liabilities", 0.0),
        fixed_assets=fy["fixed_assets"],
        total_assets=fy["total_assets"],
        trade_receivables=fy["trade_receivables"],
        cash_equivalents=fy["cash_equivalents"],

        cash_from_operating_activity=fy["cash_from_operating_activity"],
        dividends_paid=fy.get("dividends_paid", 0.0),
        proceeds_from_borrowings=fy.get("proceeds_from_borrowings", 0.0),
        repayment_of_borrowings=fy.get("repayment_of_borrowings", 0.0),
    )

        for fy in req_data["financial_data"]["financial_years"]
    ]

    module_input = RiskScenarioInput(
        company_id=req_data["company"].upper(),
        industry_code=req_data.get("industry_code", "GENERAL").upper(),
        financials_5y=financial_years,
    )

    result = risk_engine.run(module_input)
    return result