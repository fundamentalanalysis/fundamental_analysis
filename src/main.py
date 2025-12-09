# fundamental_analysis/src/main.py
from src.app.equity_funding_mix_module.equity_funding_mix_models import (
    EquityFundingInput,
    YearFinancialInput as EquityYearFinancialInput,
    IndustryBenchmarks as EquityIndustryBenchmarks,
)
from src.app.equity_funding_mix_module.equity_funding_mix_orchestrator import EquityFundingMixModule
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

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from fastapi import Request
from src.app.working_capital_module.wc_orchestrator import run_working_capital_module

# Ensure package imports work when running `python src/main.py`
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)


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

# ---------- FastAPI App ----------
app = FastAPI(
    title="Financial Analytical Engine",
    version="1.1",
    description="Multi-module financial analysis system (Borrowings, Asset Quality)",
)

borrowings_engine = BorrowingsModule()
asset_quality_engine = AssetIntangibleQualityModule()


@app.post("/borrowings/analyze")
async def analyze_borrowings(req: Request):
    try:
        req = await req.json()
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


@app.post("/asset_quality/analyze")
async def analyze_asset_quality(req: Request):
    try:
        req = await req.json()
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
async def analyze(request: Request):
    try:
        input_data = await request.json()
        print("Input to WC Module:", input_data)

        result = run_working_capital_module(input_data)

        return result

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/capex_cwip_module/analyze")
async def analyze(req: Request):
    try:
        analyzer = CapexCwipModule()
        req_data = await req.json()
        result = analyzer.run(req_data)
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/liquidity/analyze")
async def analyze_liquidity(req: Request):
    try:
        req_data = await req.json()
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


# ---------- Equity Funding Mix API Request Schemas ----------

equity_funding_engine = EquityFundingMixModule()

# Equity Funding Mix Benchmarks
DEFAULT_EQUITY_BENCHMARKS = EquityIndustryBenchmarks(
    payout_normal=0.30,
    payout_high=0.50,
    roe_good=0.15,
    roe_modest=0.10,
    dilution_warning=0.05,
)


class EquityFinancialYearInput(BaseModel):
    year: int
    # Equity fields (optional - can be computed from total_equity)
    share_capital: Optional[float] = None
    reserves_and_surplus: Optional[float] = None
    net_worth: Optional[float] = None
    # Alternative name for reserves_and_surplus
    reserves: Optional[float] = None
    # Income & Dividend fields
    net_profit: Optional[float] = None
    pat: Optional[float] = None
    dividends_paid: Optional[float] = 0.0
    free_cash_flow: Optional[float] = None
    # Capital structure fields
    new_share_issuance: Optional[float] = 0.0
    debt: Optional[float] = None
    revenue: Optional[float] = None
    # Alternative debt fields (from borrowings endpoint)
    short_term_debt: Optional[float] = None
    long_term_debt: Optional[float] = None
    lease_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    ebitda: Optional[float] = None
    ebit: Optional[float] = None
    finance_cost: Optional[float] = None
    interest: Optional[float] = None
    direct_taxes: Optional[float] = None
    # Operating profit fields
    profit_from_operations: Optional[float] = None
    operating_profit: Optional[float] = None
    # Cash flow fields
    cash_from_operating_activity: Optional[float] = None
    fixed_assets_purchased: Optional[float] = None


class EquityFinancialData(BaseModel):
    financial_years: List[EquityFinancialYearInput]


class EquityFundingMixRequest(BaseModel):
    company: str
    industry_code: Optional[str] = "GENERAL"
    financial_data: EquityFinancialData


@app.post("/equityfundingmix/analyze")
async def analyze_equity_funding_mix(req: EquityFundingMixRequest):
    try:
        # Convert request data, computing missing equity fields if needed
        equity_years = []
        for fy in req.financial_data.financial_years:
            fy_dict = fy.dict()

            # 1. Compute total debt: short_term + long_term + lease_liabilities
            if fy_dict.get("debt") is None:
                st_debt = fy_dict.get("short_term_debt") or 0.0
                lt_debt = fy_dict.get("long_term_debt") or 0.0
                lease_liab = fy_dict.get("lease_liabilities") or 0.0
                fy_dict["debt"] = st_debt + lt_debt + lease_liab

            # 2. Compute share_capital (use from input if available, otherwise use total_equity)
            if fy_dict.get("share_capital") is None:
                fy_dict["share_capital"] = fy_dict.get("total_equity") or 0.0

            # 3. Compute reserves_and_surplus (use from input if available, otherwise default to 0)
            if fy_dict.get("reserves_and_surplus") is None:
                fy_dict["reserves_and_surplus"] = fy_dict.get(
                    "reserves") or 0.0

            # 4. Compute net_worth = share_capital + reserves_and_surplus
            if fy_dict.get("net_worth") is None:
                fy_dict["net_worth"] = (fy_dict.get(
                    "share_capital") or 0.0) + (fy_dict.get("reserves_and_surplus") or 0.0)

            # 5. Compute PAT from operating profit or profit_from_operations
            fy_dict["pat"] = fy_dict.get("net_profit")

            # if fy_dict.get("pat") is None:
            #     pat_val = fy_dict.get("net_profit") or 0.0
            #     print("Initial PAT from operations:", pat_val)
            #     fy_dict["pat"] = max(0, pat_val)

            # 6. Set dividend_paid (default 0 if not provided)
            if fy_dict.get("dividends_paid") is None:
                fy_dict["dividends_paid"] = 0.0

            # fy_dict["dividends_paid"] = fy_dict.get("dividends_paid")
            # print("Year:", fy_dict["year"], "PAT:", fy_dict["pat"], "Dividends Paid:", fy_dict["dividends_paid"])

            # 7. Compute free_cash_flow if not provided
            if fy_dict.get("free_cash_flow") is None:
                ocf = fy_dict.get("cash_from_operating_activity") or 0.0
                capex = fy_dict.get("fixed_assets_purchased") or 0.0
                fy_dict["free_cash_flow"] = ocf + \
                    capex  # capex is negative (outflow)

            equity_years.append(EquityYearFinancialInput(**fy_dict))

        module_input = EquityFundingInput(
            company_id=req.company.upper(),
            industry_code=(req.industry_code or "GENERAL").upper(),
            financials_5y=equity_years,
            industry_equity_benchmarks=DEFAULT_EQUITY_BENCHMARKS,
        )
        result = equity_funding_engine.run(module_input)
        return result.dict()

    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=ve.errors())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
