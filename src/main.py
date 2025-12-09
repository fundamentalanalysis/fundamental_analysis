# =============================================================
# main.py - UPDATED FOR YOUR NEW REQUEST FORMAT
# =============================================================

import json
import os
import sys
from fastapi import FastAPI, Request
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
# from src.app.capex_cwip_module.orchestrator import run_capex_cwip_module
from src.app.capex_cwip_module.orchestrator import CapexCwipModule



# ---------------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------------
app = FastAPI(
    title="Borrowings Analytical Engine",
    version="1.0",
    description="API for 1-year borrowings analysis"
)


# ---------------------------------------------------------
# MAIN API
# ---------------------------------------------------------
@app.post("/analyze")
async def analyze(req: Request):
    try:
        analyzer = CapexCwipModule()
        req_data =  await req.json()
        result = analyzer.run(req_data)
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)



# ---------------------------------------------------------
# RUN SERVER
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)