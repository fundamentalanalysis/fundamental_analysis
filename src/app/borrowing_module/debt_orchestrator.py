
# # ============================================================
# # debt_orchestrator.py
# # Central orchestrator for the Borrowings Module
# # ============================================================

# from collections import Counter

# from .debt_metrics import compute_per_year_metrics
# from .debt_trend import compute_trend_metrics
# from .debt_rules import apply_rules
# from .debt_llm import generate_llm_narrative
# from .debt_models import BorrowingsInput, BorrowingsOutput


# # ============================================================
# # SCORE ENGINE
# # ============================================================
# def compute_sub_score(rule_results):
#     c = Counter([r.flag for r in rule_results])

#     score = 70
#     score -= 10 * c["RED"]
#     score -= 5 * c["YELLOW"]
#     score += 1 * c["GREEN"]

#     return max(0, min(100, score))


# # ============================================================
# # SUMMARY FLAGS
# # ============================================================
# def summarize(results):
#     red_flags = []
#     positives = []

#     for r in results:
#         if r.flag == "RED":
#             red_flags.append({
#                 "severity": "HIGH",
#                 "title": r.rule_name,
#                 "detail": r.reason,
#             })
#         elif r.flag == "GREEN":
#             positives.append(f"{r.rule_name} is healthy.")

#     return red_flags, positives


# # ============================================================
# # RESHAPE METRICS (Your Required Format)
# # ============================================================
# def reshape_metrics(per_year):
#     reshaped = {}

#     # sort years DESC so latest year comes first
#     for year in sorted(per_year.keys(), reverse=True):
#         label = f"Mar {year}"
#         metrics = per_year[year]

#         for metric_key, metric_value in metrics.items():
#             if metric_key not in reshaped:
#                 reshaped[metric_key] = {}
#             reshaped[metric_key][label] = metric_value

#     return reshaped


# # ============================================================
# # MAIN ORCHESTRATION FUNCTION
# # ============================================================
# def run_borrowings_module(bi: BorrowingsInput) -> BorrowingsOutput:

#     per_year_metrics = compute_per_year_metrics(bi.financials_5y, bi.midd)

#     trend_metrics = compute_trend_metrics(bi.financials_5y, per_year_metrics)

#     rule_results = apply_rules(bi.financials_5y, per_year_metrics, trend_metrics)

#     score = compute_sub_score(rule_results)
#     red_flags, positives = summarize(rule_results)

#     narration = generate_llm_narrative(
#         bi.company_id,
#         metrics={"per_year": per_year_metrics, "trends": trend_metrics},
#         rules=rule_results,
#     )

#     narrative_lines = [x.strip() for x in narration.split("\n") if x.strip()]

#     reshaped_metrics = reshape_metrics(per_year_metrics)

#     return BorrowingsOutput(
#         module="Borrowings",
#         sub_score_adjusted=score,
#         analysis_narrative=narrative_lines,
#         red_flags=red_flags,
#         positive_points=positives,
#         rule_results=rule_results,
#         metrics=reshaped_metrics,
#     )

# ============================================================
# debt_orchestrator.py
# Central orchestrator for the Borrowings Module
# ============================================================

from collections import Counter

from .debt_metrics import compute_per_year_metrics, compute_yoy_percentage
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
# METRIC OUTPUT — ONLY YOY PERCENTAGE CHANGE
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

# def compute_yoy_percentage(per_year_metrics):
#     """
#     Converts per-year metric values into YoY % growth format.
#     """
#     yoy_metrics = {}
#     years = sorted(per_year_metrics.keys())
    
#     for metric in per_year_metrics[years[0]].keys():
#         yoy_metrics[metric] = {}
#         for i, year in enumerate(years):
#             label = f"Mar {year}"
#             if i == 0:
#                 yoy_metrics[metric][label] = None  # No previous year
#             else:
#                 prev_year = years[i-1]
#                 curr_value = per_year_metrics[year][metric]
#                 prev_value = per_year_metrics[prev_year][metric]
#                 if prev_value in (0, None) or curr_value is None:
#                     yoy_metrics[metric][label] = None
#                 else:
#                     pct_change = ((curr_value - prev_value) / prev_value) * 100
#                     yoy_metrics[metric][label] = f"{pct_change:.0f}%"
#     return yoy_metrics




# ============================================================
# MAIN ORCHESTRATION FUNCTION
# ============================================================
def run_borrowings_module(bi: BorrowingsInput) -> BorrowingsOutput:

    per_year_metrics = compute_per_year_metrics(bi.financials_5y)
    
    yoy_metrics = compute_yoy_percentage(per_year_metrics)

    # 2. Compute trends (CAGR, YoY debt surge, etc.)
    trend_metrics = compute_trend_metrics(bi.financials_5y, per_year_metrics)

    # 3. Apply rules
    rule_results = apply_rules(bi.financials_5y, per_year_metrics, trend_metrics)

    # 4. Score
    score = compute_sub_score(rule_results)

    # 5. Flags
    red_flags, positives = summarize(rule_results)

    # 6. LLM narrative
    narration = generate_llm_narrative(
        bi.company_id,
        metrics={"per_year": per_year_metrics, "trends": trend_metrics},
        rules=rule_results,
    )
    narrative_lines = [line.strip() for line in narration.split("\n") if line.strip()]

    # 7. Produce ONLY YoY growth %
    metrics_output = reshape_metrics(per_year_metrics)

    reshaped_metrics = reshape_metrics(per_year_metrics)
   
    yoy_metrics['wacd'] = reshaped_metrics['wacd']
    yoy_metrics['floating_share'] = reshaped_metrics['floating_share']
    yoy_metrics['maturity_lt_1y_pct'] = reshaped_metrics['maturity_lt_1y_pct']
    yoy_metrics['maturity_1_3y_pct'] = reshaped_metrics['maturity_1_3y_pct']
    yoy_metrics['maturity_gt_3y_pct'] = reshaped_metrics['maturity_gt_3y_pct']

    return BorrowingsOutput(
        module="Borrowings",
        sub_score_adjusted=score,
        analysis_narrative=narrative_lines,
        red_flags=red_flags,
        positive_points=positives,
        rule_results=rule_results,
        metrics=yoy_metrics
        
    )