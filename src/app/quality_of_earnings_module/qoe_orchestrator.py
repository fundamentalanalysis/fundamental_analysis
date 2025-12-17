# qoe_orchestrator.py

from collections import Counter
from typing import Tuple, List, Dict, Any

from .qoe_models import QoEBenchmarks, QoEFinancialData, QoEYearInput, QualityOfEarningsInput, QualityOfEarningsOutput, RuleResult
from .qoe_metrics import compute_qoe_metrics_per_year
from .qoe_trends import compute_qoe_trend_output
from .qoe_rules import qoe_rule_engine
from .qoe_llm import run_qoe_llm_agent


def extract_year(key):
    if isinstance(key, int):
        return key
    for part in str(key).split():
        if part.isdigit():
            return int(part)
    import re
    match = re.search(r"\d{4}", str(key))
    return int(match.group()) if match else 0


class QualityOfEarningsModule:

    def __init__(self):
        print("DEBUG: Initializing QualityOfEarningsModule...")

    def run(self, input_data: QualityOfEarningsInput) -> QualityOfEarningsOutput:
        print("\n===================== QoE MODULE START =====================")
        print(f"DEBUG: Running QoE module for company: {input_data.company}")

        # -----------------------------
        # STEP 0: RAW FINANCIAL INPUT
        # -----------------------------
        financials_list = input_data.financials_5y.financial_years
        print(f"DEBUG: Raw financial years received: {len(financials_list)}")
        for f in financials_list:
            print(f"DEBUG: Year found: {f.year}")

        # -----------------------------
        # STEP 1: Compute Per-Year QoE Metrics
        # -----------------------------
        print("\n---- STEP 1: Computing QoE Per-Year Metrics ----")
        per_year_metrics = compute_qoe_metrics_per_year(financials_list)

        if not per_year_metrics:
            raise ValueError(
                "No QoE metrics computed. Check financial data fields.")

        print("DEBUG: Years with metrics:", list(per_year_metrics.keys()))
        latest_year = max(per_year_metrics.keys(), key=extract_year)
        print("DEBUG: Latest year:", latest_year)
        print("DEBUG: Latest QoE metrics:", per_year_metrics[latest_year])

        # -----------------------------
        # STEP 2: Trend Engine
        # -----------------------------
        print("\n---- STEP 2: Computing QoE Trends ----")
        try:
            trend_summary = compute_qoe_trend_output(financials_list)
            print("DEBUG: Trend summary keys:", list(trend_summary.keys()))
        except Exception as e:
            print("ERROR inside compute_qoe_trend_output:", str(e))
            raise

        # -----------------------------
        # STEP 3: Rule Engine
        # -----------------------------
        print("\n---- STEP 3: Running QoE Rule Engine ----")

        metrics_for_rules = {
            "latest_year": latest_year,
            "latest": per_year_metrics[latest_year],
            "all_years": per_year_metrics
        }

        try:
            rule_results = qoe_rule_engine(
                metrics=metrics_for_rules,
                trends=trend_summary,
                benchmarks=input_data.benchmarks
            )
        except Exception as e:
            print("ERROR inside qoe_rule_engine:", str(e))
            raise

        for r in rule_results:
            print(f"DEBUG: Rule Fired -> {r.rule_id}: {r.flag}")

        # -----------------------------
        # STEP 4: Summaries
        # -----------------------------
        print("\n---- STEP 4: Summarizing Rule Results ----")
        red_flags, positives = self._summarize(rule_results)
        print("DEBUG: Red Flags:", red_flags)
        print("DEBUG: Positives:", positives)

        # -----------------------------
        # STEP 5: Key QoE Metrics
        # -----------------------------
        print("\n---- STEP 5: Extracting Key QoE Metrics ----")
        key_metrics = self._extract_key_metrics(per_year_metrics)
        print("DEBUG: Key QoE Metrics:", key_metrics)

        deterministic_notes = self._build_narrative_notes(
            key_metrics, red_flags)
        print("DEBUG: Deterministic Notes:", deterministic_notes)

        # -----------------------------
        # STEP 6: LLM Narrative
        # -----------------------------
        print("\n---- STEP 6: Calling LLM ----")

        try:
            llm_output = run_qoe_llm_agent(
                company=input_data.company,
                metrics=metrics_for_rules,
                trends=trend_summary,
                flags=[r.to_dict() for r in rule_results],
            )
        except Exception as e:
            print("ERROR inside run_qoe_llm_agent:", str(e))
            raise

        print("DEBUG: LLM Output received.")

        # -----------------------------
        # FINAL OUTPUT
        # -----------------------------
        print("\n===================== QoE MODULE END =====================\n")

        return QualityOfEarningsOutput(
            module="QualityOfEarnings",
            company=input_data.company,
            key_metrics=key_metrics,
            trends=trend_summary,
            analysis_narrative=llm_output.get("analysis_narrative", []),
            red_flags=red_flags,
            positive_points=positives,
            rules=rule_results,
        )

    # =====================================================
    # Helper Methods
    # =====================================================

    @staticmethod
    def _summarize(rule_results: List[RuleResult]) -> Tuple[List[Dict], List[str]]:
        red_flags = []
        positives = []

        for rule in rule_results:
            if rule.flag == "RED":
                severity = "CRITICAL" if rule.rule_id in {
                    "A1", "B1"} else "RED"
                red_flags.append({
                    "module": "quality_of_earnings",
                    "severity": severity,
                    "title": rule.rule_name,
                    "detail": rule.reason,
                    "risk_category": "earnings_quality",
                })
            elif rule.flag == "GREEN":
                positives.append(f"{rule.rule_name}: {rule.reason}")

        return red_flags, positives

    @staticmethod
    def _extract_key_metrics(per_year_metrics: Dict[int, dict]) -> Dict[str, float]:
        # Determine latest year correctly
        latest_year = max(per_year_metrics.keys())
        latest = per_year_metrics[latest_year]

        return {
            "year": latest_year,
            "qoe": latest.get("qoe"),
            "accruals_ratio": latest.get("accruals_ratio"),
            "operating_cash_flow": latest.get("operating_cash_flow"),
            "net_income": latest.get("net_income"),
            "revenue_quality": latest.get("revenue_quality"),   # OCF / Revenue
            "dso": latest.get("dso"),
            "other_income_ratio": latest.get("other_income_ratio"),
        }

    @staticmethod
    def _build_narrative_notes(key_metrics, red_flags):
        notes = []

        # QoE ratio
        if key_metrics.get("qoe") is not None:
            notes.append(f"QoE Ratio = {key_metrics['qoe']:.2f}")

        # Revenue Quality (OCF / Revenue)
        if key_metrics.get("revenue_quality") is not None:
            notes.append(f"OCF/Revenue = {key_metrics['revenue_quality']:.2f}")

        # Accruals Ratio
        if key_metrics.get("accruals_ratio") is not None:
            notes.append(
                f"Accruals Ratio = {key_metrics['accruals_ratio']:.3f}")

        # Include top 2 red flags if present
        if red_flags:
            notes.append("Key concerns: " +
                         ", ".join(x["title"] for x in red_flags[:2]))

        return notes


# Wrapper function
def run_quality_of_earnings_module(payload: dict):
    print("\n\n******** QoE MODULE INVOKED ********")
    print("DEBUG: Incoming payload keys:", payload.keys())

    try:
        module = QualityOfEarningsModule()
        financial_years = [
            QoEYearInput(**fy)
            for fy in payload["financials_5y"]
        ]
        print("DEBUG: Parsed financial years:", [f for f in financial_years])

        financial_data = QoEFinancialData(
            financial_years=financial_years
        )

        benchmarks = QoEBenchmarks()
        qoe_input = QualityOfEarningsInput(
            company=payload["company"],
            industry_code=payload.get("industry_code", "GENERAL"),
            financials_5y=financial_data,
            benchmarks=benchmarks

        )

        # input_data = QualityOfEarningsInput(**payload)

        print("DEBUG: Input parsed successfully. Running QoE module...")
        result = module.run(qoe_input)
        print("DEBUG: QoE module execution successful.")
        return result.dict()

    except Exception as e:
        import traceback
        print("******** ERROR OCCURRED ********")
        print("ERROR:", str(e))
        print("TRACEBACK:\n", traceback.format_exc())
        raise
