from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, root_validator, validator


# ======================================================
# 1. YEARLY FINANCIAL INPUT MODEL
# ======================================================

class YearAssetIntangibleInput(BaseModel):
    year: int

    # Tangible assets
    gross_block: float = 0.0
    accumulated_depreciation: float = 0.0
    net_block: Optional[float] = None
    cwip: Optional[float] = 0.0

    # Intangibles
    intangible_assets: float = 0.0
    goodwill: Optional[float] = None

    # Amortization
    intangible_amortization: Optional[float] = None

    # R&D
    r_and_d_expense: Optional[float] = None

    # Revenue
    revenue: float = 0.0

    # Total Assets
    total_assets: float = 0.0

    # Optional P&L numeric fields
    depreciation: Optional[float] = None
    capex: Optional[float] = None
    operating_cash_flow: Optional[float] = None

    # Cost Structure (PERCENTAGES AS STRINGS IN YOUR INPUT)
    material_cost: Optional[float] = None
    manufacturing_cost: Optional[float] = None
    employee_cost: Optional[float] = None
    other_cost: Optional[float] = None

    # Impairment
    impairment_loss: Optional[float] = None

    # -------------------------------
    # Validators
    # -------------------------------

    @validator("material_cost", "manufacturing_cost", "employee_cost", "other_cost", pre=True)
    def parse_percentage_fields(cls, value):
        """
        Accepts:
        - 32.97
        - "32.97"
        - "32.97%"
        Converts all to float.
        """
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            return float(value.replace("%", "").strip())

        raise ValueError("Invalid percentage format")

    @root_validator(skip_on_failure=True)
    def compute_net_block(cls, values):
        """
        net_block = gross_block - accumulated_depreciation
        """
        gb = values.get("gross_block")
        ad = values.get("accumulated_depreciation")
        nb = values.get("net_block")

        if nb is None and gb is not None and ad is not None:
            values["net_block"] = gb - ad

        return values


# ======================================================
# 2. FINANCIAL DATA BLOCK (MATCHES YOUR JSON)
# ======================================================

class FinancialDataBlock(BaseModel):
    financial_years: List[YearAssetIntangibleInput]

    @root_validator(skip_on_failure=True)
    def validate_years_unique(cls, values):
        years = [y.year for y in values.get("financial_years", [])]
        if len(years) != len(set(years)):
            raise ValueError("Duplicate year detected in financial_years")
        return values


# ======================================================
# 3. BENCHMARKS
# ======================================================

class AssetIntangibleBenchmarks(BaseModel):
    asset_turnover_low: float = 1.0
    asset_turnover_critical: float = 0.7

    age_proxy_old_threshold: float = 0.60
    age_proxy_critical: float = 0.75

    goodwill_pct_warning: float = 0.25
    goodwill_pct_critical: float = 0.40

    impairment_high_threshold: float = 0.05
    impairment_sudden_spike_threshold: float = 0.30

    intangible_growth_vs_revenue_warning: float = 0.10


# ======================================================
# 4. RULE RESULT MODEL
# ======================================================

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


# ======================================================
# 5. MAIN INPUT MODEL
# ======================================================

class AssetIntangibleInput(BaseModel):
    company: str
    financial_data: FinancialDataBlock
    benchmarks: Optional[AssetIntangibleBenchmarks] = None


# ======================================================
# 6. MODULE OUTPUT
# ======================================================

class AssetIntangibleOutput(BaseModel):
    module: str = Field(default="Asset & Intangible Quality Module")
    company: str
    key_metrics: Dict[str, Any]
    trends: Dict[str, Any]
    analysis_narrative: List[str] = []
    red_flags: List[Dict[str, Any]] = []
    positive_points: List[str] = []
    rules: List[RuleResult] = []
