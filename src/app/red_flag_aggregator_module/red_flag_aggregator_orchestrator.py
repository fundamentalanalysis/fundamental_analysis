from __future__ import annotations
from typing import Dict, List, Any, Tuple, Optional

from .red_flag_aggregator_models import (
    RedFlag,
    validate_and_coerce_flag,
    severity_counts,
    ValidationError,
)
from .red_flag_aggregator_config import (
    SEVERITY_WEIGHTS,
    MODULE_CATEGORY_MAP,
    PATTERN_RULES,
    SCENARIO_MAX_OVERRIDES,
    SCENARIO_ADDITIVE_OVERRIDES,
    SCENARIO_SCORE_CAPS,
    MAX_SEVERITY_SCORE,
    CATEGORY_PRIORITY,
    CATEGORY_PRIORITY_INDEX,
)
from . import red_flag_aggregator_llm as llm
from . import red_flag_definitions as definitions


class AggregationError(Exception):
    pass


def _ensure_module_on_raw(raw: Dict[str, Any], module_key: str) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return raw
    if raw.get("module") is None:
        raw = dict(raw)
        raw["module"] = module_key
    return raw


def _map_flag_category(flag: RedFlag) -> str:
    """Extract category from flag. Since risk_category is now REQUIRED,
    this is a simple accessor (no inference needed)."""
    # print(f"Mapping flag {flag.title} to category {flag.risk_category}")
    return flag.risk_category


def _group_by_category(flags: List[RedFlag]) -> Dict[str, List[RedFlag]]:
    grouped: Dict[str, List[RedFlag]] = {}
    for f in flags:
        cat = _map_flag_category(f)
        grouped.setdefault(cat, []).append(f)
    return grouped


def _apply_pattern_rules(grouped_flags: Dict[str, List[RedFlag]]) -> Dict[str, str]:
    # Initialize all canonical categories to LOW so outputs are complete
    out: Dict[str, str] = {
        cat: "LOW" for cat in definitions.ALL_DEFINITIONS.keys()}
    print("Applying pattern rules to grouped flags:", grouped_flags)

    # Compute scores for categories that have flags (override defaults)
    for cat, flags in grouped_flags.items():
        rule = PATTERN_RULES.get(cat)
        if rule:
            try:
                out[cat] = rule(flags)
            except Exception:
                out[cat] = "LOW"
        else:
            out[cat] = "LOW"

    # Sanity: ensure we emitted the full taxonomy
    if len(out) != len(definitions.ALL_DEFINITIONS):
        raise AggregationError(
            "category_risks emission mismatch with canonical taxonomy")

    return out


def _detect_scenarios(
    grouped_flags: Dict[str, List[RedFlag]],
    counts: Dict[str, int],
    severity_score: int,
    category_risks: Dict[str, str],
    explicit_signals: Optional[Dict[str, bool]] = None,
) -> Dict[str, bool]:
    """
    Detect scenarios. If `explicit_signals` is provided, those keys take precedence
    (i.e. authoritative for fraud-related flags). Detection may set non-fraud
    scenarios when not explicitly provided.
    """
    scenarios = {
        "zombie": False,
        "rpt_fraud": False,
        "evergreening": False,
        "asset_stripping": False,
        "window_dressing": False,
    }

    explicit_signals = explicit_signals or {}
    # Apply any explicit signals first (authoritative)
    for k, v in explicit_signals.items():
        if k in scenarios:
            scenarios[k] = bool(v)

    # Scan flags for explicit indicators (these are explicit module signals,
    # not inferred from other categories). We do NOT infer fraud from governance
    # severity alone.
    for flags in grouped_flags.values():
        for f in flags:
            metric_lower = str(f.metric).lower() if f.metric else ""
            if metric_lower in ("related_party", "rpt", "rpt_fraud") or f.extra.get("rpt"):
                # If caller explicitly supplied an rpt_fraud signal, keep it;
                # otherwise allow explicit related-party metrics to set it.
                if "rpt_fraud" not in explicit_signals:
                    scenarios["rpt_fraud"] = True
            if metric_lower == "evergreening":
                if "evergreening" not in explicit_signals:
                    scenarios["evergreening"] = True
            if metric_lower == "asset_stripping":
                if "asset_stripping" not in explicit_signals:
                    scenarios["asset_stripping"] = True
            if metric_lower == "window_dressing":
                if "window_dressing" not in explicit_signals:
                    scenarios["window_dressing"] = True

    # Zombie detection: combination of high liquidity/earnings stress and high severity
    liq_risk = category_risks.get("liquidity", "LOW")
    earn_risk = category_risks.get("earnings_quality", "LOW")
    if "zombie" not in explicit_signals:
        if severity_score >= 60 and (liq_risk in ("HIGH", "VERY_HIGH") or earn_risk in ("HIGH", "VERY_HIGH")):
            scenarios["zombie"] = True

    # Asset stripping if governance severe + asset utilization high (only if not explicit)
    gov_flags = grouped_flags.get("governance_fraud", [])
    if "asset_stripping" not in explicit_signals:
        if category_risks.get("asset_utilization", "LOW") in ("HIGH", "VERY_HIGH") and any(f.severity.name == "CRITICAL" for f in gov_flags):
            scenarios["asset_stripping"] = True

    # Window dressing heuristic: many yellows and few reds (if not explicit)
    if "window_dressing" not in explicit_signals:
        if counts.get("yellow", 0) >= 5 and counts.get("red", 0) == 0 and counts.get("critical", 0) == 0:
            scenarios["window_dressing"] = True

    return scenarios


