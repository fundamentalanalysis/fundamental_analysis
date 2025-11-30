# =============================================================
# src/app/equity_funding_module/equity_trend.py
# Trend calculations for Equity & Funding Mix Module
# =============================================================

from typing import Dict, List, Optional


def compute_cagr(start: Optional[float], end: Optional[float], years: int) -> Optional[float]:
    """
    Compute Compound Annual Growth Rate.
    Returns percentage value (e.g., 7.5 for 7.5%)
    """
    if start is None or end is None or start <= 0 or years <= 0:
        return None
    return ((end / start) ** (1 / years) - 1) * 100


def compute_yoy(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    """Compute Year-over-Year growth rate"""
    if previous is None or previous == 0 or current is None:
        return None
    return (current - previous) / abs(previous) * 100


def compute_trend_slope(values: List[Optional[float]]) -> Optional[float]:
    """
    Compute linear trend slope using simple linear regression.
    Positive slope = improving, Negative slope = declining
    """
    # Filter out None values
    valid_values = [(i, v) for i, v in enumerate(values) if v is not None]
    
    if len(valid_values) < 2:
        return None
    
    n = len(valid_values)
    sum_x = sum(i for i, _ in valid_values)
    sum_y = sum(v for _, v in valid_values)
    sum_xy = sum(i * v for i, v in valid_values)
    sum_x2 = sum(i * i for i, _ in valid_values)
    
    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        return 0
    
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    return slope


def is_declining_trend(values: List[Optional[float]], consecutive_years: int = 3) -> bool:
    """Check if values show a declining trend for consecutive years"""
    # Filter out None values
    valid_values = [v for v in values if v is not None]
    
    if len(valid_values) < consecutive_years:
        return False
    
    # Check last N years
    recent = valid_values[-consecutive_years:]
    
    # Check if each year is less than the previous
    for i in range(1, len(recent)):
        if recent[i] >= recent[i - 1]:
            return False
    
    return True


def compute_trend_metrics(
    financials: List,
    yearly_metrics: Dict[int, dict]
) -> Dict[str, any]:
    """
    Compute trend metrics for Equity Funding Mix analysis.
    
    Returns:
        Dictionary of trend metrics including CAGRs, slopes, and flags
    """
    years = sorted(yearly_metrics.keys())
    
    if len(years) < 2:
        return {}
    
    first_year = years[0]
    last_year = years[-1]
    num_years = len(years) - 1
    
    # =============================================
    # 1. CAGR Calculations
    # =============================================
    
    # Retained Earnings CAGR
    re_start = yearly_metrics[first_year].get("retained_earnings")
    re_end = yearly_metrics[last_year].get("retained_earnings")
    retained_earnings_cagr = compute_cagr(re_start, re_end, num_years)
    
    # Net Worth CAGR
    nw_start = yearly_metrics[first_year].get("net_worth")
    nw_end = yearly_metrics[last_year].get("net_worth")
    networth_cagr = compute_cagr(nw_start, nw_end, num_years)
    
    # Equity (Share Capital) CAGR
    eq_start = yearly_metrics[first_year].get("share_capital")
    eq_end = yearly_metrics[last_year].get("share_capital")
    equity_cagr = compute_cagr(eq_start, eq_end, num_years)
    
    # Debt CAGR
    debt_start = yearly_metrics[first_year].get("debt")
    debt_end = yearly_metrics[last_year].get("debt")
    debt_cagr = compute_cagr(debt_start, debt_end, num_years)
    
    # PAT CAGR
    pat_start = yearly_metrics[first_year].get("pat")
    pat_end = yearly_metrics[last_year].get("pat")
    pat_cagr = compute_cagr(pat_start, pat_end, num_years)
    
    # Dividend CAGR
    div_start = yearly_metrics[first_year].get("abs_dividend")
    div_end = yearly_metrics[last_year].get("abs_dividend")
    dividend_cagr = compute_cagr(div_start, div_end, num_years) if div_start and div_end else None
    
    # =============================================
    # 2. Trend Analysis (Slopes)
    # =============================================
    
    # ROE trend
    roe_values = [yearly_metrics[y].get("roe") for y in years]
    roe_trend_slope = compute_trend_slope(roe_values)
    roe_declining_3y = is_declining_trend(roe_values, 3)
    
    # Payout ratio trend
    payout_values = [yearly_metrics[y].get("dividend_payout_ratio") for y in years]
    payout_ratio_trend = compute_trend_slope(payout_values)
    
    # Debt to equity trend
    de_values = [yearly_metrics[y].get("debt_to_equity") for y in years]
    de_trend = compute_trend_slope(de_values)
    
    # =============================================
    # 3. YoY Growth Lists
    # =============================================
    
    # RE YoY growth list
    re_yoy_growth = []
    for i in range(1, len(years)):
        prev_y = years[i - 1]
        curr_y = years[i]
        growth = compute_yoy(
            yearly_metrics[curr_y].get("retained_earnings"),
            yearly_metrics[prev_y].get("retained_earnings")
        )
        re_yoy_growth.append(growth)
    
    # ROE YoY list
    roe_yoy = []
    for i in range(1, len(years)):
        prev_y = years[i - 1]
        curr_y = years[i]
        growth = compute_yoy(
            yearly_metrics[curr_y].get("roe"),
            yearly_metrics[prev_y].get("roe")
        )
        roe_yoy.append(growth)
    
    # =============================================
    # 4. Computed Flags for Rules
    # =============================================
    
    # Check if debt is outpacing equity growth
    debt_outpacing_equity = False
    if debt_cagr is not None and equity_cagr is not None:
        debt_outpacing_equity = debt_cagr > (equity_cagr + 10)  # 10% threshold
    
    # Check if networth is stagnant while debt is rising
    networth_stagnant_debt_rising = False
    if networth_cagr is not None and debt_cagr is not None:
        networth_stagnant_debt_rising = networth_cagr < 0 and debt_cagr > 0
    
    # Check dilution without earnings growth
    dilution_without_earnings = False
    latest_dilution = yearly_metrics[last_year].get("equity_dilution_pct")
    if latest_dilution is not None and pat_cagr is not None:
        dilution_without_earnings = latest_dilution > 0.05 and pat_cagr < 5
    
    # Check payout rising while PAT stagnant
    payout_rising_pat_stagnant = False
    if payout_ratio_trend is not None and pat_cagr is not None:
        payout_rising_pat_stagnant = payout_ratio_trend > 0.02 and pat_cagr < 5
    
    # Average metrics
    avg_roe = sum(v for v in roe_values if v is not None) / len([v for v in roe_values if v is not None]) if any(v is not None for v in roe_values) else None
    avg_payout = sum(v for v in payout_values if v is not None) / len([v for v in payout_values if v is not None]) if any(v is not None for v in payout_values) else None
    
    return {
        # CAGRs
        "retained_earnings_cagr": retained_earnings_cagr,
        "networth_cagr": networth_cagr,
        "equity_cagr": equity_cagr,
        "debt_cagr": debt_cagr,
        "pat_cagr": pat_cagr,
        "dividend_cagr": dividend_cagr,
        
        # Trend slopes
        "roe_trend_slope": roe_trend_slope,
        "payout_ratio_trend": payout_ratio_trend,
        "de_trend": de_trend,
        
        # YoY lists
        "re_yoy_growth": re_yoy_growth,
        "roe_yoy": roe_yoy,
        
        # Computed flags
        "roe_declining_3y": roe_declining_3y,
        "debt_outpacing_equity": debt_outpacing_equity,
        "networth_stagnant_debt_rising": networth_stagnant_debt_rising,
        "dilution_without_earnings": dilution_without_earnings,
        "payout_rising_pat_stagnant": payout_rising_pat_stagnant,
        
        # Averages
        "avg_roe_5y": avg_roe,
        "avg_payout_5y": avg_payout,
        
        # Helper comparisons
        "debt_vs_equity_growth": (
            debt_cagr - equity_cagr
            if (debt_cagr is not None and equity_cagr is not None)
            else None
        ),
    }
