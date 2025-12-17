
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
