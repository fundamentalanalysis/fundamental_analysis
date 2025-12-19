# from typing import List, Dict

# try:
#     from .lfr_models import RuleResult
# except ImportError:
#     from lfr_models import RuleResult


# def _make(rule_id, rule_name, metric, value, threshold, flag, reason):
#     return RuleResult(
#         rule_id=rule_id,
#         rule_name=rule_name,
#         metric=metric,
#         year="Latest",
#         flag=flag,
#         value=value,
#         threshold=threshold,
#         reason=reason,
#     )


# def lfr_rule_engine(metrics: Dict, trends: Dict, rules=None, module_red_flags=None) -> List[RuleResult]:
#     results: List[RuleResult] = []
#     latest = metrics["latest"]

#     # =====================================================
#     # A1 — Debt to Equity
#     # =====================================================
#     de = latest.get("de_ratio")
#     if de is not None:
#         if de >= 3.0:
#             flag, reason = "RED", "Critical leverage with excessive debt."
#         elif de >= 2.0:
#             flag, reason = "YELLOW", "High leverage relative to equity."
#         else:
#             flag, reason = "GREEN", "Healthy capital structure."

#         results.append(_make(
#             "A1", "Debt-to-Equity Threshold",
#             "de_ratio", de, "<2 / 2–3 / >3", flag, reason
#         ))

#     # =====================================================
#     # A2 — Debt / EBITDA
#     # =====================================================
#     d_e = latest.get("debt_ebitda")
#     if d_e is not None:
#         if d_e >= 5:
#             flag, reason = "RED", "Severe leverage relative to EBITDA."
#         elif d_e >= 4:
#             flag, reason = "YELLOW", "Elevated leverage pressure."
#         else:
#             flag, reason = "GREEN", "Debt well supported by EBITDA."

#         results.append(_make(
#             "A2", "Debt / EBITDA",
#             "debt_ebitda", d_e, "<4 / 4–5 / >5", flag, reason
#         ))

#     # =====================================================
#     # A3 — Net Debt / EBITDA
#     # =====================================================
#     nde = latest.get("net_debt_ebitda")
#     if nde is not None:
#         if nde >= 5.5:
#             flag, reason = "RED", "Dangerously high net leverage."
#         elif nde >= 4:
#             flag, reason = "YELLOW", "Elevated net leverage."
#         else:
#             flag, reason = "GREEN", "Net leverage within comfort."

#         results.append(_make(
#             "A3", "Net Debt / EBITDA",
#             "net_debt_ebitda", nde, "<4 / 4–5.5 / >5.5", flag, reason
#         ))

#     # =====================================================
#     # B1 — Interest Coverage Ratio
#     # =====================================================
#     icr = latest.get("interest_coverage")
#     if icr is not None:
#         if icr < 1:
#             flag, reason = "RED", "Unsustainable interest burden."
#         elif icr < 2:
#             flag, reason = "YELLOW", "Tight interest servicing."
#         else:
#             flag, reason = "GREEN", "Comfortable interest coverage."

#         results.append(_make(
#             "B1", "Interest Coverage Ratio",
#             "interest_coverage", icr, "<1 / 1–2 / >2", flag, reason
#         ))

#     # =====================================================
#     # C1 — Short-Term Debt Dependence
#     # =====================================================
#     st = latest.get("st_debt_ratio")
#     if st is not None:
#         if st >= 0.50:
#             flag, reason = "RED", "Severe refinancing risk."
#         elif st >= 0.40:
#             flag, reason = "YELLOW", "Elevated rollover exposure."
#         else:
#             flag, reason = "GREEN", "Well balanced debt maturity."

#         results.append(_make(
#             "C1", "Short-Term Debt Ratio",
#             "st_debt_ratio", st, "<40% / 40–50% / >50%", flag, reason
#         ))

#     # =====================================================
#     # E1 — Cross Module Aggregator (OPTIONAL)
#     # =====================================================
#     if module_red_flags:
#         critical = sum(
#             1 for v in module_red_flags.values()
#             for r in v if r.get("severity") == "CRITICAL"
#         )

#         if critical >= 3:
#             flag, reason = "RED", "Systemic financial stress."
#         elif critical >= 1:
#             flag, reason = "YELLOW", "Multi-area financial stress."
#         else:
#             flag, reason = "GREEN", "No systemic stress detected."

#         results.append(_make(
#             "E1", "Cross-Module Stress Aggregation",
#             None, critical, ">=3 critical", flag, reason
#         ))

#     return results

from typing import List, Dict
from .lfr_models import RuleResult


# =========================================================
# Helper
# =========================================================
def _make(rule_id, rule_name, metric, value, threshold, flag, reason):
    return RuleResult(
        rule_id=rule_id,
        rule_name=rule_name,
        metric=metric,
        year="Latest",
        flag=flag,
        value=round(value, 4) if isinstance(value, float) else value,
        threshold=threshold,
        reason=reason,
    )


