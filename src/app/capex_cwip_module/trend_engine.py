# # trend_engine.py
# from .metrics_engine import compute_cagr
# def is_increasing_3y(values):
#     if len(values) < 3:
#         return False
#     return values[-1] > values[-2] > values[-3]


# def compute_trends(financials):
#     # Extract 5-year series
#     cwip_series = [y["cwip"] for y in financials]
#     capex_series = [y["capex"] for y in financials]
#     nfa_series = [y["net_fixed_assets"] for y in financials]
#     rev_series = [y["revenue"] for y in financials]

#     return {
#         "cwip_cagr": compute_cagr(cwip_series),
#         "capex_cagr": compute_cagr(capex_series),
#         "nfa_cagr": compute_cagr(nfa_series),
#         "revenue_cagr": compute_cagr(rev_series),
#         "cwip_increasing_3y": is_increasing_3y(cwip_series)
#     }


# trend_engine.py

from typing import Dict, List, Optional
from typing import Optional

# def compute_cagr(start, end, years) -> Optional[float]:
#     """
#     Reference-style CAGR:
#     CAGR = (end/start)^(1/years) - 1
#     Returns percent (%), not ratio.
#     """
#     if start in (None, 0) or end in (None, 0) or start <= 0 or years <= 0:
#         return None
#     return ((end / start) ** (1 / years) - 1) * 100

def compute_cagr(start, end, years) -> Optional[float]:
    """
    CAGR = (end/start)^(1/years) - 1
    Returns percent (%), supports negative-to-negative capex contraction.
    """
    if start is None or end is None or years <= 0:
        return None

    # If start is zero, CAGR is undefined
    if start == 0:
        return None

    # Same sign case (both positive OR both negative)
    if start * end > 0:
        cagr =((end / start) ** (1 / years)) - 1
        return cagr * 100

    # Mixed sign case: economically undefined for CAGR
    return None


def compute_yoy(current, previous) -> Optional[float]:
    """Reference-style YoY growth in %."""
    if previous in (None, 0) or current is None:
        return None
    return (current - previous) / abs(previous) * 100


def _series(years: List[int], yearly: Dict[int, dict], key: str) -> List[Optional[float]]:
    """Extract a value series aligned to sorted years."""
    return [yearly[y].get(key) for y in years]


def _has_consecutive_trend(values: List[Optional[float]], direction: str, span: int) -> bool:
    """
    Generic multi-year rising/falling trend detector.
    direction: "up" or "down"
    span: number of years required (e.g., 3)
    """
    if len(values) < span:
        return False

    cmp = (lambda a, b: a > b) if direction == "up" else (lambda a, b: a < b)
    streak = 0

    for prev, curr in zip(values, values[1:]):
        if prev is None or curr is None:
            streak = 0
            continue
        if cmp(curr, prev):
            streak += 1
            if streak >= span - 1:
                return True
        else:
            streak = 0

    return False


def compute_trends(yearly: Dict[int, dict]) -> Dict[str, any]:
    """
    Reference-style trend engine for Capex & CWIP.

    Input format:
        yearly = {
            2019: {"cwip":..., "capex":..., "net_fixed_assets":..., "revenue":...},
            2020: {...},
            ...
            2024: {...}
        }

    Output:
        {
            "cwip_cagr": ...,
            "capex_cagr": ...,
            "nfa_cagr": ...,
            "revenue_cagr": ...,
            "cwip_increasing_3y": True/False,
            ...
        }
    """

    years = sorted(yearly.keys())
    if len(years) < 2:
        return {}

    first_year = years[0]
    last_year = years[-1]
    num_years = len(years) 

    # print(yearly)

    # ------------------
    # CAGR calculations
    # ------------------
    cwip_cagr = compute_cagr(yearly[first_year].get("cwip"),
                             yearly[last_year].get("cwip"), num_years)

    capex_cagr = compute_cagr(yearly[first_year].get("capex"),
                              yearly[last_year].get("capex"), num_years)
    # print("yearly[first_year].get('capex'):", yearly[first_year].get("capex") , "yearly[last_year].get('capex'):", yearly[last_year].get("capex"))
    # print("CAPEX CAGR:", capex_cagr)

    nfa_cagr = compute_cagr(yearly[first_year].get("net_fixed_assets"),
                            yearly[last_year].get("net_fixed_assets"), num_years)

    revenue_cagr = compute_cagr(yearly[first_year].get("revenue"),
                                yearly[last_year].get("revenue"), num_years)

    # ------------------------------
    # YoY growth (optional but useful)
    # ------------------------------
    cwip_yoy = []
    capex_yoy = []
    nfa_yoy = []
    revenue_yoy = []

    for prev_year, curr_year in zip(years, years[1:]):
        prev = yearly[prev_year]
        curr = yearly[curr_year]

        cwip_yoy.append(compute_yoy(curr.get("cwip"), prev.get("cwip")))
        capex_yoy.append(compute_yoy(curr.get("capex"), prev.get("capex")))
        nfa_yoy.append(compute_yoy(curr.get("net_fixed_assets"), prev.get("net_fixed_assets")))
        revenue_yoy.append(compute_yoy(curr.get("revenue"), prev.get("revenue")))

    # -----------------------------
    # Multi-year trend detectors
    # -----------------------------
    cwip_series = _series(years, yearly, "cwip")
    capex_series = _series(years, yearly, "capex")
    nfa_series = _series(years, yearly, "net_fixed_assets")

    cwip_increasing_3y = _has_consecutive_trend(cwip_series, "up", 3)
    capex_increasing_3y = _has_consecutive_trend(capex_series, "up", 3)
    nfa_increasing_3y = _has_consecutive_trend(nfa_series, "up", 3)

    # -----------------------
    # Final unified output
    # -----------------------
    return {
        # CAGR %
        "cwip_cagr": cwip_cagr,
        "capex_cagr": capex_cagr,
        "nfa_cagr": nfa_cagr,
        "revenue_cagr": revenue_cagr,

        # YoY %
        "cwip_yoy": cwip_yoy,
        "capex_yoy": capex_yoy,
        "nfa_yoy": nfa_yoy,
        "revenue_yoy": revenue_yoy,

        # Raw series required by orchestrator
        "cwip_series": cwip_series,
        "capex_series": capex_series,
        "nfa_series": nfa_series,

        # Trend flags
        "cwip_increasing_3y": cwip_increasing_3y,
        "capex_increasing_3y": capex_increasing_3y,
        "nfa_increasing_3y": nfa_increasing_3y,
    }

