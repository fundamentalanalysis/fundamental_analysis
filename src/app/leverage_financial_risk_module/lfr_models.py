from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, root_validator


# =========================================================
# 1. YEAR-LEVEL FINANCIAL INPUT
# =========================================================

class YearLeverageFinancialInput(BaseModel):
    year: int

    # -----------------------------
    # Balance Sheet
    # -----------------------------
    total_debt: float = 0.0
    short_term_debt: float = 0.0
    long_term_debt: float = 0.0
    equity: float = 0.0
    cash_and_equivalents: float = 0.0

    # -----------------------------
    # Profit & Loss
    # -----------------------------
    ebitda: float = 0.0
    ebit: float = 0.0
    interest_cost: float = 0.0

    # -----------------------------
    # Optional / Extended Fields
    # -----------------------------
    taxes: Optional[float] = None
    operating_cash_flow: Optional[float] = None


# =========================================================
# 2. BENCHMARKS (INDUSTRY / YAML DRIVEN)
# =========================================================

class LeverageFinancialBenchmarks(BaseModel):
    # Debt-to-Equity
    de_ratio_high: float = 2.0
    de_ratio_critical: float = 3.0

    # Debt-to-EBITDA
    debt_ebitda_high: float = 4.0
    debt_ebitda_critical: float = 5.0

    # Net Debt / EBITDA (Fitch / S&P style)
    net_debt_ebitda_warning: float = 4.0
    net_debt_ebitda_critical: float = 5.5

    # Interest Coverage
    icr_low: float = 2.0
    icr_critical: float = 1.0

    # Short-term debt dependency
    st_debt_ratio_warning: float = 0.40
    st_debt_ratio_critical: float = 0.50

    # Trend rules
    leverage_rising_years: int = 3


# =========================================================
# 3. RULE RESULT (IDENTICAL STRUCTURE TO WC MODULE)
# =========================================================

class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    metric: Optional[str]
    year: Optional[Any]  # int or "Latest"
    flag: str  # GREEN | YELLOW | RED | CRITICAL
    value: Optional[float]
    threshold: str
    reason: str

    def to_dict(self):
        return self.dict()


# =========================================================
# 4. FINANCIAL DATA CONTAINER (5Y SERIES)
# =========================================================

class LeverageFinancialData(BaseModel):
    financial_years: List[YearLeverageFinancialInput]


# =========================================================
# 5. MODULE INPUT (ORCHESTRATOR CONTRACT)
# =========================================================

class LeverageFinancialRiskInput(BaseModel):
    company: str
    industry_code: Optional[str] = None
    year: Optional[int] = None

    financial_data: LeverageFinancialData
    benchmarks: Optional[LeverageFinancialBenchmarks] = None

    # Cross-module dependency (Debt, Liquidity, WC, QoE, etc.)
    module_red_flags: Dict[str, List[Dict[str, Any]]] = {}

    @root_validator(skip_on_failure=True)
    def validate_financial_years(cls, values):
        financial_data = values.get("financial_data")
        if financial_data:
            years = [f.year for f in financial_data.financial_years]
            if len(years) != len(set(years)):
                raise ValueError("Duplicate year detected in financial_years")
        return values


# =========================================================
# 6. MODULE OUTPUT SCHEMA
# =========================================================

class LeverageFinancialRiskOutput(BaseModel):
    module: str = Field(default="Leverage & Financial Risk")
    company: str

    key_metrics: Dict[str, Any]
    trends: Dict[str, Any]

    analysis_narrative: List[str] = []
    red_flags: List[Dict[str, Any]] = []
    positive_points: List[str] = []

    rules: List[RuleResult]
