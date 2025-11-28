from typing import Dict, List, Optional


def compute_cagr(start, end, years) -> Optional[float]:
    if start in (None, 0) or end in (None, 0) or start <= 0 or years <= 0:
        return None
    return ((end / start) ** (1 / years) - 1) * 100


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


def compute_trend_metrics(yearly: Dict[int, dict]) -> Dict[str, any]:
    years = sorted(yearly.keys())
    if len(years) < 2:
        return {}

    first_year = years[0]
    last_year = years[-1]
    num_years = len(years) - 1

    debt_cagr = compute_cagr(yearly[first_year]["total_debt"], yearly[last_year]["total_debt"], num_years)
    lt_debt_cagr = compute_cagr(yearly[first_year]["long_term_debt"], yearly[last_year]["long_term_debt"], num_years)
    st_debt_cagr = compute_cagr(yearly[first_year]["short_term_debt"], yearly[last_year]["short_term_debt"], num_years)
    ebitda_cagr = compute_cagr(yearly[first_year]["ebitda"], yearly[last_year]["ebitda"], num_years)
    finance_cost_cagr = compute_cagr(yearly[first_year]["finance_cost"], yearly[last_year]["finance_cost"], num_years)
    revenue_cagr = compute_cagr(yearly[first_year]["revenue"], yearly[last_year]["revenue"], num_years)

    st_debt_yoy = []
    lt_debt_yoy = []
    fincost_yoy = []
    wacd_delta = []
    ocf_yoy = []
    maturity_lt_yoy = []

    for prev_year, curr_year in zip(years, years[1:]):
        prev, curr = yearly[prev_year], yearly[curr_year]

        st_debt_yoy.append(compute_yoy(curr["short_term_debt"], prev["short_term_debt"]))
        lt_debt_yoy.append(compute_yoy(curr["long_term_debt"], prev["long_term_debt"]))
        fincost_yoy.append(compute_yoy(curr["finance_cost"], prev["finance_cost"]))
        ocf_yoy.append(compute_yoy(curr.get("operating_cash_flow"), prev.get("operating_cash_flow")))
        maturity_lt_yoy.append(compute_yoy(curr.get("maturity_lt_1y_pct"), prev.get("maturity_lt_1y_pct")))

        curr_wacd = curr.get("wacd")
        prev_wacd = prev.get("wacd")
        wacd_delta.append(curr_wacd - prev_wacd if curr_wacd is not None and prev_wacd is not None else None)

    de_series = _series(years, yearly, "de_ratio")
    icr_series = _series(years, yearly, "interest_coverage")
    maturity_lt_series = _series(years, yearly, "maturity_lt_1y_pct")
    st_share_series = _series(years, yearly, "st_debt_share")

    leverage_trend_increasing = _has_consecutive_trend(de_series, "up", 3)
    icr_trend_declining = _has_consecutive_trend(icr_series, "down", 3)
    refi_trend_increasing = _has_consecutive_trend(maturity_lt_series, "up", 3)
    st_share_increasing = _has_consecutive_trend(st_share_series, "up", 3)

    return {
        "debt_cagr": debt_cagr,
        "lt_debt_cagr": lt_debt_cagr,
        "st_debt_cagr": st_debt_cagr,
        "ebitda_cagr": ebitda_cagr,
        "finance_cost_cagr": finance_cost_cagr,
        "revenue_cagr": revenue_cagr,
        "debt_growth_vs_ebitda": (
            (debt_cagr - ebitda_cagr)
            if (debt_cagr is not None and ebitda_cagr is not None)
            else None
        ),
        "st_debt_yoy_growth": st_debt_yoy,
        "lt_debt_yoy_growth": lt_debt_yoy,
        "finance_cost_yoy_growth": fincost_yoy,
        "ocf_yoy_growth": ocf_yoy,
        "wacd_yoy_delta": wacd_delta,
        "maturity_lt_1y_yoy": maturity_lt_yoy,
        "leverage_trend_increasing": leverage_trend_increasing,
        "icr_trend_declining": icr_trend_declining,
        "refi_trend_increasing": refi_trend_increasing,
        "st_share_trend_increasing": st_share_increasing,
    }

