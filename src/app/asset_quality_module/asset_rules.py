from typing import List, Dict, Any
from .asset_models import RuleResult, IndustryAssetBenchmarks

def apply_rules(
    metrics: Dict[int, dict],
    trends: Dict[str, any],
    benchmarks: IndustryAssetBenchmarks
) -> List[RuleResult]:
    results = []
    years = sorted(metrics.keys())
    latest_year = years[-1]
    latest = metrics[latest_year]

    # A. Asset Productivity Rules
    # Rule A1 – Asset Turnover Threshold
    at = latest.get("asset_turnover")
    if at is not None:
        if at < benchmarks.asset_turnover_critical:
            results.append(RuleResult(
                rule_id="A1", rule_name="Asset Turnover Threshold", value=at,
                threshold=f"<{benchmarks.asset_turnover_critical}", flag="RED",
                reason="Poor asset utilization."
            ))
        elif at < benchmarks.asset_turnover_low:
            results.append(RuleResult(
                rule_id="A1", rule_name="Asset Turnover Threshold", value=at,
                threshold=f"<{benchmarks.asset_turnover_low}", flag="YELLOW",
                reason="Suboptimal efficiency."
            ))
        else:
            results.append(RuleResult(
                rule_id="A1", rule_name="Asset Turnover Threshold", value=at,
                threshold=f">={benchmarks.asset_turnover_low}", flag="GREEN",
                reason="Healthy asset utilization."
            ))

    # Rule A2 – Declining Asset Turnover Trend
    if trends.get("asset_turnover_declining"):
        results.append(RuleResult(
            rule_id="A2", rule_name="Declining Asset Turnover Trend", value=None,
            threshold="3 consecutive years decline", flag="YELLOW",
            reason="Consistent utilization decline."
        ))

    # B. Asset Age & Replacement Risk
    # Rule B1 – Aging Proxy Threshold
    age = latest.get("asset_age_proxy")
    if age is not None:
        if age > benchmarks.age_proxy_critical:
            results.append(RuleResult(
                rule_id="B1", rule_name="Aging Proxy Threshold", value=age,
                threshold=f">{benchmarks.age_proxy_critical}", flag="RED",
                reason="Very old asset base, likely near end-life."
            ))
        elif age > benchmarks.age_proxy_old_threshold:
            results.append(RuleResult(
                rule_id="B1", rule_name="Aging Proxy Threshold", value=age,
                threshold=f">{benchmarks.age_proxy_old_threshold}", flag="YELLOW",
                reason="Aging assets."
            ))
        else:
            results.append(RuleResult(
                rule_id="B1", rule_name="Aging Proxy Threshold", value=age,
                threshold=f"<{benchmarks.age_proxy_old_threshold}", flag="GREEN",
                reason="Asset base is relatively young."
            ))

    # Rule B2 – Depreciation > Capex
    if trends.get("dep_gt_capex_3y"):
        results.append(RuleResult(
            rule_id="B2", rule_name="Depreciation > Capex", value=None,
            threshold="3 consecutive years", flag="YELLOW",
            reason="No major reinvestment, aging assets."
        ))

    # C. Impairment Rules
    # Rule C1 – High Impairment Level
    imp_pct = latest.get("impairment_pct")
    if imp_pct is not None and imp_pct > benchmarks.impairment_high_threshold:
        results.append(RuleResult(
            rule_id="C1", rule_name="High Impairment Level", value=imp_pct,
            threshold=f">{benchmarks.impairment_high_threshold}", flag="RED",
            reason="Significant value erosion."
        ))

    # Rule C2 – Sudden Increase in Impairment
    imp_yoy = trends.get("impairment_yoy")
    if imp_yoy and imp_yoy[-1] is not None and imp_yoy[-1] > 30.0: # 30% threshold hardcoded in spec as 0.30 but computed as pct
        results.append(RuleResult(
            rule_id="C2", rule_name="Sudden Increase in Impairment", value=imp_yoy[-1],
            threshold=">30%", flag="YELLOW",
            reason="Possible failed investment or write-down."
        ))

    # Rule C3 – Frequent Impairments
    if trends.get("impairment_count", 0) >= 3:
        results.append(RuleResult(
            rule_id="C3", rule_name="Frequent Impairments", value=trends.get("impairment_count"),
            threshold=">=3 occurrences", flag="YELLOW",
            reason="Poor capital allocation discipline."
        ))

    # D. Goodwill & Intangible Concentration
    # Rule D1 – Goodwill % of Total Assets
    gw_pct = latest.get("goodwill_pct")
    if gw_pct is not None:
        if gw_pct > benchmarks.goodwill_pct_critical:
            results.append(RuleResult(
                rule_id="D1", rule_name="Goodwill % of Total Assets", value=gw_pct,
                threshold=f">{benchmarks.goodwill_pct_critical}", flag="RED",
                reason="High acquisition-related risk."
            ))
        elif gw_pct > benchmarks.goodwill_pct_warning:
            results.append(RuleResult(
                rule_id="D1", rule_name="Goodwill % of Total Assets", value=gw_pct,
                threshold=f">{benchmarks.goodwill_pct_warning}", flag="YELLOW",
                reason="Heavy reliance on acquisitions."
            ))
        else:
            results.append(RuleResult(
                rule_id="D1", rule_name="Goodwill % of Total Assets", value=gw_pct,
                threshold=f"<{benchmarks.goodwill_pct_warning}", flag="GREEN",
                reason="Goodwill levels are acceptable."
            ))

    # Rule D2 – Goodwill Rising Faster than Revenue
    gw_cagr = trends.get("goodwill_cagr")
    rev_cagr = trends.get("revenue_cagr")
    if gw_cagr is not None and rev_cagr is not None:
        if gw_cagr > (rev_cagr + 10.0):
            results.append(RuleResult(
                rule_id="D2", rule_name="Goodwill Rising Faster than Revenue", value=gw_cagr - rev_cagr,
                threshold=">10% spread", flag="YELLOW",
                reason="Acquisitions may not be revenue-accretive."
            ))

    # Rule D3 – Intangibles Growing Without Operating Asset Growth
    int_cagr = trends.get("intangible_cagr")
    op_cagr = trends.get("op_asset_cagr")
    if int_cagr is not None and op_cagr is not None:
        if int_cagr > (op_cagr + 15.0):
            results.append(RuleResult(
                rule_id="D3", rule_name="Intangibles Growing Without Operating Asset Growth", value=int_cagr - op_cagr,
                threshold=">15% spread", flag="YELLOW",
                reason="Excessive capitalization of development costs / risky growth."
            ))

    # E. Intangible Asset Quality Rules
    # Rule E1 – Amortization vs New Intangible Additions
    # Amortization << new intangibles added
    # We need "New Intangible Additions".
    # New Intangibles ~ (Intangibles_t - Intangibles_t-1) + Amortization_t
    # If Amortization < 0.5 * New Intangibles (heuristic for "<<")
    # Let's check the latest year.
    if len(years) >= 2:
        prev_int = metrics[years[-2]].get("intangibles") or 0
        curr_int = latest.get("intangibles") or 0
        amort = latest.get("intangible_amortization") or 0
        
        new_intangibles = (curr_int - prev_int) + amort
        if new_intangibles > 0 and amort < (0.2 * new_intangibles): # Using 20% as "<<" threshold
             results.append(RuleResult(
                rule_id="E1", rule_name="Amortization vs New Intangible Additions", value=amort/new_intangibles,
                threshold="<0.2 ratio", flag="YELLOW",
                reason="Rapid buildup in intangibles (could indicate low-quality capitalization)."
            ))

    # Rule E2 – R&D Spend vs Intangible Creation
    # If R&D << intangible addition
    rnd = latest.get("r_and_d_expenses") or 0
    # Using same new_intangibles calculated above
    if len(years) >= 2 and new_intangibles > 0 and rnd > 0:
        if rnd < (0.3 * new_intangibles): # Using 30% as "<<" threshold
             results.append(RuleResult(
                rule_id="E2", rule_name="R&D Spend vs Intangible Creation", value=rnd/new_intangibles,
                threshold="<0.3 ratio", flag="YELLOW",
                reason="Suspect capitalization policy or aggressive accounting."
            ))

    return results
