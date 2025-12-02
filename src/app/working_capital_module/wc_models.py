# models.py
from pydantic import BaseModel
from typing import List, Optional


class FinancialYear(BaseModel):
    year: str
    trade_receivables: float
    trade_payables: float
    inventory: float
    revenue: float
    cogs: float

    short_term_debt: Optional[float] = None
    long_term_debt: Optional[float] = None
    total_equity: Optional[float] = None
    ebitda: Optional[float] = None
    ebit: Optional[float] = None
    finance_cost: Optional[float] = None
    capex: Optional[float] = None
    cwip: Optional[float] = None


    total_debt_maturing_lt_1y: Optional[float] = None
    total_debt_maturing_1_3y: Optional[float] = None
    total_debt_maturing_gt_3y: Optional[float] = None
    weighted_avg_interest_rate: Optional[float] = None
    floating_rate_debt: Optional[float] = None
    fixed_rate_debt: Optional[float] = None

class WorkingCapitalRules(BaseModel):
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

class FinancialData(BaseModel):
    financial_years: List[FinancialYear]

class WorkingCapitalInput(BaseModel):
    company: str
    financial_data: FinancialData
    # rules: WorkingCapitalRules
