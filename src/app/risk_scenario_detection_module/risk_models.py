# risk_models.py
from pydantic import BaseModel
from typing import List, Dict, Optional, Any


class YearFinancials(BaseModel):
    # Include the fields present in your input JSON (common fields)
    year: int
    borrowings: Optional[float] = None
    net_debt: Optional[float] = None
    trade_receivables: Optional[float] = None
    cash_equivalents: Optional[float] = None
    total_assets: Optional[float] = None
    fixed_assets: Optional[float] = None
    revenue: Optional[float] = None
    operating_profit: Optional[float] = None
    ebit: Optional[float] = None
    interest: Optional[float] = None
    net_profit: Optional[float] = None
    other_income: Optional[float] = None
    profit_from_operations: Optional[float] = None
    interest_paid_fin: Optional[float] = None
    cash_from_operating_activity: Optional[float] = None
    dividends_paid: Optional[float] = None
    proceeds_from_borrowings: Optional[float] = None
    repayment_of_borrowings: Optional[float] = None
    # user-supplied manual RPT values could be present separately
    related_party_sales: Optional[float] = None
    related_party_receivables: Optional[float] = None


class ModuleInput(BaseModel):
    company: str
    financial_data: Dict[str, List[YearFinancials]]
    module_red_flags: Optional[Dict[str, Any]] = {}
    scenario_thresholds: Optional[Dict[str, float]] = {}


class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    value: Optional[float] = None
    threshold: Optional[str] = None
    flag: str
    reason: Optional[str] = None


class ModuleOutput(BaseModel):
    module: str
    sub_score_adjusted: int
    key_metrics: Dict[str, Any]
    trends: Dict[str, Any]
    analysis_narrative: List[str]
    red_flags: List[Dict[str, Any]]
    positive_points: List[str]
    rules: List[RuleResult]
    summary_color: str
    scenario_score: int
    scenarios_detected: List[Dict[str, Any]]
