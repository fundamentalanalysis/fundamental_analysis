# Lightweight, deterministic narrative generator for the Red Flag Aggregator.
# This is intentionally NOT an external LLM call by default; it produces an
# analyst-style summary from inputs. If the project later integrates an LLM
# the call should be wrapped here (and MUST NOT change numeric outputs).
from typing import List, Dict, Any, Optional
from . import red_flag_definitions as definitions


def generate_narrative(company_id: str, flags: List[Dict[str, Any]], category_risks: Dict[str, str], scenarios: Dict[str, bool], red_flag_index: int) -> str:
    parts: List[str] = []
    parts.append(f"Company {company_id} - Red Flag Index: {red_flag_index}.")

    # Highest-risk categories
    high_cats = [c for c, r in category_risks.items()
                 if r in ("HIGH", "VERY_HIGH")]
    if high_cats:
        parts.append("High-risk themes: " + ", ".join(high_cats) + ".")
    else:
        parts.append("No single category shows systemic high risk.")

    if any(scenarios.values()):
        active = [k for k, v in scenarios.items() if v]
        parts.append("Detected scenarios: " + ", ".join(active) + ".")

    # Top critical flag summaries (up to 5). Use `risk_category` and module for context.
    criticals = [f for f in flags if f.get("severity") == "CRITICAL"]
    if criticals:
        parts.append("Critical issues:")
        for c in criticals[:5]:
            cat_key = c.get("risk_category") or c.get("category") or "unknown"
            cat_name = definitions.CATEGORY_NAMES.get(cat_key, cat_key)
            module = c.get("module", "unknown")
            parts.append(
                f"- {cat_name} ({module}): {c.get('title')} — {c.get('detail')}")

    parts.append(
        "This summary is explanatory only. Numbers and caps are authoritative outputs.")
    return "\n".join(parts)
