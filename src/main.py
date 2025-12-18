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

from src.app.risk_scenario_detection_module.risk_models import (
    RiskScenarioInput,
    YearRiskFinancialInput
)
from src.app.risk_scenario_detection_module.risk_orchestrator import (
    RiskScenarioDetectionModule
)




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
# IMPORT RISK MODULE
# =============================================================
# from src.app.risk_scenario_detection_module.risk_orchestrator import (
#     RiskOrchestrator,   
# )


# ---------------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------------
app = FastAPI(
    title="Financial Analytical Engine",
    version="2.0",
    description="API for Borrowings + Liquidity Analysis + Risk Scenario Detection Modules"
)

DEFAULT_COVENANTS = CovenantLimits(
    de_ratio_limit=1.0,
    icr_limit=2.0,
    debt_ebitda_limit=4.0,
)

DEFAULT_ASSET_BENCHMARKS = IndustryAssetBenchmarks()


borrowings_engine = BorrowingsModule()
asset_quality_engine = AssetIntangibleQualityModule()
risk_engine = RiskScenarioDetectionModule() 


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
        return result

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    
# @app.post("/risk/analyze")
# async def analyze_risk(req: AnalysisRequest):
#     try:
#         req_data = req.dict()
#         result = await risk_engine.run(req_data)  # async call to RiskOrchestrator
#         return result
#     except Exception as e:
#         return JSONResponse({"error": str(e)}, status_code=500)
    
@app.post("/risk/analyze")
async def analyze_risk_scenario(req: Request):
    try:
        req_data = await req.json()

        financial_years = [
                YearRiskFinancialInput(
            year=fy["year"],
            revenue=fy["revenue"],
            operating_profit=fy["operating_profit"],
            interest=fy["interest"],
            net_profit=fy["net_profit"],
            other_income=fy.get("other_income", 0.0),
            depreciation=fy.get("depreciation", 0.0),  # ✅ ADD THIS

            borrowings=fy["borrowings"],
            lease_liabilities=fy.get("lease_liabilities", 0.0),
            fixed_assets=fy["fixed_assets"],
            total_assets=fy["total_assets"],
            trade_receivables=fy["trade_receivables"],
            cash_equivalents=fy["cash_equivalents"],

            cash_from_operating_activity=fy["cash_from_operating_activity"],
            dividends_paid=fy.get("dividends_paid", 0.0),
            proceeds_from_borrowings=fy.get("proceeds_from_borrowings", 0.0),
            repayment_of_borrowings=fy.get("repayment_of_borrowings", 0.0),
        )

            for fy in req_data["financial_data"]["financial_years"]
        ]

        module_input = RiskScenarioInput(
            company_id=req_data["company"].upper(),
            industry_code=req_data.get("industry_code", "GENERAL").upper(),
            financials_5y=financial_years,
        )

        result = risk_engine.run(module_input)
        return result


    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn


    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
