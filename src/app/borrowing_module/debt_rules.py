
# ==============================================================
# debt_rules.py
# Deterministic rule engine for Borrowings Module
# ==============================================================


# src/app/borrowing_module/debt_rules.py

from src.app.borrowing_module.debt_models import RuleResult


def make(flag, rule_id, name, value, threshold, reason):
    return RuleResult(
        rule_id=rule_id,
        rule_name=name,
        flag=flag,
        value=value,
        threshold=threshold,
        reason=reason,
    )


def apply_rules(financials, metrics, trends):
    results = []

    # Work with latest year snapshot
    last_year = max(metrics.keys())
    m = metrics[last_year]

    # ------------------------------------------------------------
    # A. DEBT GROWTH & TREND RULES
    # ------------------------------------------------------------

    # A1 – Rising Debt Faster Than EBITDA
    debt_cagr = trends.get("debt_cagr")
    ebitda_cagr = trends.get("ebitda_cagr")
    if debt_cagr is not None and ebitda_cagr is not None:
        if debt_cagr > ebitda_cagr:
            results.append(
                make(
                    "RED",
                    "A1",
                    "Debt CAGR > EBITDA CAGR",
                    debt_cagr,
                    f">{ebitda_cagr:.2f}",
                    (
                        "Leverage increasing faster than earnings "
                        f"(Debt CAGR: {debt_cagr:.2f}%, EBITDA CAGR: {ebitda_cagr:.2f}%)"
                    ),
                )
            )

    # A2 – ST Debt Surge Signal
    st_debt_growth = trends.get("st_debt_yoy_growth", [])
    if len(st_debt_growth) >= 2:
        last_two = st_debt_growth[-2:]
        if all(g > 30 for g in last_two):
            results.append(
                make(
                    "RED",
                    "A2",
                    "ST Debt Surge",
                    last_two[-1],
                    ">30% YoY for 2y",
                    (
                        "Short-term rollover risk "
                        f"(Last 2 years ST debt YoY: {last_two[0]:.1f}%, {last_two[1]:.1f}%)"
                    ),
                )
            )

    # A3 – LT Debt Increasing but Revenue Flat
    lt_debt_cagr = trends.get("lt_debt_cagr")
    revenue_cagr = trends.get("revenue_cagr")
    if lt_debt_cagr is not None and revenue_cagr is not None:
        if lt_debt_cagr > 10 and revenue_cagr < 5:
            results.append(
                make(
                    "YELLOW",
                    "A3",
                    "LT Debt Up, Revenue Flat",
                    lt_debt_cagr,
                    ">10% LT Debt CAGR & <5% Revenue CAGR",
                    (
                        "Possible distress borrowing "
                        f"(LT Debt CAGR: {lt_debt_cagr:.2f}%, Revenue CAGR: {revenue_cagr:.2f}%)"
                    ),
                )
            )

    # A3b – LT Debt grows & CWIP/Total_Assets > 10% (Green capex story)
    cwip = m.get("cwip", 0) or 0
    print(f'lt_debt_cagr: {lt_debt_cagr}, cwip: {cwip}')
    total_assets = m.get("total_assets", 0) or 0
    if lt_debt_cagr is not None and lt_debt_cagr > 0 and total_assets > 0:
        cwip_ratio = cwip / total_assets
        if cwip_ratio > 0.10:
            results.append(
                make(
                    "GREEN",
                    "A3b",
                    "LT Debt + Capex",
                    cwip_ratio,
                    ">10%",
                    f"Debt funding growth capex (CWIP/Total Assets: {cwip_ratio:.2%})",
                )
            )

    # ------------------------------------------------------------
    # B. LEVERAGE RATIOS
    # ------------------------------------------------------------

    # B1 – Debt-to-Equity Threshold
    de = m.get("de_ratio")
    if de is not None:
        if de > 1:
            results.append(
                make(
                    "RED",
                    "B1",
                    "Debt-to-Equity",
                    de,
                    ">1",
                    "Highly leveraged",
                )
            )
        elif de > 0.5:
            results.append(
                make(
                    "YELLOW",
                    "B1",
                    "Debt-to-Equity",
                    de,
                    "0.5–1",
                    "Moderately leveraged",
                )
            )
        else:
            results.append(
                make(
                    "GREEN",
                    "B1",
                    "Debt-to-Equity",
                    de,
                    "<=0.5",
                    "Healthy leverage",
                )
            )

    # B2 – Debt-to-EBITDA Threshold
    debt_ebitda = m.get("debt_ebitda")
    if debt_ebitda is not None:
        if debt_ebitda > 4:
            results.append(
                make(
                    "RED",
                    "B2",
                    "Debt-to-EBITDA",
                    debt_ebitda,
                    ">4",
                    "Very high leverage",
                )
            )
        elif debt_ebitda > 2:
            results.append(
                make(
                    "YELLOW",
                    "B2",
                    "Debt-to-EBITDA",
                    debt_ebitda,
                    "2–4",
                    "Slightly stressed",
                )
            )
        else:
            results.append(
                make(
                    "GREEN",
                    "B2",
                    "Debt-to-EBITDA",
                    debt_ebitda,
                    "<=2",
                    "Healthy",
                )
            )

    # ------------------------------------------------------------
    # C. INTEREST COVERAGE RULES
    # ------------------------------------------------------------

    # C1 – ICR Threshold
    icr = m.get("interest_coverage")
    if icr is not None:
        if icr < 1.5:
            results.append(
                make(
                    "RED",
                    "C1",
                    "Interest Coverage",
                    icr,
                    "<1.5",
                    "Unable to service interest",
                )
            )
        elif icr < 3:
            results.append(
                make(
                    "YELLOW",
                    "C1",
                    "Interest Coverage",
                    icr,
                    "1.5–3",
                    "Tight servicing ability",
                )
            )
        else:
            results.append(
                make(
                    "GREEN",
                    "C1",
                    "Interest Coverage",
                    icr,
                    ">=3",
                    "Comfortable",
                )
            )

    # C2 – Finance Cost Rising Faster Than Debt
    finance_cost_cagr = trends.get("finance_cost_cagr")
    print(f'finance_cost_cagr: {finance_cost_cagr}, debt_cagr: {debt_cagr}')
    if finance_cost_cagr is not None and debt_cagr is not None:
        if (finance_cost_cagr - debt_cagr) > 5:
            results.append(
                make(
                    "YELLOW",
                    "C2",
                    "Finance Cost > Debt Growth",
                    finance_cost_cagr,
                    f">{debt_cagr + 5:.2f}",
                    (
                        "Interest rate increase pressure "
                        f"(Finance Cost CAGR: {finance_cost_cagr:.2f}%, Debt CAGR: {debt_cagr:.2f}%)"
                    ),
                )
            )

    # ------------------------------------------------------------
    # D. MATURITY PROFILE RULES
    # ------------------------------------------------------------

    # D1 – Refinancing Risk
    refinancing_ratio = m.get("maturity_lt_1y_pct")
    print('refinancing_ratio', refinancing_ratio)
    if refinancing_ratio is not None:
        if refinancing_ratio > 0.5:
            results.append(
                make(
                    "RED",
                    "D1",
                    "Refinancing Risk",
                    refinancing_ratio,
                    ">50% due <1yr",
                    f"High refinancing risk ({refinancing_ratio:.2%} of debt matures <1yr)",
                )
            )

    # D2 – Balanced Maturity
    ratio_1_3y = m.get("maturity_1_3y_pct")
    ratio_gt_3y = m.get("maturity_gt_3y_pct")
    print('ratio_1_3y', ratio_1_3y)
    print('ratio_gt_3y', ratio_gt_3y)
    if ratio_1_3y is not None and ratio_gt_3y is not None:
        if ratio_1_3y >= 0.3 and ratio_gt_3y >= 0.2:
            results.append(
                make(
                    "GREEN",
                    "D2",
                    "Balanced Maturity",
                    ratio_1_3y,
                    ">=30% 1-3y & >=20% >3y",
                    (
                        "Good maturity spread "
                        f"(1-3y: {ratio_1_3y:.2%}, >3y: {ratio_gt_3y:.2%})"
                    ),
                )
            )

    # ------------------------------------------------------------
    # E. INTEREST COST RISK (FLOATING VS FIXED)
    # ------------------------------------------------------------

    floating_pct = m.get("floating_share")
    print('floating_pct', floating_pct)
    if floating_pct is not None:
        if floating_pct > 0.6:
            results.append(
                make(
                    "RED",
                    "E1",
                    "Floating-Rate Exposure",
                    floating_pct,
                    ">60%",
                    f"High rate sensitivity ({floating_pct:.2%} floating rate debt)",
                )
            )
        elif floating_pct > 0.4:
            results.append(
                make(
                    "YELLOW",
                    "E1",
                    "Floating-Rate Exposure",
                    floating_pct,
                    "40–60%",
                    f"Moderate risk ({floating_pct:.2%} floating rate debt)",
                )
            )
        else:
            results.append(
                make(
                    "GREEN",
                    "E1",
                    "Floating-Rate Exposure",
                    floating_pct,
                    "<=40%",
                    f"Stable interest profile ({floating_pct:.2%} floating rate debt)",
                )
            )

    # ------------------------------------------------------------
    # F. WEIGHTED AVERAGE COST OF DEBT (WACD)
    # ------------------------------------------------------------

    wacd = m.get("wacd")
    print('wacd', wacd)
    if wacd is not None:
        if wacd > 0.10:
            results.append(
                make(
                    "RED",
                    "F1",
                    "WACD",
                    wacd,
                    ">10%",
                    "Very high cost of borrowing",
                )
            )
        elif wacd > 0.07:
            results.append(
                make(
                    "YELLOW",
                    "F1",
                    "WACD",
                    wacd,
                    "7–10%",
                    "Somewhat expensive",
                )
            )
        else:
            results.append(
                make(
                    "GREEN",
                    "F1",
                    "WACD",
                    wacd,
                    "<=7%",
                    "Good borrowing rate",
                )
            )

    return results
