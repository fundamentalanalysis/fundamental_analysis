# =============================================================
# src/app/equity_funding_module/equity_models.py
# Data models for Equity & Funding Mix Module
# =============================================================

from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class EquityYearFinancialInput(BaseModel):
    """Per-year financial data for equity analysis"""
    year: int
    
    # Core equity data
    share_capital: float = 0.0
    reserves_and_surplus: float = 0.0
    net_worth: float = 0.0  # share_capital + reserves_and_surplus
    
    # Profitability
    pat: float = 0.0  # Profit After Tax
    
    # Dividend data
    dividend_paid: float = 0.0  # Usually negative (outflow)
    
    # Cash flow
    free_cash_flow: Optional[float] = None
    
    # Capital raising
    new_share_issuance: float = 0.0
    
    # Debt for funding mix analysis
    debt_equitymix: float = 0.0  # Total debt for funding mix calculation
    
    # Optional additional fields
    total_equity: Optional[float] = None


class EquityBenchmarks(BaseModel):
    """Industry benchmarks for equity analysis"""
    payout_normal: float = 0.30  # 30% typical
    payout_high: float = 0.50  # 50% high
    roe_good: float = 0.15  # 15% good
    roe_modest: float = 0.10  # 10% modest
    dilution_warning: float = 0.05  # 5% warning
    dilution_high: float = 0.10  # 10% high
    dividends_exceed_fcf_warning: float = 1.0
    high_dividend_to_pat: float = 1.0
    retained_earnings_decline_warning: float = 0.0
    leverage_rising_threshold: float = 0.10  # Debt CAGR > Equity CAGR + 10%


class EquityFundingInput(BaseModel):
    """Input contract for Equity Funding Mix Module"""
    company_id: str
    industry_code: str = "GENERAL"
    financials_5y: List[EquityYearFinancialInput]
    industry_benchmarks: EquityBenchmarks = EquityBenchmarks()


class EquityRuleResult(BaseModel):
    """Result from a rule evaluation"""
    rule_id: str
    rule_name: str
    flag: str  # RED, YELLOW, GREEN
    value: Optional[float] = None
    threshold: str
    reason: str


class RedFlag(BaseModel):
    """Red flag output structure"""
    severity: str  # CRITICAL, HIGH, MEDIUM
    title: str
    detail: str


class EquityFundingOutput(BaseModel):
    """Output schema for Equity Funding Mix Module"""
    module: str = "EquityFundingMix"
    sub_score_adjusted: int
    analysis_narrative: List[str]
    red_flags: List[Dict[str, Any]]
    positive_points: List[str]
    rule_results: List[EquityRuleResult]
    metrics: Dict[str, Any]
