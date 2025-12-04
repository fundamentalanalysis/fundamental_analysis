from typing import Dict, List

from ..borrowing_module.debt_models import YearFinancialInput

def safe_div(a, b):
    """Safely divide two numbers, returning None if division is invalid."""
    return a / b if (b not in (0, None) and a is not None) else None


def compute_year_metrics(current: dict, previous: dict | None) -> dict:
    """
    Compute per-year metrics for Capex & CWIP Rules.
    
    current: dict for the year
    previous: dict for previous year (or None)
    
    This matches the new CapexCwipModule orchestrator and the rules_engine.
    """

    # --- Safe getters ---
    def g(d, key):
        return None if d is None else d.get(key)

    capex = g(current, "capex")
    revenue = g(current, "revenue")
    cwip = g(current, "cwip")
    nfa = g(current, "net_fixed_assets")
    free_cf = g(current, "free_cash_flow")
    operating_cf = g(current, "operating_cash_flow")

    # -----------------------------
    # Derived Metrics
    # -----------------------------

    # Capex Intensity
    capex_intensity = None
    if capex is not None and revenue not in (None, 0):
        capex_intensity = capex / revenue

    # CWIP % of NFA
    cwip_pct = None
    if cwip is not None and nfa not in (None, 0):
        cwip_pct = cwip / nfa

    # CWIP YoY
    cwip_yoy = None
    if previous is not None:
        prev_cwip = g(previous, "cwip")
        if prev_cwip not in (None, 0) and cwip is not None:
            cwip_yoy = (cwip - prev_cwip) / prev_cwip

    # NFA YoY
    nfa_yoy = None
    if previous is not None:
        prev_nfa = g(previous, "net_fixed_assets")
        if prev_nfa not in (None, 0) and nfa is not None:
            nfa_yoy = (nfa - prev_nfa) / prev_nfa

    # Asset Turnover
    asset_turnover = None
    if revenue not in (None, 0) and nfa not in (None, 0):
        asset_turnover = revenue / nfa

    # Debt-funded Capex
    # = (Capex - FCF) / Capex
    debt_funded_capex = None
    if capex not in (None, 0) and free_cf is not None:
        debt_funded_capex = (capex - free_cf) / capex

    # FCF Coverage
    # = Free Cash Flow / Capex
    fcf_coverage = None
    if capex not in (None, 0) and free_cf is not None:
        fcf_coverage = free_cf / capex

    # -----------------------------
    # Final Metrics Output
    # -----------------------------
    return {
        "year": current.get("year"),

        "capex": capex,
        "revenue": revenue,
        "cwip": cwip,
        "net_fixed_assets": nfa,
        "free_cash_flow": free_cf,
        "operating_cash_flow": operating_cf,

        "capex_intensity": capex_intensity,
        "cwip_pct": cwip_pct,
        "cwip_yoy": cwip_yoy,
        "nfa_yoy": nfa_yoy,
        "asset_turnover": asset_turnover,
        "debt_funded_capex": debt_funded_capex,
        "fcf_coverage": fcf_coverage,
    }

    return metrics
