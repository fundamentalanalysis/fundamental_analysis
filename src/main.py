# =============================================================
# main.py - Multi-Module Analytical Engine
# =============================================================

import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List

# -------------------------------------------
# FIX PATH
# -------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

# -------------------------------------------
# IMPORT MODULES
# -------------------------------------------
# Borrowings Module
from src.app.borrowing_module.debt_models import (
    BorrowingsInput,
    YearFinancialInput,
    IndustryBenchmarks,
    CovenantLimits,
)
from src.app.borrowing_module.debt_orchestrator import run_borrowings_module

# Equity Funding Mix Module
from src.app.equity_funding_module.equity_models import (
    EquityFundingInput,
    EquityYearFinancialInput,
    EquityBenchmarks,
)
from src.app.equity_funding_module.equity_orchestrator import run_equity_funding_module

# Module Registry
from src.app.module_registry import (
    initialize_registry,
    run_module,
    get_available_modules,
    get_module_info,
    list_all_modules_info,
)


# ---------------------------------------------------------
# REQUEST MODELS - Unified Financial Input
# ---------------------------------------------------------

class FinancialYearInput(BaseModel):
    """Comprehensive financial year data supporting all modules"""
    year: int
    
    # Debt/Borrowings data
    short_term_debt: float = 0
    long_term_debt: float = 0
    total_equity: float = 0
    revenue: float = 0
    ebitda: float = 0
    ebit: float = 0
    finance_cost: float = 0
    capex: float = 0
    cwip: float = 0
    
    # Debt maturity profile
    total_debt_maturing_lt_1y: Optional[float] = None
    total_debt_maturing_1_3y: Optional[float] = None
    total_debt_maturing_gt_3y: Optional[float] = None
    weighted_avg_interest_rate: Optional[float] = None
    floating_rate_debt: Optional[float] = None
    fixed_rate_debt: Optional[float] = None
    
    # Equity & Funding Mix data
    share_capital: float = 0
    reserves_and_surplus: float = 0
    net_worth: float = 0
    pat: float = 0
    dividend_paid: float = 0
    new_share_issuance: float = 0
    debt_equitymix: float = 0
    free_cash_flow: Optional[float] = None


class FinancialData(BaseModel):
    financial_years: List[FinancialYearInput]


class AnalyzeRequest(BaseModel):
    """Request model for analysis"""
    company: str
    financial_data: FinancialData
    modules: Optional[List[str]] = None  # Optional: specify which modules to run


# ---------------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------------
app = FastAPI(
    title="Fundamental Analysis Multi-Agent Engine",
    version="2.0",
    description="API for comprehensive financial analysis with configurable modules"
)


# Initialize registry on startup
@app.on_event("startup")
async def startup_event():
    initialize_registry()


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def build_borrowings_input(company: str, fds: List[FinancialYearInput]) -> BorrowingsInput:
    """Build BorrowingsInput from unified financial data"""
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
    
    return BorrowingsInput(
        company_id=company,
        industry_code="GENERAL",
        financials_5y=yfis,
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


def build_equity_funding_input(company: str, fds: List[FinancialYearInput]) -> EquityFundingInput:
    """Build EquityFundingInput from unified financial data"""
    efis = []
    for fy in fds:
        # Calculate debt for funding mix if not provided
        debt = fy.debt_equitymix
        if debt == 0:
            debt = fy.short_term_debt + fy.long_term_debt
        
        # Calculate net_worth if not provided
        net_worth = fy.net_worth
        if net_worth == 0:
            net_worth = fy.share_capital + fy.reserves_and_surplus
        
        efi = EquityYearFinancialInput(
            year=fy.year,
            share_capital=fy.share_capital,
            reserves_and_surplus=fy.reserves_and_surplus,
            net_worth=net_worth,
            pat=fy.pat,
            dividend_paid=fy.dividend_paid,
            free_cash_flow=fy.free_cash_flow,
            new_share_issuance=fy.new_share_issuance,
            debt_equitymix=debt,
            total_equity=fy.total_equity,
        )
        efis.append(efi)
    
    return EquityFundingInput(
        company_id=company,
        industry_code="GENERAL",
        financials_5y=efis,
        industry_benchmarks=EquityBenchmarks(),
    )


# ---------------------------------------------------------
# API ENDPOINTS
# ---------------------------------------------------------

@app.get("/")
def root():
    """API root with available endpoints"""
    return {
        "message": "Fundamental Analysis Multi-Agent Engine",
        "version": "2.0",
        "endpoints": {
            "/analyze": "POST - Run analysis with specified modules",
            "/analyze/borrowings": "POST - Run borrowings analysis only",
            "/analyze/equity-funding": "POST - Run equity funding mix analysis only",
            "/modules": "GET - List available modules",
            "/modules/{module_key}": "GET - Get module information",
        }
    }


@app.get("/modules")
def list_modules():
    """List all available analytical modules"""
    return {
        "available_modules": get_available_modules(),
        "all_modules": list_all_modules_info(),
    }


@app.get("/modules/{module_key}")
def get_module(module_key: str):
    """Get information about a specific module"""
    info = get_module_info(module_key)
    if "error" in info:
        raise HTTPException(status_code=404, detail=info["error"])
    return info


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """
    Run comprehensive analysis with multiple modules.
    
    If no modules specified, runs all enabled modules.
    """
    try:
        company = req.company.upper()
        fds = req.financial_data.financial_years
        
        # Determine which modules to run
        modules_to_run = req.modules if req.modules else get_available_modules()
        
        results = {}
        
        for module_key in modules_to_run:
            try:
                if module_key == "borrowings":
                    input_data = build_borrowings_input(company, fds)
                    result = run_borrowings_module(input_data)
                    results["borrowings"] = result.model_dump()
                    
                elif module_key == "equity_funding_mix":
                    input_data = build_equity_funding_input(company, fds)
                    result = run_equity_funding_module(input_data)
                    results["equity_funding_mix"] = result.model_dump()
                    
                else:
                    results[module_key] = {"error": f"Module '{module_key}' not implemented"}
                    
            except Exception as e:
                results[module_key] = {"error": str(e)}
        
        return {
            "company": company,
            "modules_analyzed": list(results.keys()),
            "results": results,
        }
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/analyze/borrowings")
def analyze_borrowings(req: AnalyzeRequest):
    """Run borrowings analysis only"""
    try:
        company = req.company.upper()
        fds = req.financial_data.financial_years
        
        input_data = build_borrowings_input(company, fds)
        result = run_borrowings_module(input_data)
        
        return result.model_dump()
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/analyze/equity-funding")
def analyze_equity_funding(req: AnalyzeRequest):
    """Run equity funding mix analysis only"""
    try:
        company = req.company.upper()
        fds = req.financial_data.financial_years
        
        input_data = build_equity_funding_input(company, fds)
        result = run_equity_funding_module(input_data)
        
        return result.model_dump()
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------------------------------------------------------
# RUN SERVER
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
