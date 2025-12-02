from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, root_validator

class AssetFinancialYearInput(BaseModel):
    year: int
    net_block: Optional[float] = 0.0
    accumulated_depreciation: Optional[float] = 0.0
    gross_block: Optional[float] = 0.0
    impairment_loss: Optional[float] = 0.0
    cwip: Optional[float] = 0.0
    intangibles: Optional[float] = 0.0
    goodwill: Optional[float] = 0.0
    revenue: Optional[float] = 0.0
    intangible_amortization: Optional[float] = 0.0
    r_and_d_expenses: Optional[float] = 0.0

class IndustryAssetBenchmarks(BaseModel):
    asset_turnover_low: float = 1.0
    asset_turnover_critical: float = 0.7
    goodwill_pct_warning: float = 0.25
    goodwill_pct_critical: float = 0.40
    impairment_high_threshold: float = 0.05
    age_proxy_old_threshold: float = 0.60
    age_proxy_critical: float = 0.75

class AssetQualityInput(BaseModel):
    company_id: str
    industry_code: str
    financials_5y: List[AssetFinancialYearInput]
    industry_asset_quality_benchmarks: IndustryAssetBenchmarks

    @root_validator(skip_on_failure=True)
    def validate_financials(cls, values):
        financials = values.get("financials_5y") or []
        if len(financials) != 5:
            raise ValueError("Asset Quality module requires exactly 5 years of financial data")
        years = sorted([f.year for f in financials])
        if years != sorted(set(years)):
            raise ValueError("Duplicate year detected in financials_5y")
        return values

class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    value: Optional[float]
    threshold: str
    flag: str
    reason: str

class AssetQualityOutput(BaseModel):
    module: str = Field(default="AssetIntangibleQuality")
    sub_score_adjusted: int
    analysis_narrative: List[str]
    red_flags: List[Dict[str, Any]]
    positive_points: List[str]
    rules: List[RuleResult]
