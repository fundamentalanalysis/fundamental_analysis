from collections import Counter
from typing import Tuple, List, Dict

from .equity_funding_mix_config import load_rule_config, EquityFundingRuleConfig
from .equity_funding_mix_llm import generate_llm_narrative
from .equity_funding_mix_metrics import compute_per_year_metrics
from .equity_funding_mix_models import EquityFundingInput, EquityFundingOutput, RuleResult, YearFinancialInput
from .equity_funding_mix_rules import apply_rules
from .equity_funding_mix_trend import compute_trend_metrics
from .equity_funding_mix_insight_fallback import generate_fallback_insight


class EquityFundingMixModule:
    def __init__(self, rule_config: EquityFundingRuleConfig = None):
        self.rule_config = rule_config or load_rule_config()

    def run(self, efi: EquityFundingInput) -> EquityFundingOutput:

        # print(f"Running Equity Funding Mix Module for Company: {efi.company_id}")
        # print("Input Financials:", efi.financials_5y)

        per_year_metrics = compute_per_year_metrics(efi.financials_5y)
        trend_metrics = compute_trend_metrics(per_year_metrics)

        # print("Per Year Metrics:", per_year_metrics)
        # print("Trend Metrics:", trend_metrics)

        rule_results = apply_rules(
            metrics=per_year_metrics,
            trends=trend_metrics,
            benchmarks=efi.industry_equity_benchmarks,
            rule_config=self.rule_config,
        )
        # print("Rule Results:", rule_results)

        base_score = self._compute_score(rule_results)
        summary_color = self._score_to_color(base_score)
        print(
            f"Equity Funding Mix Module - Company: {efi.company}, Score: {base_score}, Summary Color: {summary_color}")

        red_flags, positives = self._summarize(rule_results)
        key_metrics = self._extract_key_metrics(
            per_year_metrics, trend_metrics)
        trend_summary = self._build_trend_summary(per_year_metrics)
        deterministic_notes = self._build_narrative_notes(
            key_metrics, trend_metrics, red_flags)

        # Generate narrative and insights
        narrative, adjusted_score, trend_insights = generate_llm_narrative(
            company_id=efi.company,
            key_metrics=key_metrics,
            rule_results=rule_results,
            deterministic_notes=deterministic_notes,
            base_score=base_score,
            trend_data=trend_summary,
        )

        # Populate insights into trend_summary
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

        return EquityFundingOutput(
            module="EquityFundingMix",
            company=efi.company,
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
                severity = "CRITICAL" if rule.rule_id in {
                    "C1", "E2", "D1"} else "HIGH"
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
            "share_capital": latest.get("share_capital"),
            "reserves_and_surplus": latest.get("reserves_and_surplus"),
            "net_worth": latest.get("net_worth"),
            "pat": latest.get("pat"),
            "dividends_paid": latest.get("dividends_paid"),
            "payout_ratio": latest.get("payout_ratio"),
            "dividend_to_fcf": latest.get("dividend_to_fcf"),
            "roe": latest.get("roe"),
            "retained_earnings": latest.get("retained_earnings"),
            "dilution_pct": latest.get("dilution_pct"),
            "debt_to_equity": latest.get("debt_to_equity"),
            "equity_cagr": trend_metrics.get("equity_cagr"),
            "debt_cagr": trend_metrics.get("debt_cagr"),
            "retained_cagr": trend_metrics.get("retained_cagr"),
            "roe_cagr": trend_metrics.get("roe_cagr"),
        }
        return key_metrics

    @staticmethod
    def _build_narrative_notes(key_metrics: Dict[str, float], trends: Dict[str, any], red_flags: List[Dict]) -> List[str]:
        notes = []
        if key_metrics.get("roe"):
            notes.append(f"ROE at {key_metrics['roe']:.1%} in latest year.")
        if key_metrics.get("payout_ratio"):
            notes.append(
                f"Dividend payout ratio at {key_metrics['payout_ratio']:.1%}.")
        if key_metrics.get("dilution_pct") and key_metrics['dilution_pct'] > 0:
            notes.append(
                f"Share capital dilution of {key_metrics['dilution_pct']:.1%} in latest year.")
        if key_metrics.get("equity_cagr") and key_metrics.get("debt_cagr"):
            notes.append(
                f"Equity CAGR {key_metrics['equity_cagr']:.1f}% vs Debt CAGR {key_metrics['debt_cagr']:.1f}%."
            )
        if red_flags:
            notes.append(
                f"Key concerns: {', '.join(flag['title'] for flag in red_flags[:2])}.")
        return notes or ["Equity and funding mix assessed based on latest financials."]

    @staticmethod
    def _build_trend_summary(per_year_metrics: Dict[int, dict]) -> Dict[str, Dict[str, any]]:
        """
        Build trend summary with historical values in Y, Y-1, Y-2, Y-3, Y-4 format
        and calculate YoY growth percentages.
        """
        tracked_metrics = ["retained_earnings", "payout_ratio",
                           "roe", "equity_growth_rate", "debt_growth_rate"]

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
                    yoy[key] = round(
                        ((curr_val - prev_val) / prev_val) * 100, 2)
            return yoy

        trend_summary = {}
        for metric in tracked_metrics:
            trend_summary[metric] = {
                "values": _values(metric),
                "yoy_growth_pct": _yoy(metric),
                "insight": None,  # Will be populated by LLM
            }
        return trend_summary
