from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, root_validator


class YearFinancialInput(BaseModel):
    year: int
    short_term_debt: float = 0.0
    long_term_debt: float = 0.0
    total_equity: float = 0.0
    ebitda: float = 0.0
    ebit: float = 0.0
    finance_cost: float = 0.0
    capex: float = 0.0
    cwip: float = 0.0
    revenue: float = 0.0
    operating_cash_flow: float = 0.0

    total_debt_maturing_lt_1y: Optional[float] = None
    total_debt_maturing_1_3y: Optional[float] = None
    total_debt_maturing_gt_3y: Optional[float] = None

    weighted_avg_interest_rate: Optional[float] = None
    floating_rate_debt: Optional[float] = None
    fixed_rate_debt: Optional[float] = None


class IndustryBenchmarks(BaseModel):
    target_de_ratio: float
    max_safe_de_ratio: float
    max_safe_debt_ebitda: float
    min_safe_icr: float
    high_floating_share: Optional[float] = 0.6
    high_wacd: Optional[float] = 0.12


class CovenantLimits(BaseModel):
    de_ratio_limit: float
    icr_limit: float
    debt_ebitda_limit: float


class BorrowingsInput(BaseModel):
    company_id: str
    industry_code: str
    financials_5y: List[YearFinancialInput]
    industry_benchmarks: IndustryBenchmarks
    covenant_limits: CovenantLimits

    @root_validator(skip_on_failure=True)
    def validate_financials(cls, values):
        financials = values.get("financials_5y") or []
        if len(financials) != 5:
            raise ValueError("Borrowings module requires exactly 5 years of financial data")
        years = sorted([f.year for f in financials])
        if years != sorted(set(years)):
            raise ValueError("Duplicate year detected in financials_5y")
        return values


class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    metric: Optional[str]
    year: Optional[int]
    flag: str
    value: Optional[float]
    threshold: str
    reason: str


class BorrowingsOutput(BaseModel):
    module: str = Field(default="Borrowings")
    company: str
    key_metrics: Dict[str, Any]
    trends: Dict[str, Any]
    analysis_narrative: List[str]
    red_flags: List[Dict[str, Any]]
    positive_points: List[str]
    rules: List[RuleResult]
    metrics: Dict[str, Dict[str, Any]]