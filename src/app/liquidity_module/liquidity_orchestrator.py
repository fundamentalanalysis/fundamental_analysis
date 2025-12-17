from collections import Counter
from typing import Dict, List, Tuple

from .liquidity_metrics import compute_per_year_metrics
# NEW: your updated trend logic
from .liquidity_trend import compute_liquidity_trends
from .liquidity_rules import evaluate_rules
from .liquidity_llm import generate_liquidity_narrative
from .liquidity_models import LiquidityModuleOutput, RuleResult, YearFinancials as LiquidityYearFinancials
from .liquidity_insight_fallback import generate_liquidity_fallback_insight   # add if needed


class LiquidityModule:

    def run(self, input_data):
        financials = input_data.financials_5y

        # -------------------------------
        # 1. Compute per-year structured metrics
        # -------------------------------

        # print("computing per-year liquidity metrics...")
        per_year_metrics = compute_per_year_metrics(financials)
        # print("computed per-year liquidity metrics.")

        latest_year = max(per_year_metrics.keys())
        metrics_latest = per_year_metrics[latest_year]

        # -------------------------------
        # 2. Compute YoY trend metrics (cash/receivables/inventory/OCF/CL)
        # -------------------------------
        # print("computing liquidity trends...")
        trend_metrics = compute_liquidity_trends(financials)
        # print("computed liquidity trends.")

        # -------------------------------
        # 3. Evaluate liquidity rules
        # -------------------------------
        # print("Evaluating liquidity rules...")
        latest_year = max(per_year_metrics.keys())
        rule_dicts = evaluate_rules(
            per_year_metrics[latest_year], trend_metrics)

        # print(f"Evaluated {len(rule_dicts)} rules.")

        # -------------------------------
        # 4. Convert to RuleResult objects
        # -------------------------------
        rule_results = [
            RuleResult(
                rule_id=r.get("rule_id", ""),
                rule_name=r.get("rule_name", ""),
                value=r.get("value", 0.0) or 0.0,
                threshold=r.get("threshold", ""),
                flag=r.get("flag", ""),
                reason=r.get("reason", "")
            )
            for r in rule_dicts
        ]

        # -------------------------------
        # 5. Compute score
        # -------------------------------
        # print("Computing liquidity score...")
        score = self._compute_score(rule_results)
        # print(f"Computed liquidity score: {score}")
        summary_color = self._score_to_color(score)

        # -------------------------------
        # 6. Classify red flags + positives
        # -------------------------------
        # print("Summarizing liquidity flags...")
        red_flags, positives = self._summarize(rule_results)

        # -------------------------------
        # 7. Extract key liquidity metrics (like borrowings module)
        # -------------------------------
        # print("Extracting key liquidity metrics...")
        key_metrics = self._extract_key_metrics(
            per_year_metrics, trend_metrics)
        # print("Extracted key liquidity metrics.")
        # -------------------------------
        # 8. Build trend summary (Y, Y-1, Y-2...)
        # -------------------------------
        trend_summary = self._build_trend_summary(financials, trend_metrics)

        # -------------------------------
        # 9. LLM Narrative + Insights
        # -------------------------------
        # print("Generating liquidity narrative via LLM...")
        narrative, trend_insights = generate_liquidity_narrative(
            company_id=input_data.company_id,
            key_metrics=key_metrics,
            rule_results=rule_results,
            trend_data=trend_summary,
        )
        # print(f"Generated liquidity narrative. \nNarrative Sections: {len(narrative)}")

        # populate insights (LLM or fallback)
        for metric_name, block in trend_summary.items():
            block_yoy = block.get("yoy_growth_pct")
            block_values = block.get("values")

            if metric_name in trend_insights and trend_insights[metric_name]:
                block["insight"] = trend_insights[metric_name]
            else:
                block["insight"] = generate_liquidity_fallback_insight(
                    metric_name=metric_name,
                    values=block_values,
                    yoy_growth_pct=block_yoy
                )

        # -------------------------------
        # 10. Final Output
        # -------------------------------
        return LiquidityModuleOutput(
            module="Liquidity",
            sub_score_adjusted=max(score, 0),
            key_metrics=key_metrics,
            trends=trend_summary,
            analysis_narrative=narrative,
            red_flags=red_flags,
            positive_points=positives,
            rules=rule_results,
            summary_color=summary_color
        )

    # ====================================================================
    # Helper Methods — Parallel to BorrowingsModule
    # ====================================================================

    @staticmethod
    def _compute_score(rules: List[RuleResult]) -> int:
        counts = Counter(r.flag for r in rules)
        score = 100
        score -= 10 * counts.get("RED", 0)
        score -= 5 * counts.get("YELLOW", 0)
        return max(0, min(100, score))

    @staticmethod
    def _score_to_color(score: int) -> str:
        if score >= 70:
            return "GREEN"
        if score >= 40:
            return "YELLOW"
        return "RED"

    @staticmethod
    def _summarize(rule_results: List[RuleResult]):
        red_flags = []
        positives = []

        for r in rule_results:
            if r.flag == "RED":
                red_flags.append({
                    "module": "liquidity",
                    "severity": "CRITICAL",
                    "title": r.rule_name,
                    "detail": r.reason,
                    "risk_category": "liquidity",
                })

            elif r.flag == "GREEN":
                positives.append(f"{r.rule_name}: {r.reason}")

        return red_flags, positives

    @staticmethod
    def _extract_key_metrics(per_year_metrics, trends) -> Dict[str, float]:
        latest_year = max(per_year_metrics.keys())
        m = per_year_metrics[latest_year]

        return {
            "year": latest_year,
            "cash": m.get("cash_and_equivalents"),
            "marketable_securities": m.get("marketable_securities"),
            "current_ratio": m.get("current_ratio"),
            "quick_ratio": m.get("quick_ratio"),
            "defensive_interval_ratio_days": m.get("defensive_interval_ratio_days"),
            "cash_ratio": m.get("cash_ratio"),
            "ocf_to_cl": m.get("ocf_to_current_liabilities"),
            "ocf_to_total_debt": m.get("ocf_to_total_debt"),
            "interest_coverage_ocf": m.get("interest_coverage_ocf"),
            "cash_coverage_st_debt": m.get("cash_coverage_st_debt"),
            "current_ratio_yoy_latest": trends["yoy"]['current_ratio_yoy'][-1],
            "cash_yoy_latest": trends["yoy"]['cash_yoy'][-1],
            "ocf_yoy_latest": trends["yoy"]['ocf_yoy'][-1],
        }

    @staticmethod
    def _build_trend_summary(financials, trends) -> Dict[str, Dict]:
        """
        Same structure as Borrowings trend_summary:
        {
            "cash": {
                "values": {Y: ..., Y-1: ...},
                "yoy_growth_pct": {...},
                "insight": None
            }
        }
        """
        metrics = ["cash_and_equivalents", "receivables", "inventory",
                   "operating_cash_flow", "current_liabilities", "current_ratio"]

        trend_summary = {}

        for metric in metrics:
            # values in Y, Y-1, Y-2, Y-3, Y-4 (Y is latest)
            values = {}
            labels = []
            for idx, fin in enumerate(reversed(financials)):
                label = "Y" if idx == 0 else f"Y-{idx}"
                labels.append(label)
                if metric == "current_ratio":
                    ca = getattr(fin, "current_assets", None)
                    cl = getattr(fin, "current_liabilities", None)
                    values[label] = round(ca / cl, 2) if ca and cl else None
                else:
                    values[label] = getattr(fin, metric, None)

            # Compute YoY pct directly from the values (Y vs Y-1, Y-1 vs Y-2, ...)
            yoy_pct = {}
            for i in range(0, len(labels) - 1):
                curr_label = labels[i]
                prev_label = labels[i + 1]
                curr_val = values.get(curr_label)
                prev_val = values.get(prev_label)

                key = f"{curr_label}_vs_{prev_label}"
                if curr_val is None or prev_val in (None, 0):
                    yoy_pct[key] = None
                else:
                    yoy_pct[key] = round(
                        ((curr_val - prev_val) / prev_val) * 100, 2)

            trend_summary[metric] = {
                "values": values,
                "yoy_growth_pct": yoy_pct,
                "insight": None,
            }

        return trend_summary


