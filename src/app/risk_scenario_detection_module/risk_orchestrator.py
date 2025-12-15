# risk_orchestrator.py
import asyncio
from typing import Dict, Any, List

from src.app.config import get_llm_client
from .risk_models import YearFinancials
from .risk_metrics import compute_derived_metrics
from .risk_rules import RiskRulesEngine
from .risk_insight_fallback import generate_fallback_narrative
from .risk_config import DEFAULT_THRESHOLDS, manual_vals
from .risk_trend import RiskTrendAnalyzer
from .risk_llm import RiskScenarioAgentLLM


class RiskOrchestrator:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            years_raw = payload.get("financial_data", {}).get("financial_years", [])
            fin_objs: List[YearFinancials] = []

            for idx, y in enumerate(years_raw):
                y["related_party_sales"] = manual_vals["related_party_sales"][idx]
                y["related_party_receivables"] = manual_vals["related_party_receivables"][idx]
                y["ebit"] = y.get("operating_profit")
                y["net_debt"] = y.get("borrowings")

                fin_objs.append(YearFinancials(**y))

            # print("Input financial data with manual RPT values:", fin_objs)

        except Exception as e:
            return {"error": "input_validation_failed", "details": str(e)}

        # DERIVED FINANCIALS
        derived = [compute_derived_metrics(y) for y in years_raw]
        fin_objs = [YearFinancials(**d) for d in derived]

        # print("Derived financial data:", fin_objs)

        # RULE ENGINE
        thresholds = {**DEFAULT_THRESHOLDS, **(payload.get("scenario_thresholds") or {})}
        engine = RiskRulesEngine(thresholds)
        rules_results = engine.evaluate(fin_objs)
        rules_serialized = [r.dict() for r in rules_results]
        print("Rules results:", rules_serialized)
        # KEY METRICS
        last = derived[-1]
        key_metrics = {
            "year": last.get("year"),
            "cash": last.get("cash_equivalents"),
            "ocf": last.get("operating_cash_flow"),
            "net_debt": last.get("net_debt"),
            "fixed_assets": last.get("fixed_assets"),
            "related_party_sales": last.get("related_party_sales"),
            "related_party_receivables": last.get("related_party_receivables"),
        }

        # -------------------------------------
        # TREND ARRAYS (MOVED TO CORRECT PLACE)
        # -------------------------------------

        ebit_arr = [y.get("ebit") for y in derived]
        interest_arr = [y.get("interest") for y in derived]
        ocf_arr = [y.get("operating_cash_flow") for y in derived]
        net_debt_arr = [y.get("net_debt") for y in derived]
        net_income_arr = [y.get("net_profit") for y in derived]

        cash_arr = [y.get("cash_equivalents") for y in derived]
        revenue_arr = [y.get("revenue") for y in derived]
        oneoff_arr = [y.get("other_income") for y in derived]

        fixed_assets_arr = [y.get("fixed_assets") for y in derived]
        dividend_arr = [y.get("dividends_paid") for y in derived]

        rollover_arr = [y.get("loan_rollover_amount") for y in derived]
        int_cap_arr = [y.get("interest_capitalized") for y in derived]
        principal_repayment_arr = [y.get("principal_repayment") for y in derived]

        rpt_sales_arr = [y.get("related_party_sales") for y in derived]
        rpt_recv_arr = [y.get("related_party_receivables") for y in derived]
        total_sales_arr = [y.get("revenue") for y in derived]
        total_recv_arr = [y.get("trade_receivables") for y in derived]

        # -----------------------------
        # YoY GROWTH FUNCTION (FIXED)
        # -----------------------------
        def yoy_growth(arr):
            if len(arr) < 2 or arr[-2] == 0:
                return 0
            return (arr[-1] - arr[-2]) / arr[-2]

        receivable_growth_val = yoy_growth(total_recv_arr)
        revenue_growth_val = yoy_growth(total_sales_arr)

        # ---------------------------------
        # BUILD ALL TRENDS (NO ERRORS NOW)
        # ---------------------------------
        trends = {
            "zombie_company_metrics": RiskTrendAnalyzer.zombie_signals(
                ebit_arr, interest_arr, ocf_arr, net_debt_arr, net_income_arr
            ),
            "window_dressing_metrics": RiskTrendAnalyzer.window_dressing(
                cash_arr, net_income_arr, oneoff_arr, total_recv_arr
            ),
            "asset_stripping_metrics": RiskTrendAnalyzer.asset_stripping(
                fixed_assets_arr, net_debt_arr, dividend_arr
            ),
            "loan_evergreening_metrics": RiskTrendAnalyzer.loan_evergreening(
                rollover_arr, net_debt_arr, int_cap_arr, interest_arr, principal_repayment_arr
            ),
            "circular_trading_rpt_fraud_metrics": RiskTrendAnalyzer.circular_trading(
                rpt_sales_arr,
                rpt_recv_arr,
                total_sales_arr,
                ocf_arr,
                receivable_growth_val,
                revenue_growth_val
            )
        }

        # RED FLAGS / POSITIVES
        red_flags = []
        positive_points = []
        severity_rank = {"GREEN": 0, "YELLOW": 1, "HIGH": 2, "RED": 3, "CRITICAL": 4}

        for r in rules_serialized:
            f = r.get("flag")
            if f in ("CRITICAL", "RED", "HIGH"):
                red_flags.append({
                    "severity": "CRITICAL" if f in ("CRITICAL", "RED") else "HIGH",
                    "title": r.get("rule_name"),
                    "detail": r.get("reason") or r.get("pattern_detected")
                })
            else:
                positive_points.append(f"{r.get('rule_name')}: {r.get('reason')}")

        total = sum(severity_rank.get(r.get("flag"), 0) for r in rules_serialized)
        max_possible = max(1, len(rules_serialized) * max(severity_rank.values()))
        scenario_score = int(round(total / max_possible * 100))

        summary_color = (
            "RED" if scenario_score >= 70
            else "YELLOW" if scenario_score >= 40
            else "GREEN"
        )

        # LLM Narrative
        narratives = []
        llm_agent = RiskScenarioAgentLLM()

        try:
            narrative = await llm_agent.interpret(rules_serialized, red_flags=red_flags)
            narratives = [narrative]
        except Exception:
            narratives = generate_fallback_narrative(rules_serialized)
            print("Fallback narrative used due to LLM error.")

        # FINAL RESPONSE
        return {
            "module": "RiskScenarioDetection",
            "sub_score_adjusted": scenario_score,
            "key_metrics": key_metrics,
            "trends": trends,
            "analysis_narrative": narratives,
            "red_flags": red_flags,
            "positive_points": positive_points,
            "rules": rules_serialized,
            "summary_color": summary_color,
            "scenario_score": scenario_score,
            "scenarios_detected": [
                {
                    "scenario": r.get("rule_name"),
                    "severity": r.get("flag"),
                    "detail": r.get("reason")
                } for r in rules_serialized
            ]
        }