def _apply_scenario_overrides(penalty: int, scenarios: Dict[str, bool]) -> int:
    # Apply max-based overrides first (raise to at least X)
    for s, threshold in SCENARIO_MAX_OVERRIDES.items():
        if scenarios.get(s):
            penalty = max(penalty, threshold)

    # Additive overrides
    for s, add in SCENARIO_ADDITIVE_OVERRIDES.items():
        if scenarios.get(s):
            penalty += add

    return penalty


def _determine_score_cap(scenarios: Dict[str, bool]) -> Optional[int]:
    # print("Determining score cap from scenarios:", scenarios)
    caps = [cap for s, cap in SCENARIO_SCORE_CAPS.items() if scenarios.get(s)]
    # print("Score caps from scenarios:", caps)
    if not caps:
        # print("No applicable score caps from scenarios")
        return None
    # print("Applicable score caps from scenarios:", caps)
    return min(caps)


def _extract_top_critical_issues(flags: List[RedFlag], grouped_by_cat: Dict[str, List[RedFlag]]) -> List[Dict[str, Any]]:
    critical = [f for f in flags if f.severity.name == "CRITICAL"]
    # Sort by category priority then by presence

    def sort_key(f: RedFlag) -> Tuple[int, str]:
        try:
            idx = CATEGORY_PRIORITY.index(_map_flag_category(f))
        except Exception:
            idx = len(CATEGORY_PRIORITY)
        return (idx, f.module or "")

    critical_sorted = sorted(critical, key=sort_key)
    out = []
    # Limit to CATEGORY_PRIORITY_INDEX items for analyst readability
    for f in critical_sorted[:CATEGORY_PRIORITY_INDEX]:
        out.append({
            "module": f.module,
            "category": _map_flag_category(f),
            "title": f.title,
            "detail": f.detail,
        })
    return out


def aggregate_red_flags(payload: Dict[str, Any], generate_narrative: bool = True) -> Dict[str, Any]:
    """Main entry: accepts dict with `company_id` and `module_red_flags`.

    Returns a structured aggregation per the spec.

    Args:
        payload: Dict with company_id and module_red_flags
        generate_narrative: Whether to include LLM narrative (default True)
    """
    if not isinstance(payload, dict):
        raise AggregationError("Payload must be a dict")

    company_id = payload.get("company_id")
    module_red_flags = payload.get("module_red_flags")
    if company_id is None or module_red_flags is None:
        raise AggregationError(
            "Payload missing required keys: company_id and module_red_flags")

    # Validation layer: coerce and validate each flag
    validated: List[RedFlag] = []
    for module_key, flags in module_red_flags.items():
        if flags is None:
            continue
        if not isinstance(flags, list):
            raise AggregationError(
                f"Flags for module {module_key} must be a list")
        for raw in flags:
            raw2 = _ensure_module_on_raw(raw, module_key)
            try:
                vf = validate_and_coerce_flag(raw2)
            except ValidationError as e:
                raise AggregationError(
                    f"Invalid flag from module {module_key}: {e}")

            validated.append(vf)

    # Flattening done - validated contains all flags
    all_flags = validated
    counts = severity_counts(all_flags)

    # Baseline penalty
    penalty = (
        counts.get("critical", 0) * SEVERITY_WEIGHTS["CRITICAL"]
        + counts.get("red", 0) * SEVERITY_WEIGHTS["RED"]
        + counts.get("yellow", 0) * SEVERITY_WEIGHTS["YELLOW"]
    )

    # print("Baseline penalty:", penalty)

    # Category mapping and grouping
    # working capital, asset utilization, leverage, liquidity, earnings quality, governance_fraud
    grouped = _group_by_category(all_flags)

    # print("Grouped flags by category:", grouped)

    # Pattern detection
    category_risks = _apply_pattern_rules(grouped)
    print("Category risks after pattern detection:", category_risks)

    # Scenario detection: allow caller to provide explicit scenario signals
    explicit_signals = payload.get(
        "scenario_signals") if isinstance(payload, dict) else None
    scenarios = _detect_scenarios(
        grouped, counts, penalty, category_risks, explicit_signals)
    # print("Detected scenarios:", scenarios)

    # Scenario-based overrides
    penalty = _apply_scenario_overrides(penalty, scenarios)
    # print("Penalty after scenario overrides:", penalty)

    # Severity capping
    final_severity_score = min(penalty, MAX_SEVERITY_SCORE)
    # print("Final severity score:", final_severity_score)

    # Red Flag Index
    red_flag_index = final_severity_score

    # Score caps
    score_cap = _determine_score_cap(scenarios)
    # print("Determined score cap:", score_cap)

    # Critical issues
    top_critical_issues = _extract_top_critical_issues(all_flags, grouped)

    # Narrative (deterministic reporter; optional LLM wrapper)
    narrative = None
    if generate_narrative:
        try:
            narrative = llm.generate_narrative(
                company_id=company_id,
                flags=[f.to_dict() for f in all_flags],
                category_risks=category_risks,
                scenarios=scenarios,
                red_flag_index=red_flag_index,
            )
        except Exception:
            narrative = None

    output = {
        "company_id": company_id,
        "severity_score": final_severity_score,
        "red_flag_index": red_flag_index,
        "counts": counts,
        "category_risks": category_risks,
        "scenarios": scenarios,
        "score_cap": score_cap,
        "top_critical_issues": top_critical_issues,
        # "flags": [f.to_dict() for f in all_flags],
        "narrative": narrative,
    }

    return output
