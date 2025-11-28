# fundamental_analysis/src/main.py
import os
import sys
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError

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


DEFAULT_BENCHMARKS = IndustryBenchmarks(
    target_de_ratio=1.5,
    max_safe_de_ratio=2.5,
    max_safe_debt_ebitda=4.0,
    min_safe_icr=2.0,
    high_floating_share=0.60,
    high_wacd=0.12,
)

DEFAULT_COVENANTS = CovenantLimits(
    de_ratio_limit=3.0,
    icr_limit=2.0,
    debt_ebitda_limit=4.0,
)


# ---------- API Request Schemas ----------
class FinancialYearInput(BaseModel):
    year: int
    short_term_debt: float = Field(ge=0)
    long_term_debt: float = Field(ge=0)
    total_equity: float = Field(ge=0)
    ebitda: float
    ebit: float
    finance_cost: float
    capex: float = 0
    cwip: float = 0
    revenue: float = 0
    operating_cash_flow: float = 0
    total_debt_maturing_lt_1y: Optional[float] = None
    total_debt_maturing_1_3y: Optional[float] = None
    total_debt_maturing_gt_3y: Optional[float] = None
    weighted_avg_interest_rate: Optional[float] = None
    floating_rate_debt: Optional[float] = None
    fixed_rate_debt: Optional[float] = None


class FinancialData(BaseModel):
    financial_years: List[FinancialYearInput]


class BorrowingsRequest(BaseModel):
    company: str
    industry_code: Optional[str] = "GENERAL"
    financial_data: FinancialData


# ---------- FastAPI App ----------
app = FastAPI(
    title="Borrowings Analytical Engine",
    version="1.0",
    description="Deterministic + LLM hybrid module for leverage risk assessment",
)

engine = BorrowingsModule()


@app.post("/borrowings/analyze")
def analyze_borrowings(req: BorrowingsRequest):
    try:
        financial_years = [
            YearFinancialInput(**fy.dict())
            for fy in req.financial_data.financial_years
        ]

        module_input = BorrowingsInput(
            company_id=req.company.upper(),
            industry_code=(req.industry_code or "GENERAL").upper(),
            financials_5y=financial_years,
            industry_benchmarks=DEFAULT_BENCHMARKS,
            covenant_limits=DEFAULT_COVENANTS,
        )
        result = engine.run(module_input)
        return result.dict()
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=ve.errors())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)