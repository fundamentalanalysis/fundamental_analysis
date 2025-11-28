from dataclasses import dataclass
from typing import Optional


@dataclass
class BorrowingsRuleThresholds:
    high_de_ratio: float = 2.0
    very_high_de_ratio: float = 3.0
    high_debt_ebitda: float = 4.0
    critical_debt_ebitda: float = 6.0
    low_icr: float = 2.0
    critical_icr: float = 1.0
    risky_st_debt_share: float = 0.5
    risky_debt_lt_1y_pct: float = 0.5
    high_floating_share: float = 0.6
    high_wacd: float = 0.12
    high_debt_cagr_vs_ebitda_gap: float = 0.10
    high_fin_cost_yoy: float = 0.25
    covenant_buffer_pct: float = 0.10


@dataclass
class BorrowingsRuleConfig:
    generic: BorrowingsRuleThresholds


DEFAULT_RULE_CONFIG = BorrowingsRuleConfig(generic=BorrowingsRuleThresholds())


def load_rule_config(_: Optional[str] = None) -> BorrowingsRuleConfig:
    """
    Placeholder for industry-specific overrides. Accepts industry_code but
    currently returns the generic configuration. Extend to load from YAML/DB.
    """
    return DEFAULT_RULE_CONFIG
from dataclasses import dataclass
from typing import Optional


@dataclass
class BorrowingsRuleThresholds:
    high_de_ratio: float = 2.0
    very_high_de_ratio: float = 3.0
    high_debt_ebitda: float = 4.0
    critical_debt_ebitda: float = 6.0
    low_icr: float = 2.0
    critical_icr: float = 1.0
    risky_st_debt_share: float = 0.5
    risky_debt_lt_1y_pct: float = 0.5
    high_floating_share: float = 0.6
    high_wacd: float = 0.12
    high_debt_cagr_vs_ebitda_gap: float = 0.10
    high_fin_cost_yoy: float = 0.25
    covenant_buffer_pct: float = 0.10


@dataclass
class BorrowingsRuleConfig:
    generic: BorrowingsRuleThresholds


DEFAULT_RULE_CONFIG = BorrowingsRuleConfig(generic=BorrowingsRuleThresholds())


def load_rule_config(_: Optional[str] = None) -> BorrowingsRuleConfig:
    """
    Placeholder for industry-specific overrides.
    Currently returns the generic configuration but can be extended
    to fetch YAML / DB-backed thresholds keyed by industry_code.
    """
    return DEFAULT_RULE_CONFIG

