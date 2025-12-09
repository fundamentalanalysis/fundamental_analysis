
from typing import Dict, List, Optional

try:
    from .wc_models import YearFinancialInput
except ImportError:
    from wc_models import YearFinancialInput

def safe_div(a, b):
    """Safely divide two numbers, returning None if division is invalid."""
    return a / b if (b not in (0, None) and a is not None) else None

def calc_dso(rec, revenue):
    return (rec / revenue) * 365 if revenue else None

def calc_dio(inv, cogs):
    return (inv / cogs) * 365 if cogs else None

def calc_dpo(payables, cogs):
    return (payables / cogs) * 365 if cogs else None

def calc_ccc(dso, dio, dpo):
    if None in (dso, dio, dpo):
        return None
    return dso + dio - dpo

def calc_nwc(rec, inv, pay):
    return rec + inv - pay

def calc_nwc_ratio(nwc, revenue):
    return safe_div(nwc, revenue)

def extract_year_int(year_str):
    """Extract integer year from string like 'Mar 2024' or just '2024'"""
    if isinstance(year_str, int):
        return year_str
    # Try to extract the last part which should be the year
    parts = str(year_str).split()
    return int(parts[-1])

def compute_per_year_metrics(financials_5y: List[YearFinancialInput]) -> Dict[int, dict]:
    """
    Calculate core working capital metrics for each year.
    
    Args:
        financials_5y: List of YearFinancialInput objects
    
    Returns:
        Dict mapping year -> metrics dictionary
    """
    metrics = {}
    sorted_fin = sorted(financials_5y, key=lambda x: extract_year_int(x.year))
    print(f"DEBUG: Sorted financial years: {[f.year for f in sorted_fin]}")

    for f in sorted_fin:
        # Core WC Metrics
        dso = calc_dso(f.Trade_receivables, f.revenue)
        dio = calc_dio(f.inventories, f.cogs)
        dpo = calc_dpo(f.trade_payables, f.cogs)
        ccc = calc_ccc(dso, dio, dpo)
        nwc = calc_nwc(f.Trade_receivables, f.inventories, f.trade_payables)
        nwc_ratio = calc_nwc_ratio(nwc, f.revenue)
        
        # Use integer year as key
        year_int = extract_year_int(f.year)

        metrics[year_int] = {
            "year": year_int,
            "year_label": f.year,  # Keep original label
            "trade_receivables": f.Trade_receivables,
            "inventory": f.inventories,
            "trade_payables": f.trade_payables,
            "revenue": f.revenue,
            "cogs": f.cogs,
            
            # Calculated Metrics
            "dso": dso,
            "dio": dio,
            "dpo": dpo,
            "ccc": ccc,
            "nwc": nwc,
            "nwc_ratio": nwc_ratio,
        }
    print(f"DEBUG: Computed per year metrics: {metrics}")
    return metrics
