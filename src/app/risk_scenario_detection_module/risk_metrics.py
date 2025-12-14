# risk_metrics.py
from typing import Dict, Any, Optional


def safe_float(v: Optional[float]) -> Optional[float]:
    try:
        return None if v is None else float(v)
    except Exception:
        return None


def compute_derived_metrics(year: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute per-year derived metrics from the raw year dict (matches your input).
    """
    out = dict(year)

    # loan rollover: proceeds - repayment (if both exist)
    proceeds = safe_float(year.get("proceeds_from_borrowings"))
    repayment = safe_float(year.get("repayment_of_borrowings"))
    if proceeds is not None and repayment is not None:
        out["loan_rollover_amount"] = proceeds - repayment

    # interest capitalized
    interest_paid_fin = safe_float(year.get("interest_paid_fin"))
    interest = safe_float(year.get("interest"))
    if interest_paid_fin is not None and interest is not None:
        out["interest_capitalized"] = interest_paid_fin - interest

    # net_debt approximation (if missing)
    if year.get("net_debt") is None:
        borrowings = safe_float(year.get("borrowings") or 0)

        out["net_debt"] = borrowings

    # canonical OCF
    if out.get("operating_cash_flow") is None:
        if year.get("cash_from_operating_activity") is not None:
            out["operating_cash_flow"] = safe_float(year.get("cash_from_operating_activity"))

    # rpt ratios placeholders (filled in trend module)
    return out
