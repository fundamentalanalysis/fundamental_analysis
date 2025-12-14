from typing import Dict, List, Optional, Any


# def compute_cagr(start, end, years) -> Optional[float]:
# 	"""Compute CAGR. Returns None if start/end are invalid, otherwise returns CAGR as percentage."""
# 	if start in (None, 0) or end in (None, 0) or years <= 0:
# 		return None
# 	if start < 0 or end < 0:  # Invalid for CAGR calculation
# 		return None
# 	return ((end / start) ** (1 / years) - 1) * 100


from typing import Optional


def compute_cagr(start, end, years) -> Optional[float]:
    if start is None or end is None or years <= 0:
        return None

    # If start is zero, CAGR is undefined
    if start == 0:
        return None

    # Same sign case (both positive OR both negative)
    if start * end > 0:
        cagr = (abs(end) / abs(start)) ** (1 / years) - 1

        # If both are negative, keep the economic direction
        if start < 0 and end < 0:
            return cagr * 100  # magnitude of loss growth

        return cagr * 100

    # Mixed signs (negative to positive or vice versa) → meaningless for CAGR
    return None


def compute_yoy(current, previous) -> Optional[float]:
    if previous in (None, 0) or current is None:
        return None
    return (current - previous) / previous * 100


def _series(years: List[int], yearly: Dict[int, dict], key: str) -> List[Optional[float]]:
    return [yearly[y].get(key) for y in years]


def _has_consecutive_trend(values: List[Optional[float]], direction: str, span: int) -> bool:
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


def compute_trend_metrics(yearly: Dict[int, dict]) -> Dict[str, Any]:
    years = sorted(yearly.keys())
    if len(years) < 2:
        return {}

    first_year = years[0]
    last_year = years[-1]
    num_years = len(years)

    # print("Computing trend metrics for years:", years)
    # print(first_year, last_year, num_years)

    retained_cagr = compute_cagr(yearly[first_year].get(
        "retained_earnings"), yearly[last_year].get("retained_earnings"), num_years - 1)
    roe_cagr = compute_cagr(yearly[first_year].get(
        "roe"), yearly[last_year].get("roe"), num_years - 1)
    payout_cagr = compute_cagr(yearly[first_year].get(
        "payout_ratio") or 0, yearly[last_year].get("payout_ratio") or 0, num_years - 1)
    pat_cagr = compute_cagr(yearly[first_year].get(
        "pat"), yearly[last_year].get("pat"), num_years - 1)

    equity_cagr = compute_cagr(yearly[first_year].get(
        "share_capital"), yearly[last_year].get("share_capital"), num_years - 1)
    debt_cagr = compute_cagr(yearly[first_year].get(
        "debt"), yearly[last_year].get("debt"), num_years - 1)

    # YoY arrays
    payout_yoy = []
    roe_yoy = []
    dilution_events = []
    for prev_year, curr_year in zip(years, years[1:]):
        prev = yearly[prev_year]
        curr = yearly[curr_year]
        payout_yoy.append(compute_yoy(
            curr.get("payout_ratio"), prev.get("payout_ratio")))
        roe_yoy.append(compute_yoy(curr.get("roe"), prev.get("roe")))
        # Dilution event if dilution_pct exists
        d = curr.get("dilution_pct")
        if d is not None and d > 0:
            dilution_events.append(
                {"year": curr.get("year"), "dilution_pct": d})

    retained_series = _series(years, yearly, "retained_earnings")
    payout_series = _series(years, yearly, "payout_ratio")
    roe_series = _series(years, yearly, "roe")

    retained_declining = _has_consecutive_trend(retained_series, "down", 3)
    roe_declining = _has_consecutive_trend(roe_series, "down", 3)

    # print("ROE Series:", roe_series)
    # print("ROE Declining:", roe_declining)

    return {
        "retained_cagr": retained_cagr,
        "roe_cagr": roe_cagr,
        "payout_cagr": payout_cagr,
        "pat_cagr": pat_cagr,
        "equity_cagr": equity_cagr,
        "debt_cagr": debt_cagr,
        "payout_yoy_growth": payout_yoy,
        "roe_yoy_growth": roe_yoy,
        "dilution_events": dilution_events,
        "retained_declining": retained_declining,
        "roe_declining": roe_declining,
    }
