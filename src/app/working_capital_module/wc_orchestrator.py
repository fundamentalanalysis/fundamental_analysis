from collections import Counter
from typing import Tuple, List, Dict, Any

from .wc_models import WorkingCapitalInput, WorkingCapitalOutput, RuleResult, WorkingCapitalBenchmarks
from .wc_metrics import compute_per_year_metrics
from .wc_trend import compute_trend_output
from .wc_rules import wc_rule_engine
from .wc_llm import run_wc_llm_agent


def extract_year(key):
    if isinstance(key, int):
        return key
    for part in str(key).split():
        if part.isdigit():
            return int(part)
    import re
    match = re.search(r"\d{4}", str(key))
    return int(match.group()) if match else 0


class WorkingCapitalModule:
    def __init__(self, benchmarks: WorkingCapitalBenchmarks = None):
        print("DEBUG: Initializing WorkingCapitalModule...")
        self.benchmarks = benchmarks or WorkingCapitalBenchmarks()

    def run(self, input_data: WorkingCapitalInput) -> WorkingCapitalOutput:
        print("\n===================== WC MODULE START =====================")
        print(f"DEBUG: Running WC module for company: {input_data.company}")

        # -----------------------------
        # STEP 0: RAW FINANCIAL INPUT
        # -----------------------------
        financials_list = input_data.financial_data.financial_years
        print(f"DEBUG: Raw financial years received: {len(financials_list)}")
        for f in financials_list:
            print(f"DEBUG: Year found: {f.year}")

        # -----------------------------
        # STEP 1: Compute Per-Year Metrics
        # -----------------------------
        print("\n---- STEP 1: Computing Per-Year Metrics ----")
        per_year_metrics = compute_per_year_metrics(financials_list)

        if not per_year_metrics:
            print("ERROR: compute_per_year_metrics returned EMPTY!")
            raise ValueError(
                "No metrics computed. Check if financial data is valid and contains required fields."
            )

        print(f"DEBUG: per_year_metrics years: {list(per_year_metrics.keys())}")
        latest_year = max(per_year_metrics.keys(), key=extract_year)
        print(f"DEBUG: Latest year: {latest_year}")
        print(f"DEBUG: Latest metrics: {per_year_metrics[latest_year]}")

        # -----------------------------
        # STEP 2: Trend Engine
        # -----------------------------
        print("\n---- STEP 2: Computing Trend Summary ----")
        try:
            trend_summary = compute_trend_output(financials_list)
            print("DEBUG: Trend summary keys:", list(trend_summary.keys()))
            for k, v in trend_summary.items():
                print(f"DEBUG: Trend sample for {k}: {v}")
        except Exception as e:
            print("ERROR inside compute_trend_output:", str(e))
            raise

        # -----------------------------
        # STEP 3: Rule Engine
        # -----------------------------
        print("\n---- STEP 3: Running Rule Engine ----")
        metrics_for_rules = {
            "latest_year": latest_year,
            "latest": per_year_metrics[latest_year],
            "all_years": per_year_metrics  # helpful for LLM prompts
        }

        print("DEBUG: metrics_for_rules (LLM format):", metrics_for_rules)
        print("DEBUG: metrics_for_rules:", metrics_for_rules)
        print("DEBUG: Passing trends to rule engine:", trend_summary)

        try:
            rule_results = wc_rule_engine(
                metrics=metrics_for_rules,
                trends=trend_summary,
                rules=self.benchmarks,
            )
        except Exception as e:
            print("ERROR inside wc_rule_engine:", str(e))
            raise

        # print("DEBUG: Rule results count:", len(rule_ressults))
        for r in rule_results:
            print(f"DEBUG: Rule Fired -> {r.rule_id}: {r.flag}")

        # -----------------------------
        # STEP 4: Summarize flags (CRITICAL/HIGH + positives)
        # -----------------------------
        print("\n---- STEP 4: Summarizing Rule Results ----")
        red_flags, positives = self._summarize(rule_results)
        print("DEBUG: Red flags (summary dicts):", red_flags)
        print("DEBUG: Positives:", positives)

        # -----------------------------
        # STEP 5: Key Metrics & Deterministic Notes
        # -----------------------------
        print("\n---- STEP 5: Extracting Key Metrics & Notes ----")
        key_metrics = self._extract_key_metrics(per_year_metrics, trend_summary)
        print("DEBUG: Key Metrics:", key_metrics)

        deterministic_notes = self._build_narrative_notes(
            key_metrics, trend_summary, red_flags
        )
        print("DEBUG: Deterministic Notes:", deterministic_notes)

        # -----------------------------
        # STEP 6: LLM Narrative
        # -----------------------------
        print("\n---- STEP 6: Calling LLM ----")
        try:
            llm_output = run_wc_llm_agent(
                company=input_data.company,
                metrics=metrics_for_rules,
                trends=trend_summary,
                flags=[r.to_dict() for r in rule_results],
            )
        except Exception as e:
            print("ERROR inside run_wc_llm_agent:", str(e))
            raise

        print("DEBUG: LLM Output received.")
        print("DEBUG: LLM Narrative:", llm_output.get("analysis_narrative"))

        # -----------------------------
        # FINAL OUTPUT
        # -----------------------------
        print("\n===================== WC MODULE END =====================\n")

        return WorkingCapitalOutput(
            module="WorkingCapital",
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
        red_flags: List[Dict[str, Any]] = []
        positives: List[str] = []

        for rule in rule_results:
            if rule.flag == "RED":
                severity = "CRITICAL" if rule.rule_id in {"D1", "E1"} else "HIGH"
                red_flags.append(
                    {
                        "severity": severity,
                        "title": rule.rule_name,
                        "detail": rule.reason,
                    }
                )
            elif rule.flag == "GREEN":
                positives.append(f"{rule.rule_name}: {rule.reason}")

        return red_flags, positives

    @staticmethod
    def _extract_key_metrics(
        per_year_metrics: Dict[int, dict], trend_summary: Dict[str, Any]
    ) -> Dict[str, float]:
        if not per_year_metrics:
            return {}

        latest_year = max(per_year_metrics.keys(), key=extract_year)
        latest = per_year_metrics[latest_year]

        return {
            "year": latest_year,
            "dso": latest.get("dso"),
            "dio": latest.get("dio"),
            "dpo": latest.get("dpo"),
            "ccc": latest.get("ccc"),
            "nwc_ratio": latest.get("nwc_ratio"),
            "revenue": latest.get("revenue"),
            "nwc": latest.get("nwc"),
        }

    @staticmethod
    def _build_narrative_notes(
        key_metrics: Dict[str, float],
        trends: Dict[str, Any],
        red_flags: List[Dict[str, Any]],
    ) -> List[str]:
        notes: List[str] = []
        if key_metrics.get("ccc") is not None:
            notes.append(f"Cash Conversion Cycle is {key_metrics['ccc']:.1f} days.")
        if key_metrics.get("dso") is not None:
            notes.append(f"DSO is {key_metrics['dso']:.1f} days.")
        if red_flags:
            notes.append(
                "Key concerns: "
                + ", ".join(flag["title"] for flag in red_flags[:2])
                + "."
            )
        return notes


# ========= WRAPPER FUNCTION WITH DEBUG LOGS =========


def run_working_capital_module(payload: dict):
    print("\n\n******** WC MODULE INVOKED ********")
    print("DEBUG: Incoming payload keys:", payload.keys())

    try:
        module = WorkingCapitalModule()
        input_data = WorkingCapitalInput(**payload)
        print("DEBUG: Input data parsed successfully. Running module...")

        result = module.run(input_data)
        print("DEBUG: Module execution successful.")
        return result.dict()
    except Exception as e:
        import traceback

        print("******** ERROR OCCURRED ********")
        print("ERROR:", str(e))
        print("TRACEBACK:\n", traceback.format_exc())
        raise
