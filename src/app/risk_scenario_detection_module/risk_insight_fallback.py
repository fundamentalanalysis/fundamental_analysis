# risk_insight_fallback.py
from typing import List, Dict


def generate_fallback_narrative(rules_triggered: List[Dict]) -> List[str]:
    narrative = []
    grouped = {}
    for r in rules_triggered:
        k = r.get("rule_name")
        grouped.setdefault(k, []).append(r)
    for name, items in grouped.items():
        flags = sorted({it.get("flag") for it in items}, reverse=True)
        reasons = "; ".join({it.get("reason") for it in items if it.get("reason")})
        narrative.append(f"{name} ({', '.join(flags)}): {reasons}")
    return narrative
