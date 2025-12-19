# fundamental_analysis/src/main.py
import os
import sys
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from fastapi import Request
from src.app.request_model import AnalysisRequest
from src.app.working_capital_module.wc_orchestrator import run_working_capital_module

# Ensure package imports work when running `python src/main.py`
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from src.app.borrowing_module.debt_models import (
    BorrowingsInput,
    YearFinancialInput,
    IndustryBenchmarks,
    CovenantLimits,
)
from src.app.borrowing_module.debt_orchestrator import BorrowingsModule

from src.app.asset_quality_module.asset_models import (
    AssetQualityInput,
    AssetFinancialYearInput,
    IndustryAssetBenchmarks,
)
from src.app.asset_quality_module.asset_orchestrator import AssetIntangibleQualityModule
from src.app.borrowing_module.debt_orchestrator import BorrowingsModule
from src.app.capex_cwip_module.orchestrator import CapexCwipModule


DEFAULT_BENCHMARKS = IndustryBenchmarks(
    target_de_ratio=0.5,
    max_safe_de_ratio=1,
    max_safe_debt_ebitda=4.0,
    min_safe_icr=2.0,
    high_floating_share=0.60,
    high_wacd=0.12,
)
# =============================================================
# IMPORT LIQUIDITY MODULE
# =============================================================
from src.app.liquidity_module.liquidity_models import (
    LiquidityModuleInput,
)
from src.app.liquidity_module.liquidity_orchestrator import (
    LiquidityModule,
    build_financial_list,  # Add this import
)

# =============================================================
# IMPORT LEVERAGE & FINANCIAL RISK MODULE
# =============================================================
from src.app.leverage_financial_risk_module.lfr_models import (
    LeverageFinancialRiskInput,
    LeverageFinancialBenchmarks,
)
from src.app.leverage_financial_risk_module.lfr_orchestrator import (
    run_leverage_financial_risk_module,
)
from src.app.config import DEFAULT_LEVERAGE_FINANCIAL_RULES
DEFAULT_LEVERAGE_BENCHMARKS = LeverageFinancialBenchmarks(
    **DEFAULT_LEVERAGE_FINANCIAL_RULES
)


# ---------------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------------
app = FastAPI(
    title="Financial Analytical Engine",
    version="2.0",
    description="API for Borrowings + Liquidity Analysis"
)

DEFAULT_COVENANTS = CovenantLimits(
    de_ratio_limit=1.0,
    icr_limit=2.0,
    debt_ebitda_limit=4.0,
)

DEFAULT_ASSET_BENCHMARKS = IndustryAssetBenchmarks()


borrowings_engine = BorrowingsModule()
asset_quality_engine = AssetIntangibleQualityModule()


@app.post("/borrowings/analyze")
async def analyze_borrowings(req: AnalysisRequest):
    try:
        req = req.dict()
        financial_years = [
            YearFinancialInput(**fy)
            for fy in req["financial_data"]["financial_years"]
        ]

        module_input = BorrowingsInput(
            company_id=req["company"].upper(),
            industry_code=(req["industry_code"] if "industry_code" in req else "GENERAL").upper(),
            financials_5y=financial_years,
            industry_benchmarks=DEFAULT_BENCHMARKS,
            covenant_limits=DEFAULT_COVENANTS,
        )
        result = borrowings_engine.run(module_input)
        return result.dict()
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=ve.errors())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/asset_quality/analyze")
async def analyze_asset_quality(req: AnalysisRequest):
    try:
        req = req.dict()
        financial_years = [
            AssetFinancialYearInput(**fy)
            for fy in req["financial_data"]["financial_years"]
        ]

        module_input = AssetQualityInput(
            company_id=req.company.upper(),
            industry_code=(req.industry_code or "GENERAL").upper(),
            financials_5y=financial_years,
            industry_asset_quality_benchmarks=DEFAULT_ASSET_BENCHMARKS,
        )
        result = asset_quality_engine.run(module_input)
        return result.dict()
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=ve.errors())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/working_capital_module/analyze")
async def analyze(request: AnalysisRequest):
    try:
        input_data = request.dict()
        print("Input to WC Module:", input_data)

        result = run_working_capital_module(input_data)
        
        return result

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/capex_cwip_module/analyze")
async def analyze(req: AnalysisRequest):
    try:
        analyzer = CapexCwipModule()
        req_data = req.dict()
        result = analyzer.run(req_data)
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    
    
    
@app.post("/leverage_financial_risk/analyze")
async def analyze_leverage_financial_risk(req: AnalysisRequest):
    try:
        req_data = req.dict()
        print("Input to LFR Module:", req_data)

        # Inject benchmarks if not present
        req_data["benchmarks"] = DEFAULT_LEVERAGE_BENCHMARKS.dict()

        result = run_leverage_financial_risk_module(req_data)

        return result

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    
    


@app.post("/liquidity/analyze")
async def analyze_liquidity(req: AnalysisRequest):
    try:
        req_data = req.dict()
        company = req_data["company"].upper()

        # Convert to liquidity models
        fin_list = build_financial_list(req_data)

        module_input = LiquidityModuleInput(
            company_id=company,
            industry_code="GENERAL",
            financials_5y=fin_list,
            # industry_liquidity_thresholds=req_data["thresholds"],
        )

        module = LiquidityModule()

        result = module.run(module_input)
        return result.model_dump()

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn


    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)