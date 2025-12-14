from typing import Dict, List, Optional, Any


def generate_fallback_insight(
    metric_name: str,
    values: Dict[str, Optional[float]],
    yoy_growth_pct: Dict[str, Optional[float]]
) -> str:
    """
    Generate fallback insights for metrics when LLM is unavailable or returns empty.
    Analyzes historical data patterns to create meaningful insights.
    """

    # Extract values in chronological order
    vals = [values.get(k) for k in ["Y-4", "Y-3", "Y-2", "Y-1", "Y"]]
    valid_vals = [v for v in vals if v is not None]

    if not valid_vals:
        return f"Insufficient data for {metric_name} analysis."

    current = values.get("Y")

    if metric_name == "retained_earnings":
        if current is None:
            return "Retained earnings data not available."
        if current == 0:
            return "No retained earnings; company may be burning through reserves or operating at breakeven."
        trend = "increasing" if len(
            valid_vals) > 1 and valid_vals[-1] >= valid_vals[-2] else "declining"
        growth = yoy_growth_pct.get("Y_vs_Y-1")
        if growth is None or growth == 0:
            return f"Retained earnings {trend}, with minimal growth. Internal capital formation is weak."
        return f"Retained earnings {trend} at {growth:.2f}% YoY. {'Strong' if growth > 5 else 'Modest'} internal capital accumulation."

    elif metric_name == "payout_ratio":
        if current is None or current == 0:
            return "No dividend payouts; all earnings retained for growth or financial stability."
        if current > 1.0:
            return f"Payout ratio {current:.0%} exceeds earnings; unsustainable dividend policy funded from reserves/debt."
        if current > 0.5:
            return f"High payout ratio of {current:.0%}; limited room for reinvestment or emergency reserves."
        return f"Moderate payout ratio of {current:.0%}; balanced between shareholder returns and reinvestment."

    elif metric_name == "roe":
        if current is None or current == 0:
            return "ROE is zero or undefined; company generating no returns on equity capital (unprofitable or minimal earnings)."
        if current < 0.10:
            return f"Weak ROE of {current:.1%}; capital efficiency below industry benchmarks. Risk of value destruction."
        if current < 0.15:
            return f"Moderate ROE of {current:.1%}; acceptable but room for improvement in capital deployment."
        if current >= 0.20:
            return f"Excellent ROE of {current:.1%}; strong capital efficiency and shareholder value creation."
        return f"ROE of {current:.1%} indicates good capital efficiency."

    elif metric_name == "equity_growth_rate":
        if current is None or current == 0:
            return "Equity base is stagnant; no share capital growth. Company retaining earnings but not expanding share capital."
        if current < 0:
            return f"Equity declining at {current:.1%} YoY; shareholder base shrinking, possibly from buybacks or losses."
        if current > 0.10:
            return f"Strong equity growth of {current:.1%} YoY; company raising capital and expanding shareholder base."
        return f"Modest equity growth of {current:.1%} YoY; steady capital base expansion."

    elif metric_name == "debt_growth_rate":
        if current is None or current == 0:
            return "Debt is stable; no new borrowings. Company maintaining current leverage levels."
        if current < 0:
            return f"Debt declining at {current:.1%} YoY; company deleveraging and reducing financial risk."

        # Compare with equity growth
        # Note: This is debt growth here
        equity_growth = yoy_growth_pct.get("Y_vs_Y-1")
        if current > 0.20:
            return f"Aggressive debt growth of {current:.1%} YoY; rising leverage and financial risk. Monitor refinancing ability."
        if current > 0.10:
            return f"Moderate debt growth of {current:.1%} YoY; increasing reliance on borrowing for growth."
        return f"Stable debt growth of {current:.1%} YoY; moderate leverage change."

    return f"Trend analysis for {metric_name}: data pattern suggests ongoing monitoring needed."
