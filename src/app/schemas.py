# =============================================================
# schemas.py - Pydantic Models for API Request/Response
# =============================================================

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


# ---------------------------------------------------------
# INPUT SCHEMAS
# ---------------------------------------------------------

class FinancialYearInput(BaseModel):
    """Comprehensive financial year data supporting all 12 modules.
    Most fields are Optional since input schema is not finalized."""
    year: int  # Required - the fiscal year
    
    # === BORROWINGS MODULE ===
    short_term_debt: Optional[float] = None
    long_term_debt: Optional[float] = None
    total_equity: Optional[float] = None
    revenue: Optional[float] = None
    ebitda: Optional[float] = None
    ebit: Optional[float] = None
    finance_cost: Optional[float] = None
    capex: Optional[float] = None
    cwip: Optional[float] = None
    
    # Debt maturity profile
    total_debt_maturing_lt_1y: Optional[float] = None
    total_debt_maturing_1_3y: Optional[float] = None
    total_debt_maturing_gt_3y: Optional[float] = None
    weighted_avg_interest_rate: Optional[float] = None
    floating_rate_debt: Optional[float] = None
    fixed_rate_debt: Optional[float] = None
    
    # === EQUITY & FUNDING MIX MODULE ===
    share_capital: Optional[float] = None
    reserves_and_surplus: Optional[float] = None
    net_worth: Optional[float] = None
    pat: Optional[float] = None
    dividend_paid: Optional[float] = None
    new_share_issuance: Optional[float] = None
    debt_equitymix: Optional[float] = None
    free_cash_flow: Optional[float] = None
    
    # === LIQUIDITY MODULE ===
    cash_and_equivalents: Optional[float] = None
    marketable_securities: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    inventory: Optional[float] = None
    daily_operating_expenses: Optional[float] = None
    
    # === WORKING CAPITAL MODULE ===
    trade_receivables: Optional[float] = None
    trade_payables: Optional[float] = None
    inventory_wc: Optional[float] = None
    revenue_wc: Optional[float] = None
    cogs: Optional[float] = None
    
    # === CAPEX & ASSET QUALITY MODULE ===
    net_fixed_assets: Optional[float] = None
    gross_block: Optional[float] = None
    accumulated_depreciation: Optional[float] = None
    cwip_asset: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    intangibles: Optional[float] = None
    goodwill: Optional[float] = None
    
    # === SOLVENCY MODULE ===
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    
    # === VALUATION MODULE ===
    market_cap: Optional[float] = None
    share_price: Optional[float] = None
    book_value: Optional[float] = None
    dividends_per_share: Optional[float] = None
    
    # === RISK ASSESSMENT ===
    risk_ebit: Optional[float] = None
    risk_interest: Optional[float] = None
    risk_net_income: Optional[float] = None
    risk_operating_cash_flow: Optional[float] = None
    risk_capex: Optional[float] = None
    risk_fixed_assets: Optional[float] = None
    risk_net_debt: Optional[float] = None
    risk_revenue: Optional[float] = None
    risk_assets_total: Optional[float] = None
    
    # === CREDIT RATING ===
    interest_expense: Optional[float] = None


class FinancialData(BaseModel):
    """Container for multiple financial years"""
    financial_years: List[FinancialYearInput]


class AnalyzeRequest(BaseModel):
    """Request model for analysis endpoint"""
    company: str
    financial_data: FinancialData
    modules: Optional[List[str]] = None  # Optional: specify which modules to run
    generate_narrative: bool = True  # Whether to generate LLM narratives


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
