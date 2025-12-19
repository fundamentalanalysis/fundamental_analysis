# from typing import List, Optional
# from pydantic import BaseModel, Field


# class FinancialYearData(BaseModel):
#     year: int
#     total_equity: float
#     reserves: float
#     short_term_debt: float
#     long_term_debt: float
#     cwip: float
#     lease_liabilities: float
#     other_borrowings: float
#     trade_payables: float
#     Trade_receivables: float  # Keeping original casing from JSON
#     advance_from_customers: float
#     other_liability_items: float
#     inventories: float
#     cash_equivalents: float
#     loans_n_advances: float
#     other_asset_items: float
#     gross_block: float
#     accumulated_depreciation: float
#     investments: float
#     preference_capital: float
#     revenue: float
#     operating_profit: float
#     interest: float
#     depreciation: float
#     material_cost: str  # Percentage as string e.g. "32.97%"
#     manufacturing_cost: str
#     employee_cost: str
#     other_cost: str
#     expenses: float
#     fixed_assets_purchased: float
#     profit_from_operations: float
#     working_capital_changes: float
#     direct_taxes: float
#     interest_paid_fin: float
#     cash_from_operating_activity: float


# class FinancialData(BaseModel):
#     financial_years: List[FinancialYearData]


# class AnalysisRequest(BaseModel):
#     company: str
#     financial_data: FinancialData

from typing import List, Optional
from pydantic import BaseModel, Field


# ======================================================
# YEAR-LEVEL FINANCIAL DATA
# ======================================================

class FinancialYearData(BaseModel):
    year: int

    # -------- Balance Sheet --------
    total_equity: Optional[float] = 0.0
    reserves: Optional[float] = 0.0
    short_term_debt: Optional[float] = 0.0
    long_term_debt: Optional[float] = 0.0
    cwip: Optional[float] = 0.0
    lease_liabilities: Optional[float] = 0.0
    other_borrowings: Optional[float] = 0.0
    trade_payables: Optional[float] = 0.0

    # ✅ FIXED FIELD (accepts both cases)
    trade_receivables: Optional[float] = Field(
        0.0, alias="Trade_receivables"
    )

    advance_from_customers: Optional[float] = 0.0
    other_liability_items: Optional[float] = 0.0
    inventories: Optional[float] = 0.0
    cash_equivalents: Optional[float] = 0.0
    loans_n_advances: Optional[float] = 0.0
    other_asset_items: Optional[float] = 0.0
    gross_block: Optional[float] = 0.0
    accumulated_depreciation: Optional[float] = 0.0
    investments: Optional[float] = 0.0
    preference_capital: Optional[float] = 0.0

    # -------- P&L --------
    revenue: Optional[float] = 0.0
    operating_profit: Optional[float] = 0.0
    interest: Optional[float] = 0.0
    depreciation: Optional[float] = 0.0

    material_cost: Optional[str] = None
    manufacturing_cost: Optional[str] = None
    employee_cost: Optional[str] = None
    other_cost: Optional[str] = None

    expenses: Optional[float] = 0.0
    fixed_assets_purchased: Optional[float] = 0.0
    profit_from_operations: Optional[float] = 0.0
    working_capital_changes: Optional[float] = 0.0
    direct_taxes: Optional[float] = 0.0
    interest_paid_fin: Optional[float] = 0.0
    cash_from_operating_activity: Optional[float] = 0.0

    class Config:
        allow_population_by_field_name = True
        extra = "allow"


# ======================================================
# FINANCIAL DATA WRAPPER
# ======================================================

class FinancialData(BaseModel):
    financial_years: List[FinancialYearData]


# ======================================================
# MAIN REQUEST MODEL
# ======================================================

class AnalysisRequest(BaseModel):
    company: str
    financial_data: FinancialData

    class Config:
        extra = "allow"
