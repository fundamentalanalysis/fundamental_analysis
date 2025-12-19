
# fundamental_analysis/src/main.py
import os
import sys

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

# -------------------------------------------------
# Ensure src is on PYTHONPATH (IMPORTANT)
# -------------------------------------------------
ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.append(ROOT)

# -------------------------------------------------
# COMMON REQUEST MODEL
# -------------------------------------------------
from src.app.request_model import AnalysisRequest

# -------------------------------------------------
# WORKING CAPITAL
# -------------------------------------------------
from src.app.working_capital_module.wc_orchestrator import run_working_capital_module

# -------------------------------------------------
# BORROWINGS
# -------------------------------------------------
from src.app.borrowing_module.debt_models import (
    BorrowingsInput,
    YearFinancialInput,
    IndustryBenchmarks,
    CovenantLimits,
)
from src.app.borrowing_module.debt_orchestrator import BorrowingsModule

# -------------------------------------------------
# ASSET QUALITY
# -------------------------------------------------
from src.app.asset_quality_module.asset_models import (
    AssetQualityInput,
    AssetFinancialYearInput,
    IndustryAssetBenchmarks,
)
from src.app.asset_quality_module.asset_orchestrator import (
    AssetIntangibleQualityModule,
)

# -------------------------------------------------
# CAPEX / CWIP
# -------------------------------------------------
from src.app.capex_cwip_module.orchestrator import CapexCwipModule

# -------------------------------------------------
# LIQUIDITY
# -------------------------------------------------
from src.app.liquidity_module.liquidity_models import LiquidityModuleInput
from src.app.liquidity_module.liquidity_orchestrator import (
    LiquidityModule,
    build_financial_list,
)



from src.app.leverage_financial_risk_module.lfr_orchestrator import (
    run_leverage_financial_risk_module,
)

# -------------------------------------------------
# FASTAPI APP
# -------------------------------------------------
app = FastAPI(
    title="Financial Analytical Engine",
    version="2.0",
)

# -------------------------------------------------
# DEFAULT BENCHMARKS
# -------------------------------------------------
DEFAULT_BENCHMARKS = IndustryBenchmarks(
    target_de_ratio=0.5,
    max_safe_de_ratio=1.0,
    max_safe_debt_ebitda=4.0,
    min_safe_icr=2.0,
    high_floating_share=0.60,
    high_wacd=0.12,
)

DEFAULT_COVENANTS = CovenantLimits(
    de_ratio_limit=1.0,
    icr_limit=2.0,
    debt_ebitda_limit=4.0,
)

DEFAULT_ASSET_BENCHMARKS = IndustryAssetBenchmarks()

borrowings_engine = BorrowingsModule()
asset_quality_engine = AssetIntangibleQualityModule()

# =================================================
# ENDPOINTS
# =================================================

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
            industry_code=req.get("industry_code", "GENERAL").upper(),
            financials_5y=financial_years,
            industry_benchmarks=DEFAULT_BENCHMARKS,
            covenant_limits=DEFAULT_COVENANTS,
        )

        return borrowings_engine.run(module_input).dict()

    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=ve.errors())


@app.post("/asset_quality/analyze")
async def analyze_asset_quality(req: AnalysisRequest):
    req = req.dict()
    financial_years = [
        AssetFinancialYearInput(**fy)
        for fy in req["financial_data"]["financial_years"]
    ]

    module_input = AssetQualityInput(
        company_id=req["company"].upper(),
        industry_code=req.get("industry_code", "GENERAL").upper(),
        financials_5y=financial_years,
        industry_asset_quality_benchmarks=DEFAULT_ASSET_BENCHMARKS,
    )

    return asset_quality_engine.run(module_input).dict()


@app.post("/working_capital_module/analyze")
async def analyze_wc(req: AnalysisRequest):
    return run_working_capital_module(req.dict())


@app.post("/capex_cwip_module/analyze")
async def analyze_capex(req: AnalysisRequest):
    analyzer = CapexCwipModule()
    return analyzer.run(req.dict())


@app.post("/liquidity/analyze")
async def analyze_liquidity(req: AnalysisRequest):
    req_data = req.dict()
    fin_list = build_financial_list(req_data)

    module_input = LiquidityModuleInput(
        company_id=req_data["company"].upper(),
        industry_code="GENERAL",
        financials_5y=fin_list,
    )

    return LiquidityModule().run(module_input).model_dump()



@app.post("/leverage_financial_risk/analyze")
async def analyze_leverage(req: AnalysisRequest):
    req_data = req.dict()
    return run_leverage_financial_risk_module(req_data)


# -------------------------------------------------
# ENTRY POINT
# -------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
