# liquidity_trend.py

from typing import Dict, List, Optional
from .liquidity_models import YearFinancials


def safe_yoy(curr: Optional[float], prev: Optional[float]) -> Optional[float]:
    if prev in (None, 0) or curr is None:
        return None
    return ((curr - prev) / prev) * 100


def compute_cagr(start: Optional[float], end: Optional[float], years: int) -> Optional[float]:
    if start in (None, 0) or end in (None, 0) or start <= 0 or years <= 0:
        return None
    return ((end / start) ** (1 / years) - 1) * 100


def _extract(series: List[YearFinancials], field: str) -> List[Optional[float]]:
    return [getattr(y, field, None) for y in series]


def _compute_series_yoy(values: List[Optional[float]]) -> List[Optional[float]]:
    if len(values) < 2:
        return [None] * len(values)

    out = [None]
    for prev, curr in zip(values, values[1:]):
        out.append(safe_yoy(curr, prev))
    return out


def _has_consecutive_decline(values: List[Optional[float]], span: int = 3) -> bool:
    streak = 0
    for prev, curr in zip(values, values[1:]):
        if prev is None or curr is None:
            streak = 0
            continue
        if curr < prev:
            streak += 1
            if streak >= span - 1:
                return True
        else:
            streak = 0
    return False


def _has_consecutive_rise(values: List[Optional[float]], span: int = 3) -> bool:
    streak = 0
    for prev, curr in zip(values, values[1:]):
        if prev is None or curr is None:
            streak = 0
            continue
        if curr > prev:
            streak += 1
            if streak >= span - 1:
                return True
        else:
            streak = 0
    return False


def _compute_ratio_series(series: List[YearFinancials], num: str, den: str) -> List[Optional[float]]:
    ratios = []
    for y in series:
        n = getattr(y, num, None)
        d = getattr(y, den, None)
        if n is None or d in (None, 0):
            ratios.append(None)
        else:
            ratios.append(n / d)
    return ratios


def compute_liquidity_trends(financials: List[YearFinancials]) -> Dict[str, dict]:
    """
    Compute YoY trends, CAGR, and stress patterns using YearFinancials.
    """

    financials = sorted(financials, key=lambda x: x.year)
    if len(financials) < 2:
        return {}

    years = [f.year for f in financials]
    n_years = len(financials) - 1

    # ---- Base Series ----
    current_ratio_values = _compute_ratio_series(
    financials, "current_assets", "current_liabilities"
    )
    current_ratio_yoy = _compute_series_yoy(current_ratio_values)

    cash = _extract(financials, "cash_and_equivalents")
    recv = _extract(financials, "receivables")
    inv = _extract(financials, "inventory")
    ocf = _extract(financials, "operating_cash_flow")
    cl = _extract(financials, "current_liabilities")
    ca = _extract(financials, "current_assets")
    ms = _extract(financials, "marketable_securities")

    # ---- YoY calculations ----
    cash_yoy = _compute_series_yoy(cash)
    recv_yoy = _compute_series_yoy(recv)
    inv_yoy = _compute_series_yoy(inv)
    ocf_yoy = _compute_series_yoy(ocf)
    cl_yoy = _compute_series_yoy(cl)

    # # ---- CAGR ----
    # cash_cagr = compute_cagr(cash[0], cash[-1], n_years)
    # recv_cagr = compute_cagr(recv[0], recv[-1], n_years)
    # inv_cagr = compute_cagr(inv[0], inv[-1], n_years)
    # ocf_cagr = compute_cagr(ocf[0], ocf[-1], n_years)
    # cl_cagr = compute_cagr(cl[0], cl[-1], n_years)

    # ---- Ratio Trend Series ----
    current_ratio = _compute_ratio_series(financials, "current_assets", "current_liabilities")
    quick_ratio = []
    cash_ratio = []

    for f in financials:
        inv_val = f.inventory or 0
        cash_val = f.cash_and_equivalents or 0
        cl_val = f.current_liabilities or 0

        if cl_val in (None, 0):
            quick_ratio.append(None)
            cash_ratio.append(None)
        else:
            quick_ratio.append((f.current_assets - inv_val) / cl_val)
            cash_ratio.append(cash_val / cl_val)

    # ---- Pattern Detection ----
    cash_falling = _has_consecutive_decline(cash, 3)
    cl_rising = _has_consecutive_rise(cl, 3)
    ocf_declining = _has_consecutive_decline(ocf, 3)
    receivables_rising = _has_consecutive_rise(recv, 3)
    inventory_rising = _has_consecutive_rise(inv, 3)

    cash_stress_pattern = cash_falling and cl_rising
    working_capital_worsening = receivables_rising or inventory_rising

    return {
        "years": years,

        "yoy": {
            "current_ratio": current_ratio_yoy,
            "cash_yoy": cash_yoy,
            "receivables_yoy": recv_yoy,
            "inventory_yoy": inv_yoy,
            "ocf_yoy": ocf_yoy,
            "current_liabilities_yoy": cl_yoy,
        },

        

        "ratios_trend": {
            "current_ratio_trend": current_ratio_values,
            "quick_ratio_trend": quick_ratio,
            "cash_ratio_trend": cash_ratio,
        },

        "patterns": {
            "cash_shrinking_3yr": cash_falling,
            "cl_rising_3yr": cl_rising,
            "ocf_declining_3yr": ocf_declining,
            "receivables_rising_3yr": receivables_rising,
            "inventory_rising_3yr": inventory_rising,
            "cash_shrinking_while_cl_rising": cash_stress_pattern,
            "working_capital_worsening": working_capital_worsening,
        }
    }
