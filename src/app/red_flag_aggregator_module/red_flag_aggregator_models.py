from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Severity(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"
    CRITICAL = "CRITICAL"


class RiskCategory(str, Enum):
    """Canonical risk categories. Every red flag MUST belong to exactly one."""
    LIQUIDITY = "liquidity"
    LEVERAGE = "leverage"
    EARNINGS_QUALITY = "earnings_quality"
    WORKING_CAPITAL = "working_capital"
    GOVERNANCE_FRAUD = "governance_fraud"
    ASSET_UTILIZATION = "asset_utilization"


@dataclass
class RedFlag:
    module: str
    severity: Severity
    title: str
    detail: str
    risk_category: str  # REQUIRED: must be one of RiskCategory values
    metric: Optional[str] = None
    value: Optional[Any] = None
    threshold: Optional[Any] = None
    period: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module": self.module,
            "severity": self.severity.value,
            "title": self.title,
            "detail": self.detail,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "period": self.period,
            "risk_category": self.risk_category,
            **(self.extra or {}),
        }


class ValidationError(ValueError):
    pass


def validate_and_coerce_flag(raw: Dict[str, Any]) -> RedFlag:
    """Validate an incoming flag dict and return a `RedFlag`.

    Required fields: module, severity, title, detail, risk_category
    Severity must be one of the `Severity` enum values.
    RiskCategory must be one of the canonical RiskCategory enum values.
    Optional: metric, value, threshold, period
    """
    if not isinstance(raw, dict):
        raise ValidationError("Red flag must be an object/dict")

    missing = [f for f in ("module", "severity", "title", "detail", "risk_category")
               if f not in raw or raw[f] is None]
    if missing:
        raise ValidationError(f"Missing required red-flag fields: {missing}")

    try:
        sev = Severity(raw["severity"])
    except Exception:
        raise ValidationError(f"Unknown severity: {raw.get('severity')}")

    # Validate risk_category against canonical enum
    try:
        risk_cat = RiskCategory(raw["risk_category"])
    except Exception:
        valid_categories = [c.value for c in RiskCategory]
        raise ValidationError(
            f"Unknown risk_category: {raw.get('risk_category')}. "
            f"Must be one of: {', '.join(valid_categories)}"
        )

    rf = RedFlag(
        module=str(raw["module"]),
        severity=sev,
        title=str(raw["title"]),
        detail=str(raw["detail"]),
        risk_category=risk_cat.value,
        metric=raw.get("metric"),
        value=raw.get("value"),
        threshold=raw.get("threshold"),
        period=raw.get("period"),
        extra={k: v for k, v in raw.items() if k not in {"module", "severity", "title",
                                                         "detail", "metric", "value", "threshold", "period", "risk_category"}},
    )

    return rf


def severity_counts(flags: List[RedFlag]) -> Dict[str, int]:
    counts = {"critical": 0, "red": 0, "yellow": 0}
    for f in flags:
        if f.severity == Severity.CRITICAL:
            counts["critical"] += 1
        elif f.severity == Severity.RED:
            counts["red"] += 1
        elif f.severity == Severity.YELLOW:
            counts["yellow"] += 1
    return counts
