
from typing import Dict, List, Optional

def compute_cagr(start, end, years) -> Optional[float]:
    if start in (None, 0) or end in (None, 0) or start <= 0 or years <= 0:
        return None
    return ((end / start) ** (1 / years) - 1) * 100

def compute_yoy(current, previous) -> Optional[float]:
    if previous in (None, 0) or current is None:
        return None
    return (current - previous) / previous 

def build_year_map(values: List[float]) -> Dict[str, float]:
    mapping = {}
    # values are expected to be oldest to newest
    # so reversed(values) gives newest (Y) to oldest (Y-n)
    for idx, val in enumerate(reversed(values)):
        if idx == 0:
            mapping["Y"] = val
        else:
            mapping[f"Y-{idx}"] = val
    return mapping

def build_yoy_map(values: List[float]) -> Dict[str, float]:
    yoy_map = {}
    n = len(values)
    # values: [oldest, ..., newest]
    # We want to compare newest vs previous, etc.
    # The loop range(1, n) goes from index 1 to n-1
    # i=1: values[1] vs values[0] (oldest pair) -> Y-(n-2) vs Y-(n-1) ?
    # Let's align with the requested format:
    # "Y_vs_Y-1" is the most recent growth.
    
    # Let's iterate backwards to match the label generation easier, or just map indices.
    # values[n-1] is Y
    # values[n-2] is Y-1
    # ...
    
    # The example output shows:
    # "Y_vs_Y-1": ...
    # "Y-1_vs_Y-2": ...
    
    # Let's iterate from newest to oldest pair
    # i goes from 0 to n-2
    # current is n-1-i (Y-i)
    # previous is n-2-i (Y-(i+1))
    
    for i in range(n - 1):
        curr_idx = n - 1 - i
        prev_idx = n - 2 - i
        
        curr_val = values[curr_idx]
        prev_val = values[prev_idx]
        
        if i == 0:
            label = "Y_vs_Y-1"
        else:
            label = f"Y-{i}_vs_Y-{i+1}"
            
        yoy_val = compute_yoy(curr_val, prev_val)
        yoy_map[label] = round(yoy_val, 2) if yoy_val is not None else None
        
    return yoy_map

def generate_insight(yoy_list: List[Optional[float]], metric_name: str) -> str:
    numeric = [v for v in yoy_list if v is not None]
    if not numeric:
        return f"No sufficient data to analyse {metric_name} trend."
    
    avg_growth = sum(numeric) / len(numeric)
    avg_growth = round(avg_growth, 1)
    
    # Check for consistent trends in the last few years if available
    if len(numeric) >= 3:
        # Simple heuristic: compare last point vs first point of the available series
        # Note: yoy_list passed here should probably be chronological for this logic to make sense?
        # The example code passed `st_yoy_list` which was constructed chronologically.
        
        if numeric[-1] > numeric[0] * 1.20: # This logic in the example seems to compare the *growth rates* themselves?
            # "numeric[-1] > numeric[0] * 1.20" means the latest growth rate is 20% higher than the earliest growth rate in the list.
            # This implies "accelerating growth" (growth rate is increasing).
             return f"{metric_name} shows accelerating growth pattern (avg: {avg_growth}%)."
        
        if numeric[-1] < numeric[0] * 0.80:
             return f"{metric_name} shows declining pattern (avg: {avg_growth}%)."
             
    return f"{metric_name} exhibits mixed trend with average YoY growth of {avg_growth}%."

def compute_trend_output(financials: List) -> Dict[str, dict]:

    # ✅ NEW FIX: Ensure financials are sorted from oldest → newest
    financials = sorted(financials, key=lambda x: x.year)

    # Extract values in chronological order (oldest to newest)

    # Extract values in chronological order (oldest to newest)
    # Assuming 'financials' is a list of objects with attributes:
    # trade_receivables, inventory, trade_payables
    
    receivables_values = [f.trade_receivables for f in financials]
    inventory_values = [f.inventory for f in financials]
    payables_values = [f.trade_payables for f in financials]
    revenue_values = [f.revenue for f in financials]

    # YoY lists (percentage growth) - Chronological order for insight generation
    # range(1, len) -> i=1 compares values[1] vs values[0]
    rcv_yoy_list = [compute_yoy(receivables_values[i], receivables_values[i - 1]) for i in range(1, len(receivables_values))]
    inv_yoy_list = [compute_yoy(inventory_values[i], inventory_values[i - 1]) for i in range(1, len(inventory_values))]
    pay_yoy_list = [compute_yoy(payables_values[i], payables_values[i - 1]) for i in range(1, len(payables_values))]
    rev_yoy_list = [compute_yoy(revenue_values[i], revenue_values[i - 1]) for i in range(1, len(revenue_values))]

    output = {
        "trade_receivables": {
            "values": build_year_map(receivables_values),
            "yoy_growth_pct": build_yoy_map(receivables_values),
            "insight": generate_insight(rcv_yoy_list, "Trade Receivables")
        },
        "inventory": {
            "values": build_year_map(inventory_values),
            "yoy_growth_pct": build_yoy_map(inventory_values),
            "insight": generate_insight(inv_yoy_list, "Inventory")
        },
        "trade_payables": {
            "values": build_year_map(payables_values),
            "yoy_growth_pct": build_yoy_map(payables_values),
            "insight": generate_insight(pay_yoy_list, "Trade Payables")
        },
        "revenue": {
            "values": build_year_map(revenue_values),
            "yoy_growth_pct": build_yoy_map(revenue_values),
            "insight": generate_insight(rev_yoy_list, "Revenue")
        }
    }
    return output
