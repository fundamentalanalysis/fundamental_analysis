from typing import Dict, List, Optional

def compute_cagr(start, end, years) -> Optional[float]:
    if start in (None, 0) or end in (None, 0) or start <= 0 or years <= 0:
        return None
    return ((end / start) ** (1 / years) - 1) * 100

def compute_yoy(current, previous) -> Optional[float]:
    if previous in (None, 0) or current is None:
        return None
    return (current - previous) / previous * 100

def _has_consecutive_trend(values: List[Optional[float]], direction: str, span: int) -> bool:
    if len(values) < span:
        return False
    cmp = (lambda a, b: a > b) if direction == "up" else (lambda a, b: a < b)
    streak = 0
    for prev, curr in zip(values, values[1:]):
        if prev is None or curr is None:
            streak = 0
            continue
        if cmp(curr, prev):
            streak += 1
            if streak >= span - 1:
                return True
        else:
            streak = 0
    return False

def compute_trend_metrics(yearly: Dict[int, dict]) -> Dict[str, any]:
    years = sorted(yearly.keys())
    if len(years) < 2:
        return {}

    first_year = years[0]
    last_year = years[-1]
    num_years = len(years) - 1

    # CAGR Calculations
    revenue_cagr = compute_cagr(yearly[first_year]["revenue"], yearly[last_year]["revenue"], num_years)
    intangible_cagr = compute_cagr(yearly[first_year]["intangibles"], yearly[last_year]["intangibles"], num_years)
    goodwill_cagr = compute_cagr(yearly[first_year]["goodwill"], yearly[last_year]["goodwill"], num_years)
    
    # Operating Asset CAGR (Net Block + CWIP)
    op_asset_start = (yearly[first_year]["net_block"] or 0) + (yearly[first_year]["cwip"] or 0)
    op_asset_end = (yearly[last_year]["net_block"] or 0) + (yearly[last_year]["cwip"] or 0)
    op_asset_cagr = compute_cagr(op_asset_start, op_asset_end, num_years)

    # YoY Calculations and Trends
    impairment_yoy = []
    asset_turnover_values = []
    depreciation_values = []
    capex_values = [] # Not directly in input, but we can infer Net Block change + Dep = Capex approx?
    # Actually, user didn't provide Capex in input for this module.
    # Rule B2 says "Depreciation > Capex".
    # We need Capex.
    # We can approximate Capex = (Net_Block_t - Net_Block_t-1) + Depreciation_t
    # This ignores disposals, but is a standard proxy.
    
    calculated_capex = {}

    for i, year in enumerate(years):
        curr = yearly[year]
        asset_turnover_values.append(curr.get("asset_turnover"))
        depreciation_values.append(curr.get("accumulated_depreciation")) # Wait, this is accumulated.
        # We need "Depreciation Expense" for the year.
        # Depreciation Expense ~ Accumulated_Dep_t - Accumulated_Dep_t-1
        # (ignoring disposals)
        
        if i > 0:
            prev = yearly[years[i-1]]
            
            # Impairment YoY
            curr_imp = curr.get("impairment_loss")
            prev_imp = prev.get("impairment_loss")
            impairment_yoy.append(compute_yoy(curr_imp, prev_imp))
            
            # Capex Proxy
            # Capex ~ (Net_Block_t - Net_Block_t-1) + Dep_Expense_t
            # Dep_Expense_t ~ Acc_Dep_t - Acc_Dep_t-1
            dep_expense = (curr.get("accumulated_depreciation") or 0) - (prev.get("accumulated_depreciation") or 0)
            # If negative, something is wrong (disposals > depreciation), assume 0 or handle?
            dep_expense = max(0, dep_expense)
            
            net_block_change = (curr.get("net_block") or 0) - (prev.get("net_block") or 0)
            capex_proxy = net_block_change + dep_expense
            calculated_capex[year] = capex_proxy
            
            # Store dep expense for comparison
            curr["depreciation_expense_proxy"] = dep_expense

    # Trends
    asset_turnover_declining = _has_consecutive_trend(asset_turnover_values, "down", 3)
    
    # Dep > Capex for 3 years
    dep_gt_capex_streak = 0
    dep_gt_capex_3y = False
    for year in years[1:]: # Skip first year as we don't have capex/dep expense
        dep = yearly[year].get("depreciation_expense_proxy", 0)
        capex = calculated_capex.get(year, 0)
        if dep > capex:
            dep_gt_capex_streak += 1
        else:
            dep_gt_capex_streak = 0
        if dep_gt_capex_streak >= 3:
            dep_gt_capex_3y = True

    # Impairment Frequency
    impairment_count = sum(1 for y in years if (yearly[y].get("impairment_loss") or 0) > 0)

    return {
        "revenue_cagr": revenue_cagr,
        "intangible_cagr": intangible_cagr,
        "goodwill_cagr": goodwill_cagr,
        "op_asset_cagr": op_asset_cagr,
        "impairment_yoy": impairment_yoy,
        "asset_turnover_declining": asset_turnover_declining,
        "dep_gt_capex_3y": dep_gt_capex_3y,
        "impairment_count": impairment_count,
        "calculated_capex": calculated_capex
    }
