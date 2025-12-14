from dataclasses import dataclass
from typing import Optional


@dataclass
class EquityFundingRuleThresholds:
    payout_high: float = 0.50
    payout_normal: float = 0.30

    roe_good: float = 0.15
    roe_modest: float = 0.10

    dilution_warning: float = 0.05
    dilution_high: float = 0.10

    dividends_exceed_fcf_warning: float = 1.0
    high_dividend_to_pat: float = 1.0

    retained_earnings_decline_warning: float = 0.0

    leverage_rising_threshold: float = 0.10  # Debt CAGR > Equity CAGR +10%


@dataclass
class EquityFundingRuleConfig:
    generic: EquityFundingRuleThresholds


DEFAULT_RULE_CONFIG = EquityFundingRuleConfig(
    generic=EquityFundingRuleThresholds())


def load_rule_config(_: Optional[str] = None) -> EquityFundingRuleConfig:
    """
    Load rule thresholds for equity/funding mix. Placeholder for YAML/DB overrides.
    """
    return DEFAULT_RULE_CONFIG
