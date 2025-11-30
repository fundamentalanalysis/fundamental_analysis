# =============================================================
# src/app/equity_funding_module/equity_orchestrator.py
# Central orchestrator for the Equity & Funding Mix Module
# =============================================================

from collections import Counter
from typing import Dict, List

from .equity_metrics import compute_per_year_metrics
from .equity_trend import compute_trend_metrics
from .equity_rules import apply_rules
from .equity_llm import generate_llm_narrative
from .equity_models import (
    EquityFundingInput,
    EquityFundingOutput,
    EquityRuleResult,
    EquityBenchmarks,
)


# =============================================================
# SCORE ENGINE
# =============================================================
def compute_sub_score(rule_results: List[EquityRuleResult]) -> int:
    """
    Compute adjusted sub-score based on rule flags.
    
    Scoring:
    - Base score: 70
    - RED flag: -10 points
    - YELLOW flag: -5 points
    - GREEN flag: +1 point
    - Final score clamped to [0, 100]
    """
    c = Counter([r.flag for r in rule_results])
    
    score = 70
    score -= 10 * c.get("RED", 0)
    score -= 5 * c.get("YELLOW", 0)
    score += 1 * c.get("GREEN", 0)
    
    return max(0, min(100, score))


# =============================================================
# SUMMARY FLAGS
# =============================================================
def summarize(results: List[EquityRuleResult]):
    """
    Summarize rule results into red flags and positive points.
    """
    red_flags = []
    positives = []
    
    for r in results:
        if r.flag == "RED":
            # Determine severity based on rule category
            severity = "HIGH"
            if r.rule_id.startswith("C") or r.rule_id.startswith("D"):
                severity = "CRITICAL" if r.value and r.value > 1.0 else "HIGH"
            
            red_flags.append({
                "severity": severity,
                "title": r.rule_name,
                "detail": r.reason,
            })
        elif r.flag == "GREEN":
            positives.append(f"{r.rule_name}: {r.reason}")
    
    return red_flags, positives


# =============================================================
# RESHAPE METRICS (For Output Format)
# =============================================================
def reshape_metrics(per_year: Dict[int, dict]) -> Dict:
    """
    Reshape metrics from per-year dict to per-metric dict with year labels.
    
    Input:  {2024: {metric1: val, metric2: val}, 2023: {...}}
    Output: {metric1: {"Mar 2024": val, "Mar 2023": val}, metric2: {...}}
    """
    reshaped = {}
    
    # Sort years DESC so latest year comes first
    for year in sorted(per_year.keys(), reverse=True):
        label = f"Mar {year}"
        metrics = per_year[year]
        
        for metric_key, metric_value in metrics.items():
            if metric_key not in reshaped:
                reshaped[metric_key] = {}
            
            # Format the value appropriately
            if metric_value is None:
                reshaped[metric_key][label] = None
            elif isinstance(metric_value, float):
                # Check if it's a ratio/percentage (small values)
                if abs(metric_value) <= 10:
                    reshaped[metric_key][label] = round(metric_value, 4)
                else:
                    reshaped[metric_key][label] = round(metric_value, 2)
            else:
                reshaped[metric_key][label] = metric_value
    
    return reshaped


# =============================================================
# MAIN ORCHESTRATION FUNCTION
# =============================================================
def run_equity_funding_module(input_data: EquityFundingInput) -> EquityFundingOutput:
    """
    Main entry point for the Equity & Funding Mix Module.
    
    Pipeline:
    1. Compute per-year metrics
    2. Compute trend metrics
    3. Apply deterministic rules
    4. Generate LLM narrative
    5. Compile final output
    
    Args:
        input_data: EquityFundingInput with company data and financials
    
    Returns:
        EquityFundingOutput with scores, narrative, flags, and metrics
    """
    
    # Step 1: Compute per-year metrics
    per_year_metrics = compute_per_year_metrics(input_data.financials_5y)
    
    # Step 2: Compute trend metrics
    trend_metrics = compute_trend_metrics(
        input_data.financials_5y,
        per_year_metrics
    )
    
    # Step 3: Apply deterministic rules
    rule_results = apply_rules(
        input_data.financials_5y,
        per_year_metrics,
        trend_metrics,
        input_data.industry_benchmarks
    )
    
    # Step 4: Calculate score and summarize
    score = compute_sub_score(rule_results)
    red_flags, positives = summarize(rule_results)
    
    # Step 5: Generate LLM narrative
    narrative = generate_llm_narrative(
        company_id=input_data.company_id,
        metrics={"per_year": per_year_metrics, "trends": trend_metrics},
        rules=rule_results,
        trends=trend_metrics
    )
    
    # Parse narrative into lines
    narrative_lines = [x.strip() for x in narrative.split("\n") if x.strip()]
    
    # Reshape metrics for output
    reshaped_metrics = reshape_metrics(per_year_metrics)
    
    # Add trend metrics to output
    reshaped_metrics["_trends"] = {
        "retained_earnings_cagr": trend_metrics.get("retained_earnings_cagr"),
        "networth_cagr": trend_metrics.get("networth_cagr"),
        "equity_cagr": trend_metrics.get("equity_cagr"),
        "debt_cagr": trend_metrics.get("debt_cagr"),
        "pat_cagr": trend_metrics.get("pat_cagr"),
        "avg_roe_5y": trend_metrics.get("avg_roe_5y"),
        "avg_payout_5y": trend_metrics.get("avg_payout_5y"),
        "roe_declining_3y": trend_metrics.get("roe_declining_3y"),
        "debt_outpacing_equity": trend_metrics.get("debt_outpacing_equity"),
    }
    
    return EquityFundingOutput(
        module="EquityFundingMix",
        sub_score_adjusted=score,
        analysis_narrative=narrative_lines,
        red_flags=red_flags,
        positive_points=positives,
        rule_results=rule_results,
        metrics=reshaped_metrics,
    )
