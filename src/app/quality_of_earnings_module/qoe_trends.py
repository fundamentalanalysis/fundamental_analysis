
# qoe_trends.py

from typing import Dict, List
from .qoe_models import QoEYearInput


# -----------------------------------------------------------
# YoY Calculation
# -----------------------------------------------------------
def compute_yoy(curr, prev):
    if prev in (None, 0) or curr is None:
        return None
    return (curr - prev) / prev


# -----------------------------------------------------------
# Build YoY Labels: ["Y_vs_Y-1", "Y-1_vs_Y-2", ...]
# -----------------------------------------------------------
def build_yoy_labels(n: int) -> List[str]:
    labels = []
    for i in range(n - 1):
        left = "Y" if i == 0 else f"Y-{i}"
        right = f"Y-{i+1}"
        labels.append(f"{left}_vs_{right}")
    return labels


# -----------------------------------------------------------
# Compute YoY (NEWEST FIRST)
# -----------------------------------------------------------
def compute_trend(values: List[float]) -> Dict[str, float]:
    yoy = {}
    labels = build_yoy_labels(len(values))
    for idx in range(len(values) - 1):
        yoy[labels[idx]] = compute_yoy(values[idx], values[idx + 1])
    return yoy


# -----------------------------------------------------------
# Convert list → {"Y": val0, "Y-1": val1, ...}
# -----------------------------------------------------------
def build_values_dict(values: List[float]) -> Dict[str, float]:
    out = {}
    for i, v in enumerate(values):
        key = "Y" if i == 0 else f"Y-{i}"
        out[key] = v
    return out


# -----------------------------------------------------------
# Compute Receivable / Revenue Ratios
# -----------------------------------------------------------
def compute_ratio_list(recv_list, rev_list):
    ratio = []
    for rcv, rev in zip(recv_list, rev_list):
        if rev in (0, None):
            ratio.append(None)
        else:
            ratio.append(rcv / rev)
    return ratio


# -----------------------------------------------------------
# Generic Insight Generator
# -----------------------------------------------------------
def generate_insight(name: str, yoy_map: Dict[str, float]) -> str:
    yoy_values = [v for v in yoy_map.values() if v is not None]

    if not yoy_values:
        return f"No sufficient data to derive insights for {name}."

    avg = sum(yoy_values) / len(yoy_values)
    avg_pct = round(avg * 100, 2)

    if avg > 0.1:
        trend = "strong growth"
    elif 0.03 < avg <= 0.1:
        trend = "moderate growth"
    elif -0.03 <= avg <= 0.03:
        trend = "stable performance"
    elif -0.1 <= avg < -0.03:
        trend = "moderate decline"
    else:
        trend = "strong decline"

    return f"{name.replace('_', ' ').title()} shows {trend} with average YoY change of {avg_pct}%."


# -----------------------------------------------------------
# Insight for Receivables vs Revenue
# -----------------------------------------------------------
def generate_recv_vs_revenue_insight(recv_yoy, rev_yoy, ratio_list, ratio_yoy):
    recv_vals = [v for v in recv_yoy.values() if v is not None]
    rev_vals = [v for v in rev_yoy.values() if v is not None]
    ratio_vals = [v for v in ratio_list if v is not None]

    if not recv_vals or not rev_vals:
        return "Insufficient data for receivables vs revenue analysis."

    avg_recv = sum(recv_vals) / len(recv_vals)
    avg_rev = sum(rev_vals) / len(rev_vals)
    avg_ratio = sum(ratio_vals) / len(ratio_vals) if ratio_vals else None

    spread = avg_recv - avg_rev
    spread_pct = round(spread * 100, 2)

    # CASE 1: Receivables ↑ while Revenue ↓
    if avg_recv > 0 and avg_rev < 0:
        return f"Receivables rising while revenue falling — major collection stress (spread: {spread_pct}%)."

    # CASE 2: Receivables grow much faster than revenue
    if spread > 0.10:
        return f"Receivables growing much faster than revenue — collection risk increasing (spread: {spread_pct}%)."

    # CASE 3: Slightly faster growth
    if 0.03 < spread <= 0.10:
        return f"Receivables slightly outpacing revenue (spread: {spread_pct}%). Monitor working capital."

    # CASE 4: Aligned growth
    if -0.03 <= spread <= 0.03:
        return f"Receivables growth aligned with revenue — stable collection efficiency."

    # CASE 5: Receivables growing slower than revenue
    if spread < -0.03:
        return f"Receivables growing slower than revenue — collection efficiency improving."

    return "Receivables vs revenue trend appears mixed."


