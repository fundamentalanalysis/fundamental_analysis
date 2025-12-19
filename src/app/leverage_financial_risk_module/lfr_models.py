
# lfr_models.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, root_validator


# ======================================================
# INPUT MODEL
# ======================================================
class YearLeverageInput(BaseModel):
    year: int

    # ------------------------
    # Balance Sheet
    # ------------------------
    borrowings: float = 0.0
    short_term_debt: float = 0.0
    cash_equivalents: float = 0.0

    equity_capital: float = 0.0
    reserves: float = 0.0

    # ------------------------
    # P&L
    # ------------------------
    operating_profit: float = 0.0  # EBIT
    depreciation: float = 0.0
    interest: float = 0.0

    profit_before_tax: float = 0.0
    tax: Optional[str] = None  # e.g. "19%"

    # ------------------------
    # Cash Flow
    # ------------------------
    direct_taxes: float = 0.0

    # ------------------------
    # DERIVED (computed)
    # ------------------------
    equity: float = 0.0
    ebitda: float = 0.0
    tax_amount: float = 0.0
    ffo: float = 0.0

    @root_validator(pre=False, skip_on_failure=True)
    def compute_derived_fields(cls, values):
        equity_capital = values.get("equity_capital", 0.0)
        reserves = values.get("reserves", 0.0)
        operating_profit = values.get("operating_profit", 0.0)
        depreciation = values.get("depreciation", 0.0)
        interest = values.get("interest", 0.0)
        profit_before_tax = values.get("profit_before_tax", 0.0)
        tax = values.get("tax")
        direct_taxes = values.get("direct_taxes", 0.0)

        # Equity
        values["equity"] = equity_capital + reserves

        # EBITDA
        values["ebitda"] = operating_profit + depreciation

        # Tax amount
        tax_amount = 0.0
        if isinstance(tax, str) and "%" in tax:
            try:
                tax_pct = float(tax.replace("%", "").strip())
                tax_amount = profit_before_tax * tax_pct / 100
            except ValueError:
                tax_amount = 0.0
        else:
            tax_amount = direct_taxes or 0.0

        values["tax_amount"] = tax_amount

        # Funds From Operations (FFO)
        values["ffo"] = values["ebitda"] - interest - tax_amount

        return values


# ======================================================
# BENCHMARKS
# ======================================================
class LeverageBenchmarks(BaseModel):
    # Debt / Equity
    de_ratio_high: float = 2.0
    de_ratio_critical: float = 3.0

    # Debt / EBITDA
    debt_ebitda_high: float = 4.0
    debt_ebitda_critical: float = 5.0

    # Net Debt / EBITDA
    net_debt_ebitda_warning: float = 4.0
    net_debt_ebitda_critical: float = 5.5

    # Interest Coverage
    icr_low: float = 2.0
    icr_critical: float = 1.0

    # Short-term debt ratio
    st_debt_ratio_warning: float = 0.40
    st_debt_ratio_critical: float = 0.50


# ======================================================
# RULE OUTPUT
# ======================================================
class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    metric: Optional[str]
    year: Optional[Any]
    flag: str
    value: Optional[Any]
    threshold: str
    reason: str


# ======================================================
# FINAL MODULE OUTPUT
# ======================================================
class LeverageFinancialRiskOutput(BaseModel):
    module: str = Field(default="LeverageFinancialRisk")
    company: str
    key_metrics: Dict[str, Any]
    trends: Dict[str, Any]
    analysis_narrative: List[str] = []
    red_flags: List[Dict[str, Any]] = []
    positive_points: List[str] = []
    rules: List[RuleResult] = []
