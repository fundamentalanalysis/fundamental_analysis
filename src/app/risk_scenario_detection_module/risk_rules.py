from .risk_models import RuleResult


# ==================================================
# Helper
# ==================================================
def _make(rule_id, rule_name, flag, year, pattern, reason):
    return RuleResult(
        rule_id=rule_id,
        rule_name=rule_name,
        flag=flag,
        year=year,
        value=None,
        threshold=pattern,
        reason=reason,
    )


# ==================================================
# RULE ENGINE (STRICT CONTRACT)
# RETURNS: List[RuleResult] ONLY
# ==================================================
def apply_rules(metrics, trends, cfg=None):
    year = max(metrics.keys())
    rules = []

    # ==================================================
    # 3.1 ZOMBIE COMPANY
    # ==================================================
    z = trends["zombie_company"]

    # Z1 — EBIT < Interest (2+ years) → CRITICAL
    if z["ebit_vs_interest"]["comparison"]["rule_triggered"]:
        cnt = z["ebit_vs_interest"]["comparison"]["count"]
        rules.append(_make(
            "Z1",
            "Zombie Company Detection",
            "CRITICAL",
            year,
            f"EBIT < Interest for {cnt} years",
            "Company unable to cover interest through earnings; survival dependent on lenders."
        ))

    # Z2 — CFO < Interest (2+ years) → HIGH
    if z["cfo_vs_interest"]["comparison"]["rule_triggered"]:
        cnt = z["cfo_vs_interest"]["comparison"]["count"]
        rules.append(_make(
            "Z2",
            "Zombie Company – Cash Stress",
            "HIGH",
            year,
            f"CFO < Interest for {cnt} years",
            "Operating cash flows insufficient to service interest."
        ))

    # Z3 — Net Debt ↑ + Profit ↓ → HIGH
    if z["debt_vs_profit"]["comparison"]["rule_triggered"]:
        rules.append(_make(
            "Z3",
            "Zombie Company – Debt Spiral",
            "HIGH",
            year,
            "Debt ↑ while Profit ↓",
            "Debt increased while profitability weakened."
        ))

    # ==================================================
    # 3.2 WINDOW DRESSING
    # ==================================================
    w = trends["window_dressing"]

    if w["cash_spike"]["comparison"]["rule_triggered"]:
        rules.append(_make(
            "W1",
            "Window Dressing – Cash Spike",
            "YELLOW",
            year,
            "Cash spike >30% YoY",
            "Sudden year-end liquidity spike detected."
        ))

    if w["one_off_income"]["comparison"]["rule_triggered"]:
        cnt = w["one_off_income"]["comparison"]["count"]
        rules.append(_make(
            "W2",
            "Window Dressing – One-off Income",
            "YELLOW",
            year,
            f"One-off income >20% PAT in {cnt} years",
            "Exceptional income materially influenced profits."
        ))

    if w["profit_spike"]["comparison"]["rule_triggered"]:
        rules.append(_make(
            "W3",
            "Window Dressing – Profit Spike",
            "YELLOW",
            year,
            "Profit spike without revenue support",
            "Profit growth appears cosmetic."
        ))

    # ==================================================
    # 3.3 ASSET STRIPPING (Dividend rule REMOVED as requested)
    # ==================================================
    a = trends["asset_stripping"]

    if a["fixed_asset_decline"]["comparison"]["rule_triggered"]:
        rules.append(_make(
            "A1",
            "Asset Stripping – Asset Base Erosion",
            "RED",
            year,
            "Fixed assets declined ≥2 years",
            "Sustained erosion of asset base detected."
        ))

    if a["debt_vs_assets"]["comparison"]["rule_triggered"]:
        rules.append(_make(
            "A3",
            "Asset Stripping – Leverage Hollowing",
            "CRITICAL",
            year,
            "Debt rising while assets shrinking",
            "Leverage increased despite shrinking assets."
        ))

    # ==================================================
    # 3.4 LOAN EVERGREENING
    # ==================================================
    e = trends["loan_evergreening"]

    if e["loan_rollover"]["comparison"]["rule_triggered"]:
        rules.append(_make(
            "E1",
            "Loan Evergreening – Rollovers",
            "RED",
            year,
            "Loan rollover >50%",
            "Debt repeatedly refinanced instead of repaid."
        ))

    if e["interest_capitalized"]["comparison"]["rule_triggered"]:
        rules.append(_make(
            "E2",
            "Loan Evergreening – Interest Capitalized",
            "YELLOW",
            year,
            "Interest capitalized >20%",
            "Interest obligations deferred via capitalization."
        ))

    if e["principal_repayment"]["comparison"]["rule_triggered"]:
        rules.append(_make(
            "E3",
            "Loan Evergreening – Weak Repayment",
            "YELLOW",
            year,
            "Principal repayment <10%",
            "No meaningful reduction in outstanding debt."
        ))

    # ==================================================
    # 3.5 CIRCULAR TRADING / RPT FRAUD
    # (ONLY rules you kept)
    # ==================================================
    c = trends["circular_trading"]

    if c["sales_vs_cfo"]["comparison"]["rule_triggered"]:
        rules.append(_make(
            "C3",
            "Circular Trading – Revenue Quality Risk",
            "RED",
            year,
            "Sales ↑ while OCF ↓",
            "Revenue growth not supported by cash flows."
        ))

    if c["receivables_vs_revenue"]["comparison"]["rule_triggered"]:
        rules.append(_make(
            "C4",
            "Circular Trading – Aggressive Revenue Recognition",
            "YELLOW",
            year,
            "Receivables growth > revenue growth",
            "Potential premature or aggressive revenue booking."
        ))

    if c["rpt_balance_surge"]["comparison"]["rule_triggered"]:
        rules.append(_make(
            "C5",
            "Circular Trading – RPT Round-Tripping",
            "RED",
            year,
            "Rapid rise in RPT balances",
            "Possible circular fund movements detected."
        ))

    # 🔒 CRITICAL: RETURN ONLY LIST
    return rules
