# =============================================================
# src/app/equity_funding_module/equity_rules.py
# Deterministic rule engine for Equity & Funding Mix Module
# =============================================================

from typing import Dict, List, Optional
from .equity_models import EquityRuleResult, EquityBenchmarks


def make_rule(
    flag: str,
    rule_id: str,
    name: str,
    value: Optional[float],
    threshold: str,
    reason: str
) -> EquityRuleResult:
    """Factory function to create rule results"""
    return EquityRuleResult(
        rule_id=rule_id,
        rule_name=name,
        flag=flag,
        value=value,
        threshold=threshold,
        reason=reason,
    )


def apply_rules(
    financials: List,
    metrics: Dict[int, dict],
    trends: Dict,
    benchmarks: EquityBenchmarks
) -> List[EquityRuleResult]:
    """
    Apply deterministic rules to evaluate equity & funding mix health.
    
    Rules are organized by category:
    A. Retained Earnings & Internal Capital Formation
    B. ROE Quality Rules
    C. Dividend Policy & Sustainability
    D. Equity Dilution & Capital Raising
    E. Funding Mix: Debt vs Equity
    """
    results = []
    
    # Work with latest year snapshot
    last_year = max(metrics.keys())
    m = metrics[last_year]
    
    # ============================================================
    # A. RETAINED EARNINGS & INTERNAL CAPITAL FORMATION
    # ============================================================
    
    # A1 – Retained Earnings Growth
    re_growth = m.get("re_growth_yoy")
    if re_growth is not None:
        if re_growth < 0:
            results.append(make_rule(
                "RED", "A1", "Retained Earnings Growth",
                re_growth,
                "< 0",
                f"Profit retention deteriorating - negative retained earnings growth ({re_growth*100:.1f}%)"
            ))
        elif re_growth < 0.05:
            results.append(make_rule(
                "YELLOW", "A1", "Retained Earnings Growth",
                re_growth,
                "0-5%",
                f"Weak internal capital formation - RE growth below 5% ({re_growth*100:.1f}%)"
            ))
        else:
            results.append(make_rule(
                "GREEN", "A1", "Retained Earnings Growth",
                re_growth,
                ">= 5%",
                f"Healthy retained earnings growth ({re_growth*100:.1f}%) supporting internal capital formation"
            ))
    
    # A2 – 5-Year Retained Earnings CAGR
    re_cagr = trends.get("retained_earnings_cagr")
    if re_cagr is not None:
        if re_cagr < 0:
            results.append(make_rule(
                "RED", "A2", "Retained Earnings 5Y CAGR",
                re_cagr,
                "< 0%",
                f"Long-term erosion in retained earnings (5Y CAGR: {re_cagr:.1f}%)"
            ))
        elif re_cagr < 5:
            results.append(make_rule(
                "YELLOW", "A2", "Retained Earnings 5Y CAGR",
                re_cagr,
                "0-5%",
                f"Modest retained earnings growth over 5 years (CAGR: {re_cagr:.1f}%)"
            ))
        else:
            results.append(make_rule(
                "GREEN", "A2", "Retained Earnings 5Y CAGR",
                re_cagr,
                ">= 5%",
                f"Strong internal capital accumulation (5Y RE CAGR: {re_cagr:.1f}%)"
            ))
    
    # ============================================================
    # B. ROE QUALITY RULES
    # ============================================================
    
    # B1 – Return on Equity Threshold
    roe = m.get("roe")
    if roe is not None:
        if roe < benchmarks.roe_modest:  # < 10%
            results.append(make_rule(
                "RED", "B1", "Return on Equity",
                roe,
                f"< {benchmarks.roe_modest*100:.0f}%",
                f"Poor returns to equity holders - ROE ({roe*100:.1f}%) below {benchmarks.roe_modest*100:.0f}%"
            ))
        elif roe < benchmarks.roe_good:  # 10-15%
            results.append(make_rule(
                "YELLOW", "B1", "Return on Equity",
                roe,
                f"{benchmarks.roe_modest*100:.0f}-{benchmarks.roe_good*100:.0f}%",
                f"Moderate but acceptable ROE ({roe*100:.1f}%)"
            ))
        else:  # >= 15%
            results.append(make_rule(
                "GREEN", "B1", "Return on Equity",
                roe,
                f">= {benchmarks.roe_good*100:.0f}%",
                f"Strong returns to equity holders - ROE ({roe*100:.1f}%) above {benchmarks.roe_good*100:.0f}%"
            ))
    
    # B2 – ROE Declining Trend (3 consecutive years)
    roe_declining = trends.get("roe_declining_3y", False)
    if roe_declining:
        results.append(make_rule(
            "YELLOW", "B2", "ROE Declining Trend",
            None,
            "3 consecutive years decline",
            "Erosion in profitability and capital efficiency - ROE declining for 3 consecutive years"
        ))
    
    # B3 – Average ROE over 5 years
    avg_roe = trends.get("avg_roe_5y")
    if avg_roe is not None:
        if avg_roe >= benchmarks.roe_good:
            results.append(make_rule(
                "GREEN", "B3", "5-Year Average ROE",
                avg_roe,
                f">= {benchmarks.roe_good*100:.0f}%",
                f"Consistent strong ROE over 5 years (Avg: {avg_roe*100:.1f}%)"
            ))
    
    # ============================================================
    # C. DIVIDEND POLICY & SUSTAINABILITY
    # ============================================================
    
    # C1 – Dividend Payout Ratio Threshold
    payout = m.get("dividend_payout_ratio")
    if payout is not None:
        if payout > benchmarks.high_dividend_to_pat:  # > 100%
            results.append(make_rule(
                "RED", "C1", "Dividend Payout Ratio",
                payout,
                "> 100%",
                f"Paying more than earnings (unsustainable) - payout ratio ({payout*100:.1f}%) exceeds 100%"
            ))
        elif payout > benchmarks.payout_high:  # 50-100%
            results.append(make_rule(
                "YELLOW", "C1", "Dividend Payout Ratio",
                payout,
                f"{benchmarks.payout_high*100:.0f}-100%",
                f"High payouts limiting reinvestment - payout ratio {payout*100:.1f}%"
            ))
        elif payout >= benchmarks.payout_normal:  # 30-50%
            results.append(make_rule(
                "GREEN", "C1", "Dividend Payout Ratio",
                payout,
                f"{benchmarks.payout_normal*100:.0f}-{benchmarks.payout_high*100:.0f}%",
                f"Normal payout discipline - payout ratio {payout*100:.1f}%"
            ))
        else:  # < 30%
            results.append(make_rule(
                "GREEN", "C1", "Dividend Payout Ratio",
                payout,
                f"< {benchmarks.payout_normal*100:.0f}%",
                f"Conservative payout supporting reinvestment - payout ratio {payout*100:.1f}%"
            ))
    
    # C2 – Dividend vs FCF Check
    div_to_fcf = m.get("dividend_to_fcf_ratio")
    if div_to_fcf is not None:
        if div_to_fcf > benchmarks.dividends_exceed_fcf_warning:  # > 100%
            results.append(make_rule(
                "RED", "C2", "Dividend vs FCF Check",
                div_to_fcf,
                "> 100% FCF",
                f"Paying dividends from debt/financing - dividends ({div_to_fcf*100:.1f}%) exceed free cash flow"
            ))
        elif div_to_fcf > 0.80:
            results.append(make_rule(
                "YELLOW", "C2", "Dividend vs FCF Check",
                div_to_fcf,
                "80-100% FCF",
                f"Dividends consuming most of free cash flow ({div_to_fcf*100:.1f}%)"
            ))
        else:
            results.append(make_rule(
                "GREEN", "C2", "Dividend vs FCF Check",
                div_to_fcf,
                "<= 80% FCF",
                f"Sustainable dividend coverage from free cash flow ({div_to_fcf*100:.1f}%)"
            ))
    
    # C3 – Payout Rising While PAT Stagnant
    payout_rising_pat_stagnant = trends.get("payout_rising_pat_stagnant", False)
    if payout_rising_pat_stagnant:
        results.append(make_rule(
            "YELLOW", "C3", "Payout Rising While PAT Stagnant",
            None,
            "Payout ↑ AND PAT CAGR < 5%",
            "Capital discipline risk - payout ratio rising while PAT remains stagnant"
        ))
    
    # ============================================================
    # D. EQUITY DILUTION & CAPITAL RAISING
    # ============================================================
    
    # D1 – Dilution Threshold
    dilution = m.get("equity_dilution_pct")
    if dilution is not None:
        if dilution > benchmarks.dilution_high:  # > 10%
            results.append(make_rule(
                "RED", "D1", "Equity Dilution",
                dilution,
                f"> {benchmarks.dilution_high*100:.0f}%",
                f"Significant dilution - equity issuance ({dilution*100:.1f}%) exceeds {benchmarks.dilution_high*100:.0f}%"
            ))
        elif dilution > benchmarks.dilution_warning:  # 5-10%
            results.append(make_rule(
                "YELLOW", "D1", "Equity Dilution",
                dilution,
                f"{benchmarks.dilution_warning*100:.0f}-{benchmarks.dilution_high*100:.0f}%",
                f"Moderate dilution - equity issuance {dilution*100:.1f}%"
            ))
        elif dilution > 0:
            results.append(make_rule(
                "GREEN", "D1", "Equity Dilution",
                dilution,
                f"< {benchmarks.dilution_warning*100:.0f}%",
                f"Minimal dilution - equity issuance {dilution*100:.1f}%"
            ))
    
    # D2 – Dilution Without Earnings Growth
    dilution_without_earnings = trends.get("dilution_without_earnings", False)
    if dilution_without_earnings:
        pat_cagr = trends.get("pat_cagr", 0)
        results.append(make_rule(
            "YELLOW", "D2", "Dilution Without Earnings Growth",
            dilution,
            "Dilution >5% AND PAT CAGR <5%",
            f"Weak return on new equity capital - dilution occurred with minimal PAT growth ({pat_cagr:.1f}% CAGR)"
        ))
    
    # ============================================================
    # E. FUNDING MIX: DEBT VS EQUITY
    # ============================================================
    
    # E1 – Debt Rising vs Equity Stagnating
    debt_outpacing = trends.get("debt_outpacing_equity", False)
    if debt_outpacing:
        debt_cagr = trends.get("debt_cagr", 0)
        equity_cagr = trends.get("equity_cagr", 0)
        results.append(make_rule(
            "YELLOW", "E1", "Debt Rising vs Equity Stagnating",
            debt_cagr - equity_cagr if debt_cagr and equity_cagr else None,
            f"Debt CAGR > Equity CAGR + {benchmarks.leverage_rising_threshold*100:.0f}%",
            f"Higher reliance on debt - Debt CAGR ({debt_cagr:.1f}%) significantly exceeds Equity CAGR ({equity_cagr:.1f}%)"
        ))
    
    # E2 – Net Worth Stagnating While Debt Rising
    nw_stagnant_debt_rising = trends.get("networth_stagnant_debt_rising", False)
    if nw_stagnant_debt_rising:
        nw_cagr = trends.get("networth_cagr", 0)
        debt_cagr = trends.get("debt_cagr", 0)
        results.append(make_rule(
            "RED", "E2", "Net Worth Stagnating While Debt Rising",
            None,
            "Net Worth CAGR < 0 AND Debt CAGR > 0",
            f"Weak equity cushion with rising leverage - Net Worth CAGR ({nw_cagr:.1f}%) while Debt CAGR ({debt_cagr:.1f}%)"
        ))
    
    # E3 – Debt to Equity Ratio
    de_ratio = m.get("debt_to_equity")
    if de_ratio is not None:
        if de_ratio > 1.5:
            results.append(make_rule(
                "RED", "E3", "Debt-to-Equity Ratio",
                de_ratio,
                "> 1.5",
                f"High leverage in funding mix - D/E ratio {de_ratio:.2f}"
            ))
        elif de_ratio > 1.0:
            results.append(make_rule(
                "YELLOW", "E3", "Debt-to-Equity Ratio",
                de_ratio,
                "1.0-1.5",
                f"Moderately leveraged funding mix - D/E ratio {de_ratio:.2f}"
            ))
        else:
            results.append(make_rule(
                "GREEN", "E3", "Debt-to-Equity Ratio",
                de_ratio,
                "<= 1.0",
                f"Equity-dominated funding mix - D/E ratio {de_ratio:.2f}"
            ))
    
    # E4 – Equity Ratio (Equity as % of total capital)
    equity_ratio = m.get("equity_ratio")
    if equity_ratio is not None:
        if equity_ratio >= 0.60:
            results.append(make_rule(
                "GREEN", "E4", "Equity Ratio",
                equity_ratio,
                ">= 60%",
                f"Strong equity base - equity comprises {equity_ratio*100:.1f}% of total capital"
            ))
        elif equity_ratio >= 0.40:
            results.append(make_rule(
                "YELLOW", "E4", "Equity Ratio",
                equity_ratio,
                "40-60%",
                f"Balanced capital structure - equity comprises {equity_ratio*100:.1f}% of total capital"
            ))
        else:
            results.append(make_rule(
                "RED", "E4", "Equity Ratio",
                equity_ratio,
                "< 40%",
                f"Debt-heavy capital structure - equity only {equity_ratio*100:.1f}% of total capital"
            ))
    
    return results
