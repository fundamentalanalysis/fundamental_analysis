# fundamental_analysis/src/main.py
from src.app.quality_of_earnings_module.qoe_orchestrator import run_quality_of_earnings_module
from src.app.equity_funding_mix_module.equity_funding_mix_models import (
    EquityFundingInput,
    YearFinancialInput as EquityYearFinancialInput,
    IndustryBenchmarks as EquityIndustryBenchmarks,
)
from src.app.equity_funding_mix_module.equity_funding_mix_orchestrator import EquityFundingMixModule, run_equity_funding_mix_module
from src.app.liquidity_module.liquidity_orchestrator import (
    LiquidityModule,
    build_financial_list,  # Add this import
)
from src.app.liquidity_module.liquidity_models import (
    LiquidityModuleInput,
)
from src.app.capex_cwip_module.orchestrator import CapexCwipModule
from src.app.asset_quality_module.asset_orchestrator import AssetIntangibleQualityModule
from src.app.asset_quality_module.asset_models import (
    AssetQualityInput,
    AssetFinancialYearInput,
    IndustryAssetBenchmarks,
)
from src.app.borrowing_module.debt_orchestrator import BorrowingsModule
from src.app.borrowing_module.debt_models import (
    BorrowingsInput,
    YearFinancialInput,
    IndustryBenchmarks,
    CovenantLimits,
)
import os
import sys
from typing import List, Optional

from src.app.quality_of_earnings_module.qoe_models import QoEBenchmarks, QoEYearInput, QualityOfEarningsInput
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


from src.app.asset_intangible_quality_module.aiqm_orchestrator import AssetIntangibleQualityModule
from src.app.asset_intangible_quality_module.aiqm_models import (
    AssetIntangibleInput,
    YearAssetIntangibleInput,
    AssetIntangibleBenchmarks,
    FinancialDataBlock,
)


from src.app.borrowing_module.debt_orchestrator import BorrowingsModule
from src.app.capex_cwip_module.orchestrator import CapexCwipModule

from src.app.asset_intangible_quality_module.aiqm_orchestrator import run_aiqm_module

from src.app.asset_intangible_quality_module.aiqm_models import AssetIntangibleInput

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

# =============================================================
# IMPORT RISK MODULE
# =============================================================
from src.app.risk_scenario_detection_module.risk_orchestrator import (
    RiskOrchestrator,   
)


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

# DEFAULT_ASSET_BENCHMARKS = IndustryAssetBenchmarks()


borrowings_engine = BorrowingsModule()
asset_quality_engine = AssetIntangibleQualityModule()
risk_engine = RiskOrchestrator()  


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
            industry_code=(req["industry_code"]
                           if "industry_code" in req else "GENERAL").upper(),
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


# @app.post("/asset_quality/analyze")
# async def analyze_asset_quality(req: AnalysisRequest):
#     try:
#         req = req.dict()
#         financial_years = [
#             AssetFinancialYearInput(**fy)
#             for fy in req["financial_data"]["financial_years"]
#         ]

#         module_input = AssetQualityInput(
#             company_id=req.company.upper(),
#             industry_code=(req.industry_code or "GENERAL").upper(),
#             financials_5y=financial_years,
#             industry_asset_quality_benchmarks=DEFAULT_ASSET_BENCHMARKS,
#         )
#         result = asset_quality_engine.run(module_input)
#         return result.dict()
#     except ValidationError as ve:
#         raise HTTPException(status_code=422, detail=ve.errors())
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc))


@app.post("/working_capital_module/analyze")
async def analyze(request: AnalysisRequest):
    try:
        input_data = request.dict()
        print("Input to WC Module:", input_data)

        result = run_working_capital_module(input_data)

        return result

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    
@app.post("/quality_of_earnings/analyze")
async def analyze_qoe(req: AnalysisRequest):
    try:
        data = req.dict()

        # convert to QoE expected format
        financial_years = data["financial_data"]["financial_years"]

        qoe_input = {
            "company": data["company"],
            "financials_5y": financial_years
        }

        

        result = run_quality_of_earnings_module(qoe_input)
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
    
@app.post("/risk/analyze")
async def analyze_risk(req: AnalysisRequest):
    try:
        req_data = req.dict()
        result = await risk_engine.run(req_data)  # async call to RiskOrchestrator
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    


# ---------- Equity Funding Mix API Request Schemas ----------

@app.post("/equityfundingmix/analyze")
async def analyze_equity_funding_mix(req: AnalysisRequest):
    try:
        req_data = req.dict()
        result = run_equity_funding_mix_module(req_data)
        return result

    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=ve.errors())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    
@app.post("/asset_intangible_quality/analyze")
async def analyze_asset_quality(req: Request):
    try:
        req_data = await req.json()

        # LET PYDANTIC PARSE NESTED STRUCTURES AUTOMATICALLY
        module_input = AssetIntangibleInput(**req_data)

        result = asset_quality_engine.run(module_input)
        return result.dict()

    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=ve.errors())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
