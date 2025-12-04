# # rules_engine.py

# from typing import Dict, Any
# from src.app.config import DEFAULT_CAPEX_CWIP_RULES as R

# def flag(rule_id, name, value, threshold, flag, reason):
#     return {
#         "rule_id": rule_id,
#         "rule_name": name,
#         "value": value,
#         "threshold": threshold,
#         "flag": flag,
#         "reason": reason
#     }


# def evaluate_rules(metrics, cagr_data):
#     flags = []

#     capex_int = metrics["capex_intensity"]

#     # A1 – Capex Intensity
#     if capex_int is not None:
#         if capex_int > R["capex_intensity_high"]:
#             flags.append(flag("A1", "High Capex Intensity", capex_int, ">0.15", "RED",
#                               "Capex intensity exceeds 15%, aggressive expansion."))
#         elif capex_int > R["capex_intensity_moderate"]:
#             flags.append(flag("A1", "Moderate Capex Intensity", capex_int, "0.10–0.15", "YELLOW",
#                               "Capex is elevated versus revenue."))
#         else:
#             flags.append(flag("A1", "Normal Capex", capex_int, "<0.10", "GREEN",
#                               "Capex intensity is healthy."))
#     else:
#         flags.append(flag("A1", "Capex Intensity", None, "<0.10", "NOT_APPLICABLE",
#                           "Insufficient data to evaluate."))

#     # A2 – Capex growing faster than revenue
#     if cagr_data["capex_cagr"] is not None and cagr_data["revenue_cagr"] is not None:
#         if cagr_data["capex_cagr"] > (cagr_data["revenue_cagr"] + R["capex_vs_revenue_gap_warning"]):
#             flags.append(flag("A2", "Capex Growing Too Fast", cagr_data["capex_cagr"],
#                               "Capex CAGR > Revenue CAGR + 10%", "YELLOW",
#                               "Capex growth exceeds revenue growth by more than 10%."))
#         else:
#             flags.append(flag("A2", "Capex vs Revenue Growth Normal", cagr_data["capex_cagr"],
#                               "Capex CAGR ≤ Revenue CAGR + 10%", "GREEN",
#                               "Capex growth in line with revenue growth."))
#     else:
#         flags.append(flag("A2", "Capex vs Revenue Growth", None,
#                           "Capex CAGR > Revenue CAGR + 10%", "NOT_APPLICABLE",
#                           "Insufficient data to evaluate."))

#     # B1 – CWIP %
#     cwip_pct = metrics["cwip_pct"]
#     if cwip_pct is not None:
#         if cwip_pct > R["cwip_pct_critical"]:
#             flags.append(flag("B1", "CWIP % Critical", cwip_pct, ">0.40", "RED",
#                               "CWIP > 40% of fixed assets."))
#         elif cwip_pct > R["cwip_pct_warning"]:
#             flags.append(flag("B1", "CWIP % High", cwip_pct, "0.30–0.40", "YELLOW",
#                               "Heavy project pipeline indicated."))
#         else:
#             flags.append(flag("B1", "CWIP % Normal", cwip_pct, "<0.30", "GREEN",
#                               "CWIP as % of fixed assets is normal."))
#     else:
#         flags.append(flag("B1", "CWIP %", None, "<0.30", "NOT_APPLICABLE",
#                           "Insufficient data to evaluate."))

#     # B2 – CWIP rising 3 years
#     if cagr_data["cwip_increasing_3y"]:
#         flags.append(flag("B2", "CWIP Increasing 3 Years",
#                           None, "Rise 3 consecutive years", "YELLOW",
#                           "CWIP has risen 3 consecutive years."))
#     else:
#         flags.append(flag("B2", "CWIP Trend",
#                           None, "Rise 3 consecutive years", "GREEN",
#                           "CWIP not increasing for 3 consecutive years."))

#     # B3 – CWIP down + NFA up
#     if metrics["cwip_yoy"] is not None and metrics["nfa_yoy"] is not None and metrics["cwip_yoy"] < 0 and metrics["nfa_yoy"] > 0:
#         flags.append(flag("B3", "CWIP Rollover", None,
#                           "CWIP↓ & NFA↑", "GREEN",
#                           "Projects capitalized from CWIP into NFA."))
#     else:
#         flags.append(flag("B3", "CWIP Rollover",
#                           None, "CWIP↓ & NFA↑", "NOT_APPLICABLE",
#                           "No CWIP rollover pattern detected or insufficient data."))

