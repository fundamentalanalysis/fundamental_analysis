from typing import Dict, List, Optional
from .equity_funding_mix_models import YearFinancialInput


def safe_div(a, b):
    """Safely divide two numbers, returning None if division is invalid."""
    if b in (0, None) or a is None:
        return None
    return a / b


def compute_per_year_metrics(financials_5y: List[YearFinancialInput]) -> Dict[int, dict]:
    """
    Compute per-year equity & funding mix metrics.
    """
    metrics = {}
    sorted_fin = sorted(financials_5y, key=lambda x: x.year)

    # print("Computing per-year metrics for years:", [f.year for f in sorted_fin])
    # print("Financials:", sorted_fin)

    prev = None
    for f in sorted_fin:
        retained = f.reserves_and_surplus
        share_capital = f.share_capital
        net_worth = f.net_worth or (
            share_capital + (f.reserves_and_surplus or 0.0))

        payout_ratio = safe_div(f.dividends_paid, f.pat)
        dividend_fcf = safe_div(f.dividends_paid, f.free_cash_flow)

        # Dilution relative to prior share capital
        dilution_pct = None
        if prev is not None and prev.share_capital not in (None, 0):
            dilution_pct = safe_div(f.new_share_issuance, prev.share_capital)

        # ROE calculation
        avg_equity = None
        if prev is not None:
            prev_net = prev.share_capital
            avg_equity = safe_div((share_capital + prev_net), 2)
        else:
            # for 2021 Avg Share Holders Equity was 31.5 Cr as per FY21 AR
            avg_equity = 31.5

        roe = safe_div(f.pat, avg_equity)

        # print(prev.share_capital if prev else None, "->", share_capital, "Dilution:", dilution_pct)
        # print("Year:", f.year, "PAT:", f.pat, "Avg Equity:", avg_equity, "ROE:", roe)

        # Growth rates vs previous year
        equity_growth = None
        debt_growth = None
        if prev is not None and prev.share_capital not in (None, 0):
            equity_growth = safe_div(
                (share_capital - prev.share_capital), prev.share_capital)
            debt_growth = safe_div(
                (f.debt - prev.debt), prev.debt) if prev.debt not in (None, 0) else None

        metrics[f.year] = {
            "year": f.year,
            "share_capital": share_capital,
            "reserves_and_surplus": retained,
            "net_worth": net_worth,
            "pat": f.pat,
            "dividends_paid": f.dividends_paid,
            "free_cash_flow": f.free_cash_flow,
            "new_share_issuance": f.new_share_issuance,
            "debt": f.debt,

            # Derived
            "retained_earnings": retained,
            "retained_yoy_pct": safe_div((retained - (prev.reserves_and_surplus if prev else None)), (prev.reserves_and_surplus if prev else None)) if prev and prev.reserves_and_surplus not in (None, 0) else None,
            "payout_ratio": payout_ratio,
            "dividend_to_fcf": dividend_fcf,
            "dilution_pct": dilution_pct,
            "roe": roe,
            "avg_equity": avg_equity,

            "equity_growth_rate": equity_growth,
            "debt_growth_rate": debt_growth,
            "debt_to_equity": safe_div(f.debt, net_worth),
        }

        prev = f

    # print("Per-year metrics computed:", metrics)

    return metrics
