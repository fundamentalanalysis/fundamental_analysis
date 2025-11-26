# src/app/borrowing_module/debt_models.py

from typing import List, Optional
from pydantic import BaseModel



class YearFinancialInput(BaseModel):
    year: int
    short_term_debt: float = 0
    long_term_debt: float = 0
    total_equity: float = 0
    ebitda: float = 0
    ebit: float = 0
    finance_cost: float = 0
    capex: float = 0
    cwip: float = 0
    revenue: float = 0

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
    # midd: Optional[dict] = None


class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    flag: str
    value: float
    threshold: str
    reason: str


class BorrowingsOutput(BaseModel):
    module: str
    sub_score_adjusted: int
    analysis_narrative: List[str]
    red_flags: List[dict]
    positive_points: List[str]
    rule_results: List[RuleResult]
    metrics: dict