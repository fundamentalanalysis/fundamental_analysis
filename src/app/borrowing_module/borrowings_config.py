from dataclasses import dataclass
from typing import Optional


@dataclass
class BorrowingsRuleThresholds:
    high_de_ratio: float = 2.0
    very_high_de_ratio: float = 3.0
    high_debt_ebitda: float = 4.0
    critical_debt_ebitda: float = 6.0
    # ICR thresholds for 6-tier system
    icr_critical: float = 1.0  # < 1.0: CRITICAL
    icr_high_risk: float = 1.5  # 1.0-1.5: HIGH RISK
    icr_weak: float = 2.0  # 1.5-2.0: Weak
    icr_tight: float = 2.5  # 2.0-2.5: Tight but acceptable
    icr_comfortable: float = 4.0  # 2.5-4.0: Comfortable, >4.0: Very strong
    # Finance cost gap thresholds (percentage points)
    moderate_finance_gap: float = 2.0  # < 2%: GREEN, 2-7%: YELLOW
    high_finance_gap: float = 7.0  # > 7%: RED
    # Refinancing risk thresholds (short-term maturity ratio)
    low_st_maturity_pct: float = 0.30  # <= 0.30: GREEN
    moderate_st_maturity_pct: float = 0.50  # 0.30-0.50: YELLOW, >0.50: RED
    critical_st_maturity_pct: float = 0.70  # > 0.70: CRITICAL
    liquidity_buffer_threshold: float = 0.5  # Cash ratio threshold for risk downgrade
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