# =========================================================
# LFR RULES (FINAL, STRICT, AUDITABLE)
# =========================================================
def lfr_rules(
    key_metrics: Dict,
    trends: Dict = None,
    module_red_flags: Dict[str, List[Dict]] = None,
) -> List[RuleResult]:

    rules: List[RuleResult] = []

    # -------------------------
    # Extract metrics safely
    # -------------------------
    de = key_metrics.get("de_ratio")
    debt_ebitda = key_metrics.get("debt_ebitda")
    net_debt_ebitda = key_metrics.get("net_debt_ebitda")
    st_ratio = key_metrics.get("st_debt_ratio")

    ebit = key_metrics.get("ebit")
    interest = key_metrics.get("interest_cost")
    icr = (ebit / interest) if ebit and interest else None

    # =====================================================
    # A. LEVERAGE RATIOS
    # =====================================================

    # A1 — Debt-to-Equity
    if de is not None:
        if de >= 3.0:
            rules.append(_make(
                "A1", "Debt-to-Equity Threshold", "de_ratio",
                de, ">=3.0", "RED",
                "Critical leverage with excessive reliance on debt."
            ))
        elif de >= 2.0:
            rules.append(_make(
                "A1", "Debt-to-Equity Threshold", "de_ratio",
                de, "2.0–3.0", "YELLOW",
                "High leverage indicating stressed capital structure."
            ))
        else:
            rules.append(_make(
                "A1", "Debt-to-Equity Threshold", "de_ratio",
                de, "<2.0", "GREEN",
                "Leverage within acceptable capital structure limits."
            ))

    # A2 — Debt / EBITDA
    if debt_ebitda is not None:
        if debt_ebitda >= 5.0:
            rules.append(_make(
                "A2", "Debt/EBITDA Threshold", "debt_ebitda",
                debt_ebitda, ">=5.0", "RED",
                "Severe leverage with weak earnings support."
            ))
        elif debt_ebitda >= 4.0:
            rules.append(_make(
                "A2", "Debt/EBITDA Threshold", "debt_ebitda",
                debt_ebitda, "4.0–5.0", "YELLOW",
                "Elevated leverage putting pressure on earnings."
            ))
        else:
            rules.append(_make(
                "A2", "Debt/EBITDA Threshold", "debt_ebitda",
                debt_ebitda, "<4.0", "GREEN",
                "Debt levels well supported by EBITDA."
            ))

    # A3 — Net Debt / EBITDA (Fitch / S&P)
    if net_debt_ebitda is not None:
        if net_debt_ebitda >= 5.5:
            rules.append(_make(
                "A3", "Net Debt/EBITDA (Fitch/S&P)", "net_debt_ebitda",
                net_debt_ebitda, ">=5.5", "RED",
                "Dangerously high net leverage, near sub-investment grade."
            ))
        elif net_debt_ebitda >= 4.0:
            rules.append(_make(
                "A3", "Net Debt/EBITDA (Fitch/S&P)", "net_debt_ebitda",
                net_debt_ebitda, "4.0–5.5", "YELLOW",
                "Elevated net leverage with refinancing sensitivity."
            ))
        else:
            rules.append(_make(
                "A3", "Net Debt/EBITDA (Fitch/S&P)", "net_debt_ebitda",
                net_debt_ebitda, "<4.0", "GREEN",
                "Net leverage within comfortable rating thresholds."
            ))

    # =====================================================
    # B. DEBT SERVICING RISK
    # =====================================================

    # B1 — Interest Coverage Ratio
    if icr is not None:
        if icr < 1.0:
            rules.append(_make(
                "B1", "Interest Coverage Ratio", "icr",
                icr, "<1.0", "RED",
                "Unsustainable interest burden with high default risk."
            ))
        elif icr < 2.0:
            rules.append(_make(
                "B1", "Interest Coverage Ratio", "icr",
                icr, "1.0–2.0", "YELLOW",
                "Tight interest servicing capacity."
            ))
        else:
            rules.append(_make(
                "B1", "Interest Coverage Ratio", "icr",
                icr, ">=2.0", "GREEN",
                "Comfortable ability to service interest obligations."
            ))

    # =====================================================
    # C. SHORT-TERM DEBT DEPENDENCE
    # =====================================================

    if st_ratio is not None:
        if st_ratio >= 0.50:
            rules.append(_make(
                "C1", "Short-Term Debt Dependence", "st_debt_ratio",
                st_ratio, ">=50%", "RED",
                "Severe refinancing risk due to high short-term debt."
            ))
        elif st_ratio >= 0.40:
            rules.append(_make(
                "C1", "Short-Term Debt Dependence", "st_debt_ratio",
                st_ratio, "40–50%", "YELLOW",
                "Elevated rollover risk from short-term borrowings."
            ))
        else:
            rules.append(_make(
                "C1", "Short-Term Debt Dependence", "st_debt_ratio",
                st_ratio, "<40%", "GREEN",
                "Well-balanced debt maturity profile."
            ))

    # =====================================================
    # E. CROSS-MODULE AGGREGATION (OPTIONAL)
    # =====================================================

    if module_red_flags:
        critical = sum(
            1 for flags in module_red_flags.values()
            for f in flags if f.get("severity") == "CRITICAL"
        )
        high = sum(
            1 for flags in module_red_flags.values()
            for f in flags if f.get("severity") == "HIGH"
        )

        if critical >= 3:
            rules.append(_make(
                "E1", "Cross-Module Stress", "aggregate",
                critical, ">=3 Critical", "RED",
                "Systemic financial risk across multiple modules."
            ))
        elif critical >= 1 or high >= 3:
            rules.append(_make(
                "E1", "Cross-Module Stress", "aggregate",
                critical, "Multi-area stress", "YELLOW",
                "Multiple modules indicate elevated financial stress."
            ))
        else:
            rules.append(_make(
                "E1", "Cross-Module Stress", "aggregate",
                critical, "Low", "GREEN",
                "No material stress signals from other modules."
            ))

    return rules
