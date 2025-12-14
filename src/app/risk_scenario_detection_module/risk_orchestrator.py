# risk_orchestrator.py
import asyncio
from typing import Dict, Any, List

from src.app.config import get_llm_client
from .risk_models import YearFinancials
from .risk_metrics import compute_derived_metrics
from .risk_rules import RiskRulesEngine
from .risk_insight_fallback import generate_fallback_narrative
from .risk_config import DEFAULT_THRESHOLDS , manual_vals

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
            print("Input financial data with manual RPT values:", fin_objs)
            
        except Exception as e:
            return {"error": "input_validation_failed", "details": str(e)}

        derived = [compute_derived_metrics(y) for y in years_raw]
        fin_objs = [YearFinancials(**d) for d in derived]
        print("Derived financial data:", fin_objs)

        thresholds = {**DEFAULT_THRESHOLDS, **(payload.get("scenario_thresholds") or {})}

        engine = RiskRulesEngine(thresholds)
        rules_results = engine.evaluate(fin_objs)
        rules_serialized = [r.dict() for r in rules_results]



        # Key metrics
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

        # -------- FIXED TREND CALCULATION (NO MORE NoneType ERRORS) --------
        def safe_num(v):
            return 0 if v is None else v

        def build_trend(key):
            raw_values = [y.get(key) for y in derived]
            values = [safe_num(v) for v in raw_values]   # <-- FIX HERE

            labels = {}
            for idx, val in enumerate(reversed(values)):
                labels["Y" if idx == 0 else f"Y-{idx}"] = val

            yoy = {}
            for i in range(1, len(values)):
                prev = safe_num(values[i - 1])
                curr = safe_num(values[i])
                if prev == 0:
                    pct = None
                else:
                    pct = ((curr - prev) / abs(prev)) * 100
                yoy[f"Y-{i-1}_vs_Y-{i}"] = pct

            return {
                "values": labels,
                "yoy_growth_pct": yoy,
                "insight": f"{key} shows YoY changes and patterns."
            }

        trends_keys = [
            "cash_equivalents", "trade_receivables", "total_assets",
            "operating_cash_flow"
        ]
        trends = {k: build_trend(k) for k in trends_keys}

        # Red flags / Positive
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

        summary_color = "RED" if scenario_score >= 70 else "YELLOW" if scenario_score >= 40 else "GREEN"
        # LLM Narrative or fallback
        # if self.llm_client:
        from .risk_llm import RiskScenarioAgentLLM
        llm_agent = RiskScenarioAgentLLM()
        try:
            narrative = [await llm_agent.interpret(rules_serialized, red_flags=red_flags)]
            print("LLM-generated narrative:", narrative)
        except Exception:
            narrative = generate_fallback_narrative(rules_serialized)
            print("Fallback narrative used due to LLM error.")
        # else:
        #     narrative = generate_fallback_narrative(rules_serialized)
        return {
            "module": "RiskScenarioDetection",
            "sub_score_adjusted": scenario_score,
            "key_metrics": key_metrics,
            "trends": trends,
            "analysis_narrative": narrative,
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
