from typing import List, Optional
from pydantic import BaseModel, Field


class FinancialYearData(BaseModel):
    year: int
    total_equity: float
    reserves: float
    short_term_debt: float
    long_term_debt: float
    cwip: float
    lease_liabilities: float
    other_borrowings: float
    trade_payables: float
    trade_receivables: float  # Keeping original casing from JSON
    advance_from_customers: float
    other_liability_items: float
    inventories: float
    cash_equivalents: float
    loans_n_advances: float
    other_asset_items: float
    gross_block: float
    accumulated_depreciation: float
    investments: float
    preference_capital: float
    revenue: float
    operating_profit: float
    interest: float
    depreciation: float
    material_cost: str  # Percentage as string e.g. "32.97%"
    manufacturing_cost: str
    net_profit: float
    employee_cost: str
    other_cost: str
    other_income: float
    total_assets: float
    expenses: float
    fixed_assets_purchased: float
    profit_from_operations: float
    working_capital_changes: float
    direct_taxes: float
    interest_paid_fin: float
    cash_from_operating_activity: float


class FinancialData(BaseModel):
    financial_years: List[FinancialYearData]


class AnalysisRequest(BaseModel):
    company: str
    financial_data: FinancialData