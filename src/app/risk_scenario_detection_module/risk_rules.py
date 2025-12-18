
# from .risk_models import RuleResult


# def _make(id, name, flag, year, threshold, reason):
#     return RuleResult(
#         rule_id=id,
#         rule_name=name,
#         flag=flag,
#         year=year,
#         value=None,
#         threshold=threshold,
#         reason=reason,
#     )


# def apply_rules(metrics, trends, cfg=None):
#     year = max(metrics.keys())
#     rules = []

#     z = trends["zombie_company"]
#     le = trends.get("loan_evergreening", {})

#     if z["cfo_vs_interest"]["comparison"]["rule_triggered"]:
#         rules.append(_make(
#             "Z2", "Zombie Company – Cash Stress", "HIGH",
#             year, "CFO < Interest ≥2Y",
#             "Operating cash flows insufficient to service interest."
#         ))

#     if z["debt_vs_profit"]["comparison"]["rule_triggered"]:
#         rules.append(_make(
#             "Z3", "Zombie Company – Debt Spiral", "HIGH",
#             year, "Debt ↑ Profit ↓",
#             "Debt increased while profitability weakened."
#         ))

#     if le.get("loan_rollover", {}).get("comparison", {}).get("rule_triggered"):
#         rules.append(_make(
#             "E2", "Loan Evergreening – High Rollover", "YELLOW",
#             year, "Borrowings > Repayments",
#             "New borrowings materially exceeded repayments, indicating refinancing risk."
#         ))

#     return rules

# risk_rules.py





# from .risk_models import RuleResult


# def _make(id, name, flag, year, reason):
#     return RuleResult(
#         rule_id=id,
#         rule_name=name,
#         flag=flag,
#         year=year,
#         value=None,
#         threshold="Pattern-based",
#         reason=reason,
#     )


# def apply_rules(metrics, trends, cfg=None):
#     year = max(metrics.keys())
#     rules = []

#     c = trends.get("circular_trading", {})

#     if c.get("rpt_sales_spike", {}).get("comparison", {}).get("rule_triggered"):
#         rules.append(_make("C1", "Circular Trading – RPT Sales Spike", "HIGH", year,
#                            "Related party sales unusually high."))

#     if c.get("rpt_receivables_high", {}).get("comparison", {}).get("rule_triggered"):
#         rules.append(_make("C2", "Circular Trading – RPT Receivables", "HIGH", year,
#                            "Large receivables due from related parties."))

#     if c.get("sales_up_cfo_down", {}).get("comparison", {}).get("rule_triggered"):
#         rules.append(_make("C3", "Circular Trading – Fake Revenue", "HIGH", year,
#                            "Revenue increased while operating cash flows declined."))

#     if c.get("receivables_vs_revenue", {}).get("comparison", {}).get("rule_triggered"):
#         rules.append(_make("C4", "Circular Trading – Aggressive Recognition", "HIGH", year,
#                            "Receivables growing faster than revenue."))

#     if c.get("rpt_balance_rising", {}).get("comparison", {}).get("rule_triggered"):
#         rules.append(_make("C5", "Circular Trading – Round Tripping", "HIGH", year,
#                            "Rapid increase in related party balances."))

#     return rules






from .risk_models import RuleResult


def _make(rule_id, rule_name, flag, year, value, threshold, reason):
    return RuleResult(
        rule_id=rule_id,
        rule_name=rule_name,
        flag=flag,
        year=year,
        value=value,
        threshold=threshold,
        reason=reason,
    )


