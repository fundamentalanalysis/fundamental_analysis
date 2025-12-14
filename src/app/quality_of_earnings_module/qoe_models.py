from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, root_validator


# -----------------------------from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, root_validator


# -----------------------------
# Yearly QoE Input Structure
# -----------------------------
class QoEYearInput(BaseModel):
    year: int  # Same style as WC module

    # Raw Inputs
    cash_from_operating_activity: float = 0.0
    net_profit: float = 0.0
    working_capital_changes: float = 0.0

    Trade_receivables: float = 0.0
    revenue: float = 0.0
    total_assets: float = 0.0

    dso: Optional[float] = None
    other_income: float = 0.0




# -----------------------------
# Benchmark Levels for QoE
# -----------------------------
class QoEBenchmarks(BaseModel):
    qoe_red: float = 0.80
    qoe_green: float = 1.00

    accruals_warning: float = 0.10
    accruals_red: float = 0.20

    ocf_revenue_warning: float = 0.10
    ocf_revenue_red: float = 0.05

    dso_high: int = 80
    dso_rising_years: int = 3

    other_income_warning_ratio: float = 0.20


# -----------------------------
# Rule Result Object
# -----------------------------
class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    metric: Optional[str]
    year: Optional[Any]
    flag: str
    value: Optional[float]
    threshold: str
    reason: str

    def to_dict(self):
        return self.dict()


# -----------------------------
# Top-Level Financial Holder
# -----------------------------
class QoEFinancialData(BaseModel):
    financial_years: List[QoEYearInput]


# -----------------------------
# QoE Input Contract
# -----------------------------
class QualityOfEarningsInput(BaseModel):
    company: str
    industry_code: Optional[str] = None
    year: Optional[int] = None  # Not required but allowed

    financials_5y: QoEFinancialData
    benchmarks: Optional[QoEBenchmarks] = None

    @root_validator(skip_on_failure=True)
    def validate_financials(cls, values):
        financials = values.get("financials_5y")
        if financials:
            years = [f.year for f in financials.financial_years]
            if len(years) != len(set(years)):
                raise ValueError("Duplicate year detected in QoE financial_years")
        return values


# -----------------------------
# Output Schema
# -----------------------------
class QualityOfEarningsOutput(BaseModel):
    module: str = Field(default="Quality of Earnings")
    company: str

    key_metrics: Dict[str, Any]
    trends: Dict[str, Any]

    analysis_narrative: List[str] = []
    red_flags: List[Dict[str, Any]] = []
    positive_points: List[str] = []
    rules: List[RuleResult] = []
