# from .risk_models import RuleResult


# def _make(id, name, flag, year, value, threshold, reason):
#     return RuleResult(
#         rule_id=id,
#         rule_name=name,
#         flag=flag,
#         year=year,
#         value=value,
#         threshold=threshold,
#         reason=reason,
#     )


# def apply_rules(metrics, trends, cfg):
#     year = max(metrics.keys())
#     rules = []

#     z = trends["zombie_company"]

#     if z["ebit_vs_interest"]["years_below_1"] >= cfg.zombie.ebit_interest_years:
#         rules.append(_make("Z1", "Zombie Company – Earnings Stress", "CRITICAL",
#                            year, None, "EBIT < Interest ≥2Y",
#                            "Earnings insufficient to cover interest."))

#     if z["cfo_vs_interest"]["years_below_1"] >= cfg.zombie.cfo_interest_years:
#         rules.append(_make("Z2", "Zombie Company – Cash Stress", "HIGH",
#                            year, None, "CFO < Interest ≥2Y",
#                            "Cash flows insufficient for debt servicing."))

#     if z["net_debt"]["rising"] and z["profit"]["falling"]:
#         rules.append(_make("Z3", "Debt Spiral Risk", "HIGH",
#                            year, None, "Debt ↑ Profit ↓",
#                            "Rising debt with declining profits."))

#     w = trends["window_dressing"]
#     if w["cash_spike_yoy"] and w["cash_spike_yoy"] > cfg.window.cash_spike_threshold:
#         rules.append(_make("W1", "Window Dressing – Cash Spike", "YELLOW",
#                            year, w["cash_spike_yoy"], ">30% YoY",
#                            "Sudden year-end cash spike."))

#     if w["one_off_income_ratio"] and w["one_off_income_ratio"] > cfg.window.one_off_income_ratio:
#         rules.append(_make("W2", "Window Dressing – One-off Income", "YELLOW",
#                            year, w["one_off_income_ratio"], ">20% of PAT",
#                            "One-off income inflating profits."))

#         a = trends["asset_stripping"]
#         if a["fixed_assets"]["decline_years"] >= cfg.asset.fixed_asset_decline_years:
#             rules.append(_make(
#                 "A1",
#                 "Asset Stripping",
#                 "RED",
#                 year,
#                 None,
#                 "Assets declining ≥2Y",
#                 "Structural hollowing of asset base."
#             ))


#     e = trends["loan_evergreening"]
#     if e["loan_rollover_ratio"] and e["loan_rollover_ratio"] > cfg.evergreen.rollover_ratio_critical:
#         rules.append(_make("E1", "Loan Evergreening", "RED",
#                            year, e["loan_rollover_ratio"], ">50%",
#                            "Debt rolled over instead of repaid."))

#     c = trends["circular_trading"]
#     if c["sales_up_cash_down"]:
#         rules.append(_make("C3", "Circular Trading Risk", "RED",
#                            year, None, "Sales ↑ Cash ↓",
#                            "Revenue growth not converting to cash."))

#     return rules


from .risk_models import RuleResult


def _make(id, name, flag, year, threshold, reason):
    return RuleResult(
        rule_id=id,
        rule_name=name,
        flag=flag,
        year=year,
        value=None,
        threshold=threshold,
        reason=reason,
    )


def apply_rules(metrics, trends, cfg=None):
    year = max(metrics.keys())
    rules = []

    z = trends["zombie_company"]

    if z["cfo_vs_interest"]["comparison"]["rule_triggered"]:
        rules.append(_make(
            "Z2", "Zombie Company – Cash Stress", "HIGH",
            year, "CFO < Interest ≥2Y",
            "Operating cash flows insufficient to service interest."
        ))

    if z["debt_vs_profit"]["comparison"]["rule_triggered"]:
        rules.append(_make(
            "Z3", "Zombie Company – Debt Spiral", "HIGH",
            year, "Debt ↑ Profit ↓",
            "Debt increased while profitability weakened."
        ))

    return rules
