from typing import List, Dict

from .equity_funding_mix_config import EquityFundingRuleConfig, EquityFundingRuleThresholds
from .equity_funding_mix_models import RuleResult, IndustryBenchmarks


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
    rule_config: EquityFundingRuleConfig,
) -> List[RuleResult]:
    last_year = _latest_year(metrics)
    m = metrics[last_year]
    cfg: EquityFundingRuleThresholds = rule_config.generic
    results: List[RuleResult] = []

    # A1 – Retained Earnings Growth
    retained_yoy = m.get("retained_yoy_pct")

    if retained_yoy is not None:
        if retained_yoy < cfg.retained_earnings_decline_warning:
            results.append(
                _make(
                    "A1",
                    "Retained Earnings Growth",
                    "retained_earnings",
                    last_year,
                    "RED",
                    retained_yoy,
                    f"<{cfg.retained_earnings_decline_warning:.1%}",
                    "Retained earnings declining; internal capital formation deteriorating.",
                )
            )
        elif retained_yoy < 0.05:
            results.append(
                _make(
                    "A1",
                    "Retained Earnings Growth",
                    "retained_earnings",
                    last_year,
                    "YELLOW",
                    retained_yoy,
                    "0-5%",
                    "Weak internal capital formation; retained earnings growing slowly.",
                )
            )
        else:
            results.append(
                _make(
                    "A1",
                    "Retained Earnings Growth",
                    "retained_earnings",
                    last_year,
                    "GREEN",
                    retained_yoy,
                    ">=5%",
                    "Healthy retained earnings growth supporting capital formation.",
                )
            )

    # B1 – Return on Equity Threshold
    roe = m.get("roe")
    if roe is not None:
        if roe < cfg.roe_modest:
            results.append(
                _make(
                    "B1",
                    "Return on Equity",
                    "roe",
                    last_year,
                    "RED",
                    roe,
                    f"<{cfg.roe_modest:.1%}",
                    "Poor returns to equity holders; capital efficiency weak.",
                )
            )
        elif roe < cfg.roe_good:
            results.append(
                _make(
                    "B1",
                    "Return on Equity",
                    "roe",
                    last_year,
                    "YELLOW",
                    roe,
                    f"{cfg.roe_modest:.1%}-{cfg.roe_good:.1%}",
                    "Moderate ROE; acceptable but room for improvement.",
                )
            )
        else:
            results.append(
                _make(
                    "B1",
                    "Return on Equity",
                    "roe",
                    last_year,
                    "GREEN",
                    roe,
                    f">={cfg.roe_good:.1%}",
                    "Strong ROE indicating good capital efficiency.",
                )
            )

    # B2 – ROE Declining Trend
    roe_declining = trends.get("roe_declining", False)

    if roe_declining:
        results.append(
            _make(
                "B2",
                "ROE Declining Trend",
                "roe",
                last_year,
                "YELLOW",
                roe,
                "3+ consecutive years decline",
                "ROE showing declining trend; profitability and capital efficiency eroding.",
            )
        )
    else:
        results.append(
            _make(
                "B2",
                "ROE Declining Trend",
                "roe",
                last_year,
                "Green",
                roe,
                "Not Found 3+ consecutive years decline",
                "ROE is not in declining trend.",
            )
        )

    # C1 – Dividend Payout Ratio Threshold
    payout_ratio = m.get("payout_ratio")
    if payout_ratio is not None:
        if payout_ratio > cfg.high_dividend_to_pat:
            results.append(
                _make(
                    "C1",
                    "Dividend Payout Ratio",
                    "payout_ratio",
                    last_year,
                    "RED",
                    payout_ratio,
                    f">{cfg.high_dividend_to_pat:.1%}",
                    "Paying more than earnings (unsustainable); dividends likely funded from reserves or debt.",
                )
            )
        elif payout_ratio > cfg.payout_high:
            results.append(
                _make(
                    "C1",
                    "Dividend Payout Ratio",
                    "payout_ratio",
                    last_year,
                    "YELLOW",
                    payout_ratio,
                    f"{cfg.payout_high:.1%}-{cfg.high_dividend_to_pat:.1%}",
                    "Excessive payout limiting reinvestment; above industry norms.",
                )
            )
        elif payout_ratio > cfg.payout_normal:
            results.append(
                _make(
                    "C1",
                    "Dividend Payout Ratio",
                    "payout_ratio",
                    last_year,
                    "YELLOW",
                    payout_ratio,
                    f"{cfg.payout_normal:.1%}-{cfg.payout_high:.1%}",
                    "Payout moderately high; discipline warranted.",
                )
            )
        else:
            results.append(
                _make(
                    "C1",
                    "Dividend Payout Ratio",
                    "payout_ratio",
                    last_year,
                    "GREEN",
                    payout_ratio,
                    f"<={cfg.payout_normal:.1%}",
                    "Normal dividend payout discipline; reinvestment capacity preserved.",
                )
            )

    # C2 – Dividend to FCF Ratio
    dividend_fcf = m.get("dividend_to_fcf")
    if dividend_fcf is not None:
        if dividend_fcf > cfg.dividends_exceed_fcf_warning:
            results.append(
                _make(
                    "C2",
                    "Dividend vs FCF Check",
                    "dividend_to_fcf",
                    last_year,
                    "RED",
                    dividend_fcf,
                    f">{cfg.dividends_exceed_fcf_warning:.1f}",
                    "Dividends exceed free cash flow; payouts may be funded through borrowings or reserves.",
                )
            )
        else:
            results.append(
                _make(
                    "C2",
                    "Dividend vs FCF Check",
                    "dividend_to_fcf",
                    last_year,
                    "GREEN",
                    dividend_fcf,
                    f"<={cfg.dividends_exceed_fcf_warning:.1f}",
                    "Dividends covered by free cash flow; sustainable payout policy.",
                )
            )

    # C3 – Payout Rising While PAT Stagnant
    payout_yoy = trends.get("payout_yoy_growth", [])
    pat_latest = m.get("pat")
    if len(payout_yoy) > 0 and payout_yoy[-1] is not None:
        if payout_yoy[-1] > 0.10:  # Payout increased >10% YoY
            # Check if PAT is stagnant
            if pat_latest is not None and len(payout_yoy) > 0:
                results.append(
                    _make(
                        "C3",
                        "Payout Rising While PAT Stagnant",
                        "payout_ratio",
                        last_year,
                        "YELLOW",
                        payout_yoy[-1],
                        ">10% YoY & PAT stagnant",
                        "Payout ratio increasing despite flat PAT; capital discipline risk.",
                    )
                )
            elif pat_latest is not None and pat_latest < 0:  # PAT is negative
                results.append(
                    _make(
                        "C3",
                        "Payout Rising While PAT Stagnant",
                        "payout_ratio",
                        last_year,
                        "RED",
                        payout_yoy[-1],
                        ">10% YoY & PAT negative",
                        "Payout ratio increasing despite negative PAT; unsustainable dividend policy.",
                    )
                )

        elif pat_latest is not None and len(payout_yoy) > 0:
            results.append(
                _make(
                    "C3",
                    "Payout Rising While PAT Stagnant",
                    "payout_ratio",
                    last_year,
                    "GREEN",
                    payout_yoy[-1],
                    ">10% YoY & PAT growing",
                    "Payout ratio increasing in line with PAT growth; acceptable policy.",
                )
            )

    # D1 – Dilution Threshold
    dilution_pct = m.get("dilution_pct")
    if dilution_pct is not None and dilution_pct > 0:
        if dilution_pct > cfg.dilution_high:
            results.append(
                _make(
                    "D1",
                    "Equity Dilution – High",
                    "dilution_pct",
                    last_year,
                    "RED",
                    dilution_pct,
                    f">{cfg.dilution_high:.1%}",
                    "Significant equity dilution; shareholder value impacted.",
                )
            )
        elif dilution_pct > cfg.dilution_warning:
            results.append(
                _make(
                    "D1",
                    "Equity Dilution – Moderate",
                    "dilution_pct",
                    last_year,
                    "YELLOW",
                    dilution_pct,
                    f"{cfg.dilution_warning:.1%}-{cfg.dilution_high:.1%}",
                    "Moderate equity dilution; monitor ongoing issuances.",
                )
            )
        else:
            results.append(
                _make(
                    "D1",
                    "Equity Dilution – Low",
                    "dilution_pct",
                    last_year,
                    "GREEN",
                    dilution_pct,
                    f"<={cfg.dilution_warning:.1%}",
                    "Minimal dilution; share capital change within normal range.",
                )
            )

    # D2 – Dilution Without Earnings Growth
    pat_cagr = trends.get("pat_cagr")
    if dilution_pct is not None and dilution_pct > cfg.dilution_warning:
        if pat_cagr is not None and pat_cagr < 0.05:  # PAT CAGR < 5%
            results.append(
                _make(
                    "D2",
                    "Dilution Without Earnings Growth",
                    "dilution_pct",
                    last_year,
                    "YELLOW",
                    dilution_pct,
                    f">{cfg.dilution_warning:.1%} & PAT CAGR <5%",
                    "Equity issuance with weak earnings growth; poor return on new capital.",
                )
            )

    # E1 – Debt Rising vs Equity Stagnating
    equity_cagr = trends.get("equity_cagr")
    debt_cagr = trends.get("debt_cagr")
    if equity_cagr is not None and debt_cagr is not None:
        growth_gap = debt_cagr - equity_cagr
        if growth_gap > cfg.leverage_rising_threshold * 100:  # gap > 10%
            results.append(
                _make(
                    "E1",
                    "Debt Rising vs Equity Stagnating",
                    "debt_to_equity",
                    last_year,
                    "YELLOW",
                    growth_gap,
                    f">10% (gap {growth_gap:.1f}%)",
                    "Debt growing faster than equity; rising reliance on borrowings.",
                )
            )
        else:
            results.append(
                _make(
                    "E1",
                    "Debt vs Equity Growth",
                    "debt_to_equity",
                    last_year,
                    "GREEN",
                    growth_gap,
                    f"<10% (gap {growth_gap:.1f}%)",
                    "Balanced capital structure evolution.",
                )
            )

    # E2 – Net Worth Stagnating while Debt Rising
    net_worth_latest = m.get("net_worth")
    debt_latest = m.get("debt")
    if equity_cagr is not None and debt_cagr is not None:
        if equity_cagr <= 0 and debt_cagr > 0:
            results.append(
                _make(
                    "E2",
                    "Net Worth Stagnating while Debt Rising",
                    "net_worth",
                    last_year,
                    "RED",
                    equity_cagr,
                    "Net Worth CAGR <=0 & Debt CAGR >0",
                    "Weak equity cushion with rising leverage; financial stress signal.",
                )
            )

    return results