from .equity_funding_mix_models import EquityFundingInput as EquityYearFinancialInput, EquityFundingOutput, IndustryBenchmarks as EquityIndustryBenchmarks

equity_funding_engine = EquityFundingMixModule()

# Equity Funding Mix Benchmarks
DEFAULT_EQUITY_BENCHMARKS = EquityIndustryBenchmarks(
    payout_normal=0.30,
    payout_high=0.50,
    roe_good=0.15,
    roe_modest=0.10,
    dilution_warning=0.05,
)
def run_equity_funding_mix_module(efi: dict) -> EquityFundingOutput:
        # Convert request data, computing missing equity fields if needed
        equity_years = []
        
        for fy in efi["financial_data"]["financial_years"]:
            fy_dict = fy

            # 1. Compute total debt: short_term + long_term + lease_liabilities
            if fy_dict.get("debt") is None:
                st_debt = fy_dict.get("short_term_debt") or 0.0
                lt_debt = fy_dict.get("long_term_debt") or 0.0
                lease_liab = fy_dict.get("lease_liabilities") or 0.0
                fy_dict["debt"] = st_debt + lt_debt + lease_liab

            # 2. Compute share_capital (use from input if available, otherwise use total_equity)
            if fy_dict.get("share_capital") is None:
                fy_dict["share_capital"] = fy_dict.get("total_equity") or 0.0

            # 3. Compute reserves_and_surplus (use from input if available, otherwise default to 0)
            if fy_dict.get("reserves_and_surplus") is None:
                fy_dict["reserves_and_surplus"] = fy_dict.get(
                    "reserves") or 0.0

            # 4. Compute net_worth = share_capital + reserves_and_surplus
            if fy_dict.get("net_worth") is None:
                fy_dict["net_worth"] = (fy_dict.get(
                    "share_capital") or 0.0) + (fy_dict.get("reserves_and_surplus") or 0.0)

            # 5. Compute PAT from operating profit or profit_from_operations
            fy_dict["pat"] = fy_dict.get("net_profit")

            # if fy_dict.get("pat") is None:
            #     pat_val = fy_dict.get("net_profit") or 0.0
            #     print("Initial PAT from operations:", pat_val)
            #     fy_dict["pat"] = max(0, pat_val)

            # 6. Set dividend_paid (default 0 if not provided)
            if fy_dict.get("dividends_paid") is None:
                fy_dict["dividends_paid"] = 0.0

            # fy_dict["dividends_paid"] = fy_dict.get("dividends_paid")
            # print("Year:", fy_dict["year"], "PAT:", fy_dict["pat"], "Dividends Paid:", fy_dict["dividends_paid"])

            # 7. Compute free_cash_flow if not provided
            if fy_dict.get("free_cash_flow") is None:
                ocf = fy_dict.get("cash_from_operating_activity") or 0.0
                capex = fy_dict.get("fixed_assets_purchased") or 0.0
                fy_dict["free_cash_flow"] = ocf + \
                    capex  # capex is negative (outflow)

            equity_years.append(YearFinancialInput(**fy_dict))

        module_input = EquityFundingInput(
            company=efi["company"].upper(),
            industry_code=(efi.get("industry_code") or "GENERAL").upper(),
            financials_5y=equity_years,
            industry_equity_benchmarks=DEFAULT_EQUITY_BENCHMARKS,
        )
        result = equity_funding_engine.run(module_input)
        return result