def build_financial_list(req) -> List[LiquidityYearFinancials]:
    """
    Build a list of LiquidityYearFinancials from request data.
    """
    fin_list = []

    for fy in req["financial_data"]["financial_years"]:
        # Calculate current_assets if not provided
        inventory = fy["inventories"]
        cash_equivalents = fy["cash_equivalents"]
        total_debt = fy["short_term_debt"] + fy["long_term_debt"] + \
            fy["lease_liabilities"] + fy["other_borrowings"] + \
            fy["preference_capital"]
        # print(f"Processing Year: {fy['year']} : {fy['short_term_debt']} + {fy['other_liability_items']} + {fy['long_term_debt']} + {fy['lease_liabilities']} + {fy['other_borrowings']} + {fy['preference_capital']}")
        # print("Total Debt Calculated:", total_debt)
        current_assets = fy["investments"] + \
            fy["inventories"] + fy["trade_receivables"]
        current_liablities = fy["short_term_debt"] + \
            fy["other_liability_items"]
        operating_cash_flow = fy["profit_from_operations"] + \
            fy["working_capital_changes"] - fy["direct_taxes"]
        daily_expenses = (fy["expenses"] - fy["depreciation"]) / 365
        marketable_securities = fy["investments"]
        receivables = fy["trade_receivables"]
        fin_list.append(
            LiquidityYearFinancials(
                **{**fy, "inventory": inventory, "cash_and_equivalents": cash_equivalents,
                    "current_assets": current_assets, "current_liabilities": current_liablities,
                    "operating_cash_flow": operating_cash_flow, "daily_operating_expenses": daily_expenses,
                    "total_debt": total_debt, "marketable_securities": marketable_securities,
                    "receivables": receivables, "interest_expense": fy["interest_paid_fin"]}
            )
        )

    return fin_list
