from typing import Dict, List, Optional

try:
    from .qoe_models import QoEYearInput
except ImportError:
    from qoe_models import QoEYearInput


# ---------------------------------------------------------
# SAFE DIVISION
# ---------------------------------------------------------
def safe_div(a, b):
    """Safely divide two numbers, returning None if invalid."""
    return a / b if (b not in (0, None) and a is not None) else None


# ---------------------------------------------------------
# METRIC CALCULATIONS
# ---------------------------------------------------------
def calc_qoe(cfo, net_income):
    """CFO / Net Income"""
    return safe_div(cfo, net_income)


def calc_accruals_ratio(net_income, cfo, total_assets):
    """(Net Income – CFO) / Total Assets"""
    if total_assets in (None, 0):
        return None
    return (net_income - cfo) / total_assets


def calc_revenue_quality(cfo, revenue):
    """CFO / Revenue"""
    return safe_div(cfo, revenue)


def calc_dso(receivables, revenue):
    """(Receivables / Revenue) * 365"""
    if revenue in (None, 0):
        return None
    return (receivables / revenue) * 365


def calc_wc_adjusted_income(net_income, wc_change):
    """Net Income - Working Capital Change"""
    if net_income is None or wc_change is None:
        return None
    return net_income - wc_change


def calc_other_income_ratio(other_income, net_income):
    """Other Income / Net Income"""
    return safe_div(other_income, net_income)


# ---------------------------------------------------------
# YEAR EXTRACTION
# ---------------------------------------------------------
def extract_year_int(year_str):
    """Extract integer from inputs like 'Mar 2024' or '2024'."""
    if isinstance(year_str, int):
        return year_str
    try:
        return int(str(year_str).split()[-1])
    except:
        import re
        match = re.search(r"\d{4}", str(year_str))
        return int(match.group()) if match else 0


# ---------------------------------------------------------
# MAIN METRIC ENGINE
# ---------------------------------------------------------
def compute_qoe_metrics_per_year(financials_5y: List[QoEYearInput]) -> Dict[int, dict]:
    """
    Calculate Quality of Earnings metrics for each year.
    
    Returns:
        Dict mapping year -> metrics
    """
    metrics = {}

    # Sort oldest -> newest
    sorted_fin = sorted(financials_5y, key=lambda x: extract_year_int(x.year))
    print(f"\nDEBUG: Sorted QoE financial years: {[f.year for f in sorted_fin]}")
    print(f"DEBUG: Computing QoE metrics...", sorted_fin)

    for f in sorted_fin:

        # -----------------------------
        # DERIVED METRICS
        # -----------------------------
        qoe = calc_qoe(f.cash_from_operating_activity, f.net_profit)
        accruals_ratio = calc_accruals_ratio(f.net_profit, f.cash_from_operating_activity, f.total_assets)
        revenue_quality = calc_revenue_quality(f.cash_from_operating_activity, f.revenue)

        # DSO — use provided OR compute internally
        dso = f.dso if f.dso is not None else calc_dso(f.Trade_receivables, f.revenue)

        wc_adjusted_income = calc_wc_adjusted_income(f.net_profit, f.working_capital_changes)
        other_income_ratio = calc_other_income_ratio(f.other_income, f.net_profit)

        year_int = extract_year_int(f.year)

        metrics[year_int] = {
            # ----------------------------------
            # RAW INPUTS
            # ----------------------------------
            "year": year_int,
            "year_label": f.year,

            "operating_cash_flow": f.cash_from_operating_activity,
            "net_income": f.net_profit,
            "change_in_working_capital": f.working_capital_changes,
            "receivables": f.Trade_receivables,
            "revenue": f.revenue,
            "total_assets": f.total_assets,
            "other_income": f.other_income,

            # ----------------------------------
            # DERIVED QoE METRICS
            # ----------------------------------
            "qoe": qoe,
            "accruals_ratio": accruals_ratio,
            "revenue_quality": revenue_quality,
            "dso": dso,
            "wc_adjusted_income": wc_adjusted_income,
            "other_income_ratio": other_income_ratio,
        }

        print(f"DEBUG: QoE metrics for {f.year}: {metrics[year_int]}")

    print("\nDEBUG: FINAL COMPUTED QoE METRICS:", metrics)
    return metrics