#     # C1 – Asset turnover
#     at = metrics["asset_turnover"]
#     if at is not None:
#         if at < R["asset_turnover_critical"]:
#             flags.append(flag("C1", "Asset Turnover Very Low", at, "<0.7", "RED",
#                               "Fixed asset turnover extremely weak."))
#         elif at < R["asset_turnover_low"]:
#             flags.append(flag("C1", "Asset Turnover Low", at, "0.7–1.0", "YELLOW",
#                               "Fixed asset utilization below optimal."))
#         else:
#             flags.append(flag("C1", "Asset Turnover Healthy", at, ">1.0", "GREEN",
#                               "Good utilization of fixed assets."))
#     else:
#         flags.append(flag("C1", "Asset Turnover", None, ">1.0", "NOT_APPLICABLE",
#                           "Insufficient data to evaluate."))

#     # C2 – NFA rising while revenue stagnant
#     if cagr_data["nfa_cagr"] is not None and cagr_data["revenue_cagr"] is not None:
#         if cagr_data["nfa_cagr"] > (cagr_data["revenue_cagr"] + 0.10):
#             flags.append(flag("C2", "NFA Growing Too Fast",
#                                cagr_data["nfa_cagr"],
#                                "NFA CAGR > Revenue CAGR + 10%", "RED",
#                                "Underutilized capacity or stranded assets."))
#         else:
#             flags.append(flag("C2", "NFA vs Revenue Growth Normal",
#                                cagr_data["nfa_cagr"],
#                                "NFA CAGR ≤ Revenue CAGR + 10%", "GREEN",
#                                "NFA growth in line with revenue growth."))
#     else:
#         flags.append(flag("C2", "NFA vs Revenue Growth", None,
#                           "NFA CAGR > Revenue CAGR + 10%", "NOT_APPLICABLE",
#                           "Insufficient data to evaluate."))

#     # D1 – Debt-funded capex
#     dfc = metrics["debt_funded_capex"]
#     if dfc is not None:
#         if dfc >= 1.0:
#             flags.append(flag("D1", "Fully Debt Funded Capex", dfc, ">=1.0", "RED",
#                               "Capex entirely funded through debt."))
#         elif dfc >= R["debt_funded_capex_warning"]:
#             flags.append(flag("D1", "Debt-Funded Capex High", dfc, ">=0.5", "YELLOW",
#                               "Significant dependency on debt for capex."))
#         else:
#             flags.append(flag("D1", "Debt-Funded Capex Low", dfc, "<0.5", "GREEN",
#                               "Capex mostly internally funded."))
#     else:
#         flags.append(flag("D1", "Debt-Funded Capex", None, "<0.5", "NOT_APPLICABLE",
#                           "Insufficient data to evaluate."))

#     # D2 – FCF coverage
#     fcf_cov = metrics["fcf_coverage"]
#     if fcf_cov is not None:
#         if fcf_cov < 0:
#             flags.append(flag("D2", "Negative FCF Coverage", fcf_cov, "<0", "RED",
#                               "Capex executed despite negative free cash flow."))
#         elif fcf_cov < 0.5:
#             flags.append(flag("D2", "Weak FCF Coverage", fcf_cov, "0–0.5", "YELLOW",
#                               "Limited internal reinvestment capacity."))
#         else:
#             flags.append(flag("D2", "Strong FCF Coverage", fcf_cov, ">0.5", "GREEN",
#                               "Capex well supported by free cash flow."))
#     else:
#         flags.append(flag("D2", "FCF Coverage", None, ">0.5", "NOT_APPLICABLE",
#                           "Insufficient data to evaluate."))

#     return flags


# capex_rules_engine.py

from typing import List, Dict, Any

from src.app.config import DEFAULT_CAPEX_CWIP_RULES as R
from .models import RuleResult # 👈 adjust import path if RuleResult is elsewhere
# from .llm_agent import generate_llm_narrative

def _make(
    rule_id: str,
    name: str,
    metric: str,
    year: int,
    flag: str,
    value: Any,
    threshold: str,
    reason: str,
) -> RuleResult:
    """
    Helper to build a RuleResult, matching the style of the borrowings rules engine.
    """
    return RuleResult(
        rule_id=rule_id,
        rule_name=name,
        metric=metric,
        year=year,
        flag=flag,
        value=value,
        threshold=threshold,
        reason=reason,
    )


