from typing import Dict, List

from .debt_models import YearFinancialInput


def safe_div(a, b):
    """Safely divide two numbers, returning None if division is invalid."""
    return a / b if (b not in (0, None) and a is not None) else None


def compute_per_year_metrics(financials_5y: List[YearFinancialInput]) -> Dict[int, dict]:
    """
    Calculate core financial metrics for each year.
    
    Args:
        financials_5y: List of YearFinancialInput objects (5 years of data)
    
    Returns:
        Dict mapping year -> metrics dictionary
    """
    metrics = {}
    sorted_fin = sorted(financials_5y, key=lambda x: x.year)

    for f in sorted_fin:
        total_debt = (f.short_term_debt or 0.0) + (f.long_term_debt or 0.0)
        total_assets = (f.total_equity or 0.0) + total_debt

        # Calculate floating/fixed share (can be provided as ratio or absolute amount)
        floating_share = None
        if f.floating_rate_debt is not None:
            if 0 < f.floating_rate_debt <= 1:
                floating_share = f.floating_rate_debt
            else:
                floating_share = safe_div(f.floating_rate_debt, total_debt)

        fixed_share = None
        if f.fixed_rate_debt is not None:
            if 0 < f.fixed_rate_debt <= 1:
                fixed_share = f.fixed_rate_debt
            else:
                fixed_share = safe_div(f.fixed_rate_debt, total_debt)
        elif floating_share is not None:
            fixed_share = max(0.0, 1 - floating_share)

        # Calculate weighted average cost of debt
        finance_cost_yield = safe_div(f.finance_cost, total_debt)
        wacd = f.weighted_avg_interest_rate if f.weighted_avg_interest_rate is not None else finance_cost_yield

        metrics[f.year] = {
            "year": f.year,
            "short_term_debt": f.short_term_debt,
            "long_term_debt": f.long_term_debt,
            "total_debt": total_debt,
            "total_equity": f.total_equity,
            "ebitda": f.ebitda,
            "ebit": f.ebit,
            "finance_cost": f.finance_cost,
            "capex": f.capex,
            "cwip": f.cwip,
            "revenue": f.revenue,
            "operating_cash_flow": f.operating_cash_flow,
            "total_assets": total_assets,
            
            # Derived metrics
            "st_debt_share": safe_div(f.short_term_debt, total_debt),
            "de_ratio": safe_div(total_debt, f.total_equity),
            "debt_ebitda": safe_div(total_debt, f.ebitda),
            "interest_coverage": safe_div(f.ebit, f.finance_cost),
            "floating_share": floating_share,
            "fixed_share": fixed_share,
            
            # Maturity profile
            "maturity_lt_1y_pct": safe_div(f.total_debt_maturing_lt_1y, total_debt),
            "maturity_1_3y_pct": safe_div(f.total_debt_maturing_1_3y, total_debt),
            "maturity_gt_3y_pct": safe_div(f.total_debt_maturing_gt_3y, total_debt),
            
            # Cost of debt
            "wacd": wacd,
            "finance_cost_yield": finance_cost_yield,
            "ocf_to_debt": safe_div(f.operating_cash_flow, total_debt),
        }

    return metrics
