from dataclasses import dataclass, field


@dataclass
class ZombieRules:
    ebit_interest_years: int = 2
    cfo_interest_years: int = 2


@dataclass
class WindowDressingRules:
    cash_spike_threshold: float = 0.30
    profit_spike_threshold: float = 0.25
    one_off_income_ratio: float = 0.20


@dataclass
class AssetStrippingRules:
    fixed_asset_decline_years: int = 2
    dividend_high_ratio: float = 0.50
    net_debt_rising: bool = True


@dataclass
class EvergreeningRules:
    rollover_ratio_critical: float = 0.50
    principal_repayment_min: float = 0.10
    interest_capitalized_ratio: float = 0.20


@dataclass
class CircularTradingRules:
    receivables_spike_ratio: float = 0.25


@dataclass
class RiskRuleConfig:
    zombie: ZombieRules = field(default_factory=ZombieRules)
    window: WindowDressingRules = field(default_factory=WindowDressingRules)
    asset: AssetStrippingRules = field(default_factory=AssetStrippingRules)
    evergreen: EvergreeningRules = field(default_factory=EvergreeningRules)
    circular: CircularTradingRules = field(default_factory=CircularTradingRules)


def load_risk_config() -> RiskRuleConfig:
    return RiskRuleConfig()