def apply_rules(metrics: Dict[str, Any], cagr_data: Dict[str, Any]) -> List[RuleResult]:
    """
    Capex & CWIP rules, refactored to return RuleResult objects similar to the
    borrowings rules engine.

    `metrics` is assumed to be a dict for a single (latest) year, e.g.
        {
            "year": 2024,
            "capex_intensity": ...,
            "cwip_pct": ...,
            "cwip_yoy": ...,
            "nfa_yoy": ...,
            "asset_turnover": ...,
            "debt_funded_capex": ...,
            "fcf_coverage": ...,
            ...
        }

    `cagr_data` is assumed to contain trend metrics, e.g.
        {
            "capex_cagr": ...,
            "revenue_cagr": ...,
            "cwip_increasing_3y": ...,
            "nfa_cagr": ...,
            ...
        }
    """
    results: List[RuleResult] = []

    # Try to pick a year if available; otherwise default to 0 or any sentinel
    year = metrics.get("year") if isinstance(metrics, dict) else None
    if year is None:
        year = 0  # or your preferred default

    # --------------------
    # A1 – Capex Intensity
    # --------------------
    capex_int = metrics.get("capex_intensity")

    if capex_int is not None:
        if capex_int > R["capex_intensity_high"]:
            results.append(
                _make(
                    "A1",
                    "High Capex Intensity",
                    "capex_intensity",
                    year,
                    "RED",
                    capex_int,
                    ">0.15",
                    "Capex intensity exceeds 15%, aggressive expansion.",
                )
            )
        elif capex_int > R["capex_intensity_moderate"]:
            results.append(
                _make(
                    "A1",
                    "Moderate Capex Intensity",
                    "capex_intensity",
                    year,
                    "YELLOW",
                    capex_int,
                    "0.10–0.15",
                    "Capex is elevated versus revenue.",
                )
            )
        else:
            results.append(
                _make(
                    "A1",
                    "Normal Capex",
                    "capex_intensity",
                    year,
                    "GREEN",
                    capex_int,
                    "<0.10",
                    "Capex intensity is healthy.",
                )
            )
    else:
        results.append(
            _make(
                "A1",
                "Capex Intensity",
                "capex_intensity",
                year,
                "NOT_APPLICABLE",
                None,
                "<0.10",
                "Insufficient data to evaluate.",
            )
        )

    # --------------------------------------------------
    # A2 – Capex growing faster than revenue (CAGR gap)
    # --------------------------------------------------
    capex_cagr = cagr_data.get("capex_cagr")
    revenue_cagr = cagr_data.get("revenue_cagr")
    gap_warn = R["capex_vs_revenue_gap_warning"]

    if capex_cagr is not None and revenue_cagr is not None:
        if capex_cagr > (revenue_cagr + gap_warn):
            results.append(
                _make(
                    "A2",
                    "Capex Growing Too Fast",
                    "capex_cagr",
                    year,
                    "YELLOW",
                    capex_cagr,
                    "Capex CAGR > Revenue CAGR + 10%",
                    "Capex growth exceeds revenue growth by more than 10%.",
                )
            )
        else:
            results.append(
                _make(
                    "A2",
                    "Capex vs Revenue Growth Normal",
                    "capex_cagr",
                    year,
                    "GREEN",
                    capex_cagr,
                    "Capex CAGR ≤ Revenue CAGR + 10%",
                    "Capex growth in line with revenue growth.",
                )
            )
    else:
        results.append(
            _make(
                "A2",
                "Capex vs Revenue Growth",
                "capex_cagr",
                year,
                "NOT_APPLICABLE",
                None,
                "Capex CAGR > Revenue CAGR + 10%",
                "Insufficient data to evaluate.",
            )
        )

    # -------------
    # B1 – CWIP %
    # -------------
    cwip_pct = metrics.get("cwip_pct")
    if cwip_pct is not None:
        if cwip_pct > R["cwip_pct_critical"]:
            results.append(
                _make(
                    "B1",
                    "CWIP % Critical",
                    "cwip_pct",
                    year,
                    "RED",
                    cwip_pct,
                    ">0.40",
                    "CWIP > 40% of fixed assets.",
                )
            )
        elif cwip_pct > R["cwip_pct_warning"]:
            results.append(
                _make(
                    "B1",
                    "CWIP % High",
                    "cwip_pct",
                    year,
                    "YELLOW",
                    cwip_pct,
                    "0.30–0.40",
                    "Heavy project pipeline indicated.",
                )
            )
        else:
            results.append(
                _make(
                    "B1",
                    "CWIP % Normal",
                    "cwip_pct",
                    year,
                    "GREEN",
                    cwip_pct,
                    "<0.30",
                    "CWIP as % of fixed assets is normal.",
                )
            )
    else:
        results.append(
            _make(
                "B1",
                "CWIP %",
                "cwip_pct",
                year,
                "NOT_APPLICABLE",
                None,
                "<0.30",
                "Insufficient data to evaluate.",
            )
        )

    # --------------------------------
    # B2 – CWIP rising 3 consecutive years
    # --------------------------------
    cwip_increasing_3y = cagr_data.get("cwip_increasing_3y")
    if cwip_increasing_3y is True:
        results.append(
            _make(
                "B2",
                "CWIP Increasing 3 Years",
                "cwip",
                year,
                "YELLOW",
                None,
                "Rise 3 consecutive years",
                "CWIP has risen 3 consecutive years.",
            )
        )
    elif cwip_increasing_3y is False:
        results.append(
            _make(
                "B2",
                "CWIP Trend",
                "cwip",
                year,
                "GREEN",
                None,
                "Rise 3 consecutive years",
                "CWIP not increasing for 3 consecutive years.",
            )
        )
    else:
        results.append(
            _make(
                "B2",
                "CWIP Trend",
                "cwip",
                year,
                "NOT_APPLICABLE",
                None,
                "Rise 3 consecutive years",
                "Insufficient data to evaluate CWIP trend.",
            )
        )

    # --------------------------------------
    # B3 – CWIP down + NFA up (rollover)
    # --------------------------------------
    cwip_yoy = metrics.get("cwip_yoy")
    nfa_yoy = metrics.get("nfa_yoy")
    if cwip_yoy is not None and nfa_yoy is not None and cwip_yoy < 0 and nfa_yoy > 0:
        results.append(
            _make(
                "B3",
                "CWIP Rollover",
                "cwip_nfa_rollover",
                year,
                "GREEN",
                None,
                "CWIP↓ & NFA↑",
                "Projects capitalized from CWIP into NFA.",
            )
        )
    elif cwip_yoy is None or nfa_yoy is None:
        results.append(
            _make(
                "B3",
                "CWIP Rollover",
                "cwip_nfa_rollover",
                year,
                "NOT_APPLICABLE",
                None,
                "CWIP↓ & NFA↑",
                "No CWIP rollover pattern detected or insufficient data.",
            )
        )
    else:
        # pattern explicitly *not* present
        results.append(
            _make(
                "B3",
                "CWIP Rollover",
                "cwip_nfa_rollover",
                year,
                "NOT_APPLICABLE",
                None,
                "CWIP↓ & NFA↑",
                "No CWIP rollover pattern detected.",
            )
        )

    # -----------------------
    # C1 – Asset turnover
    # -----------------------
    at = metrics.get("asset_turnover")
    if at is not None:
        if at < R["asset_turnover_critical"]:
            results.append(
                _make(
                    "C1",
                    "Asset Turnover Very Low",
                    "asset_turnover",
                    year,
                    "RED",
                    at,
                    "<0.7",
                    "Fixed asset turnover extremely weak.",
                )
            )
        elif at < R["asset_turnover_low"]:
            results.append(
                _make(
                    "C1",
                    "Asset Turnover Low",
                    "asset_turnover",
                    year,
                    "YELLOW",
                    at,
                    "0.7–1.0",
                    "Fixed asset utilization below optimal.",
                )
            )
        else:
            results.append(
                _make(
                    "C1",
                    "Asset Turnover Healthy",
                    "asset_turnover",
                    year,
                    "GREEN",
                    at,
                    ">1.0",
                    "Good utilization of fixed assets.",
                )
            )
    else:
        results.append(
            _make(
                "C1",
                "Asset Turnover",
                "asset_turnover",
                year,
                "NOT_APPLICABLE",
                None,
                ">1.0",
                "Insufficient data to evaluate.",
            )
        )

    # --------------------------------------------------------
    # C2 – NFA rising while revenue stagnant (CAGR comparison)
    # --------------------------------------------------------
    nfa_cagr = cagr_data.get("nfa_cagr")
    revenue_cagr = cagr_data.get("revenue_cagr")

    if nfa_cagr is not None and revenue_cagr is not None:
        if nfa_cagr > (revenue_cagr + 0.10):
            results.append(
                _make(
                    "C2",
                    "NFA Growing Too Fast",
                    "nfa_cagr",
                    year,
                    "RED",
                    nfa_cagr,
                    "NFA CAGR > Revenue CAGR + 10%",
                    "Underutilized capacity or stranded assets.",
                )
            )
        else:
            results.append(
                _make(
                    "C2",
                    "NFA vs Revenue Growth Normal",
                    "nfa_cagr",
                    year,
                    "GREEN",
                    nfa_cagr,
                    "NFA CAGR ≤ Revenue CAGR + 10%",
                    "NFA growth in line with revenue growth.",
                )
            )
    else:
        results.append(
            _make(
                "C2",
                "NFA vs Revenue Growth",
                "nfa_cagr",
                year,
                "NOT_APPLICABLE",
                None,
                "NFA CAGR > Revenue CAGR + 10%",
                "Insufficient data to evaluate.",
            )
        )

    # -----------------------------
    # D1 – Debt-funded capex
    # -----------------------------
    dfc = metrics.get("debt_funded_capex")
    if dfc is not None:
        if dfc >= 1.0:
            results.append(
                _make(
                    "D1",
                    "Fully Debt Funded Capex",
                    "debt_funded_capex",
                    year,
                    "RED",
                    dfc,
                    ">=1.0",
                    "Capex entirely funded through debt.",
                )
            )
        elif dfc >= R["debt_funded_capex_warning"]:
            results.append(
                _make(
                    "D1",
                    "Debt-Funded Capex High",
                    "debt_funded_capex",
                    year,
                    "YELLOW",
                    dfc,
                    ">=0.5",
                    "Significant dependency on debt for capex.",
                )
            )
        else:
            results.append(
                _make(
                    "D1",
                    "Debt-Funded Capex Low",
                    "debt_funded_capex",
                    year,
                    "GREEN",
                    dfc,
                    "<0.5",
                    "Capex mostly internally funded.",
                )
            )
    else:
        results.append(
            _make(
                "D1",
                "Debt-Funded Capex",
                "debt_funded_capex",
                year,
                "NOT_APPLICABLE",
                None,
                "<0.5",
                "Insufficient data to evaluate.",
            )
        )

    # ------------------------
    # D2 – FCF coverage
    # ------------------------
    fcf_cov = metrics.get("fcf_coverage")
    if fcf_cov is not None:
        if fcf_cov < 0:
            results.append(
                _make(
                    "D2",
                    "Negative FCF Coverage",
                    "fcf_coverage",
                    year,
                    "RED",
                    fcf_cov,
                    "<0",
                    "Capex executed despite negative free cash flow.",
                )
            )
        elif fcf_cov < 0.5:
            results.append(
                _make(
                    "D2",
                    "Weak FCF Coverage",
                    "fcf_coverage",
                    year,
                    "YELLOW",
                    fcf_cov,
                    "0–0.5",
                    "Limited internal reinvestment capacity.",
                )
            )
        else:
            results.append(
                _make(
                    "D2",
                    "Strong FCF Coverage",
                    "fcf_coverage",
                    year,
                    "GREEN",
                    fcf_cov,
                    ">0.5",
                    "Capex well supported by free cash flow.",
                )
            )
    else:
        results.append(
            _make(
                "D2",
                "FCF Coverage",
                "fcf_coverage",
                year,
                "NOT_APPLICABLE",
                None,
                ">0.5",
                "Insufficient data to evaluate.",
            )
        )

    return results


# Backward-compatible wrapper if other parts of the code still call `evaluate_rules`
def evaluate_rules(metrics: Dict[str, Any], cagr_data: Dict[str, Any]) -> List[RuleResult]:
    """
    Backward-compatible alias to apply_rules. Prefer calling apply_rules going forward.
    """
    return apply_rules(metrics, cagr_data)
