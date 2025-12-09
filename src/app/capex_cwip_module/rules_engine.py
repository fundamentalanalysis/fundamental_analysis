from typing import List, Dict, Any
from .models import RuleResult


def apply_rules(
    metrics_by_year: Dict[int, Dict[str, Any]],
    trends: Dict[str, Any]
) -> List[RuleResult]:
    """
    Apply ALL Capex–CWIP rules A1–D2.
    Evaluates rules ONLY for the latest year.
    """

    results: List[RuleResult] = []

    # -------------------------------
    # Identify latest year
    # -------------------------------
    latest_year = max(metrics_by_year.keys())
    latest = metrics_by_year[latest_year]

    # Extract key metrics
    capex_intensity = latest.get("capex_intensity")
    cwip_pct = latest.get("cwip_pct")
    asset_turnover = latest.get("asset_turnover")
    debt_funded_capex = latest.get("debt_funded_capex")
    fcf_coverage = latest.get("fcf_coverage")

    # Trend data (CAGR + YoY)
    capex_cagr = trends.get("capex_cagr")
    cwip_cagr = trends.get("cwip_cagr")
    nfa_cagr = trends.get("nfa_cagr")
    revenue_cagr = trends.get("revenue_cagr")

    cwip_yoy_list = trends.get("cwip_yoy", [])
    nfa_yoy_list = trends.get("nfa_yoy", [])

    # 3-year increasing CWIP flag
    cwip_increasing_3y = trends.get("cwip_increasing_3y")

    # -------------------------------
    #  A. CAPEX INTENSITY RULES
    # -------------------------------

    # A1 — Capex Intensity
    # if capex_intensity is not None:
    #     if capex_intensity > 0.15:
    #         results.append(RuleResult(
    #             rule_id="A1",
    #             rule_name="High Capex Intensity Warning",
    #             metric="capex_intensity",
    #             year=latest_year,
    #             flag="RED",
    #             value=capex_intensity,
    #             threshold=">15%",
    #             reason=f"Capex intensity {capex_intensity:.2f} is very high."
    #         ))
    #     elif capex_intensity > 0.10:
    #         results.append(RuleResult(
    #             rule_id="A1",
    #             rule_name="Moderate Capex Intensity",
    #             metric="capex_intensity",
    #             year=latest_year,
    #             flag="YELLOW",
    #             value=capex_intensity,
    #             threshold="10–15%",
    #             reason="Capex intensity is elevated."
    #         ))
    #     else:
    #         results.append(RuleResult(
    #             rule_id="A1",
    #             rule_name="Normal Capex Intensity",
    #             metric="capex_intensity",
    #             year=latest_year,
    #             flag="GREEN",
    #             value=capex_intensity,
    #             threshold="<10%",
    #             reason="Capex intensity is normal."
    #         ))

    # A1 — Capex Intensity (Investment vs Disinvestment)
    if capex_intensity is not None:

        # ----------------------------
        # POSITIVE CAPEX → Investment
        # ----------------------------
        if capex_intensity >= 0:
            if capex_intensity > 0.15:
                results.append(RuleResult(
                    rule_id="A1",
                    rule_name="High Capex Intensity Warning",
                    metric="capex_intensity",
                    year=latest_year,
                    flag="RED",
                    value=capex_intensity,
                    threshold=">15%",
                    reason=f"Capex intensity {capex_intensity:.2f} indicates aggressive capital investment."
                ))
            elif capex_intensity > 0.10:
                results.append(RuleResult(
                    rule_id="A1",
                    rule_name="Moderate Capex Intensity",
                    metric="capex_intensity",
                    year=latest_year,
                    flag="YELLOW",
                    value=capex_intensity,
                    threshold="10–15%",
                    reason="Capex intensity is elevated, showing increased investment."
                ))
            else:
                results.append(RuleResult(
                    rule_id="A1",
                    rule_name="Normal Capex Intensity",
                    metric="capex_intensity",
                    year=latest_year,
                    flag="GREEN",
                    value=capex_intensity,
                    threshold="<10%",
                    reason="Capex intensity is within normal operating levels."
                ))

        # --------------------------------
        # NEGATIVE CAPEX → Disinvestment
        # --------------------------------
        else:
            disinvestment_ratio = abs(capex_intensity)

            if disinvestment_ratio > 0.10:
                results.append(RuleResult(
                    rule_id="A1",
                    rule_name="Aggressive Asset Sell-Off Warning",
                    metric="capex_intensity",
                    year=latest_year,
                    flag="RED",
                    value=capex_intensity,
                    threshold="< -10%",
                    reason=f"Negative capex intensity {capex_intensity:.2f} indicates aggressive asset liquidation."
                ))
            elif disinvestment_ratio > 0.05:
                results.append(RuleResult(
                    rule_id="A1",
                    rule_name="Moderate Disinvestment Warning",
                    metric="capex_intensity",
                    year=latest_year,
                    flag="YELLOW",
                    value=capex_intensity,
                    threshold="-5% to -10%",
                    reason="Negative capex intensity suggests asset sales for cash recovery or restructuring."
                ))
            else:
                results.append(RuleResult(
                    rule_id="A1",
                    rule_name="Minor Asset Recycling",
                    metric="capex_intensity",
                    year=latest_year,
                    flag="GREEN",
                    value=capex_intensity,
                    threshold=">-5%",
                    reason="Negative capex intensity reflects minor asset optimization."
                ))


    # A2 — Capex Growing Faster Than Revenue
    if capex_cagr is not None and revenue_cagr is not None:
        # print("CAPEX CAGR in RULES ENGINE:", capex_cagr)
        # print("REVENUE CAGR in RULES ENGINE:", revenue_cagr)
        if capex_cagr > revenue_cagr + 10:
            results.append(RuleResult(
                rule_id="A2",
                rule_name="Capex Growing Faster Than Revenue",
                metric="capex_cagr",
                year=latest_year,
                flag="YELLOW",
                value=capex_cagr,
                threshold=f"> revenue CAGR + 10% ({revenue_cagr + 10:.2f})",
                reason=f"Capex CAGR {capex_cagr:.2f}% exceeds revenue CAGR {revenue_cagr:.2f}% by more than 10%."
            ))

    # -------------------------------
    #  B. CWIP RULES
    # -------------------------------

    # B1 — CWIP % of Total Fixed Assets
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

    # B2 — CWIP Rising for 3 Consecutive Years
    if cwip_increasing_3y:
        results.append(RuleResult(
            rule_id="B2",
            rule_name="CWIP Rising Continuously",
            metric="cwip",
            year=latest_year,
            flag="YELLOW",
            value=None,
            threshold="Increasing 3 consecutive years",
            reason="CWIP has increased for 3 consecutive years."
        ))

    # B3 — CWIP ↓ AND NFA ↑ → Projects capitalized
    if len(cwip_yoy_list) > 0 and len(nfa_yoy_list) > 0:
        # Last YoY changes
        cwip_yoy_latest = cwip_yoy_list[-1]
        nfa_yoy_latest = nfa_yoy_list[-1]

        if cwip_yoy_latest is not None and nfa_yoy_latest is not None:
            if cwip_yoy_latest < 0 and nfa_yoy_latest > 0:
                results.append(RuleResult(
                    rule_id="B3",
                    rule_name="CWIP Falling & NFA Rising",
                    metric="cwip_nfa",
                    year=latest_year,
                    flag="GREEN",
                    value=None,
                    threshold="CWIP YoY < 0 AND NFA YoY > 0",
                    reason="CWIP falling while NFA rising indicates successful project capitalization."
                ))

    # -------------------------------
    #  C. ASSET PRODUCTIVITY RULES
    # -------------------------------

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

    # C2 — NFA Rising Faster Than Revenue Growth → Red Flag
    if nfa_cagr is not None and revenue_cagr is not None:
        # print("NFA CAGR in RULES ENGINE:", nfa_cagr)
        # print("REVENUE CAGR in RULES ENGINE:", revenue_cagr)

        # print("Per year metrics:", metrics_by_year)
        # print("Trend metrics:", trends)

        if nfa_cagr > revenue_cagr + 10:
            results.append(RuleResult(
                rule_id="C2",
                rule_name="NFA Rising Without Revenue Growth",
                metric="nfa_cagr",
                year=latest_year,
                flag="RED",
                value=nfa_cagr,
                threshold=f"> revenue CAGR + 10% ({revenue_cagr + 10:.2f})",
                reason=f"NFA CAGR {nfa_cagr:.2f}% significantly exceeds revenue CAGR {revenue_cagr:.2f}%, indicating underutilized capacity."
            ))

    # -------------------------------
    #  D. CAPEX FUNDING RULES
    # -------------------------------

    # D1 — Debt-funded Capex
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
                reason=f"Capex executed despite negative FCF ({fcf_coverage:.2f})."
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
