# =============================================================
# src/app/equity_funding_module/equity_llm.py
# LLM Agent for Equity & Funding Mix narrative generation
# =============================================================

from typing import Dict, List, Any

# Import from the config.py file (not the config/ folder)
from src.app.config import OPENAI_MODEL, get_llm_client
from .equity_models import EquityRuleResult

client = get_llm_client()
model = OPENAI_MODEL


def generate_llm_narrative(
    company_id: str,
    metrics: Dict[str, Any],
    rules: List[EquityRuleResult],
    trends: Dict[str, Any]
) -> str:
    """
    Generate LLM-based narrative analysis for Equity & Funding Mix.
    
    Args:
        company_id: Company identifier
        metrics: Per-year and trend metrics
        rules: List of rule evaluation results
        trends: Trend metrics
    
    Returns:
        Structured narrative analysis
    """
    
    # Prepare rule summaries by flag type
    red_rules = [r for r in rules if r.flag == "RED"]
    yellow_rules = [r for r in rules if r.flag == "YELLOW"]
    green_rules = [r for r in rules if r.flag == "GREEN"]
    
    prompt = f"""
You are a senior equity analyst specializing in capital structure and shareholder value analysis.

Generate a comprehensive Equity, Retained Earnings & Funding Mix Analysis for company {company_id}.

## METRICS SUMMARY
{_format_metrics(metrics)}

## TREND ANALYSIS
{_format_trends(trends)}

## RULE FLAGS
### Critical Issues (RED):
{_format_rules(red_rules) if red_rules else "None"}

### Warnings (YELLOW):
{_format_rules(yellow_rules) if yellow_rules else "None"}

### Positives (GREEN):
{_format_rules(green_rules) if green_rules else "None"}

---

Write a structured analysis covering ONLY these sections:

1. **Overall Equity Quality Assessment**
   - Brief summary of equity health and capital structure

2. **Retained Earnings & Internal Capital Formation**
   - Analysis of profit retention and reserves growth
   - Internal financing capacity

3. **Return on Equity (ROE) Analysis**
   - Capital efficiency assessment
   - Trend analysis

4. **Dividend Policy Sustainability**
   - Payout discipline evaluation
   - FCF coverage of dividends
   - Long-term sustainability

5. **Equity Dilution Assessment**
   - Share issuance analysis
   - Impact on existing shareholders

6. **Funding Mix Analysis**
   - Debt vs equity reliance
   - Capital structure evolution

7. **Key Concerns**
   - List main red and yellow flags with implications

8. **Positive Factors**
   - List strengths and healthy indicators

9. **Final Assessment & Recommendations**
   - Overall equity quality score narrative
   - Investment/credit implications
   - Key monitoring points

Keep the analysis factual, concise, and actionable.
"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    return response.choices[0].message.content


def _format_metrics(metrics: Dict[str, Any]) -> str:
    """Format metrics for prompt"""
    per_year = metrics.get("per_year", {})
    
    if not per_year:
        return "No metrics available"
    
    # Get latest year metrics
    latest_year = max(per_year.keys())
    latest = per_year[latest_year]
    
    lines = [
        f"Latest Year ({latest_year}):",
        f"  - Net Worth: {latest.get('net_worth', 'N/A'):,.0f}" if latest.get('net_worth') else "",
        f"  - Retained Earnings: {latest.get('retained_earnings', 'N/A'):,.0f}" if latest.get('retained_earnings') else "",
        f"  - PAT: {latest.get('pat', 'N/A'):,.0f}" if latest.get('pat') else "",
        f"  - ROE: {latest.get('roe', 0)*100:.1f}%" if latest.get('roe') else "",
        f"  - Dividend Payout Ratio: {latest.get('dividend_payout_ratio', 0)*100:.1f}%" if latest.get('dividend_payout_ratio') else "",
        f"  - Dividend to FCF Ratio: {latest.get('dividend_to_fcf_ratio', 0)*100:.1f}%" if latest.get('dividend_to_fcf_ratio') else "",
        f"  - Equity Dilution: {latest.get('equity_dilution_pct', 0)*100:.2f}%" if latest.get('equity_dilution_pct') else "",
        f"  - Debt-to-Equity: {latest.get('debt_to_equity', 0):.2f}" if latest.get('debt_to_equity') else "",
        f"  - Equity Ratio: {latest.get('equity_ratio', 0)*100:.1f}%" if latest.get('equity_ratio') else "",
    ]
    
    return "\n".join([l for l in lines if l])


def _format_trends(trends: Dict[str, Any]) -> str:
    """Format trends for prompt"""
    lines = [
        f"5-Year CAGRs:",
        f"  - Retained Earnings CAGR: {trends.get('retained_earnings_cagr', 'N/A'):.1f}%" if trends.get('retained_earnings_cagr') is not None else "",
        f"  - Net Worth CAGR: {trends.get('networth_cagr', 'N/A'):.1f}%" if trends.get('networth_cagr') is not None else "",
        f"  - PAT CAGR: {trends.get('pat_cagr', 'N/A'):.1f}%" if trends.get('pat_cagr') is not None else "",
        f"  - Debt CAGR: {trends.get('debt_cagr', 'N/A'):.1f}%" if trends.get('debt_cagr') is not None else "",
        f"  - Equity (Share Capital) CAGR: {trends.get('equity_cagr', 'N/A'):.1f}%" if trends.get('equity_cagr') is not None else "",
        "",
        f"Trend Indicators:",
        f"  - ROE Declining 3Y: {'Yes' if trends.get('roe_declining_3y') else 'No'}",
        f"  - Debt Outpacing Equity: {'Yes' if trends.get('debt_outpacing_equity') else 'No'}",
        f"  - Net Worth Stagnant + Debt Rising: {'Yes' if trends.get('networth_stagnant_debt_rising') else 'No'}",
        f"  - Average ROE (5Y): {trends.get('avg_roe_5y', 0)*100:.1f}%" if trends.get('avg_roe_5y') is not None else "",
    ]
    
    return "\n".join([l for l in lines if l])


def _format_rules(rules: List[EquityRuleResult]) -> str:
    """Format rule results for prompt"""
    if not rules:
        return "None"
    
    lines = []
    for r in rules:
        value_str = f" (Value: {r.value:.4f})" if r.value is not None else ""
        lines.append(f"- [{r.rule_id}] {r.rule_name}{value_str}: {r.reason}")
    
    return "\n".join(lines)
