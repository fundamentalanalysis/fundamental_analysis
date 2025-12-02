from typing import List, Dict

from .borrowings_config import BorrowingsRuleConfig, BorrowingsRuleThresholds
from .debt_models import RuleResult, IndustryBenchmarks, CovenantLimits


def _make(rule_id, name, metric, year, flag, value, threshold, reason):
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


def _latest_year(metrics: Dict[int, dict]) -> int:
    return max(metrics.keys())


def apply_rules(
    metrics: Dict[int, dict],
    trends: Dict[str, any],
    benchmarks: IndustryBenchmarks,
    covenants: CovenantLimits,
    rule_config: BorrowingsRuleConfig,
) -> List[RuleResult]:
    last_year = _latest_year(metrics)
    m = metrics[last_year]
    cfg: BorrowingsRuleThresholds = rule_config.generic
    results: List[RuleResult] = []

    debt_cagr = trends.get("debt_cagr")
    ebitda_cagr = trends.get("ebitda_cagr")

    # A1 – Debt CAGR vs EBITDA CAGR (Quantified Impact)
    if debt_cagr is not None and ebitda_cagr is not None:
        growth_gap = debt_cagr - ebitda_cagr
        
        # CRITICAL - Extreme imbalance
        if growth_gap >= 12 and ebitda_cagr <= 0:
            results.append(
                _make(
                    "A1",
                    "Debt CAGR vs EBITDA",
                    "debt_cagr",
                    last_year,
                    "RED",  # Using RED as CRITICAL severity
                    debt_cagr,
                    f"gap >={growth_gap:.1f}% & EBITDA <=0%",
                    f"CRITICAL: Earnings stagnant/shrinking (EBITDA CAGR {ebitda_cagr:.2f}%) while debt is compounding rapidly (Debt CAGR {debt_cagr:.2f}%). Gap: {growth_gap:.1f}%.",
                )
            )
        # RED - Severe mismatch
        elif growth_gap >= 8 or (debt_cagr >= 12 and ebitda_cagr <= 2):
            results.append(
                _make(
                    "A1",
                    "Debt CAGR vs EBITDA",
                    "debt_cagr",
                    last_year,
                    "RED",
                    debt_cagr,
                    f"gap >={growth_gap:.1f}%",
                    f"Debt growing far faster than earnings; leverage worsening sharply. Debt CAGR {debt_cagr:.2f}% vs EBITDA CAGR {ebitda_cagr:.2f}%. Gap: {growth_gap:.1f}%.",
                )
            )
        # YELLOW - Moderate mismatch
        elif growth_gap >= 3:
            results.append(
                _make(
                    "A1",
                    "Debt CAGR vs EBITDA",
                    "debt_cagr",
                    last_year,
                    "YELLOW",
                    debt_cagr,
                    f"gap {growth_gap:.1f}% (3-8%)",
                    f"Debt growing moderately faster than EBITDA; leverage pressure increasing. Debt CAGR {debt_cagr:.2f}% vs EBITDA CAGR {ebitda_cagr:.2f}%. Gap: {growth_gap:.1f}%.",
                )
            )
        # GREEN - Balanced growth
        else:
            if debt_cagr < ebitda_cagr:
                reason = f"Debt CAGR {debt_cagr:.2f}% is growing slower than EBITDA CAGR {ebitda_cagr:.2f}%, indicating improving leverage. Gap: {growth_gap:.1f}%."
            else:
                reason = f"Debt growth aligned with earnings growth; leverage stable. Debt CAGR {debt_cagr:.2f}% vs EBITDA CAGR {ebitda_cagr:.2f}%. Gap: {growth_gap:.1f}%."
            
            results.append(
                _make(
                    "A1",
                    "Debt CAGR vs EBITDA",
                    "debt_cagr",
                    last_year,
                    "GREEN",
                    debt_cagr,
                    f"gap <3% ({growth_gap:.1f}%)",
                    reason,
                )
            )

    # A2 – ST debt surge with weak OCF
    st_debt_growth = trends.get("st_debt_yoy_growth", [])
    ocf_growth = trends.get("ocf_yoy_growth", [])
    if (
        len(st_debt_growth) >= 2
        and st_debt_growth[-2] is not None
        and st_debt_growth[-1] is not None
        and st_debt_growth[-2] > 30
        and st_debt_growth[-1] > 30
    ):
        ocf_condition = not ocf_growth or (ocf_growth and (ocf_growth[-1] is None or ocf_growth[-1] <= 0))
        if ocf_condition:
            results.append(
                _make(
                    "A2",
                    "ST Debt Surge",
                    "short_term_debt",
                    last_year,
                    "RED",
                    st_debt_growth[-1],
                    ">30% YoY for 2 years",
                    "Short-term borrowings growing >30% YoY for two consecutive years while operating cash flow is flat/declining.",
                )
            )

    # A3 – LT debt growth vs revenue
    lt_debt_cagr = trends.get("lt_debt_cagr")
    revenue_cagr = trends.get("revenue_cagr")
    if lt_debt_cagr is not None and revenue_cagr is not None:
        if lt_debt_cagr > 15 and revenue_cagr < 3:
            results.append(
                _make(
                    "A3",
                    "LT Debt vs Revenue",
                    "long_term_debt",
                    last_year,
                    "RED",
                    lt_debt_cagr,
                    ">15% LT debt CAGR & <3% revenue CAGR",
                    "Severe distress borrowing: Long-term debt growing rapidly while revenue is stagnant.",
                )
            )
        elif lt_debt_cagr > 10 and revenue_cagr < 5:
            results.append(
                _make(
                    "A3",
                    "LT Debt vs Revenue",
                    "long_term_debt",
                    last_year,
                    "YELLOW",
                    lt_debt_cagr,
                    ">10% LT debt CAGR & <5% revenue CAGR",
                    "Long-term debt growing faster than revenue, indicating potential distress borrowing.",
                )
            )
        else:
            # GREEN - Healthy alignment
            if lt_debt_cagr <= revenue_cagr:
                reason = f"LT debt growth ({lt_debt_cagr:.2f}%) is aligned with or slower than revenue growth ({revenue_cagr:.2f}%), indicating healthy borrowing."
            else:
                reason = f"LT debt growth ({lt_debt_cagr:.2f}%) moderately exceeds revenue growth ({revenue_cagr:.2f}%), but within acceptable range."
            
            results.append(
                _make(
                    "A3",
                    "LT Debt vs Revenue",
                    "long_term_debt",
                    last_year,
                    "GREEN",
                    lt_debt_cagr,
                    "LT debt <= revenue or gap < 10%",
                    reason,
                )
            )

    cwip_ratio = (m.get("cwip") or 0) / (m.get("total_assets") or 1)
    if lt_debt_cagr and lt_debt_cagr > 0 and cwip_ratio >= 0.10:
        results.append(
            _make(
                "A3b",
                "LT Debt funding CWIP",
                "cwip",
                last_year,
                "GREEN",
                cwip_ratio,
                ">=10%",
                "Meaningful portion of LT debt appears to fund CWIP / growth capex.",
            )
        )

    # B1 – Debt-to-Equity
    de = m.get("de_ratio")
    yellow_limit = max(benchmarks.target_de_ratio, cfg.high_de_ratio)
    red_limit = max(benchmarks.max_safe_de_ratio, cfg.very_high_de_ratio)
    if de is not None:
        if de > red_limit:
            results.append(
                _make(
                    "B1",
                    "Debt-to-Equity",
                    "de_ratio",
                    last_year,
                    "RED",
                    de,
                    f">{red_limit}",
                    "Very high leverage relative to equity base.",
                )
            )
        elif de > yellow_limit:
            results.append(
                _make(
                    "B1",
                    "Debt-to-Equity",
                    "de_ratio",
                    last_year,
                    "YELLOW",
                    de,
                    f"{yellow_limit}-{red_limit}",
                    "High leverage compared to equity.",
                )
            )
        else:
            results.append(
                _make(
                    "B1",
                    "Debt-to-Equity",
                    "de_ratio",
                    last_year,
                    "GREEN",
                    de,
                    f"<={yellow_limit}",
                    "Acceptable leverage relative to equity.",
                )
            )

    # B2 – Debt-to-EBITDA
    debt_ebitda = m.get("debt_ebitda")
    yellow_debt_ebitda = max(benchmarks.max_safe_debt_ebitda, cfg.high_debt_ebitda)
    red_debt_ebitda = max(cfg.critical_debt_ebitda, yellow_debt_ebitda + 2)
    if debt_ebitda is not None:
        if debt_ebitda > red_debt_ebitda:
            results.append(
                _make(
                    "B2",
                    "Debt-to-EBITDA",
                    "debt_ebitda",
                    last_year,
                    "RED",
                    debt_ebitda,
                    f">{red_debt_ebitda}",
                    "Very high leverage relative to EBITDA.",
                )
            )
        elif debt_ebitda > yellow_debt_ebitda:
            results.append(
                _make(
                    "B2",
                    "Debt-to-EBITDA",
                    "debt_ebitda",
                    last_year,
                    "YELLOW",
                    debt_ebitda,
                    f"{yellow_debt_ebitda}-{red_debt_ebitda}",
                    "Leverage above comfortable levels.",
                )
            )
        else:
            results.append(
                _make(
                    "B2",
                    "Debt-to-EBITDA",
                    "debt_ebitda",
                    last_year,
                    "GREEN",
                    debt_ebitda,
                    f"<={yellow_debt_ebitda}",
                    "Debt-to-EBITDA within safe range.",
                )
            )

    # C1 – ICR thresholds (6-tier system)
    icr = m.get("interest_coverage")
    if icr is not None:
        # RED: < 1.0 - CRITICAL
        if icr < cfg.icr_critical:
            results.append(
                _make(
                    "C1",
                    "Interest Coverage",
                    "interest_coverage",
                    last_year,
                    "RED",
                    icr,
                    f"<{cfg.icr_critical}",
                    "🟥 CRITICAL – interest not covered",
                )
            )
        # RED: 1.0–1.5 - HIGH RISK
        elif icr < cfg.icr_high_risk:
            results.append(
                _make(
                    "C1",
                    "Interest Coverage",
                    "interest_coverage",
                    last_year,
                    "RED",
                    icr,
                    f"{cfg.icr_critical}-{cfg.icr_high_risk}",
                    "🟥 HIGH RISK – very thin buffer",
                )
            )
        # YELLOW: 1.5–2.0 - Weak
        elif icr < cfg.icr_weak:
            results.append(
                _make(
                    "C1",
                    "Interest Coverage",
                    "interest_coverage",
                    last_year,
                    "YELLOW",
                    icr,
                    f"{cfg.icr_high_risk}-{cfg.icr_weak}",
                    "🟨 Weak servicing ability",
                )
            )
        # YELLOW: 2.0–2.5 - Tight but acceptable
        elif icr < cfg.icr_tight:
            results.append(
                _make(
                    "C1",
                    "Interest Coverage",
                    "interest_coverage",
                    last_year,
                    "YELLOW",
                    icr,
                    f"{cfg.icr_weak}-{cfg.icr_tight}",
                    "🟨 Tight but acceptable",
                )
            )
        # GREEN: 2.5–4.0 - Comfortable
        elif icr < cfg.icr_comfortable:
            results.append(
                _make(
                    "C1",
                    "Interest Coverage",
                    "interest_coverage",
                    last_year,
                    "GREEN",
                    icr,
                    f"{cfg.icr_tight}-{cfg.icr_comfortable}",
                    "🟩 Comfortable",
                )
            )
        # GREEN: > 4.0 - Very strong
        else:
            results.append(
                _make(
                    "C1",
                    "Interest Coverage",
                    "interest_coverage",
                    last_year,
                    "GREEN",
                    icr,
                    f">{cfg.icr_comfortable}",
                    "🟩 Very strong (investment grade)",
                )
            )



    # C2 – Finance cost rising faster than debt (3-tier system)
    if debt_cagr is not None:
        finance_cost_cagr = trends.get("finance_cost_cagr")
        if finance_cost_cagr is not None:
            finance_gap = finance_cost_cagr - debt_cagr
            
            # RED: finance_gap > 7% - High interest rate pressure
            if finance_gap > cfg.high_finance_gap:
                results.append(
                    _make(
                        "C2",
                        "Finance Cost Pressure",
                        "finance_cost",
                        last_year,
                        "RED",
                        finance_cost_cagr,
                        f"gap >{cfg.high_finance_gap:.0f}% ({finance_gap:.1f}%)",
                        f"🟥 RED – Borrowing cost rising sharply; high sensitivity to interest rate cycles. Finance cost CAGR {finance_cost_cagr:.2f}% vs Debt CAGR {debt_cagr:.2f}%.",
                    )
                )
            # YELLOW: 2% <= finance_gap <= 7% - Moderate pressure
            elif finance_gap >= cfg.moderate_finance_gap:
                results.append(
                    _make(
                        "C2",
                        "Finance Cost Pressure",
                        "finance_cost",
                        last_year,
                        "YELLOW",
                        finance_cost_cagr,
                        f"gap {cfg.moderate_finance_gap:.0f}-{cfg.high_finance_gap:.0f}% ({finance_gap:.1f}%)",
                        f"🟨 YELLOW – Finance cost rising moderately faster than debt; interest rate pressure emerging. Finance cost CAGR {finance_cost_cagr:.2f}% vs Debt CAGR {debt_cagr:.2f}%.",
                    )
                )
            # GREEN: finance_gap < 2% - Stable cost
            else:
                results.append(
                    _make(
                        "C2",
                        "Finance Cost Pressure",
                        "finance_cost",
                        last_year,
                        "GREEN",
                        finance_cost_cagr,
                        f"gap <{cfg.moderate_finance_gap:.0f}% ({finance_gap:.1f}%)",
                        f"🟩 GREEN – Borrowing cost stable; changes in finance cost match debt movement. Finance cost CAGR {finance_cost_cagr:.2f}% vs Debt CAGR {debt_cagr:.2f}%.",
                    )
                )


    fincost_yoy = trends.get("finance_cost_yoy_growth", [])
    if len(fincost_yoy) >= 2:
        if fincost_yoy[-1] and fincost_yoy[-2]:
            if fincost_yoy[-1] > cfg.high_fin_cost_yoy * 100 and fincost_yoy[-2] > cfg.high_fin_cost_yoy * 100:
                results.append(
                    _make(
                        "C2b",
                        "Finance Cost YoY",
                        "finance_cost",
                        last_year,
                        "YELLOW",
                        fincost_yoy[-1],
                        f"> {cfg.high_fin_cost_yoy*100:.0f}% YoY for 2 years",
                        "Finance cost rising >25% YoY for two years.",
                    )
                )

    # D1 – Refinancing risk (3-tier system with conditional escalation)
    maturity_lt = m.get("maturity_lt_1y_pct")
    if maturity_lt is not None:
        floating_share = m.get("floating_share")
        
        # Initial flag determination based on maturity thresholds
        base_flag = None
        base_threshold = None
        base_reason = None
        
        # CRITICAL: > 0.70 (70%) - Majority of debt due immediately
        if maturity_lt > cfg.critical_st_maturity_pct:
            base_flag = "RED"  # Using RED as CRITICAL severity
            base_threshold = f">{cfg.critical_st_maturity_pct:.0%}"
            base_reason = f"🟥 CRITICAL – Majority of debt ({maturity_lt:.1%}) due immediately; severe refinancing stress."
        
        # RED: > 0.50 (50%) - High refinancing risk
        elif maturity_lt > cfg.moderate_st_maturity_pct:
            base_flag = "RED"
            base_threshold = f">{cfg.moderate_st_maturity_pct:.0%}"
            base_reason = f"🟥 RED – Large portion of debt ({maturity_lt:.1%}) matures within the next 12 months; high rollover risk."
            
            # ESCALATION: If floating rate > 60% AND maturity > 50%
            if floating_share is not None and floating_share > cfg.high_floating_share:
                base_flag = "RED"  # Using RED as CRITICAL
                base_threshold = f">{cfg.moderate_st_maturity_pct:.0%} + floating >{cfg.high_floating_share:.0%}"
                base_reason = f"🟥 CRITICAL – {maturity_lt:.1%} debt maturing soon with {floating_share:.1%} floating rate exposure; extreme refinancing + rate sensitivity."
        
        # YELLOW: 0.30 < maturity <= 0.50 - Moderate refinancing risk
        elif maturity_lt > cfg.low_st_maturity_pct:
            base_flag = "YELLOW"
            base_threshold = f"{cfg.low_st_maturity_pct:.0%}-{cfg.moderate_st_maturity_pct:.0%}"
            base_reason = f"🟨 YELLOW – Meaningful refinancing exposure ({maturity_lt:.1%}); monitor liquidity buffers."
        
        # GREEN: <= 0.30 - Low refinancing risk
        else:
            base_flag = "GREEN"
            base_threshold = f"<={cfg.low_st_maturity_pct:.0%}"
            base_reason = f"🟩 GREEN – Well-spread maturity profile ({maturity_lt:.1%}); low short-term pressure."
        
        results.append(
            _make(
                "D1",
                "Refinancing Risk – Debt Maturing in <1 Year",
                "maturity_lt_1y_pct",
                last_year,
                base_flag,
                maturity_lt,
                base_threshold,
                base_reason,
            )
        )


    # D2 – Balanced maturity
    maturity_mid = m.get("maturity_1_3y_pct")
    maturity_long = m.get("maturity_gt_3y_pct")
    if (
        maturity_mid is not None
        and maturity_long is not None
        and maturity_mid >= 0.30
        and maturity_long >= 0.20
    ):
        results.append(
            _make(
                "D2",
                "Balanced Maturity",
                "maturity_profile",
                last_year,
                "GREEN",
                maturity_mid,
                ">=30% (1-3y) & >=20% (>3y)",
                "Debt maturity is well spread across 1-3 years and >3 years.",
            )
        )

    # E1 – Floating rate exposure
    floating_share = m.get("floating_share")
    if floating_share is not None:
        high_floating = benchmarks.high_floating_share or cfg.high_floating_share
        if floating_share > high_floating:
            results.append(
                _make(
                    "E1",
                    "Floating Rate Exposure",
                    "floating_share",
                    last_year,
                    "RED",
                    floating_share,
                    f">{high_floating}",
                    "High floating rate debt share increases rate sensitivity.",
                )
            )
        elif floating_share > 0.4:
            results.append(
                _make(
                    "E1",
                    "Floating Rate Exposure",
                    "floating_share",
                    last_year,
                    "YELLOW",
                    floating_share,
                    "0.4-0.6",
                    "Moderate floating rate exposure.",
                )
            )
        else:
            results.append(
                _make(
                    "E1",
                    "Floating Rate Exposure",
                    "floating_share",
                    last_year,
                    "GREEN",
                    floating_share,
                    "<=0.4",
                    "Stable interest profile with higher fixed component.",
                )
            )

    # E2 – Cost of debt (WACD)
    wacd = m.get("wacd")
    if wacd is not None:
        high_wacd = benchmarks.high_wacd or cfg.high_wacd
        if wacd > high_wacd:
            results.append(
                _make(
                    "E2",
                    "Weighted Avg Cost of Debt",
                    "wacd",
                    last_year,
                    "RED",
                    wacd,
                    f">{high_wacd}",
                    "Very high borrowing cost versus benchmark.",
                )
            )
        elif wacd > 0.07:
            results.append(
                _make(
                    "E2",
                    "Weighted Avg Cost of Debt",
                    "wacd",
                    last_year,
                    "YELLOW",
                    wacd,
                    "7-12%",
                    "Cost of debt moderately high.",
                )
            )
        else:
            results.append(
                _make(
                    "E2",
                    "Weighted Avg Cost of Debt",
                    "wacd",
                    last_year,
                    "GREEN",
                    wacd,
                    "<=7%",
                    "Competitive borrowing cost.",
                )
            )

    # F1 – Covenant near breach
    buffer_pct = cfg.covenant_buffer_pct or 0.1

    def _headroom(limit, actual):
        if limit in (None, 0) or actual is None:
            return None
        return (limit - actual) / limit

    de_headroom = _headroom(covenants.de_ratio_limit, de)
    icr_headroom = _headroom(covenants.icr_limit, icr)
    debt_eb_headroom = _headroom(covenants.debt_ebitda_limit, debt_ebitda)

    if de is not None and de > covenants.de_ratio_limit:
        results.append(
            _make(
                "F2",
                "Covenant Breach D/E",
                "de_ratio",
                last_year,
                "RED",
                de,
                f">{covenants.de_ratio_limit}",
                "Debt-to-equity exceeds covenant limit.",
            )
        )
    elif de_headroom is not None and 0 <= de_headroom <= buffer_pct:
        results.append(
            _make(
                "F1",
                "Covenant Headroom D/E",
                "de_ratio",
                last_year,
                "YELLOW",
                de,
                f"within {buffer_pct*100:.0f}% buffer",
                "Debt-to-equity near covenant limit.",
            )
        )

    if icr is not None and icr < covenants.icr_limit:
        results.append(
            _make(
                "F2",
                "Covenant Breach ICR",
                "interest_coverage",
                last_year,
                "RED",
                icr,
                f"<{covenants.icr_limit}",
                "Interest coverage below covenant limit.",
            )
        )
    elif icr_headroom is not None and 0 <= icr_headroom <= buffer_pct:
        results.append(
            _make(
                "F1",
                "Covenant Headroom ICR",
                "interest_coverage",
                last_year,
                "YELLOW",
                icr,
                f"within {buffer_pct*100:.0f}% buffer",
                "Interest coverage close to covenant limit.",
            )
        )

    if debt_ebitda is not None and debt_ebitda > covenants.debt_ebitda_limit:
        results.append(
            _make(
                "F2",
                "Covenant Breach Debt/EBITDA",
                "debt_ebitda",
                last_year,
                "RED",
                debt_ebitda,
                f">{covenants.debt_ebitda_limit}",
                "Debt/EBITDA exceeds covenant limit.",
            )
        )
    elif debt_eb_headroom is not None and 0 <= debt_eb_headroom <= buffer_pct:
        results.append(
            _make(
                "F1",
                "Covenant Headroom Debt/EBITDA",
                "debt_ebitda",
                last_year,
                "YELLOW",
                debt_ebitda,
                f"within {buffer_pct*100:.0f}% buffer",
                "Debt/EBITDA close to covenant limit.",
            )
        )

    return results

