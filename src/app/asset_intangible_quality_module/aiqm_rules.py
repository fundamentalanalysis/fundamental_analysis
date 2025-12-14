from typing import Dict, List, Optional

try:
    from .aiqm_models import RuleResult, AssetIntangibleBenchmarks
except ImportError:
    from aiqm_models import RuleResult, AssetIntangibleBenchmarks


# ------------------------------------------------------------
# Helper RuleResult creator
# ------------------------------------------------------------
def _make(rule_id, name, metric, year, flag, value, threshold, reason):
    return RuleResult(
        rule_id=rule_id,
        rule_name=name,
        metric=metric,
        year=year,
        flag=flag,
        value=value,
        threshold=threshold,
        reason=reason,
    )


# ------------------------------------------------------------
# Asset & Intangible Quality Rule Engine
# ------------------------------------------------------------
def aiqm_rule_engine(metrics: Dict, trends: Dict, benchmarks: AssetIntangibleBenchmarks):
    results: List[RuleResult] = []

    latest = metrics["latest"]
    all_years = metrics["all_years"]
    current_year = "Latest"

    # Extract metrics
    asset_turnover = latest.get("asset_turnover")
    age_proxy = latest.get("asset_age_proxy")
    goodwill_pct = latest.get("goodwill_pct")
    impairment_pct = latest.get("impairment_pct")
    impairment_yoy = latest.get("impairment_yoy")
    intangible_growth = latest.get("intangible_growth_yoy")
    revenue_growth = latest.get("revenue_growth_yoy")
    goodwill_growth = latest.get("goodwill_growth_yoy")
    amort_ratio = latest.get("amortization_ratio")
    r_and_d_ratio = latest.get("r_and_d_intangible_ratio")

    # ============================================================
    # A. ASSET PRODUCTIVITY RULES
    # ============================================================

    # ---- A1: Asset Turnover Threshold ----
    if asset_turnover is not None:
        if asset_turnover < benchmarks.asset_turnover_critical:
            results.append(_make(
                "A1", "Asset Turnover Threshold", "asset_turnover", current_year,
                "RED", asset_turnover, f"<{benchmarks.asset_turnover_critical}",
                "Asset turnover extremely low — very poor utilization."
            ))
        elif asset_turnover < benchmarks.asset_turnover_low:
            results.append(_make(
                "A1", "Asset Turnover Threshold", "asset_turnover", current_year,
                "YELLOW", asset_turnover,
                f"{benchmarks.asset_turnover_critical}–{benchmarks.asset_turnover_low}",
                "Asset turnover below optimal levels — suboptimal utilization."
            ))
        else:
            results.append(_make(
                "A1", "Asset Turnover Threshold", "asset_turnover", current_year,
                "GREEN", asset_turnover, f">={benchmarks.asset_turnover_low}",
                "Healthy asset utilization."
            ))

    # ---- A2: Asset Turnover Decline ----
    at_yoy_map = trends["asset_turnover"]["yoy_growth_pct"]
    declines = [v for v in at_yoy_map.values() if v is not None and v < 0]
    decline_count = len(declines)

    if decline_count >= 3:
        results.append(_make(
            "A2", "Asset Turnover Declining 3Y", "asset_turnover", "5Y Trend",
            "YELLOW", decline_count, "3 consecutive declines",
            "Asset turnover has declined for 3 consecutive years."
        ))
    else:
        results.append(_make(
            "A2", "Asset Turnover Declining 3Y", "asset_turnover", "5Y Trend",
            "GREEN", decline_count, "No 3-year decline",
            "Asset turnover trend is stable."
        ))

    # ============================================================
    # B. ASSET AGE & REPLACEMENT RISK
    # ============================================================

    # ---- B1: Age Proxy ----
    if age_proxy is not None:
        if age_proxy > benchmarks.age_proxy_critical:
            results.append(_make(
                "B1", "Asset Age Proxy", "asset_age_proxy", current_year,
                "RED", age_proxy, f">{benchmarks.age_proxy_critical}",
                "Very old asset base — nearing replacement."
            ))
        elif age_proxy > benchmarks.age_proxy_old_threshold:
            results.append(_make(
                "B1", "Asset Age Proxy", "asset_age_proxy", current_year,
                "YELLOW", age_proxy,
                f"{benchmarks.age_proxy_old_threshold}–{benchmarks.age_proxy_critical}",
                "Aging asset base — higher maintenance & replacement risk."
            ))
        else:
            results.append(_make(
                "B1", "Asset Age Proxy", "asset_age_proxy", current_year,
                "GREEN", age_proxy, f"<{benchmarks.age_proxy_old_threshold}",
                "Healthy asset age profile."
            ))

    # ---- B2: Depreciation > Capex (3Y) ----
    dep_gt_capex_count = sum(
        1 for y, yr in all_years.items()
        if yr.get("depreciation") is not None and yr.get("capex") is not None
        and yr["depreciation"] > yr["capex"]
    )

    if dep_gt_capex_count >= 3:
        results.append(_make(
            "B2", "Depreciation > Capex (3Y)", "capex_vs_depreciation", "5Y",
            "YELLOW", float(dep_gt_capex_count), ">=3 years",
            "Depreciation exceeded capex for 3+ years — weak reinvestment."
        ))
    else:
        results.append(_make(
            "B2", "Depreciation > Capex (3Y)", "capex_vs_depreciation", "5Y",
            "GREEN", float(dep_gt_capex_count), "<3 years",
            "Reinvestment appears sufficient."
        ))

    # ============================================================
    # C. IMPAIRMENT RULES
    # ============================================================

    if impairment_pct is not None and impairment_pct > benchmarks.impairment_high_threshold:
        results.append(_make(
            "C1", "High Impairment Level", "impairment_pct", current_year,
            "RED", impairment_pct, f">{benchmarks.impairment_high_threshold}",
            "Significant impairment relative to net block."
        ))

    if impairment_yoy is not None and impairment_yoy > benchmarks.impairment_sudden_spike_threshold:
        results.append(_make(
            "C2", "Sudden Impairment Spike", "impairment_yoy", current_year,
            "YELLOW", impairment_yoy,
            f">{benchmarks.impairment_sudden_spike_threshold}",
            "Large YoY impairment spike — possible failed project."
        ))

    if "impairment_count_5y" in trends and trends["impairment_count_5y"] >= 3:
        results.append(_make(
            "C3", "Frequent Impairments", "impairment", "5Y",
            "YELLOW", float(trends["impairment_count_5y"]), ">=3",
            "Frequent impairments indicate weak capital allocation."
        ))

    # ============================================================
    # D. GOODWILL & INTANGIBLE CONCENTRATION
    # ============================================================

    if goodwill_pct is not None:
        if goodwill_pct > benchmarks.goodwill_pct_critical:
            results.append(_make(
                "D1", "Goodwill Concentration", "goodwill_pct", current_year,
                "RED", goodwill_pct, f">{benchmarks.goodwill_pct_critical}",
                "High goodwill concentration — elevated impairment risk."
            ))
        elif goodwill_pct > benchmarks.goodwill_pct_warning:
            results.append(_make(
                "D1", "Goodwill Concentration", "goodwill_pct", current_year,
                "YELLOW", goodwill_pct,
                f"{benchmarks.goodwill_pct_warning}–{benchmarks.goodwill_pct_critical}",
                "Moderate reliance on acquisitions."
            ))
        else:
            results.append(_make(
                "D1", "Goodwill Concentration", "goodwill_pct", current_year,
                "GREEN", goodwill_pct, f"<{benchmarks.goodwill_pct_warning}",
                "Healthy goodwill exposure."
            ))

    if goodwill_growth is not None and revenue_growth is not None:
        if goodwill_growth > (revenue_growth + 0.10):
            results.append(_make(
                "D2", "Goodwill Growth vs Revenue", "goodwill_growth", current_year,
                "YELLOW", goodwill_growth,
                "Goodwill CAGR > Revenue CAGR +10%",
                "Goodwill rising faster than revenue — questionable acquisition quality."
            ))

    int_cagr = trends["cagr"].get("intangible_cagr")
    op_cagr = trends["cagr"].get("operating_asset_cagr")

    if int_cagr is not None and op_cagr is not None:
        limit = op_cagr + 15
        if int_cagr > limit:
            results.append(_make(
                "D3", "Intangible Growth vs Operating Assets", "intangible_cagr", "5Y CAGR",
                "YELLOW", int_cagr, f">{limit}",
                "Intangibles are growing much faster than operating assets — possible aggressive capitalization."
            ))
        else:
            results.append(_make(
                "D3", "Intangible Growth vs Operating Assets", "intangible_cagr", "5Y CAGR",
                "GREEN", int_cagr, f"<{limit}",
                "Intangible growth aligned with operating asset expansion."
            ))

    # ============================================================
    # E. INTANGIBLE QUALITY RULES
    # ============================================================

    if amort_ratio is not None:
        if amort_ratio < 0.02:
            results.append(_make(
                "E1", "Amortization Discipline", "amortization_ratio", current_year,
                "YELLOW", amort_ratio, "<0.02",
                "Amortization too low — possible over-capitalization."
            ))
        else:
            results.append(_make(
                "E1", "Amortization Discipline", "amortization_ratio", current_year,
                "GREEN", amort_ratio, ">=0.02",
                "Healthy amortization policy."
            ))

    if r_and_d_ratio is not None:
        if r_and_d_ratio < 0.5:
            results.append(_make(
                "E2", "R&D to Intangible Additions", "r_and_d_intangible_ratio", current_year,
                "YELLOW", r_and_d_ratio, "<0.5",
                "R&D does not sufficiently support new intangible additions."
            ))
        else:
            results.append(_make(
                "E2", "R&D to Intangible Additions", "r_and_d_intangible_ratio", current_year,
                "GREEN", r_and_d_ratio, ">=0.5",
                "Intangibles supported by R&D investment."
            ))

    # ============================================================
    # F. **CWIP TREND VS CAPITALIZATION RULE**
    # ============================================================

    try:
        cap_values = trends["capitalization"]["values"]
        cwip_ratio_values = trends["cwip_vs_capitalization"]["values"]
    except KeyError:
        # CWIP or Capitalization not available
        return results

    latest_cap = cap_values.get("Y")
    latest_cwip_cap_ratio = cwip_ratio_values.get("Y")

    # ---- F1. Red Flag: Capitalization Negative ----
    if latest_cap is not None and latest_cap < 0:
        results.append(_make(
            "F1", "CWIP Trend vs Capitalization", "capitalization", current_year,
            "RED", latest_cap, "<0",
            "Capitalization negative — possible stalled or abandoned projects."
        ))

    # ---- F1 Yellow: CWIP Increasing but Capitalization Low ----
    cwip_yoy = trends["cwip"]["yoy_growth_pct"].get("Y_vs_Y-1")
    cap_yoy = trends["capitalization"]["yoy_growth_pct"].get("Y_vs_Y-1")

    if cwip_yoy is not None and cwip_yoy > 0 and (cap_yoy is None or cap_yoy < 0):
        results.append(_make(
            "F1", "CWIP Trend vs Capitalization", "cwip_vs_cap", current_year,
            "YELLOW", latest_cwip_cap_ratio, "CWIP↑ & Capex↓",
            "CWIP increasing while capitalization declining — conversion is weak."
        ))

    # ---- F1 Green: CWIP conversion strong ----
    if latest_cwip_cap_ratio is not None and latest_cwip_cap_ratio > 0.10:
        results.append(_make(
            "F1", "CWIP Trend vs Capitalization", "cwip_vs_cap", current_year,
            "GREEN", latest_cwip_cap_ratio, ">0.10",
            "Healthy CWIP conversion into fixed assets."
        ))

    return results
