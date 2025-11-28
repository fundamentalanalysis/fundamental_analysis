"""
Generate data-driven insights from trend patterns (fallback when LLM is unavailable)
"""
from typing import Dict


def generate_fallback_insight(metric_name: str, values: Dict[str, float], yoy_growth_pct: Dict[str, float]) -> str:
    """
    Generate intelligent insights based on actual data patterns without LLM.
    Analyzes growth patterns, volatility, and trends.
    """
    # Extract growth values (filter out None)
    growth_values = [v for v in yoy_growth_pct.values() if v is not None]
    
    if not growth_values:
        return f"{metric_name.replace('_', ' ').title()} data is insufficient for trend analysis."
    
    # Calculate statistics
    avg_growth = sum(growth_values) / len(growth_values)
    max_growth = max(growth_values)
    min_growth = min(growth_values)
    volatility = max_growth - min_growth
    
    # Recent trend (last 2 periods)
    recent_growth = [yoy_growth_pct.get('Y_vs_Y-1'), yoy_growth_pct.get('Y-1_vs_Y-2')]
    recent_growth = [v for v in recent_growth if v is not None]
    recent_avg = sum(recent_growth) / len(recent_growth) if recent_growth else 0
    
    # Pattern detection
    is_accelerating = len(growth_values) >= 3 and growth_values[0] > growth_values[1] > growth_values[2]
    is_decelerating = len(growth_values) >= 3 and growth_values[0] < growth_values[1] < growth_values[2]
    is_volatile = volatility > 30
    is_high_growth = avg_growth > 15
    is_declining = avg_growth < -5
    
    # Build insight based on patterns
    insights = []
    
    # Metric-specific context
    if metric_name == "short_term_debt":
        if is_declining:
            insights.append("Short-term debt is declining, suggesting improved liquidity management or shift to long-term financing.")
        elif is_high_growth:
            insights.append("Short-term debt shows rising reliance on rollover funding.")
            if max_growth > 20:
                insights.append(f"Peak YoY spike of {max_growth:.1f}% indicates stressed liquidity or dependency on working-capital loans.")
        
        if is_volatile:
            insights.append(f"High volatility (range: {min_growth:.1f}% to {max_growth:.1f}%) suggests unstable funding patterns.")
        
        if recent_avg < 0:
            insights.append(f"Recent deceleration to {recent_avg:.1f}% suggests stabilization.")
    
    elif metric_name == "long_term_debt":
        if is_high_growth:
            insights.append("Long-term debt has been increasing steadily, suggesting capacity expansion or CWIP funding.")
            if recent_avg > avg_growth:
                insights.append("Acceleration in recent years may indicate distress-driven borrowing if outpacing revenue/EBITDA growth.")
        elif is_declining:
            insights.append("Long-term debt reduction indicates deleveraging or debt repayment focus.")
        elif abs(recent_growth[0]) < 2 if recent_growth else False:
            insights.append(f"Recent plateau (Y vs Y-1: {yoy_growth_pct.get('Y_vs_Y-1', 0):.1f}%) may indicate completed projects or constrained credit access.")
    
    elif metric_name == "finance_cost":
        if avg_growth > 10:
            insights.append("Finance cost growth consistently outpaces typical debt growth patterns.")
            insights.append("This indicates rising borrowing costs, interest rate pressure, or shift toward more expensive debt instruments.")
        
        if max_growth > 30:
            insights.append(f"Peak growth of {max_growth:.1f}% suggests significant rate or structure changes during the period.")
        
        if is_decelerating and recent_avg < avg_growth / 2:
            insights.append("Recent deceleration suggests stabilizing rates or improved debt mix.")
    
    # Generic patterns if no specific insights
    if not insights:
        if is_accelerating:
            insights.append(f"{metric_name.replace('_', ' ').title()} shows accelerating growth pattern (avg: {avg_growth:.1f}%).")
        elif is_decelerating:
            insights.append(f"{metric_name.replace('_', ' ').title()} shows decelerating growth pattern (avg: {avg_growth:.1f}%).")
        else:
            insights.append(f"{metric_name.replace('_', ' ').title()} exhibits mixed trend with average YoY growth of {avg_growth:.1f}%.")
    
    return " ".join(insights)
