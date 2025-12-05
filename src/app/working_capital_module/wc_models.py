
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, root_validator


class YearFinancialInput(BaseModel):
    year: str  # Changed to str to accept "Mar 2024" format
    trade_receivables: float = 0.0
    trade_payables: float = 0.0
    inventory: float = 0.0
    revenue: float = 0.0
    cogs: float = 0.0
    
    # Optional fields that might be used for broader context or derived metrics
    short_term_debt: Optional[float] = None
    long_term_debt: Optional[float] = None
    total_equity: Optional[float] = None
    ebitda: Optional[float] = None
    ebit: Optional[float] = None
    finance_cost: Optional[float] = None
    capex: Optional[float] = None
    cwip: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    
    total_debt_maturing_lt_1y: Optional[float] = None
    total_debt_maturing_1_3y: Optional[float] = None
    total_debt_maturing_gt_3y: Optional[float] = None
    weighted_avg_interest_rate: Optional[float] = None
    floating_rate_debt: Optional[float] = None
    fixed_rate_debt: Optional[float] = None


class WorkingCapitalBenchmarks(BaseModel):
    critical_ccc: int = 180
    moderate_ccc: int = 120

    dso_high: int = 75
    dso_moderate: int = 60

    dio_high: int = 120
    dio_moderate: int = 90

    dpo_high: int = 90
    dpo_low: int = 30

    nwc_revenue_critical_ratio: float = 0.25
    nwc_revenue_moderate_ratio: float = 0.15

    receivable_growth_threshold: float = 0.20
    inventory_growth_threshold: float = 0.20


class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    metric: Optional[str]
    year: Optional[Any] # Can be int or string like "Latest"
    flag: str
    value: Optional[float]
    threshold: str
    reason: str
    
    def to_dict(self):
        return self.dict()


class FinancialData(BaseModel):
    financial_years: List[YearFinancialInput]


class WorkingCapitalInput(BaseModel):
    company: str
    year: Optional[int] = None  # Top level year field
    financial_data: FinancialData  # Nested structure
    benchmarks: Optional[WorkingCapitalBenchmarks] = None

    @root_validator(skip_on_failure=True)
    def validate_financials(cls, values):
        financial_data = values.get("financial_data")
        if financial_data:
            financials = financial_data.financial_years
            # Ensure years are unique
            years = [f.year for f in financials]
            if len(years) != len(set(years)):
                raise ValueError("Duplicate year detected in financial_years")
        return values


class WorkingCapitalOutput(BaseModel):
    module: str = Field(default="Working Capital")
    company: str
    key_metrics: Dict[str, Any]
    trends: Dict[str, Any]
    analysis_narrative: List[str] = []
    red_flags: List[Dict[str, Any]] = []
    positive_points: List[str] = []
    rules: List[RuleResult]
