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
from .models import RuleResult

def apply_rules(
    metrics_by_year: Dict[int, Dict[str, Any]],
    trends: Dict[str, Any]
) -> List[RuleResult]:
    """
    metrics_by_year: {year → metrics dict}
    trends: full output from compute_trends()
    Evaluates rules ONLY for latest year.
    """
    results: List[RuleResult] = []

    # -------------------------------
    # 1️⃣ Identify latest year
    # -------------------------------
    latest_year = max(metrics_by_year.keys())
    latest = metrics_by_year[latest_year]

    capex_intensity = latest.get("capex_intensity")
    cwip_pct = latest.get("cwip_pct")
    asset_turnover = latest.get("asset_turnover")
    debt_funded_capex = latest.get("debt_funded_capex")
    fcf_coverage = latest.get("fcf_coverage")

    capex_cagr = trends.get("capex_cagr")
    cwip_cagr = trends.get("cwip_cagr")
    nfa_cagr = trends.get("nfa_cagr")
    revenue_cagr = trends.get("revenue_cagr")

    # -------------------------------
    # 2️⃣ RULES
    # -------------------------------

    # A1 — Capex Intensity
    if capex_intensity is not None:
        if capex_intensity > 0.15:
            results.append(RuleResult(
                rule_id="A1",
                rule_name="High Capex Intensity",
                metric="capex_intensity",
                year=latest_year,
                flag="RED",
                value=capex_intensity,
                threshold=">0.15",
                reason=f"Capex intensity {capex_intensity:.2f} is very high."
            ))
        elif capex_intensity > 0.10:
            results.append(RuleResult(
                rule_id="A1",
                rule_name="Moderate Capex Intensity",
                metric="capex_intensity",
                year=latest_year,
                flag="YELLOW",
                value=capex_intensity,
                threshold="0.10–0.15",
                reason="Capex intensity is elevated."
            ))
        else:
            results.append(RuleResult(
                rule_id="A1",
                rule_name="Normal Capex",
                metric="capex_intensity",
                year=latest_year,
                flag="GREEN",
                value=capex_intensity,
                threshold="<0.10",
                reason="Capex intensity is normal."
            ))

    # B1 — CWIP %
    if cwip_pct is not None:
        if cwip_pct > 0.40:
            results.append(RuleResult(
                rule_id="B1",
                rule_name="CWIP % Critical",
                metric="cwip_pct",
                year=latest_year,
                flag="RED",
                value=cwip_pct,
                threshold=">40%",
                reason="CWIP extremely high."
            ))
        elif cwip_pct > 0.30:
            results.append(RuleResult(
                rule_id="B1",
                rule_name="CWIP % High",
                metric="cwip_pct",
                year=latest_year,
                flag="YELLOW",
                value=cwip_pct,
                threshold="30–40%",
                reason="CWIP level is elevated."
            ))
        else:
            results.append(RuleResult(
                rule_id="B1",
                rule_name="CWIP % Normal",
                metric="cwip_pct",
                year=latest_year,
                flag="GREEN",
                value=cwip_pct,
                threshold="<30%",
                reason="CWIP level normal."
            ))

    # C1 — Asset Turnover
    if asset_turnover is not None:
        if asset_turnover < 0.7:
            results.append(RuleResult(
                rule_id="C1",
                rule_name="Asset Turnover Very Low",
                metric="asset_turnover",
                year=latest_year,
                flag="RED",
                value=asset_turnover,
                threshold="<0.7",
                reason="Very poor utilization of fixed assets."
            ))
        elif asset_turnover < 1.0:
            results.append(RuleResult(
                rule_id="C1",
                rule_name="Asset Turnover Low",
                metric="asset_turnover",
                year=latest_year,
                flag="YELLOW",
                value=asset_turnover,
                threshold="0.7–1.0",
                reason="Asset turnover slightly weak."
            ))
        else:
            results.append(RuleResult(
                rule_id="C1",
                rule_name="Asset Turnover Healthy",
                metric="asset_turnover",
                year=latest_year,
                flag="GREEN",
                value=asset_turnover,
                threshold=">1.0",
                reason="Good asset utilization."
            ))

    # D1 — Debt-funded capex
    if debt_funded_capex is not None:
        if debt_funded_capex >= 1.0:
            results.append(RuleResult(
                rule_id="D1",
                rule_name="Fully Debt Funded Capex",
                metric="debt_funded_capex",
                year=latest_year,
                flag="RED",
                value=debt_funded_capex,
                threshold=">=1.0",
                reason="Capex entirely funded by debt."
            ))
        elif debt_funded_capex >= 0.5:
            results.append(RuleResult(
                rule_id="D1",
                rule_name="High Debt-Funded Capex",
                metric="debt_funded_capex",
                year=latest_year,
                flag="YELLOW",
                value=debt_funded_capex,
                threshold=">=0.5",
                reason="Significant dependency on debt for capex."
            ))
        else:
            results.append(RuleResult(
                rule_id="D1",
                rule_name="Low Debt-Funded Capex",
                metric="debt_funded_capex",
                year=latest_year,
                flag="GREEN",
                value=debt_funded_capex,
                threshold="<0.5",
                reason="Capex mostly internally funded."
            ))

    # D2 — FCF Coverage
    if fcf_coverage is not None:
        if fcf_coverage < 0:
            results.append(RuleResult(
                rule_id="D2",
                rule_name="Negative FCF Coverage",
                metric="fcf_coverage",
                year=latest_year,
                flag="RED",
                value=fcf_coverage,
                threshold="<0",
                reason="Capex executed despite negative FCF."
            ))
        elif fcf_coverage < 0.5:
            results.append(RuleResult(
                rule_id="D2",
                rule_name="Weak FCF Coverage",
                metric="fcf_coverage",
                year=latest_year,
                flag="YELLOW",
                value=fcf_coverage,
                threshold="0–0.5",
                reason="Limited internal reinvestment capacity."
            ))
        else:
            results.append(RuleResult(
                rule_id="D2",
                rule_name="Strong FCF Coverage",
                metric="fcf_coverage",
                year=latest_year,
                flag="GREEN",
                value=fcf_coverage,
                threshold=">0.5",
                reason="Capex well funded by FCF."
            ))

    return results
