# =============================================================
# main.py - UPDATED FOR YOUR NEW REQUEST FORMAT
# =============================================================

import os
import sys
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

# -------------------------------------------
# FIX PATH
# -------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

# -------------------------------------------
# IMPORT MODULES
# -------------------------------------------
from src.app.borrowing_module.debt_models import (
    BorrowingsInput,
    YearFinancialInput,
    IndustryBenchmarks,
    CovenantLimits,
)
from src.app.borrowing_module.debt_orchestrator import run_borrowings_module
from src.app.working_capital_module.wc_orchestrator import run_working_capital_module
from src.app.config import WORKING_CAPITAL_RULES    #  <-- YOU ALREADY HAVE




# ---------------------------------------------------------
# REQUEST MODELS
# ---------------------------------------------------------

class FinancialYearInput(BaseModel):
    year: str
    short_term_debt: float
    long_term_debt: float
    total_equity: float
    revenue : float
    ebitda: float
    ebit: float
    finance_cost: float
    capex: float
    cwip: float
    trade_receivables: float
    trade_payables: float
    inventory: float
    revenue: float
    cogs: float

    total_debt_maturing_lt_1y: Optional[float] = None
    total_debt_maturing_1_3y: Optional[float] = None
    total_debt_maturing_gt_3y: Optional[float] = None

    weighted_avg_interest_rate: Optional[float] = None
    floating_rate_debt: Optional[float] = None
    fixed_rate_debt: Optional[float] = None


class FinancialData(BaseModel):

    financial_years : list[FinancialYearInput]

    
    
    # total_debt_maturing_lt_1y: float
    # total_debt_maturing_1_3y: float
    # total_debt_maturing_gt_3y: float

    # weighted_avg_interest_rate: float
    # floating_rate_debt: float
    # fixed_rate_debt: float


class AnalyzeRequest(BaseModel):
    #year: int  # e.g. "Mar 2024"
    company: str
    financial_data: FinancialData   # <-- EXACT INPUT YOU WANTED


# ---------------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------------
app = FastAPI(
    title="Borrowings Analytical Engine",
    version="1.0",
    description="API for 1-year borrowings analysis"
)
def execute_borrowings_module(req: dict):
    
    company = req.company.upper()
    fd = req.financial_data

    fds = fd.financial_years
    
    yfis = []
    
    for fy in fds:
        yfi = YearFinancialInput(
            year=fy.year,   
            short_term_debt=fy.short_term_debt,
            long_term_debt=fy.long_term_debt,
            total_equity=fy.total_equity,
            revenue=fy.revenue,
            ebitda=fy.ebitda,
            ebit=fy.ebit,   
            finance_cost=fy.finance_cost,
            capex=fy.capex,
            cwip=fy.cwip,
            total_debt_maturing_lt_1y=fy.total_debt_maturing_lt_1y,
            total_debt_maturing_1_3y=fy.total_debt_maturing_1_3y,
            total_debt_maturing_gt_3y=fy.total_debt_maturing_gt_3y,
            weighted_avg_interest_rate=fy.weighted_avg_interest_rate,
            floating_rate_debt=fy.floating_rate_debt,
            fixed_rate_debt=fy.fixed_rate_debt,
        )
        yfis.append(yfi)   

        module_input = BorrowingsInput(
            company_id=company,
            industry_code="GENERAL",
            financials_5y=yfis,  # ONLY ONE YEAR USED
            industry_benchmarks=IndustryBenchmarks(
                target_de_ratio=1.5,
                max_safe_de_ratio=2.5,
                max_safe_debt_ebitda=4.0,
                min_safe_icr=2.0,
            ),
            covenant_limits=CovenantLimits(
                de_ratio_limit=3.0,
                icr_limit=2.0,
                debt_ebitda_limit=4.0,
            ),
        )

        result = run_borrowings_module(module_input)
    return result

# ---------------------------------------------------------
# MAIN API
# ---------------------------------------------------------
@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    try:

        input = req.dict()
        print("Input to WC Module:", input)
        result = run_working_capital_module(input)
        
            
        return result

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------------------------------------------------------
# RUN SERVER
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)