# -----------------------------------------------------------
# MAIN FUNCTION
# -----------------------------------------------------------
def compute_qoe_trend_output(financials: List[QoEYearInput]) -> Dict[str, dict]:

    # Sort oldest → newest
    financials = sorted(financials, key=lambda x: int(str(x.year).split()[-1]))

    # Lists oldest → newest
    qoe_vals = [f.cash_from_operating_activity / f.net_profit if f.net_profit else None for f in financials]
    accrual_vals = [(f.net_profit - f.cash_from_operating_activity) / f.total_assets if f.total_assets else None for f in financials]
    ocf_vals = [f.cash_from_operating_activity for f in financials]
    net_income_vals = [f.net_profit for f in financials]

    dso_vals = [
        f.dso if f.dso is not None else (f.Trade_receivables / f.revenue * 365 if f.revenue else None)
        for f in financials
    ]

    receivable_vals = [f.Trade_receivables for f in financials]
    revenue_vals = [f.revenue for f in financials]

    # Reverse → NEWEST FIRST for YoY logic
    qoe_new = qoe_vals[::-1]
    accrual_new = accrual_vals[::-1]
    ocf_new = ocf_vals[::-1]
    net_new = net_income_vals[::-1]
    dso_new = dso_vals[::-1]
    recv_new = receivable_vals[::-1]
    rev_new = revenue_vals[::-1]

    # YoY maps
    recv_yoy = compute_trend(recv_new)
    rev_yoy = compute_trend(rev_new)

    # Ratio: Receivables / Revenue
    recv_rev_ratio = compute_ratio_list(recv_new, rev_new)

    # Ratio YoY
    recv_rev_ratio_yoy = compute_trend(recv_rev_ratio)

    # ---------------------------------------------------------
    # Build Output Dictionary
    # ---------------------------------------------------------
    trends = {
        "qoe": {
            "values": build_values_dict(qoe_new),
            "yoy_growth_pct": compute_trend(qoe_new),
            "insight": generate_insight("qoe", compute_trend(qoe_new)),
        },
        "accruals_ratio": {
            "values": build_values_dict(accrual_new),
            "yoy_growth_pct": compute_trend(accrual_new),
            "insight": generate_insight("accruals_ratio", compute_trend(accrual_new)),
        },
        "ocf": {
            "values": build_values_dict(ocf_new),
            "yoy_growth_pct": compute_trend(ocf_new),
            "insight": generate_insight("ocf", compute_trend(ocf_new)),
        },
        "net_income": {
            "values": build_values_dict(net_new),
            "yoy_growth_pct": compute_trend(net_new),
            "insight": generate_insight("net_income", compute_trend(net_new)),
        },
        "ocf_revenue_ratio": {
            "values": build_values_dict(
                [o / r if r not in (0, None) else None for o, r in zip(ocf_new, rev_new)]
            ),
            "yoy_growth_pct": compute_trend(
                [o / r if r not in (0, None) else None for o, r in zip(ocf_new, rev_new)]
            ),
            "insight": generate_insight(
                "ocf_revenue_ratio",
                compute_trend([o / r if r not in (0, None) else None for o, r in zip(ocf_new, rev_new)])
            ),
        },
        "dso": {
            "values": build_values_dict(dso_new),
            "yoy_growth_pct": compute_trend(dso_new),
            "insight": generate_insight("dso", compute_trend(dso_new)),
        },

        # -------------------------------------------------------
        # RECEIVABLES VS REVENUE (Your requested block)
        # -------------------------------------------------------
        "receivables_vs_revenue": {
            "receivable_yoy": recv_yoy,
            "revenue_yoy": rev_yoy,
            "receivable_to_revenue_pct": build_values_dict(recv_rev_ratio),
            "receivable_to_revenue_yoy": recv_rev_ratio_yoy,
            "insight": generate_recv_vs_revenue_insight(
                recv_yoy, rev_yoy, recv_rev_ratio, recv_rev_ratio_yoy
            ),
        },
    }

    return trends
