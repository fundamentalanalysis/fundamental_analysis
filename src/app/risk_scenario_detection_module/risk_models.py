from pydantic import BaseModel
from typing import List, Optional


class YearRiskFinancialInput(BaseModel):
    # Identity
    year: int

    # P&L
    revenue: float
    operating_profit: float      # EBIT
    interest: float
    net_profit: float
    other_income: float = 0.0
    depreciation: float = 0.0    # for EBITDA

    # Balance Sheet
    borrowings: float
    short_term_debt: float = 0.0
    long_term_debt: float = 0.0
    lease_liabilities: float = 0.0

    fixed_assets: float
    total_assets: float
    trade_receivables: float
    cash_equivalents: float

    # Cash Flow
    cash_from_operating_activity: float
    dividends_paid: float = 0.0

    proceeds_from_borrowings: float = 0.0
    repayment_of_borrowings: float = 0.0

    # Evergreening
    interest_paid_fin: float = 0.0
    interest_capitalized: float = 0.0

    # RPT
    related_party_sales: float = 0.0
    related_party_receivables: float = 0.0


class RiskScenarioInput(BaseModel):
    company_id: str
    industry_code: str
    financials_5y: List[YearRiskFinancialInput]


class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    flag: str
    year: int
    value: Optional[float]
    threshold: str
    reason: str