# ==================================================
# RULE ENGINE (STRICT CONTRACT)
# RETURNS: List[RuleResult] ONLY
# ==================================================
def apply_rules(metrics, trends, cfg=None):
    rules = []
    latest_year = max(metrics.keys())

    # =====================================================
    # 3.1 ZOMBIE COMPANY
    # =====================================================
    z = trends.get("zombie_company", {})

    # Z1 – EBIT < Interest ≥2 years
    ebit_below = z.get("ebit_vs_interest", {}).get("comparison", {}).get("years_below", [])
    if len(ebit_below) >= 2:
        y = ebit_below[-1]
        ratio = round(metrics[y]["ebit"] / metrics[y]["interest"], 2)
        rules.append(_make(
            "Z1",
            "Zombie Company – EBIT Stress",
            "CRITICAL",
            y,
            ratio,
            "<1.0",
            "EBIT failed to cover interest for multiple years."
        ))

    # Z2 – CFO < Interest ≥2 years
    cfo_below = z.get("cfo_vs_interest", {}).get("comparison", {}).get("years_below", [])
    if len(cfo_below) >= 2:
        y = cfo_below[-1]
        ratio = round(metrics[y]["cfo"] / metrics[y]["interest"], 2)
        rules.append(_make(
            "Z2",
            "Zombie Company – Cash Stress",
            "HIGH",
            y,
            ratio,
            "<1.0",
            "Operating cash flows insufficient to service interest."
        ))

    # Z3 – Debt ↑ Profit ↓
    overlap = z.get("debt_vs_profit", {}).get("comparison", {}).get("overlap_years", [])
    if len(overlap) >= 2:
        y = overlap[-1]
        rules.append(_make(
            "Z3",
            "Zombie Company – Debt Spiral",
            "HIGH",
            y,
            metrics[y]["net_debt"],
            "Debt ↑ Profit ↓",
            "Debt increased while profitability weakened."
        ))

    # =====================================================
    # 3.2 WINDOW DRESSING
    # =====================================================
    w = trends.get("window_dressing", {})

    # W1 – Cash spike
    cash_years = w.get("cash_spike", {}).get("comparison", {}).get("flagged_years", [])
    if cash_years:
        y = cash_years[-1]
        rules.append(_make(
            "W1",
            "Window Dressing – Cash Spike",
            "YELLOW",
            y,
            metrics[y]["cash"],
            ">30% YoY",
            "Sudden year-end cash increase detected."
        ))

    # W2 – One-off income >20% PAT (SAFE)
    oneoff_years = w.get("one_off_income", {}).get("comparison", {}).get("flagged_years", [])
    if oneoff_years:
        y = oneoff_years[-1]
        profit = metrics[y].get("net_profit", 0)
        other_income = metrics[y].get("other_income", 0)
        if profit != 0:
            ratio = round(abs(other_income) / abs(profit), 2)
            rules.append(_make(
                "W2",
                "Window Dressing – One-off Income",
                "YELLOW",
                y,
                ratio,
                ">20% of PAT",
                "One-off income materially impacted profits."
            ))

    # =====================================================
    # 3.3 ASSET STRIPPING
    # =====================================================
    a = trends.get("asset_stripping", {})

    # A1 – Fixed assets decline ≥2 years
    decline_years = a.get("fixed_asset_decline", {}).get("comparison", {}).get("flagged_years", [])
    if len(decline_years) >= 2:
        y = decline_years[-1]
        rules.append(_make(
            "A1",
            "Asset Stripping – Asset Base Decline",
            "RED",
            y,
            metrics[y]["fixed_assets"],
            "≥2Y decline",
            "Sustained reduction in fixed assets detected."
        ))

    # A3 – Debt ↑ Assets ↓
    debt_asset = a.get("debt_vs_assets", {}).get("comparison", {}).get("flagged_years", [])
    if len(debt_asset) >= 2:
        y = debt_asset[-1]
        rules.append(_make(
            "A3",
            "Asset Stripping – Debt-Funded Hollowing",
            "CRITICAL",
            y,
            metrics[y]["net_debt"],
            "Debt ↑ Assets ↓",
            "Debt increased while asset base shrank."
        ))

    # =====================================================
    # 3.4 LOAN EVERGREENING
    # =====================================================
    e = trends.get("loan_evergreening", {})

    # E1 – Loan rollover >50%
    rollover = e.get("loan_rollover", {}).get("comparison", {}).get("flagged_years", [])
    if rollover:
        y = rollover[-1]
        proceeds = metrics[y]["proceeds_from_borrowings"]
        repaid = metrics[y]["repayment_of_borrowings"]
        total = proceeds + repaid
        ratio = round(proceeds / total, 2) if total else 0

        rules.append(_make(
            "E1",
            "Loan Evergreening – High Rollover",
            "RED",
            y,
            ratio,
            ">50%",
            "Borrowings largely used to refinance existing debt."
        ))

    # =====================================================
    # 3.5 CIRCULAR TRADING
    # =====================================================
    c = trends.get("circular_trading", {})

    # C3 – Sales ↑ CFO ↓
    sales_cfo = c.get("sales_up_cfo_down", {}).get("comparison", {}).get("flagged_years", [])
    if sales_cfo:
        y = sales_cfo[-1]
        rules.append(_make(
            "C3",
            "Circular Trading – Fake Revenue",
            "RED",
            y,
            metrics[y]["cfo"],
            "Sales ↑ CFO ↓",
            "Revenue growth not supported by cash flows."
        ))

    # C4 – Receivables ↑ > Revenue ↑
    recv_rev = c.get("receivables_vs_revenue", {}).get("comparison", {}).get("flagged_years", [])
    if recv_rev:
        y = recv_rev[-1]
        rules.append(_make(
            "C4",
            "Circular Trading – Aggressive Recognition",
            "HIGH",
            y,
            metrics[y]["receivables"],
            "Receivables ↑ > Revenue ↑",
            "Receivables growth outpaced revenue growth."
        ))

    return rules
