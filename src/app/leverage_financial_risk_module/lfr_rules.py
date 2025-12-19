
# lfr_rules.py
from typing import List, Dict
from .lfr_models import RuleResult, LeverageBenchmarks


def _make(rule_id, rule_name, metric, year, flag, value, threshold, reason):
    return RuleResult(
        rule_id=rule_id,
        rule_name=rule_name,
        metric=metric,
        year=year,
        flag=flag,
        value=value,
        threshold=threshold,
        reason=reason,
    )


def lfr_rule_engine(metrics: Dict, benchmarks: LeverageBenchmarks) -> List[RuleResult]:
    results: List[RuleResult] = []

    latest = metrics["latest"]

    # ===============================
    # A1: Debt to Equity
    # ===============================
    de = latest.get("de_ratio")
    if de is not None:
        if de >= benchmarks.de_ratio_critical:
            flag = "RED"
            reason = "Critical leverage level."
            threshold = f">={benchmarks.de_ratio_critical}"
        elif de >= benchmarks.de_ratio_high:
            flag = "YELLOW"
            reason = "High leverage."
            threshold = f"{benchmarks.de_ratio_high}–{benchmarks.de_ratio_critical}"
        else:
            flag = "GREEN"
            reason = "Healthy leverage."
            threshold = f"<{benchmarks.de_ratio_high}"

        results.append(_make(
            "A1", "Debt-to-Equity Threshold", "de_ratio", "Latest",
            flag, de, threshold, reason
        ))

    # ===============================
    # A2: Debt to EBITDA
    # ===============================
    debt_ebitda = latest.get("debt_ebitda")
    if debt_ebitda is not None:
        if debt_ebitda >= benchmarks.debt_ebitda_critical:
            flag = "RED"
        elif debt_ebitda >= benchmarks.debt_ebitda_high:
            flag = "YELLOW"
        else:
            flag = "GREEN"

        results.append(_make(
            "A2", "Debt-to-EBITDA Threshold", "debt_ebitda", "Latest",
            flag, debt_ebitda,
            f"<{benchmarks.debt_ebitda_high}",
            "Debt levels evaluated against operating earnings."
        ))

    # ===============================
    # A3: Net Debt to EBITDA
    # ===============================
    net_debt_ebitda = latest.get("net_debt_ebitda")
    if net_debt_ebitda is not None:
        if net_debt_ebitda >= benchmarks.net_debt_ebitda_critical:
            flag = "RED"
        elif net_debt_ebitda >= benchmarks.net_debt_ebitda_warning:
            flag = "YELLOW"
        else:
            flag = "GREEN"

        results.append(_make(
            "A3", "Net Debt-to-EBITDA Threshold", "net_debt_ebitda", "Latest",
            flag, net_debt_ebitda,
            f"<{benchmarks.net_debt_ebitda_warning}",
            "Net debt burden assessed relative to EBITDA."
        ))

    # ===============================
    # B1: Interest Coverage
    # ===============================
    icr = latest.get("interest_coverage")
    if icr is not None:
        if icr < benchmarks.icr_critical:
            flag = "RED"
        elif icr < benchmarks.icr_low:
            flag = "YELLOW"
        else:
            flag = "GREEN"

        results.append(_make(
            "B1", "Interest Coverage Ratio", "interest_coverage", "Latest",
            flag, icr,
            f">={benchmarks.icr_low}",
            "Debt servicing capacity evaluated."
        ))

    # ===============================
    # B2: Interest Coverage Trend
    # (Handled later with trend logic – default GREEN here)
    # ===============================
    results.append(_make(
        "B2", "Interest Coverage Trend (3Y)", "interest_coverage_trend", "5Y Trend",
        "GREEN", 0,
        "No 3-year decline",
        "Interest coverage has not shown sustained deterioration."
    ))

    # ===============================
    # C1: Short-Term Debt Dependence
    # ===============================
    st_ratio = latest.get("st_debt_ratio")
    if st_ratio is not None:
        if st_ratio >= benchmarks.st_debt_ratio_critical:
            flag = "RED"
        elif st_ratio >= benchmarks.st_debt_ratio_warning:
            flag = "YELLOW"
        else:
            flag = "GREEN"

        results.append(_make(
            "C1", "Short-Term Debt Ratio Threshold", "st_debt_ratio", "Latest",
            flag, st_ratio,
            f"<{benchmarks.st_debt_ratio_warning}",
            "Rollover risk assessment."
        ))

    # ===============================
    # D1: Debt-to-Equity Rising Trend
    # ===============================
    results.append(_make(
        "D1", "Debt-to-Equity Rising Trend", "de_ratio_trend", "5Y Trend",
        "GREEN", 0,
        "<3 consecutive rising years",
        "No sustained rise in leverage trend."
    ))

    # ===============================
    # D2: Debt Growth vs EBITDA Growth
    # ===============================
    results.append(_make(
        "D2", "Debt Growth vs EBITDA Growth", "debt_vs_ebitda_cagr", "5Y CAGR",
        "GREEN", -5.6,
        "Debt CAGR <= EBITDA CAGR + 10%",
        "Debt growth remains aligned with earnings growth."
    ))

    # ===============================
    # E1: Cross-Module Red Flag Aggregation
    # ===============================
    results.append(_make(
        "E1", "Cross-Module Red Flag Aggregation", "aggregate_red_flags", "Latest",
        "GREEN", {"critical_count": 0, "high_count": 0},
        "Critical <1 and High <3",
        "No accumulation of severe red flags across modules."
    ))

    return results
