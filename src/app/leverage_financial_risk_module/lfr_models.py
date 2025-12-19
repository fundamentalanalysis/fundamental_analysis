
# # lfr_models.py
# from typing import List, Optional, Dict, Any
# from pydantic import BaseModel, Field, model_validator


# class YearLeverageInput(BaseModel):
#     year: int

#     # ------------------------
#     # Balance Sheet
#     # ------------------------
#     borrowings: float = 0.0
#     short_term_debt: float = 0.0
#     cash_equivalents: float = 0.0

#     equity_capital: float = 0.0
#     reserves: float = 0.0

#     # ------------------------
#     # P&L
#     # ------------------------
#     operating_profit: float = 0.0  # EBIT
#     depreciation: float = 0.0
#     interest: float = 0.0

#     profit_before_tax: float = 0.0
#     tax: str | None = None  # e.g. "19%"

#     # ------------------------
#     # Cash Flow
#     # ------------------------
#     direct_taxes: float = 0.0

#     # ------------------------
#     # DERIVED (computed)
#     # ------------------------
#     equity: float = 0.0
#     ebitda: float = 0.0
#     tax_amount: float = 0.0
#     ffo: float = 0.0

#     @model_validator(mode="after")
#     def compute_derived_fields(self):
#         # Equity
#         self.equity = self.equity_capital + self.reserves

#         # EBITDA
#         self.ebitda = self.operating_profit + self.depreciation

#         # Tax % → amount
#         if self.tax and isinstance(self.tax, str) and "%" in self.tax:
#             try:
#                 tax_pct = float(self.tax.replace("%", "").strip())
#                 self.tax_amount = self.profit_before_tax * tax_pct / 100
#             except ValueError:
#                 self.tax_amount = 0.0
#         else:
#             self.tax_amount = self.direct_taxes or 0.0

#         # FFO (Fitch / S&P style)
#         self.ffo = self.ebitda - self.interest - self.tax_amount

#         return self



# # ======================================================
# # BENCHMARKS
# # ======================================================
# class LeverageBenchmarks(BaseModel):
#     de_ratio_high: float = 2.0
#     de_ratio_critical: float = 3.0

#     debt_ebitda_high: float = 4.0
#     debt_ebitda_critical: float = 5.0

#     net_debt_ebitda_warning: float = 4.0
#     net_debt_ebitda_critical: float = 5.5

#     icr_low: float = 2.0
#     icr_critical: float = 1.0

#     st_debt_ratio_warning: float = 0.40
#     st_debt_ratio_critical: float = 0.50


# # ======================================================
# # RULE OUTPUT
# # ======================================================
# class RuleResult(BaseModel):
#     rule_id: str
#     rule_name: str
#     metric: Optional[str]
#     year: Optional[Any]
#     flag: str
#     value: Optional[float]
#     threshold: str
#     reason: str


# # ======================================================
# # FINAL MODULE OUTPUT  ✅ THIS FIXES YOUR ERROR
# # ======================================================
# class LeverageFinancialRiskOutput(BaseModel):
#     module: str = Field(default="LeverageFinancialRisk")
#     company: str
#     key_metrics: Dict[str, Any]
#     trends: Dict[str, Any]
#     analysis_narrative: List[str] = []
#     red_flags: List[Dict[str, Any]] = []
#     positive_points: List[str] = []
#     rules: List[RuleResult] = []


# lfr_models.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator


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
    tax: str | None = None  # e.g. "19%"

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

    @model_validator(mode="after")
    def compute_derived_fields(self):
        self.equity = self.equity_capital + self.reserves
        self.ebitda = self.operating_profit + self.depreciation

        if self.tax and isinstance(self.tax, str) and "%" in self.tax:
            try:
                tax_pct = float(self.tax.replace("%", "").strip())
                self.tax_amount = self.profit_before_tax * tax_pct / 100
            except ValueError:
                self.tax_amount = 0.0
        else:
            self.tax_amount = self.direct_taxes or 0.0

        self.ffo = self.ebitda - self.interest - self.tax_amount
        return self


# ======================================================
# BENCHMARKS
# ======================================================
class LeverageBenchmarks(BaseModel):
    de_ratio_high: float = 2.0
    de_ratio_critical: float = 3.0

    debt_ebitda_high: float = 4.0
    debt_ebitda_critical: float = 5.0

    net_debt_ebitda_warning: float = 4.0
    net_debt_ebitda_critical: float = 5.5

    icr_low: float = 2.0
    icr_critical: float = 1.0

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
    value: Optional[Any]   # ✅ FIXED
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
