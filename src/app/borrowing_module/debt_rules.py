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

    # A1 – Debt growing faster than EBITDA
    if debt_cagr is not None and ebitda_cagr is not None:
        gap = cfg.high_debt_cagr_vs_ebitda_gap or 0
        if debt_cagr > ebitda_cagr + gap:
            results.append(
                _make(
                    "A1",
                    "Debt CAGR vs EBITDA",
                    "debt_cagr",
                    last_year,
                    "RED",
                    debt_cagr,
                    f">{ebitda_cagr + gap:.2f}",
                    f"Debt CAGR {debt_cagr:.2f}% exceeds EBITDA CAGR {ebitda_cagr:.2f}% by more than {gap*100:.0f}bps.",
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
    if lt_debt_cagr is not None and revenue_cagr is not None and lt_debt_cagr > 10 and revenue_cagr < 5:
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

    # C1 – ICR thresholds
    icr = m.get("interest_coverage")
    if icr is not None:
        if icr < cfg.critical_icr:
            results.append(
                _make(
                    "C1",
                    "Interest Coverage",
                    "interest_coverage",
                    last_year,
                    "RED",
                    icr,
                    f"<{cfg.critical_icr}",
                    "EBIT does not cover finance cost; default risk elevated.",
                )
            )
        elif icr < max(cfg.low_icr, benchmarks.min_safe_icr):
            results.append(
                _make(
                    "C1",
                    "Interest Coverage",
                    "interest_coverage",
                    last_year,
                    "YELLOW",
                    icr,
                    f"{cfg.critical_icr}-{cfg.low_icr}",
                    "Tight interest servicing ability.",
                )
            )

    # C2 – Finance cost rising faster than debt
    if debt_cagr is not None:
        finance_cost_cagr = trends.get("finance_cost_cagr")
        if finance_cost_cagr is not None and finance_cost_cagr > debt_cagr + 5:
            results.append(
                _make(
                    "C2",
                    "Finance Cost Pressure",
                    "finance_cost",
                    last_year,
                    "YELLOW",
                    finance_cost_cagr,
                    f">{debt_cagr + 5:.2f}",
                    "Finance cost growing faster than debt, indicating rate pressure.",
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

    # D1 – Refinancing risk (<1y maturity)
    maturity_lt = m.get("maturity_lt_1y_pct")
    if maturity_lt is not None and maturity_lt > cfg.risky_debt_lt_1y_pct:
        results.append(
            _make(
                "D1",
                "Refinancing Risk",
                "maturity_lt_1y_pct",
                last_year,
                "RED",
                maturity_lt,
                f">{cfg.risky_debt_lt_1y_pct}",
                "More than half of debt matures within one year.",
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

