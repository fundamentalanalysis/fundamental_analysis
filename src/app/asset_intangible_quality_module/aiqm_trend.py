from typing import Dict, List, Optional

def compute_cagr(start, end, years):
    if start in (None, 0) or end in (None, 0) or start <= 0 or years <= 0:
        return None
    return ((end / start) ** (1 / years) - 1) * 100

def compute_yoy(current, previous):
    if previous in (None, 0) or current is None:
        return None
    return (current - previous) / previous

def build_year_map(values):
    mapping = {}
    for idx, val in enumerate(reversed(values)):
        mapping["Y" if idx == 0 else f"Y-{idx}"] = val
    return mapping

def build_yoy_map(values):
    yoy_map = {}
    n = len(values)
    for i in range(n - 1):
        curr = values[n - 1 - i]
        prev = values[n - 2 - i]
        label = "Y_vs_Y-1" if i == 0 else f"Y-{i}_vs_Y-{i+1}"
        yoy = compute_yoy(curr, prev)
        yoy_map[label] = round(yoy, 2) if yoy is not None else None
    return yoy_map

def generate_insight(yoy_list, metric):
    numeric = [v for v in yoy_list if v is not None]
    if not numeric:
        return f"No sufficient data to analyse {metric} trend."
    avg = round(sum(numeric) / len(numeric), 2)
    return f"{metric} exhibits mixed trend with average YoY growth of {avg}%."

# ------------------------------------------------------------
# MAIN TREND ENGINE
# ------------------------------------------------------------
def compute_aiqm_trends(financials):

    financials = sorted(financials, key=lambda x: x.year)

    gross_block_values = [f.gross_block for f in financials]
    cwip_values = [f.cwip for f in financials]
    revenue_values = [f.revenue for f in financials]
    intangible_values = [f.intangible_assets for f in financials]

    # 1️⃣ Intangible Growth YoY
    intangible_growth_yoy_values = [
        compute_yoy(intangible_values[i], intangible_values[i - 1])
        for i in range(1, len(intangible_values))
    ]

    # 2️⃣ Capitalization = ΔGrossBlock – ΔCWIP
    capitalization_values = [None]
    for i in range(1, len(financials)):
        gb_change = gross_block_values[i] - gross_block_values[i - 1]
        cwip_change = cwip_values[i] - cwip_values[i - 1]
        capitalization_values.append(gb_change - cwip_change)

    # 3️⃣ CWIP vs Capitalization Ratio
    cwip_vs_cap = [
        (cwip_values[i] / capitalization_values[i])
        if capitalization_values[i] not in (None, 0) else None
        for i in range(len(financials))
    ]

    # 4️⃣ Revenue YoY
    revenue_yoy_values = [
        compute_yoy(revenue_values[i], revenue_values[i - 1])
        for i in range(1, len(revenue_values))
    ]

    # 5️⃣ Asset Turnover Trend
    asset_turnover_values = [
        (f.revenue / f.net_block) if f.net_block not in (None, 0) else None
        for f in financials
    ]
    asset_turnover_yoy = [
        compute_yoy(asset_turnover_values[i], asset_turnover_values[i - 1])
        for i in range(1, len(asset_turnover_values))
    ]

    # 6️⃣ Asset Age Proxy Trend
    age_proxy_values = [
        (f.accumulated_depreciation / f.gross_block)
        if f.gross_block not in (None, 0) else None
        for f in financials
    ]
    age_proxy_yoy = [
        compute_yoy(age_proxy_values[i], age_proxy_values[i - 1])
        for i in range(1, len(age_proxy_values))
    ]

    capitalization_yoy = [
        compute_yoy(capitalization_values[i], capitalization_values[i - 1])
        for i in range(1, len(capitalization_values))
    ]

    cwip_yoy = [
        compute_yoy(cwip_values[i], cwip_values[i - 1])
        for i in range(1, len(cwip_values))
    ]

    # --------------------------------------------------------
    # CAGR CALCULATIONS
    # --------------------------------------------------------
    intangible_cagr = compute_cagr(intangible_values[0], intangible_values[-1], len(financials) - 1)
    revenue_cagr = compute_cagr(revenue_values[0], revenue_values[-1], len(financials) - 1)
    operating_asset_cagr = compute_cagr(gross_block_values[0], gross_block_values[-1], len(financials) - 1)

    # NEW FIELD: Intangible vs Revenue CAGR
    intangible_cagr_vs_revenue_cagr = None
    if intangible_cagr is not None and revenue_cagr is not None:
        intangible_cagr_vs_revenue_cagr = intangible_cagr - revenue_cagr

    # --------------------------------------------------------
    # BUILD FINAL TRENDS DICTIONARY
    # --------------------------------------------------------
    trends = {
        "asset_turnover": {
            "values": build_year_map(asset_turnover_values),
            "yoy_growth_pct": build_yoy_map(asset_turnover_values),
            "insight": generate_insight(asset_turnover_yoy, "Asset Turnover"),
        },
        "asset_age_proxy": {
            "values": build_year_map(age_proxy_values),
            "yoy_growth_pct": build_yoy_map(age_proxy_values),
            "insight": generate_insight(age_proxy_yoy, "Asset Age Proxy"),
        },
        "intangible_assets": {
            "values": build_year_map(intangible_values),
            "yoy_growth_pct": build_yoy_map(intangible_values),
            "insight": generate_insight(intangible_growth_yoy_values, "Intangibles"),
        },
        "cwip": {
            "values": build_year_map(cwip_values),
            "yoy_growth_pct": build_yoy_map(cwip_values),
            "insight": generate_insight(cwip_yoy, "CWIP"),
        },
        "capitalization": {
            "values": build_year_map(capitalization_values),
            "yoy_growth_pct": build_yoy_map(capitalization_values),
            "insight": generate_insight(capitalization_yoy, "Capitalization"),
        },
        "cwip_vs_capitalization": {
            "values": build_year_map(cwip_vs_cap),
            "insight": "CWIP vs Capitalization ratio evaluated.",
        },
        "revenue": {
            "values": build_year_map(revenue_values),
            "yoy_growth_pct": build_yoy_map(revenue_values),
            "insight": generate_insight(revenue_yoy_values, "Revenue"),
        },
        "cagr": {
            "intangible_cagr": intangible_cagr,
            "revenue_cagr": revenue_cagr,
            "operating_asset_cagr": operating_asset_cagr,
            "intangible_cagr_vs_revenue_cagr": intangible_cagr_vs_revenue_cagr,  # ✅ NEW FIELD
        },
    }

    return trends
