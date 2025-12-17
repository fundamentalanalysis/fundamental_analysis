# Configuration for Red Flag Aggregator
from typing import Dict, List, Callable, Any


# Severity weights (doctrine: severity meaning is fixed; weights are tunable)
SEVERITY_WEIGHTS: Dict[str, int] = {
    "GREEN": 0,
    "YELLOW": 5,
    "RED": 10,
    "CRITICAL": 20,
}


# Category taxonomy - exhaustive set of categories used by the system
CATEGORIES: List[str] = [
    "liquidity",
    "leverage",
    "earnings_quality",
    "working_capital",
    "governance_fraud",
    "asset_utilization",
]


# Preferred mapping: module name -> canonical category
# Downstream modules SHOULD set `risk_category` explicitly. If not provided,
# this table is used as the deterministic fallback (no text inference).
MODULE_CATEGORY_MAP: Dict[str, str] = {
    "borrowings": "leverage",
    "liquidity": "liquidity",
    "quality_of_earnings": "earnings_quality",
    "working_capital": "working_capital",
    "governance": "governance_fraud",
    "asset_quality": "asset_utilization",
    "asset_intangible_quality": "asset_utilization",
}


# Pattern detection rules per category. Each rule is a callable that receives
# a list of flags for the category and returns one of: "LOW","MEDIUM","HIGH","VERY_HIGH".
def _governance_rule(flags):
    for f in flags:
        if f.severity == f.severity.__class__.CRITICAL:
            return "VERY_HIGH"
    red_count = sum(1 for f in flags if f.severity.name == "RED")
    if red_count >= 2:
        return "HIGH"
    return "LOW"


def _working_capital_rule(flags):
    red_count = sum(1 for f in flags if f.severity.name == "RED")
    if red_count >= 3:
        return "HIGH"
    yellow_count = sum(1 for f in flags if f.severity.name == "YELLOW")
    if yellow_count >= 4:
        return "MEDIUM"
    return "LOW"


def _borrowings_rule(flags):
    red_count = sum(1 for f in flags if f.severity.name == "RED")
    critical = any(f.severity.name == "CRITICAL" for f in flags)
    if critical:
        return "VERY_HIGH"
    if red_count >= 2:
        return "VERY_HIGH"
    if red_count == 1:
        return "HIGH"
    return "LOW"


def _liquidity_rule(flags):
    critical = any(f.severity.name == "CRITICAL" for f in flags)
    red_count = sum(1 for f in flags if f.severity.name == "RED")
    if critical:
        return "VERY_HIGH"
    if red_count >= 3:
        return "HIGH"
    if red_count == 1:
        return "MEDIUM"
    return "LOW"


def _earnings_rule(flags):
    red_count = sum(1 for f in flags if f.severity.name == "RED")
    critical_count = sum(1 for f in flags if f.severity.name == "CRITICAL")
    # Treat criticals as at least as important as multiple red signals.
    if critical_count >= 1:
        return "HIGH"
    if red_count >= 2:
        return "HIGH"
    if red_count == 1:
        return "MEDIUM"
    return "LOW"


def _asset_util_rule(flags):
    red_count = sum(1 for f in flags if f.severity.name == "RED")
    if red_count >= 2:
        return "HIGH"
    return "LOW"


PATTERN_RULES: Dict[str, Callable[[List[Any]], str]] = {
    "governance_fraud": _governance_rule,
    "working_capital": _working_capital_rule,
    "leverage": _borrowings_rule,
    "liquidity": _liquidity_rule,
    "earnings_quality": _earnings_rule,
    "asset_utilization": _asset_util_rule,
}


# Scenario caps and overrides. Max-based overrides (set penalty to at least X)
# and additive overrides (increase penalty by X).
SCENARIO_MAX_OVERRIDES: Dict[str, int] = {
    "zombie": 60,
    "rpt_fraud": 70,
}

SCENARIO_ADDITIVE_OVERRIDES: Dict[str, int] = {
    "evergreening": 15,
    "asset_stripping": 20,
}


# Score caps applied to final ratings (lower number is stricter). When
# multiple caps apply, the lowest cap wins.
SCENARIO_SCORE_CAPS: Dict[str, int] = {
    "rpt_fraud": 30,
    "zombie": 40,
    "evergreening": 50,
}


# Hard cap for severity score
MAX_SEVERITY_SCORE = 100


# Category priority for listing critical issues (lower index = higher priority)
CATEGORY_PRIORITY = [
    "governance_fraud",
    "leverage",
    "working_capital",
    "earnings_quality",
    "asset_utilization",
    "liquidity",
]

CATEGORY_PRIORITY_INDEX = 10
