
# ============================================================
# debt_orchestrator.py
# Central orchestrator for the Borrowings Module
# ============================================================

from collections import Counter

from .debt_metrics import compute_per_year_metrics
from .debt_trend import compute_trend_metrics
from .debt_rules import apply_rules
from .debt_llm import generate_llm_narrative
from .debt_models import BorrowingsInput, BorrowingsOutput


# ============================================================
# SCORE ENGINE
# ============================================================
def compute_sub_score(rule_results):
    c = Counter([r.flag for r in rule_results])

    score = 70
    score -= 10 * c["RED"]
    score -= 5 * c["YELLOW"]
    score += 1 * c["GREEN"]

    return max(0, min(100, score))


# ============================================================
# SUMMARY FLAGS
# ============================================================
def summarize(results):
    red_flags = []
    positives = []

    for r in results:
        if r.flag == "RED":
            red_flags.append({
                "severity": "HIGH",
                "title": r.rule_name,
                "detail": r.reason,
            })
        elif r.flag == "GREEN":
            positives.append(f"{r.rule_name} is healthy.")

    return red_flags, positives


# ============================================================
# RESHAPE METRICS (Your Required Format)
# ============================================================
def reshape_metrics(per_year):
    reshaped = {}

    # sort years DESC so latest year comes first
    for year in sorted(per_year.keys(), reverse=True):
        label = f"Mar {year}"
        metrics = per_year[year]

        for metric_key, metric_value in metrics.items():
            if metric_key not in reshaped:
                reshaped[metric_key] = {}
            reshaped[metric_key][label] = metric_value

    return reshaped


# ============================================================
# MAIN ORCHESTRATION FUNCTION
# ============================================================
def run_borrowings_module(bi: BorrowingsInput) -> BorrowingsOutput:

    per_year_metrics = compute_per_year_metrics(bi.financials_5y, bi.midd)

    trend_metrics = compute_trend_metrics(bi.financials_5y, per_year_metrics)

    rule_results = apply_rules(bi.financials_5y, per_year_metrics, trend_metrics)

    score = compute_sub_score(rule_results)
    red_flags, positives = summarize(rule_results)

    narration = generate_llm_narrative(
        bi.company_id,
        metrics={"per_year": per_year_metrics, "trends": trend_metrics},
        rules=rule_results,
    )

    narrative_lines = [x.strip() for x in narration.split("\n") if x.strip()]

    reshaped_metrics = reshape_metrics(per_year_metrics)

    return BorrowingsOutput(
        module="Borrowings",
        sub_score_adjusted=score,
        analysis_narrative=narrative_lines,
        red_flags=red_flags,
        positive_points=positives,
        rule_results=rule_results,
        metrics=reshaped_metrics,
    )
