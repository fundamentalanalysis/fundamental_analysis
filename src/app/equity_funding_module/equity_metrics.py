# =============================================================
# src/app/equity_funding_module/equity_metrics.py
# Core per-year metric calculations for Equity Funding Mix Module
# =============================================================

from typing import Dict, List, Optional
from .equity_models import EquityYearFinancialInput


def safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    """Safe division handling None and zero"""
    if a is None or b is None or b == 0:
        return None
    return a / b


def compute_per_year_metrics(financials_5y: List[EquityYearFinancialInput]) -> Dict[int, dict]:
    """
    Compute per-year equity and funding mix metrics.
    
    Input:  List[EquityYearFinancialInput]
    Output: Dict[year, metrics_dict]
    """
    metrics = {}
    
    # Sort by year ascending
    sorted_fin = sorted(financials_5y, key=lambda x: x.year)
    if not sorted_fin:
        return {}
    
    # Build lookup for previous year data
    year_data = {f.year: f for f in sorted_fin}
    years = [f.year for f in sorted_fin]
    
    for i, f in enumerate(sorted_fin):
        year = f.year
        
        # Get previous year data for YoY calculations
        prev_year_data = None
        if i > 0:
            prev_year = years[i - 1]
            prev_year_data = year_data.get(prev_year)
        
        # Calculate net worth if not provided
        net_worth = f.net_worth
        if net_worth == 0:
            net_worth = f.share_capital + f.reserves_and_surplus
        
        # Calculate average equity for ROE (using current and previous year)
        avg_equity = net_worth
        if prev_year_data:
            prev_net_worth = prev_year_data.net_worth
            if prev_net_worth == 0:
                prev_net_worth = prev_year_data.share_capital + prev_year_data.reserves_and_surplus
            avg_equity = (net_worth + prev_net_worth) / 2
        
        # Total capital for funding mix
        total_capital = net_worth + f.debt_equitymix
        
        # Absolute dividend paid (handle negative values)
        abs_dividend = abs(f.dividend_paid) if f.dividend_paid else 0
        
        # =============================================
        # 3.1 Core Equity & Retained Earnings Metrics
        # =============================================
        
        # Retained Earnings = Reserves & Surplus
        retained_earnings = f.reserves_and_surplus
        
        # Retained Earnings Growth YoY
        re_growth_yoy = None
        if prev_year_data and prev_year_data.reserves_and_surplus and prev_year_data.reserves_and_surplus != 0:
            re_growth_yoy = (f.reserves_and_surplus - prev_year_data.reserves_and_surplus) / prev_year_data.reserves_and_surplus
        
        # Dividend Payout Ratio = Dividend Paid / PAT
        dividend_payout_ratio = safe_div(abs_dividend, f.pat)
        
        # Dividend to FCF Ratio
        dividend_to_fcf_ratio = None
        if f.free_cash_flow is not None and f.free_cash_flow > 0:
            dividend_to_fcf_ratio = safe_div(abs_dividend, f.free_cash_flow)
        
        # Equity Dilution %
        equity_dilution_pct = None
        if prev_year_data and prev_year_data.share_capital and prev_year_data.share_capital != 0:
            equity_dilution_pct = safe_div(f.new_share_issuance, prev_year_data.share_capital)
        
        # =============================================
        # 3.2 Profitability Metrics
        # =============================================
        
        # ROE = PAT / Avg Shareholders' Equity
        roe = safe_div(f.pat, avg_equity)
        
        # =============================================
        # 3.3 Funding Mix Metrics
        # =============================================
        
        # Debt-to-Equity = Debt / Net Worth
        debt_to_equity = safe_div(f.debt_equitymix, net_worth)
        
        # Equity Growth Rate YoY
        equity_growth_yoy = None
        if prev_year_data and prev_year_data.share_capital and prev_year_data.share_capital != 0:
            equity_growth_yoy = (f.share_capital - prev_year_data.share_capital) / prev_year_data.share_capital
        
        # Net Worth Growth YoY
        networth_growth_yoy = None
        if prev_year_data:
            prev_nw = prev_year_data.net_worth
            if prev_nw == 0:
                prev_nw = prev_year_data.share_capital + prev_year_data.reserves_and_surplus
            if prev_nw != 0:
                networth_growth_yoy = (net_worth - prev_nw) / prev_nw
        
        # Debt Growth Rate YoY
        debt_growth_yoy = None
        if prev_year_data and prev_year_data.debt_equitymix and prev_year_data.debt_equitymix != 0:
            debt_growth_yoy = (f.debt_equitymix - prev_year_data.debt_equitymix) / prev_year_data.debt_equitymix
        
        # Equity Ratio = Net Worth / Total Capital
        equity_ratio = safe_div(net_worth, total_capital)
        
        # Debt Ratio = Debt / Total Capital
        debt_ratio = safe_div(f.debt_equitymix, total_capital)
        
        # PAT Growth YoY
        pat_growth_yoy = None
        if prev_year_data and prev_year_data.pat and prev_year_data.pat != 0:
            pat_growth_yoy = (f.pat - prev_year_data.pat) / prev_year_data.pat
        
        # Payout ratio change
        payout_change_yoy = None
        if prev_year_data:
            prev_payout = safe_div(abs(prev_year_data.dividend_paid) if prev_year_data.dividend_paid else 0, 
                                   prev_year_data.pat)
            if prev_payout is not None and dividend_payout_ratio is not None:
                payout_change_yoy = dividend_payout_ratio - prev_payout
        
        # Build metrics dictionary
        m = {
            "year": year,
            
            # Raw values
            "share_capital": f.share_capital,
            "reserves_and_surplus": f.reserves_and_surplus,
            "net_worth": net_worth,
            "pat": f.pat,
            "dividend_paid": f.dividend_paid,
            "abs_dividend": abs_dividend,
            "free_cash_flow": f.free_cash_flow,
            "new_share_issuance": f.new_share_issuance,
            "debt": f.debt_equitymix,
            
            # Derived metrics - Retained Earnings
            "retained_earnings": retained_earnings,
            "re_growth_yoy": re_growth_yoy,
            
            # Derived metrics - Dividend
            "dividend_payout_ratio": dividend_payout_ratio,
            "dividend_to_fcf_ratio": dividend_to_fcf_ratio,
            "payout_change_yoy": payout_change_yoy,
            
            # Derived metrics - Dilution
            "equity_dilution_pct": equity_dilution_pct,
            
            # Derived metrics - Profitability
            "roe": roe,
            "avg_equity": avg_equity,
            
            # Derived metrics - Funding Mix
            "debt_to_equity": debt_to_equity,
            "equity_growth_yoy": equity_growth_yoy,
            "networth_growth_yoy": networth_growth_yoy,
            "debt_growth_yoy": debt_growth_yoy,
            "equity_ratio": equity_ratio,
            "debt_ratio": debt_ratio,
            
            # PAT metrics
            "pat_growth_yoy": pat_growth_yoy,
            
            # Total capital
            "total_capital": total_capital,
        }
        
        metrics[year] = m
    
    return metrics


