from typing import Dict, List, Optional, Union


# =========================================================
# Helpers
# =========================================================

def safe_div(a, b) -> Optional[float]:
    if a is None or b in (None, 0):
        return None
    return round(a / b, 4)


def build_year_map(values: List[Optional[float]]) -> Dict[str, Optional[float]]:
    return {
        "Y" if i == 0 else f"Y-{i}": v
        for i, v in enumerate(reversed(values))
    }


def normalize_metrics(per_year_metrics: Union[Dict[int, dict], List[dict]]) -> Dict[int, dict]:
    if isinstance(per_year_metrics, dict):
        return per_year_metrics
    if isinstance(per_year_metrics, list):
        return {m["year"]: m for m in per_year_metrics}
    raise TypeError("per_year_metrics must be dict or list")


# =========================================================
# PUBLIC API — TREND ENGINE
# =========================================================

def compute_trend_output(per_year_metrics: Union[Dict[int, dict], List[dict]]) -> Dict[str, dict]:

    per_year_metrics = normalize_metrics(per_year_metrics)
    years = sorted(per_year_metrics.keys())

    total_debt = [per_year_metrics[y]["total_debt"] for y in years]
    short_term_debt = [per_year_metrics[y]["short_term_debt"] for y in years]
    cash = [per_year_metrics[y]["cash"] for y in years]
    equity = [per_year_metrics[y]["equity"] for y in years]

    ebit = [per_year_metrics[y]["ebit"] for y in years]
    ebitda = [per_year_metrics[y]["ebitda"] for y in years]
    interest_cost = [per_year_metrics[y]["interest_cost"] for y in years]
    taxes = [per_year_metrics[y]["tax_amount"] for y in years]

    net_debt = [d - c for d, c in zip(total_debt, cash)]

    debt_to_equity = [safe_div(d, e) for d, e in zip(total_debt, equity)]
    debt_to_ebitda = [safe_div(d, e) for d, e in zip(total_debt, ebitda)]
    interest_coverage = [safe_div(e, i) for e, i in zip(ebit, interest_cost)]

    ffo = [
        ebitda[i] - interest_cost[i] - taxes[i]
        for i in range(len(years))
    ]

    ffo_coverage = [safe_div(f, i) for f, i in zip(ffo, interest_cost)]
    net_debt_to_ebitda = [safe_div(nd, e) for nd, e in zip(net_debt, ebitda)]
    st_debt_share = [safe_div(st, td) for st, td in zip(short_term_debt, total_debt)]

    return {
        "basic leverage metrics": {
            "debt_to_equity": {
                "total_debt": {"values": build_year_map(total_debt)},
                "equity": {"values": build_year_map(equity)},
                "debt to equity": {"values": build_year_map(debt_to_equity)},
            },
            "debt_to_ebitda": {
                "total_debt": {"values": build_year_map(total_debt)},
                "ebitda": {"values": build_year_map(ebitda)},
                "debt to ebitda": {"values": build_year_map(debt_to_ebitda)},
            },
            "interest_coverage": {
                "ebit": {"values": build_year_map(ebit)},
                "interest_cost": {"values": build_year_map(interest_cost)},
                "interest coverage ratio": {"values": build_year_map(interest_coverage)},
            },
        },
        "advanced fitch / s&p style metrics": {
            "net_debt": {
                "total_debt": {"values": build_year_map(total_debt)},
                "cash": {"values": build_year_map(cash)},
                "net debt": {"values": build_year_map(net_debt)},
            },
            "net_debt_to_ebitda": {
                "net_debt": {"values": build_year_map(net_debt)},
                "ebitda": {"values": build_year_map(ebitda)},
                "net debt to ebitda": {"values": build_year_map(net_debt_to_ebitda)},
            },
            "ffo_coverage": {
                "ebitda": {"values": build_year_map(ebitda)},
                "interest_cost": {"values": build_year_map(interest_cost)},
                "taxes": {"values": build_year_map(taxes)},
                "ffo": {"values": build_year_map(ffo)},
                "ffo coverage": {"values": build_year_map(ffo_coverage)},
            },
            "debt_service_burden": {
                "short_term_debt": {"values": build_year_map(short_term_debt)},
                "total_debt": {"values": build_year_map(total_debt)},
                "debt service burden": {"values": build_year_map(st_debt_share)},
            },
        },
        "short-term debt dependence": {
            "short_term_debt": {"values": build_year_map(short_term_debt)},
            "total_debt": {"values": build_year_map(total_debt)},
            "st debt share": {"values": build_year_map(st_debt_share)},
        },
    }
