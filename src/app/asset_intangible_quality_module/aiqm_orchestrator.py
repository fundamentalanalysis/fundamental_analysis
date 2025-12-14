from typing import Tuple, List, Dict, Any

from .aiqm_models import (
    AssetIntangibleInput,
    AssetIntangibleOutput,
    RuleResult,
    AssetIntangibleBenchmarks,
    FinancialDataBlock,
)

from .aiqm_metrics import compute_per_year_metrics
from .aiqm_trend import compute_aiqm_trends
from .aiqm_rules import aiqm_rule_engine
from .aiqm_llm import run_aiqm_llm_agent


def extract_year(key):
    if isinstance(key, int):
        return key

    for part in str(key).split():
        if part.isdigit():
            return int(part)

    import re
    match = re.search(r"\d{4}", str(key))
    return int(match.group()) if match else 0


# =============================================================
# ASSET & INTANGIBLE QUALITY MODULE ORCHESTRATOR
# =============================================================

class AssetIntangibleQualityModule:
    def __init__(self, benchmarks: AssetIntangibleBenchmarks = None):
        print("DEBUG: Initializing AssetIntangibleQualityModule...")
        self.benchmarks = benchmarks or AssetIntangibleBenchmarks()

    # ------------------------------------------------------
    # MAIN MODULE RUNNER
    # ------------------------------------------------------
    def run(self, input_data: AssetIntangibleInput) -> AssetIntangibleOutput:
        print("\n===================== AIQM MODULE START =====================")
        print(f"DEBUG: Running AIQM module for company: {input_data.company}")

        # -------------------------
        # STEP 0: RAW INPUT
        # -------------------------
        financials_list = input_data.financial_data.financial_years

        print(f"DEBUG: Raw financial years received: {len(financials_list)}")
        for f in financials_list:
            print(f"DEBUG: Year found: {f.year}")

        # -------------------------
        # STEP 1: PER-YEAR METRICS
        # -------------------------
        print("\n---- STEP 1: Computing Per-Year Metrics ----")
        per_year_metrics = compute_per_year_metrics(financials_list)

        if not per_year_metrics:
            raise ValueError("ERROR: No metrics generated. Please verify input data.")

        latest_year = max(per_year_metrics.keys(), key=extract_year)
        latest_metrics = per_year_metrics[latest_year]

        print(f"DEBUG: Latest year: {latest_year}")
        print(f"DEBUG: Latest metrics: {latest_metrics}")

        # -------------------------
        # STEP 2: TREND ENGINE
        # -------------------------
        print("\n---- STEP 2: Computing Trends ----")
        trend_summary = compute_aiqm_trends(financials_list)
        print("DEBUG: Trend Summary Keys:", list(trend_summary.keys()))

        # -------------------------
        # STEP 3: RULE ENGINE INPUT PREP
        # -------------------------
        latest_metrics["revenue_growth_yoy"] = \
            trend_summary["revenue"]["yoy_growth_pct"].get("Y_vs_Y-1")

        latest_metrics["intangible_growth_yoy"] = \
            trend_summary["intangible_assets"]["yoy_growth_pct"].get("Y_vs_Y-1")

        latest_metrics["operating_asset_growth"] = \
            trend_summary["cagr"].get("operating_asset_cagr")

        # Goodwill YoY
        latest_metrics["goodwill_growth_yoy"] = (
            trend_summary.get("goodwill", {})
            .get("yoy_growth_pct", {})
            .get("Y_vs_Y-1")
        )

        # Impairment YoY
        latest_metrics["impairment_yoy"] = (
            trend_summary.get("impairment", {})
            .get("yoy_growth_pct", {})
            .get("Y_vs_Y-1")
        )

        metrics_for_rules = {
            "latest_year": latest_year,
            "latest": latest_metrics,
            "all_years": per_year_metrics,
        }

        # -------------------------
        # STEP 3B: RULE ENGINE
        # -------------------------
        rule_results = aiqm_rule_engine(
            metrics_for_rules, trend_summary, self.benchmarks
        )

        # -------------------------
        # STEP 4: SUMMARY FLAGS
        # -------------------------
        red_flags, positives = self._summarize(rule_results)

        # -------------------------
        # STEP 5: KEY METRICS
        # -------------------------
        key_metrics = self._extract_key_metrics(per_year_metrics)

        # -------------------------
        # STEP 6: LLM NARRATIVE
        # -------------------------
        llm_output = run_aiqm_llm_agent(
            company=input_data.company,
            metrics=metrics_for_rules,
            trends=trend_summary,
            flags=[r.to_dict() for r in rule_results],
        )

        print("\n===================== AIQM MODULE END =====================\n")

        return AssetIntangibleOutput(
            module="AssetIntangibleQuality",
            company=input_data.company,
            key_metrics=key_metrics,
            trends=trend_summary,
            analysis_narrative=llm_output.get("analysis_narrative", []),
            red_flags=red_flags,
            positive_points=positives,
            rules=rule_results,
        )

    # =====================================================
    # INTERNAL HELPERS
    # =====================================================

    @staticmethod
    def _summarize(rule_results: List[RuleResult]):
        red_flags = []
        positives = []

        for rule in rule_results:
            if rule.flag == "RED":
                severity = "CRITICAL" if rule.rule_id in {"D1", "C1"} else "HIGH"
                red_flags.append({
                    "severity": severity,
                    "title": rule.rule_name,
                    "detail": rule.reason,
                })
            elif rule.flag == "GREEN":
                positives.append(f"{rule.rule_name}: {rule.reason}")

        return red_flags, positives

    @staticmethod
    def _extract_key_metrics(per_year_metrics: Dict[int, dict]):
        latest_year = max(per_year_metrics.keys())
        latest = per_year_metrics[latest_year]

        return {
            "year": latest_year,
            "asset_turnover": latest.get("asset_turnover"),
            "asset_age_proxy": latest.get("asset_age_proxy"),
            "intangible_pct_total": latest.get("intangible_pct_total_assets"),
            "intangible_growth": latest.get("intangible_growth_yoy"),
            "amortization_ratio": latest.get("amortization_ratio"),
            "r_and_d_ratio": latest.get("r_and_d_intangible_ratio"),
            "revenue": latest.get("revenue"),
            "intangibles": latest.get("intangibles"),
        }


# --------------------------------------------------------
# PUBLIC WRAPPER — REQUIRED FOR IMPORT
# --------------------------------------------------------

def run_aiqm_module(payload: dict):
    module = AssetIntangibleQualityModule()
    input_data = AssetIntangibleInput(**payload)
    return module.run(input_data).dict()
