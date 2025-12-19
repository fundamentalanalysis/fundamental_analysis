
# from dataclasses import dataclass, field


# @dataclass
# class ZombieRules:
#     ebit_interest_years: int = 2
#     cfo_interest_years: int = 2


# @dataclass
# class WindowDressingRules:
#     cash_spike_threshold: float = 0.30
#     profit_spike_threshold: float = 0.25
#     one_off_income_ratio: float = 0.20
#     receivable_drop_threshold: float = 0.10


# @dataclass
# class AssetStrippingRules:
#     fixed_asset_decline_years: int = 2
#     dividend_high_ratio: float = 0.50
#     net_debt_rising: bool = True


# @dataclass
# class EvergreeningRules:
#     rollover_ratio_critical: float = 0.50
#     principal_repayment_min: float = 0.10
#     interest_capitalized_ratio: float = 0.20


# @dataclass
# class CircularTradingRules:
#     receivables_spike_ratio: float = 0.25


# @dataclass
# class RiskRuleConfig:
#     zombie: ZombieRules = field(default_factory=ZombieRules)
#     window: WindowDressingRules = field(default_factory=WindowDressingRules)
#     asset: AssetStrippingRules = field(default_factory=AssetStrippingRules)
#     evergreen: EvergreeningRules = field(default_factory=EvergreeningRules)
#     circular: CircularTradingRules = field(default_factory=CircularTradingRules)


# def load_risk_config() -> RiskRuleConfig:
#     return RiskRuleConfig()


from dataclasses import dataclass, field


# =========================
# ZOMBIE COMPANY RULES
# =========================
@dataclass
class ZombieRules:
    ebit_interest_years: int = 2
    cfo_interest_years: int = 2


# =========================
# WINDOW DRESSING RULES
# =========================
@dataclass
class WindowDressingRules:
    cash_spike_threshold: float = 0.30          # >30% YoY cash spike
    profit_spike_threshold: float = 0.25        # >25% profit spike
    one_off_income_ratio: float = 0.20          # >20% of PAT
    receivable_drop_threshold: float = 0.10     # >10% receivable drop


# =========================
# ASSET STRIPPING RULES
# =========================
@dataclass
class AssetStrippingRules:
    fixed_asset_decline_years: int = 2           # ≥2 years decline
    dividend_high_ratio: float = 0.50            # Dividends / PAT
    net_debt_rising: bool = True
    rpt_assets_threshold: float = 0.10           # RPT / Assets


# =========================
# LOAN EVERGREENING RULES
# =========================
@dataclass
class EvergreeningRules:
    rollover_ratio_critical: float = 0.50        # >50% rollover
    principal_repayment_min: float = 0.10        # <10% ST debt
    interest_capitalized_ratio: float = 0.20     # >20% interest


# =========================
# CIRCULAR TRADING RULES
# =========================
@dataclass
class CircularTradingRules:
    receivables_spike_ratio: float = 0.25        # >25% YoY spike


# =========================
# MASTER CONFIG
# =========================
@dataclass
class RiskRuleConfig:
    zombie: ZombieRules = field(default_factory=ZombieRules)
    window: WindowDressingRules = field(default_factory=WindowDressingRules)
    asset: AssetStrippingRules = field(default_factory=AssetStrippingRules)
    evergreen: EvergreeningRules = field(default_factory=EvergreeningRules)
    circular: CircularTradingRules = field(default_factory=CircularTradingRules)


def load_risk_config() -> RiskRuleConfig:
    return RiskRuleConfig()
