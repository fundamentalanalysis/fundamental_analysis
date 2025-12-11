
from typing import List, Dict, Any

try:
    from .qoe_models import RuleResult, QoEBenchmarks
except ImportError:
    from qoe_models import RuleResult, QoEBenchmarks


def _mk(rule_id, name, metric, year, flag, value, threshold, reason):
    """ Helper to create rule result objects """
    return RuleResult(
        rule_id=rule_id,
        rule_name=name,
        metric=metric,
        year=year,
        flag=flag,
        value=value,
        threshold=threshold,
        reason=reason
    )


def qoe_rule_engine(metrics: Dict, trends: Dict, benchmarks: QoEBenchmarks) -> List[RuleResult]:
    """
    Ensures ALL rules A1–E1 are evaluated and included in the final `rules` array.
    """

    results = []

    latest_year = metrics["latest_year"]
    latest = metrics["latest"]

    qoe = latest["qoe"]
    accr = latest["accruals_ratio"]
    ocf_rev = latest["revenue_quality"]
    dso = latest["dso"]
    other_income_ratio = latest["other_income_ratio"]

    # Trend flags coming from qoe_trends.py
    qoe_trend_flag = trends.get("qoe_trend")
    accrual_trend_flag = trends.get("accruals_trend")
    rev_up_ocf_down = trends.get("rev_up_ocf_down")
    dso_trend_flag = trends.get("dso_trend")

    # ======================================================
    # A. QoE RATIO RULES — A1 is ALWAYS evaluated
    # ======================================================
    if qoe is not None:
        if qoe < benchmarks.qoe_red:
            flag = "RED"
            reason = "Profits not backed by cash flow. Very weak earnings quality."
            threshold = f"<{benchmarks.qoe_red}"
        elif qoe < benchmarks.qoe_green:
            flag = "YELLOW"
            reason = "Moderate cash conversion — earnings partly supported by cash."
            threshold = f"{benchmarks.qoe_red}–{benchmarks.qoe_green}"
        else:
            flag = "GREEN"
            reason = "High-quality earnings with strong cash backing."
            threshold = f">={benchmarks.qoe_green}"

        results.append(_mk("A1", "QoE Threshold", "qoe", latest_year, flag, qoe, threshold, reason))

    # ---------------------------------------
    # A2 — QoE deteriorating trend (ALWAYS ADDED)
    # ---------------------------------------
    if qoe_trend_flag == "deteriorating":
        results.append(_mk(
            "A2", "QoE Deteriorating Trend", "qoe", latest_year,
            "YELLOW", qoe, "3-year decline",
            "QoE ratio declining for 3 consecutive years — weakening cash conversion."
        ))
    else:
        results.append(_mk(
            "A2", "QoE Deteriorating Trend", "qoe", latest_year,
            "GREEN", qoe, "No 3-year decline",
            "QoE trend is stable or improving."
        ))

    # ======================================================
    # B. ACCRUAL INTENSITY RULES — ALWAYS INCLUDED
    # ======================================================
    if accr is not None:
        if accr > benchmarks.accruals_red:
            flag = "RED"
            reason = "High accruals — profit not supported by cash inflows."
            threshold = f">{benchmarks.accruals_red}"
        elif accr > benchmarks.accruals_warning:
            flag = "YELLOW"
            reason = "Moderate accrual dependency — partial earnings inflation risk."
            threshold = f"{benchmarks.accruals_warning}–{benchmarks.accruals_red}"
        else:
            flag = "GREEN"
            reason = "Low accruals — clean earnings."
            threshold = f"<{benchmarks.accruals_warning}"

        results.append(_mk("B1", "Accrual Intensity", "accruals_ratio", latest_year, flag, accr, threshold, reason))

    # B2 — Accruals rising with profits — ALWAYS INCLUDED
    if accrual_trend_flag == "rising_with_profits":
        results.append(_mk(
            "B2", "Accruals Rising With Profits", "accruals_ratio", latest_year,
            "YELLOW", accr, "Accruals↑ & Profit↑",
            "Accruals increasing along with profit — potential earnings manipulation."
        ))
    else:
        results.append(_mk(
            "B2", "Accruals Rising With Profits", "accruals_ratio", latest_year,
            "GREEN", accr, "No accrual-profits link",
            "Accrual levels do not indicate manipulation pressure."
        ))

    # ======================================================
    # C. REVENUE QUALITY RULES — ALWAYS INCLUDED
    # ======================================================
    if ocf_rev is not None:
        if ocf_rev < benchmarks.ocf_revenue_red:
            flag = "RED"
            reason = "Extremely weak cash conversion from revenue."
            threshold = f"<{benchmarks.ocf_revenue_red}"
        elif ocf_rev < benchmarks.ocf_revenue_warning:
            flag = "YELLOW"
            reason = "Weak but not critical cash generation from sales."
            threshold = f"{benchmarks.ocf_revenue_red}–{benchmarks.ocf_revenue_warning}"
        else:
            flag = "GREEN"
            reason = "Healthy cash generation relative to sales."
            threshold = f">={benchmarks.ocf_revenue_warning}"

        results.append(_mk("C1", "OCF / Revenue", "revenue_quality", latest_year, flag, ocf_rev, threshold, reason))

    # C2 — Revenue up while OCF down — ALWAYS INCLUDED
    if rev_up_ocf_down:
        results.append(_mk(
            "C2", "Revenue↑ but OCF↓", "ocf", latest_year,
            "YELLOW", ocf_rev, "Revenue↑ OCF↓",
            "Sales increasing while cash flow drops — revenue quality deteriorating."
        ))
    else:
        results.append(_mk(
            "C2", "Revenue↑ but OCF↓", "ocf", latest_year,
            "GREEN", ocf_rev, "Healthy or stable",
            "Revenue growth is supported by cash flow."
        ))

    # ======================================================
    # D. DSO RULES — ALWAYS INCLUDED
    # ======================================================
    if dso is not None:
        if dso > benchmarks.dso_high:
            flag = "YELLOW"
            reason = "Slow collections — possible aggressive revenue recognition."
            threshold = f">{benchmarks.dso_high}"
        else:
            flag = "GREEN"
            reason = "Healthy collection cycle."
            threshold = f"<={benchmarks.dso_high}"

        results.append(_mk("D1", "High DSO", "dso", latest_year, flag, dso, threshold, reason))

    # D2 — DSO rising three years — ALWAYS INCLUDED
    if dso_trend_flag == "rising_3yr":
        results.append(_mk(
            "D2", "DSO Rising 3 Years", "dso", latest_year,
            "RED", dso, "3-year rising",
            "DSO rising for 3 straight years — severe collection deterioration."
        ))
    else:
        results.append(_mk(
            "D2", "DSO Rising 3 Years", "dso", latest_year,
            "GREEN", dso, "Not rising 3 years",
            "DSO trend is not materially deteriorating."
        ))

    # ======================================================
    # E. OTHER INCOME RULE — ALWAYS INCLUDED
    # ======================================================
    if other_income_ratio is not None:
        if other_income_ratio > benchmarks.other_income_warning_ratio:
            flag = "YELLOW"
            reason = "Net income heavily dependent on non-operating income."
            threshold = f">{benchmarks.other_income_warning_ratio}"
        else:
            flag = "GREEN"
            reason = "PAT is not overly dependent on non-core income."
            threshold = f"<={benchmarks.other_income_warning_ratio}"

        results.append(_mk("E1", "Other Income Ratio", "other_income_ratio", latest_year,
                           flag, other_income_ratio, threshold, reason))

    return results
