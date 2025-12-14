from typing import Optional

# ============================================================
# metrics_engine.py  (Final Production-Ready Version)
# ============================================================

# def compute_year_metrics(current: dict, prev: dict | None) -> dict:
def compute_year_metrics(current: dict, prev: Optional[dict]) -> dict:
    """
    Compute all per-year metrics for Capex/CWIP module.
    Automatically derives missing fields like:
      - net_fixed_assets
      - capex
      - operating_cash_flow
      - free_cash_flow
    """

    # -----------------------------------------------------------
    # 1) Compute Net Fixed Assets (NFA)
    #     If user did not provide "net_fixed_assets", derive it:
    #     NFA = Gross Block - Accumulated Depreciation
    # -----------------------------------------------------------
    if not current.get("net_fixed_assets"):
        gb = current.get("gross_block") or 0
        ad = current.get("accumulated_depreciation") or 0
        current["net_fixed_assets"] = gb - ad

    nfa = current["net_fixed_assets"]

    # -----------------------------------------------------------
    # 2) Compute Capex
    #     Your input uses "fixed_assets_purchased" (negative value).
    #     Convert to positive capex.
    # -----------------------------------------------------------
    # if current.get("capex") is None:
    #     fa = current.get("fixed_assets_purchased")
    #     current["capex"] = abs(fa) if fa is not None else 0

    # capex = current["capex"]

    if current.get("capex") is None:
        current["capex"]  = current.get("fixed_assets_purchased")

    capex = current["capex"]

    # -----------------------------------------------------------
    # 3) Compute Operating Cash Flow (OCF)
    #     OCF = Profit from Operations + WC changes + Interest Paid - Taxes
    #
    #     interest_paid_fin is negative in your dataset.
    # -----------------------------------------------------------
    if current.get("operating_cash_flow") is None:
        pfo = current.get("profit_from_operations") or 0
        wc = current.get("working_capital_changes") or 0
        ip = current.get("interest_paid_fin") or 0
        tax = current.get("direct_taxes") or 0

        current["operating_cash_flow"] = pfo + wc + ip - tax

    ocf = current["operating_cash_flow"]

    # -----------------------------------------------------------
    # 4) Compute Free Cash Flow (FCF)
    #     FCF = OCF – Capex
    # -----------------------------------------------------------
    if current.get("free_cash_flow") is None:
        current["free_cash_flow"] = ocf - capex

    fcf = current["free_cash_flow"]

    # -----------------------------------------------------------
    # Extract revenue
    # -----------------------------------------------------------
    rev = current.get("revenue") or 0

    # -----------------------------------------------------------
    # 5) Capex Metrics
    # -----------------------------------------------------------

    # Capex Intensity = Capex / Revenue
    capex_intensity = capex / rev if rev else None

    # CWIP % of Fixed Assets
    cwip = current.get("cwip") or 0
    cwip_pct = cwip / nfa if nfa else None

    # Asset Turnover = Revenue / NFA
    asset_turnover = rev / nfa if nfa else None

    # Debt-Funded Capex = Change in Total Debt / Capex
    debt_funded_capex = None
    if prev:
        prev_debt = (prev.get("short_term_debt") or 0) + (prev.get("long_term_debt") or 0)
        curr_debt = (current.get("short_term_debt") or 0) + (current.get("long_term_debt") or 0)
        debt_change = curr_debt - prev_debt
        if capex:
            debt_funded_capex = debt_change / capex

    # FCF Coverage = FCF / Capex
    fcf_coverage = fcf / capex if capex else None

    # -----------------------------------------------------------
    # 6) Return dictionary of computed metrics
    # -----------------------------------------------------------
    return {
        "capex": capex,
        "cwip": cwip,
        "nfa": nfa,
        "revenue": rev,

        "capex_intensity": capex_intensity,
        "cwip_pct": cwip_pct,
        "asset_turnover": asset_turnover,
        "debt_funded_capex": debt_funded_capex,
        "fcf_coverage": fcf_coverage,
    }
