from collections import Counter
from typing import Tuple, List, Dict

from .borrowings_config import load_rule_config, BorrowingsRuleConfig
from .debt_llm import generate_llm_narrative
from .debt_metrics import compute_per_year_metrics
from .debt_models import BorrowingsInput, BorrowingsOutput, RuleResult
from .debt_rules import apply_rules
from .debt_trend import compute_trend_metrics
from .debt_insight_fallback import generate_fallback_insight


class BorrowingsModule:
    def __init__(self, rule_config: BorrowingsRuleConfig = None):
        self.rule_config = rule_config or load_rule_config()

    def run(self, bi: BorrowingsInput) -> BorrowingsOutput:
        per_year_metrics = compute_per_year_metrics(bi.financials_5y)
        trend_metrics = compute_trend_metrics(per_year_metrics)

        rule_results = apply_rules(
            metrics=per_year_metrics,
            trends=trend_metrics,
            benchmarks=bi.industry_benchmarks,
            covenants=bi.covenant_limits,
            rule_config=self.rule_config,
        )

        base_score = self._compute_score(rule_results)
        summary_color = self._score_to_color(base_score)

        red_flags, positives = self._summarize(rule_results)
        key_metrics = self._extract_key_metrics(per_year_metrics, trend_metrics)
        trend_summary = self._build_trend_summary(per_year_metrics)
        deterministic_notes = self._build_narrative_notes(key_metrics, trend_metrics, red_flags)

        # Generate narrative and insights
        base_score = self._compute_score(rule_results)
        narrative, adjusted_score, trend_insights = generate_llm_narrative(
            company_id=bi.company_id,
            key_metrics=key_metrics,
            rule_results=rule_results,
            deterministic_notes=deterministic_notes,
            base_score=base_score,
            trend_data=trend_summary,
        )

        # Populate insights into trend_summary
        # Use LLM insights if available, otherwise generate fallback insights
        for metric_name, metric_data in trend_summary.items():
            if metric_name in trend_insights and trend_insights[metric_name]:
                # Use LLM-generated insight
                metric_data["insight"] = trend_insights[metric_name]
            else:
                # Generate fallback insight from data patterns
                metric_data["insight"] = generate_fallback_insight(
                    metric_name=metric_name,
                    values=metric_data["values"],
                    yoy_growth_pct=metric_data["yoy_growth_pct"]
                )

        return BorrowingsOutput(
            module="Borrowings",
            company=bi.company_id,
            key_metrics=key_metrics,
            trends=trend_summary,
            analysis_narrative=narrative,
            red_flags=red_flags,
            positive_points=positives,
            rules=rule_results,
        )

    @staticmethod
    def _compute_score(rule_results: List[RuleResult]) -> int:
        counts = Counter(r.flag for r in rule_results)
        score = 100
        score -= 10 * counts.get("RED", 0)
        score -= 5 * counts.get("YELLOW", 0)
        score = max(0, min(100, score))
        return score

    @staticmethod
    def _score_to_color(score: int) -> str:
        if score >= 70:
            return "GREEN"
        if score >= 40:
            return "YELLOW"
        return "RED"

    @staticmethod
    def _summarize(rule_results: List[RuleResult]) -> Tuple[List[Dict], List[str]]:
        red_flags = []
        positives = []
        for rule in rule_results:
            if rule.flag == "RED":
                severity = "CRITICAL" if rule.rule_id in {"B1", "B2", "C1", "F2"} else "HIGH"
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
    def _extract_key_metrics(per_year_metrics, trend_metrics) -> Dict[str, float]:
        latest_year = max(per_year_metrics.keys())
        latest = per_year_metrics[latest_year]
        key_metrics = {
            "year": latest_year,
            "total_debt": latest.get("total_debt"),
            "st_debt_share": latest.get("st_debt_share"),
            "debt_to_equity": latest.get("de_ratio"),
            "debt_to_ebitda": latest.get("debt_ebitda"),
            "interest_coverage": latest.get("interest_coverage"),
            "debt_lt_1y_pct": latest.get("maturity_lt_1y_pct"),
            "debt_1_3y_pct": latest.get("maturity_1_3y_pct"),
            "debt_gt_3y_pct": latest.get("maturity_gt_3y_pct"),
            "floating_share": latest.get("floating_share"),
            "wacd": latest.get("wacd"),
            "ocf_to_debt": latest.get("ocf_to_debt"),
            "debt_cagr": trend_metrics.get("debt_cagr"),
            "ebitda_cagr": trend_metrics.get("ebitda_cagr"),
            "finance_cost_cagr": trend_metrics.get("finance_cost_cagr"),
        }
        return key_metrics

    @staticmethod
    def _build_narrative_notes(key_metrics: Dict[str, float], trends: Dict[str, any], red_flags: List[Dict]) -> List[str]:
        notes = []
        if key_metrics.get("debt_cagr") and key_metrics.get("ebitda_cagr"):
            notes.append(
                f"Total debt CAGR {key_metrics['debt_cagr']:.1f}% vs EBITDA CAGR {key_metrics['ebitda_cagr']:.1f}%."
            )
        if key_metrics.get("debt_to_ebitda"):
            notes.append(f"Debt/EBITDA at {key_metrics['debt_to_ebitda']:.1f}x.")
        if key_metrics.get("interest_coverage"):
            notes.append(f"Interest coverage at {key_metrics['interest_coverage']:.1f}x.")
        if key_metrics.get("debt_lt_1y_pct"):
            notes.append(f"{key_metrics['debt_lt_1y_pct']*100:.0f}% of debt matures within one year.")
        if key_metrics.get("floating_share") is not None:
            notes.append(f"Floating rate exposure at {key_metrics['floating_share']*100:.0f}%.")
        if red_flags:
            notes.append(f"Key concerns: {', '.join(flag['title'] for flag in red_flags[:2])}.")
        return notes or ["Debt profile assessed based on latest financials."]

    @staticmethod
    def _build_trend_summary(per_year_metrics: Dict[int, dict]) -> Dict[str, Dict[str, any]]:
        """
        Build trend summary with historical values in Y, Y-1, Y-2, Y-3, Y-4 format
        and calculate YoY growth percentages.
        Insights will be generated by LLM based on actual data patterns.
        """
        tracked_metrics = ["short_term_debt", "long_term_debt", "finance_cost"]

        if not per_year_metrics:
            return {}

        years = sorted(per_year_metrics.keys())
        years_desc = list(reversed(years))  # [Y, Y-1, Y-2, Y-3, Y-4]

        def _values(metric: str) -> Dict[str, float]:
            """Extract historical values in Y, Y-1, Y-2, Y-3, Y-4 format"""
            out = {}
            for offset, year in enumerate(years_desc):
                label = "Y" if offset == 0 else f"Y-{offset}"
                out[label] = per_year_metrics[year].get(metric)
            return out

        def _yoy(metric: str) -> Dict[str, float]:
            """Calculate YoY growth percentages"""
            yoy = {}
            for offset in range(len(years_desc) - 1):
                curr_year = years_desc[offset]
                prev_year = years_desc[offset + 1]
                curr_label = "Y" if offset == 0 else f"Y-{offset}"
                prev_label = f"Y-{offset+1}"
                key = f"{curr_label}_vs_{prev_label}"
                curr_val = per_year_metrics[curr_year].get(metric)
                prev_val = per_year_metrics[prev_year].get(metric)
                if curr_val is None or prev_val in (None, 0):
                    yoy[key] = None
                else:
                    yoy[key] = round(((curr_val - prev_val) / prev_val) * 100, 2)
            return yoy

        trend_summary = {}
        for metric in tracked_metrics:
            trend_summary[metric] = {
                "values": _values(metric),
                "yoy_growth_pct": _yoy(metric),
                "insight": None,  # Will be populated by LLM
            }
        return trend_summary

