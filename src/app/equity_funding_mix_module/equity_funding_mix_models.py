from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, root_validator


class YearFinancialInput(BaseModel):
    year: int
    share_capital: float = 0.0
    reserves_and_surplus: float = 0.0
    net_worth: float = 0.0
    pat: float = 0.0
    net_profit: int
    dividends_paid: float = 0.0
    free_cash_flow: Optional[float] = None
    new_share_issuance: Optional[float] = 0.0
    debt: float = 0.0
    revenue: Optional[float] = None


class IndustryBenchmarks(BaseModel):
    payout_normal: float
    payout_high: float
    roe_good: float
    roe_modest: float
    dilution_warning: float = 0.05


class EquityFundingInput(BaseModel):
    company: str
    industry_code: Optional[str] = "GENERAL"
    financials_5y: List[YearFinancialInput]
    industry_equity_benchmarks: IndustryBenchmarks

    @root_validator(skip_on_failure=True)
    def validate_financials(cls, values):
        financials = values.get("financials_5y") or []
        if len(financials) != 5:
            raise ValueError(
                "EquityFunding module requires exactly 5 years of financial data")
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


class EquityFundingOutput(BaseModel):
    module: str = Field(default="EquityFundingMix")
    company: str
    key_metrics: Dict[str, Any]
    trends: Dict[str, Any]
    analysis_narrative: List[str]
    red_flags: List[Dict[str, Any]]
    positive_points: List[str]
    rules: List[RuleResult]
