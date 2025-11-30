# =============================================================
# test_equity_funding_module.py
# Test script for the Equity & Funding Mix Module
# =============================================================

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app.equity_funding_module.equity_models import (
    EquityFundingInput,
    EquityYearFinancialInput,
    EquityBenchmarks,
)
from src.app.equity_funding_module.equity_metrics import compute_per_year_metrics
from src.app.equity_funding_module.equity_trend import compute_trend_metrics
from src.app.equity_funding_module.equity_rules import apply_rules


def test_reliance_data():
    """Test with Reliance Industries data from all_input.txt"""
    
    # Create financial data from the input file
    financials = [
        EquityYearFinancialInput(
            year=2024,
            share_capital=6766,
            reserves_and_surplus=786715,
            net_worth=793481,
            pat=79020,
            dividend_paid=-6089,
            free_cash_flow=127528,
            new_share_issuance=20915,
            debt_equitymix=324622,
        ),
        EquityYearFinancialInput(
            year=2023,
            share_capital=6766,
            reserves_and_surplus=709106,
            net_worth=715872,
            pat=74088,
            dividend_paid=-5083,
            free_cash_flow=86132,
            new_share_issuance=479,
            debt_equitymix=426813,
        ),
        EquityYearFinancialInput(
            year=2022,
            share_capital=6765,
            reserves_and_surplus=772720,
            net_worth=779485,
            pat=67845,
            dividend_paid=-4297,
            free_cash_flow=83154,
            new_share_issuance=455,
            debt_equitymix=303489,
        ),
        EquityYearFinancialInput(
            year=2021,
            share_capital=6445,
            reserves_and_surplus=693727,
            net_worth=700172,
            pat=53739,
            dividend_paid=-3921,
            free_cash_flow=958,
            new_share_issuance=5,
            debt_equitymix=270648,
        ),
        EquityYearFinancialInput(
            year=2020,
            share_capital=6339,
            reserves_and_surplus=442827,
            net_worth=449166,
            pat=39880,
            dividend_paid=-4592,
            free_cash_flow=70377,
            new_share_issuance=129,
            debt_equitymix=310256,
        ),
    ]
    
    # Compute metrics
    print("=" * 60)
    print("RELIANCE INDUSTRIES - EQUITY & FUNDING MIX ANALYSIS")
    print("=" * 60)
    
    # Per-year metrics
    per_year_metrics = compute_per_year_metrics(financials)
    
    print("\n--- PER-YEAR METRICS (Latest Year: 2024) ---")
    m = per_year_metrics[2024]
    print(f"  Net Worth: {m['net_worth']:,.0f}")
    print(f"  Retained Earnings: {m['retained_earnings']:,.0f}")
    print(f"  PAT: {m['pat']:,.0f}")
    print(f"  ROE: {m['roe']*100:.2f}%")
    print(f"  Dividend Payout Ratio: {m['dividend_payout_ratio']*100:.2f}%")
    print(f"  Dividend to FCF Ratio: {m['dividend_to_fcf_ratio']*100:.2f}%")
    print(f"  RE Growth YoY: {m['re_growth_yoy']*100:.2f}%" if m['re_growth_yoy'] else "  RE Growth YoY: N/A")
    print(f"  Equity Dilution: {m['equity_dilution_pct']*100:.2f}%" if m['equity_dilution_pct'] else "  Equity Dilution: N/A")
    print(f"  Debt-to-Equity: {m['debt_to_equity']:.2f}")
    print(f"  Equity Ratio: {m['equity_ratio']*100:.2f}%")
    
    # Trend metrics
    trend_metrics = compute_trend_metrics(financials, per_year_metrics)
    
    print("\n--- TREND METRICS (5-Year) ---")
    print(f"  Retained Earnings CAGR: {trend_metrics['retained_earnings_cagr']:.2f}%")
    print(f"  Net Worth CAGR: {trend_metrics['networth_cagr']:.2f}%")
    print(f"  PAT CAGR: {trend_metrics['pat_cagr']:.2f}%")
    print(f"  Debt CAGR: {trend_metrics['debt_cagr']:.2f}%")
    print(f"  Average ROE (5Y): {trend_metrics['avg_roe_5y']*100:.2f}%")
    print(f"  ROE Declining 3Y: {trend_metrics['roe_declining_3y']}")
    print(f"  Debt Outpacing Equity: {trend_metrics['debt_outpacing_equity']}")
    
    # Apply rules
    benchmarks = EquityBenchmarks()
    rule_results = apply_rules(financials, per_year_metrics, trend_metrics, benchmarks)
    
    print("\n--- RULE RESULTS ---")
    red_count = sum(1 for r in rule_results if r.flag == "RED")
    yellow_count = sum(1 for r in rule_results if r.flag == "YELLOW")
    green_count = sum(1 for r in rule_results if r.flag == "GREEN")
    
    print(f"  RED Flags: {red_count}")
    print(f"  YELLOW Flags: {yellow_count}")
    print(f"  GREEN Flags: {green_count}")
    
    print("\n  --- Detailed Rules ---")
    for r in rule_results:
        flag_emoji = "🔴" if r.flag == "RED" else "🟡" if r.flag == "YELLOW" else "🟢"
        print(f"  {flag_emoji} [{r.rule_id}] {r.rule_name}")
        print(f"      → {r.reason}")
    
    # Calculate score
    from collections import Counter
    c = Counter([r.flag for r in rule_results])
    score = 70 - (10 * c["RED"]) - (5 * c["YELLOW"]) + (1 * c["GREEN"])
    score = max(0, min(100, score))
    
    print(f"\n--- FINAL SCORE ---")
    print(f"  Adjusted Sub-Score: {score}/100")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    test_reliance_data()
