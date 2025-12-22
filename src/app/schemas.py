# =============================================================
# schemas.py - Pydantic Models for API Request/Response
# =============================================================

from typing import Optional, List, Dict, Any

try:
    from pydantic import BaseModel, field_validator
    _HAS_FIELD_VALIDATOR = True
except ImportError:  # Pydantic v1 fallback
    from pydantic import BaseModel, validator
    _HAS_FIELD_VALIDATOR = False


def _parse_percent_float(value: Any) -> Any:
    if value is None:
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned == "":
            return None
        if cleaned.endswith("%"):
            cleaned = cleaned[:-1].strip()
        cleaned = cleaned.replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return value
    return value


# ---------------------------------------------------------
# INPUT SCHEMAS
# ---------------------------------------------------------

class FinancialYearInput(BaseModel):
    """Comprehensive financial year data supporting all 12 modules."""
    year: int  # Required - the fiscal year
    
    # === BALANCE SHEET - EQUITY & CAPITAL ===
    equity_capital: Optional[float] = None
    total_equity: Optional[float] = None
    reserves: Optional[float] = None
    preference_capital: Optional[float] = None
    
    # === BALANCE SHEET - BORROWINGS & LIABILITIES ===
    borrowings: Optional[float] = None
    short_term_debt: Optional[float] = None
    long_term_debt: Optional[float] = None
    lease_liabilities: Optional[float] = None
    other_borrowings: Optional[float] = None
    trade_payables: Optional[float] = None
    advance_from_customers: Optional[float] = None
    other_liability_items: Optional[float] = None
    
    # === BALANCE SHEET - ASSETS ===
    trade_receivables: Optional[float] = None
    inventories: Optional[float] = None
    cash_equivalents: Optional[float] = None
    loans_n_advances: Optional[float] = None
    other_asset_items: Optional[float] = None
    
    # === FIXED ASSETS ===
    gross_block: Optional[float] = None
    accumulated_depreciation: Optional[float] = None
    fixed_assets: Optional[float] = None
    intangible_assets: Optional[float] = None
    investments: Optional[float] = None
    cwip: Optional[float] = None
    total_assets: Optional[float] = None
    
    # === INCOME STATEMENT ===
    revenue: Optional[float] = None
    expenses: Optional[float] = None
    material_cost: Optional[float] = None  # Stored as percentage value (e.g., 32.97 for 32.97%)
    manufacturing_cost: Optional[float] = None  # Stored as percentage value
    employee_cost: Optional[float] = None  # Stored as percentage value
    other_cost: Optional[float] = None  # Stored as percentage value
    operating_profit: Optional[float] = None
    interest: Optional[float] = None
    depreciation: Optional[float] = None
    profit_before_tax: Optional[float] = None
    tax: Optional[float] = None  # Stored as percentage value (e.g., 19 for 19%)
    net_profit: Optional[float] = None
    other_income: Optional[float] = None
    
    # === CASH FLOW STATEMENT ===
    profit_from_operations: Optional[float] = None
    working_capital_changes: Optional[float] = None
    direct_taxes: Optional[float] = None
    interest_paid_fin: Optional[float] = None
    cash_from_operating_activity: Optional[float] = None
    fixed_assets_purchased: Optional[float] = None
    dividends_paid: Optional[float] = None
    proceeds_from_shares: Optional[float] = None
    proceeds_from_borrowings: Optional[float] = None
    repayment_of_borrowings: Optional[float] = None
    
    # === RELATED PARTY TRANSACTIONS ===
    related_party_sales: Optional[float] = None
    related_party_receivables: Optional[float] = None

    if _HAS_FIELD_VALIDATOR:
        @field_validator(
            "material_cost",
            "manufacturing_cost",
            "employee_cost",
            "other_cost",
            "tax",
            mode="before",
        )
        def _parse_percent_fields(cls, value: Any) -> Any:
            return _parse_percent_float(value)
    else:
        @validator(
            "material_cost",
            "manufacturing_cost",
            "employee_cost",
            "other_cost",
            "tax",
            pre=True,
        )
        def _parse_percent_fields(cls, value: Any) -> Any:
            return _parse_percent_float(value)


class FinancialData(BaseModel):
    """Container for multiple financial years"""
    financial_years: List[FinancialYearInput]


class AnalyzeRequest(BaseModel):
    """Request model for analysis endpoint"""
    company: str
    financial_data: FinancialData
    modules: Optional[List[str]] = None  # Optional: specify which modules to run
    generate_narrative: bool = True  # Whether to generate LLM narratives
    year: Optional[int] = None  # Current financial year for analysis (e.g., 2024)


# ---------------------------------------------------------
# OUTPUT SCHEMAS
# ---------------------------------------------------------

class RuleResult(BaseModel):
    """Result of a single rule evaluation"""
    rule_id: str
    description: str
    passed: bool
    score: int
    details: Optional[str] = None


class TrendResult(BaseModel):
    """Result of a trend analysis"""
    metric: str
    direction: str  # "increasing", "decreasing", "stable"
    change_percent: Optional[float] = None
    assessment: str


class ModuleResult(BaseModel):
    """Result from a single module analysis"""
    module: str
    score: int
    max_score: int
    metrics: Dict[str, Any]
    rules: List[RuleResult]
    trends: List[TrendResult]
    narrative: Optional[str] = None
    flags: List[str] = []


class AnalyzeResponse(BaseModel):
    """Complete response from analysis endpoint"""
    company: str
    modules_analyzed: List[str]
    results: List[ModuleResult]
    yoy_growth: Optional[Dict[str, Dict[str, Optional[float]]]] = None  # metric_name -> {year: growth%}
    overall_score: Optional[int] = None
    summary: Optional[str] = None
