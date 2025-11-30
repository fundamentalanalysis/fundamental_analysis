# =============================================================
# main.py - Multi-Module Analytical Engine v3.0
# SINGLE ENTRY POINT using YAML-driven GenericAgent
# =============================================================

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any

# -------------------------------------------
# FIX PATH
# -------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

# -------------------------------------------
# IMPORT SCHEMAS & AGENTS
# -------------------------------------------
from src.app.schemas import (
    FinancialYearInput,
    FinancialData,
    AnalyzeRequest,
)
from src.app.agents import AgentOrchestrator, GenericAgent


# ---------------------------------------------------------
# FASTAPI APP WITH LIFESPAN
# ---------------------------------------------------------

# Global orchestrator instance
orchestrator: AgentOrchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize orchestrator on startup, cleanup on shutdown"""
    global orchestrator
    orchestrator = AgentOrchestrator()
    print(f"Initialized {len(orchestrator.list_modules())} modules from YAML config")
    yield
    # Cleanup on shutdown (if needed)
    print("Shutting down...")

app = FastAPI(
    title="Fundamental Analysis Multi-Agent Engine",
    version="3.0",
    description="API for comprehensive financial analysis with 12 YAML-configurable modules",
    lifespan=lifespan
)


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def financial_year_to_dict(fy: FinancialYearInput) -> Dict[str, float]:
    """Convert FinancialYearInput to flat dictionary for GenericAgent"""
    data = fy.model_dump()
    
    # Add computed fields
    data["total_debt"] = data.get("short_term_debt", 0) + data.get("long_term_debt", 0)
    
    # Map revenue_wc if not set
    if data.get("revenue_wc", 0) == 0:
        data["revenue_wc"] = data.get("revenue", 0)
    
    # Map inventory_wc if not set  
    if data.get("inventory_wc", 0) == 0:
        data["inventory_wc"] = data.get("inventory", 0)
        
    return data


def prepare_historical_data(fds: List[FinancialYearInput]) -> List[Dict[str, float]]:
    """Convert list of financial years to historical data format"""
    # Sort by year ascending (oldest first) for CAGR calculations
    sorted_fds = sorted(fds, key=lambda x: x.year)
    return [financial_year_to_dict(fy) for fy in sorted_fds]


def calculate_yoy_growth(fds: List[FinancialYearInput]) -> Dict[str, Dict[str, Optional[float]]]:
    """
    Calculate Year-over-Year growth for all metrics across all years.
    Returns metrics in descending year order (newest first).
    
    Excludes debt maturity profile metrics that are only available for latest year:
    - total_debt_maturing_lt_1y, total_debt_maturing_1_3y, total_debt_maturing_gt_3y
    - weighted_avg_interest_rate, floating_rate_debt, fixed_rate_debt
    """
    # Metrics to exclude (only available for latest year)
    EXCLUDED_METRICS = {
        'total_debt_maturing_lt_1y',
        'total_debt_maturing_1_3y', 
        'total_debt_maturing_gt_3y',
        'weighted_avg_interest_rate',
        'floating_rate_debt',
        'fixed_rate_debt',
        'year',  # Not a metric
    }
    
    # Sort by year descending (newest first for output)
    sorted_fds = sorted(fds, key=lambda x: x.year, reverse=True)
    
    if len(sorted_fds) < 2:
        return {}
    
    # Convert to dicts
    years_data = [financial_year_to_dict(fy) for fy in sorted_fds]
    
    # Get all metric names from first year (excluding non-metrics)
    all_metrics = [
        key for key in years_data[0].keys() 
        if key not in EXCLUDED_METRICS and isinstance(years_data[0].get(key), (int, float, type(None)))
    ]
    
    yoy_growth = {}
    
    for metric in all_metrics:
        metric_growth = {}
        
        for i in range(len(years_data) - 1):
            current_year = sorted_fds[i].year
            current_val = years_data[i].get(metric)
            prev_val = years_data[i + 1].get(metric)
            
            # Format year as "MAR YYYY" (fiscal year ending March)
            year_label = f"MAR {current_year}"
            
            # Calculate YoY growth %
            if current_val is not None and prev_val is not None and prev_val != 0:
                growth_pct = round(((current_val - prev_val) / abs(prev_val)) * 100, 2)
                metric_growth[year_label] = growth_pct
            else:
                metric_growth[year_label] = None
        
        # Only include metrics that have at least one valid growth value
        if any(v is not None for v in metric_growth.values()):
            yoy_growth[metric] = metric_growth
    
    return yoy_growth


# ---------------------------------------------------------
# API ENDPOINTS
# ---------------------------------------------------------

@app.get("/")
def root():
    """API root with available endpoints"""
    return {
        "message": "Fundamental Analysis Multi-Agent Engine",
        "version": "3.0",
        "architecture": "YAML-driven GenericAgent with single entry point",
        "endpoints": {
            "/analyze": "POST - Run analysis with specified modules (or all)",
            "/analyze/{module_id}": "POST - Run specific module analysis",
            "/modules": "GET - List all available modules",
            "/modules/{module_id}": "GET - Get module details",
            "/modules/{module_id}/required-fields": "GET - Get required input fields",
            "/reload-config": "POST - Reload YAML configuration",
        }
    }


@app.get("/modules")
def list_modules(include_disabled: bool = False):
    """List all available analytical modules from YAML config"""
    modules = orchestrator.list_modules(include_disabled=include_disabled)
    return {
        "total_modules": len(modules),
        "modules": [m.model_dump() for m in modules],
    }


@app.get("/modules/{module_id}")
def get_module(module_id: str):
    """Get information about a specific module"""
    info = orchestrator.get_module_info(module_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not found")
    return info.model_dump()


@app.get("/modules/{module_id}/required-fields")
def get_module_fields(module_id: str):
    """Get required input fields for a module"""
    info = orchestrator.get_module_info(module_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not found")
    return {
        "module_id": module_id,
        "module_name": info.name,
        "required_fields": info.input_fields,
    }


@app.post("/reload-config")
def reload_config():
    """Reload YAML configuration (useful after editing agents_config.yaml)"""
    orchestrator.reload_config()
    modules = orchestrator.list_modules()
    return {
        "status": "success",
        "message": "Configuration reloaded",
        "modules_loaded": len(modules),
    }


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """
    Run comprehensive analysis with multiple modules.
    
    If no modules specified, runs all enabled modules.
    Includes YoY growth metrics for all years (descending order).
    """
    try:
        company = req.company.upper()
        fds = req.financial_data.financial_years
        
        # Use most recent year for current data
        sorted_fds = sorted(fds, key=lambda x: x.year, reverse=True)
        current_data = financial_year_to_dict(sorted_fds[0])
        historical_data = prepare_historical_data(fds)
        
        # Calculate YoY growth for all metrics
        yoy_growth = calculate_yoy_growth(fds)
        
        # Determine which modules to run
        if req.modules:
            result = orchestrator.run_multiple(
                module_ids=req.modules,
                data=current_data,
                historical_data=historical_data,
                generate_narrative=req.generate_narrative
            )
        else:
            result = orchestrator.run_all(
                data=current_data,
                historical_data=historical_data,
                generate_narrative=req.generate_narrative
            )
        
        return {
            "company": company,
            "analysis": result.model_dump(),
            "yoy_growth": {"metrics": yoy_growth},
        }
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/analyze/{module_id}")
def analyze_single_module(module_id: str, req: AnalyzeRequest):
    """Run analysis for a specific module with YoY growth metrics"""
    try:
        company = req.company.upper()
        fds = req.financial_data.financial_years
        
        # Use most recent year for current data
        sorted_fds = sorted(fds, key=lambda x: x.year, reverse=True)
        current_data = financial_year_to_dict(sorted_fds[0])
        historical_data = prepare_historical_data(fds)
        
        # Calculate YoY growth for all metrics
        yoy_growth = calculate_yoy_growth(fds)
        
        result = orchestrator.run(
            module_id=module_id,
            data=current_data,
            historical_data=historical_data,
            generate_narrative=req.generate_narrative
        )
        
        return {
            "company": company,
            "module": module_id,
            "analysis": result.model_dump(),
            "yoy_growth": {"metrics": yoy_growth},
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------------------------------------------------------
# RUN SERVER
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