def compute_yoy_percentage(metrics_by_year: Dict[int, dict]) -> Dict[str, dict]:
    """
    Converts absolute per-year metrics into YoY % growth for display.
    Output will have years in descending order: latest → oldest
    """
    yoy_output = {}
    
    years = sorted(metrics_by_year.keys())
    if not years:
        return {}
    
    # Metrics to compute YoY for (skip already computed YoY and ratios)
    skip_metrics = {'year', 're_growth_yoy', 'equity_growth_yoy', 'debt_growth_yoy', 
                    'networth_growth_yoy', 'pat_growth_yoy', 'payout_change_yoy'}
    ratio_metrics = {'dividend_payout_ratio', 'dividend_to_fcf_ratio', 'equity_dilution_pct',
                     'roe', 'debt_to_equity', 'equity_ratio', 'debt_ratio'}
    
    metric_keys = [k for k in metrics_by_year[years[0]].keys() 
                   if k not in skip_metrics and k not in ratio_metrics]
    
    for metric in metric_keys:
        temp_dict = {}
        for i, year in enumerate(years):
            label = f"Mar {year}"
            if i == 0:
                temp_dict[label] = None
            else:
                prev_year = years[i - 1]
                curr_val = metrics_by_year[year].get(metric)
                prev_val = metrics_by_year[prev_year].get(metric)
                
                if curr_val is None or prev_val in (None, 0):
                    temp_dict[label] = None
                else:
                    pct_change = ((curr_val - prev_val) / abs(prev_val)) * 100
                    temp_dict[label] = f"{round(pct_change, 1)}%"
        
        yoy_output[metric] = dict(sorted(temp_dict.items(), reverse=True))
    
    return yoy_output
