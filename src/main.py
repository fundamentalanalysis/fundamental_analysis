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
from src.app.agents import AgentOrchestrator, GenericAgent, AnalysisWorkflow, create_workflow


# ---------------------------------------------------------
# FASTAPI APP WITH LIFESPAN
# ---------------------------------------------------------

# Global instances
orchestrator: AgentOrchestrator = None
workflow: AnalysisWorkflow = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize orchestrator and workflow on startup, cleanup on shutdown"""
    global orchestrator, workflow
    orchestrator = AgentOrchestrator()
    workflow = create_workflow(enable_checkpoints=True)
    print(f"Initialized {len(orchestrator.list_modules())} modules from YAML config")
    print("LangGraph workflow initialized")
    
    # Save workflow graph on startup
    try:
        import os
        graph_dir = os.path.join(ROOT, "graphs")
        os.makedirs(graph_dir, exist_ok=True)
        
        # Save PNG
        png_path = os.path.join(graph_dir, "workflow_graph.png")
        workflow.save_graph_image(png_path)
        print(f"✅ Workflow graph saved to: {png_path}")
        
        # Save Mermaid markdown
        graph = workflow.graph.get_graph()
        mermaid_code = graph.draw_mermaid()
        
        md_path = os.path.join(graph_dir, "workflow_graph.md")
        with open(md_path, "w") as f:
            f.write("# LangGraph Workflow Visualization\n\n")
            f.write(f"## Available Modules: {', '.join(workflow.available_modules)}\n\n")
            f.write("```mermaid\n")
            f.write(mermaid_code)
            f.write("\n```\n")
        print(f"✅ Workflow mermaid saved to: {md_path}")
        
    except Exception as e:
        print(f"⚠️ Could not save workflow graph: {e}")
    
    yield
    # Cleanup on shutdown (if needed)
    print("Shutting down...")

app = FastAPI(
    title="Fundamental Analysis Multi-Agent Engine",
    version="3.0",
    description="API for comprehensive financial analysis with 12 YAML-configurable modules and LangGraph workflow",
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


# Metric descriptions for investor-friendly summaries
METRIC_DESCRIPTIONS = {
    # Debt metrics
    "short_term_debt": {"name": "Short-term Debt", "category": "Leverage", "good_direction": "stable", "description": "Debt maturing within 1 year"},
    "long_term_debt": {"name": "Long-term Debt", "category": "Leverage", "good_direction": "stable", "description": "Debt maturing after 1 year"},
    "total_debt": {"name": "Total Debt", "category": "Leverage", "good_direction": "down", "description": "Combined short and long-term borrowings"},
    "total_equity": {"name": "Total Equity", "category": "Capital Structure", "good_direction": "up", "description": "Shareholders' funds including reserves"},
    
    # Profitability metrics
    "revenue": {"name": "Revenue", "category": "Growth", "good_direction": "up", "description": "Total sales/income from operations"},
    "ebitda": {"name": "EBITDA", "category": "Profitability", "good_direction": "up", "description": "Earnings before interest, tax, depreciation & amortization"},
    "ebit": {"name": "EBIT", "category": "Profitability", "good_direction": "up", "description": "Operating profit before interest and tax"},
    "pat": {"name": "PAT", "category": "Profitability", "good_direction": "up", "description": "Profit after tax - bottom line earnings"},
    
    # Cost metrics
    "finance_cost": {"name": "Finance Cost", "category": "Cost", "good_direction": "down", "description": "Interest and borrowing costs"},
    "interest_expense": {"name": "Interest Expense", "category": "Cost", "good_direction": "down", "description": "Interest paid on borrowings"},
    "cogs": {"name": "Cost of Goods Sold", "category": "Cost", "good_direction": "stable", "description": "Direct costs of production"},
    
    # Investment metrics
    "capex": {"name": "Capital Expenditure", "category": "Investment", "good_direction": "context", "description": "Investment in fixed assets"},
    "cwip": {"name": "CWIP", "category": "Investment", "good_direction": "context", "description": "Capital work-in-progress - ongoing projects"},
    "net_fixed_assets": {"name": "Net Fixed Assets", "category": "Assets", "good_direction": "up", "description": "Fixed assets after depreciation"},
    "gross_block": {"name": "Gross Block", "category": "Assets", "good_direction": "up", "description": "Total fixed assets at cost"},
    
    # Equity & Funding
    "share_capital": {"name": "Share Capital", "category": "Capital Structure", "good_direction": "stable", "description": "Paid-up equity share capital"},
    "reserves_and_surplus": {"name": "Reserves & Surplus", "category": "Capital Structure", "good_direction": "up", "description": "Retained earnings and other reserves"},
    "net_worth": {"name": "Net Worth", "category": "Capital Structure", "good_direction": "up", "description": "Total shareholders' equity"},
    "dividend_paid": {"name": "Dividend Paid", "category": "Shareholder Returns", "good_direction": "up", "description": "Cash dividends distributed to shareholders"},
    
    # Cash Flow metrics
    "operating_cash_flow": {"name": "Operating Cash Flow", "category": "Cash Flow", "good_direction": "up", "description": "Cash generated from core operations"},
    "free_cash_flow": {"name": "Free Cash Flow", "category": "Cash Flow", "good_direction": "up", "description": "Cash available after capex"},
    "cash_and_equivalents": {"name": "Cash & Equivalents", "category": "Liquidity", "good_direction": "up", "description": "Liquid cash and near-cash holdings"},
    
    # Working Capital metrics
    "current_assets": {"name": "Current Assets", "category": "Working Capital", "good_direction": "up", "description": "Assets convertible to cash within 1 year"},
    "current_liabilities": {"name": "Current Liabilities", "category": "Working Capital", "good_direction": "stable", "description": "Obligations due within 1 year"},
    "inventory": {"name": "Inventory", "category": "Working Capital", "good_direction": "context", "description": "Stock of raw materials, WIP, finished goods"},
    "trade_receivables": {"name": "Trade Receivables", "category": "Working Capital", "good_direction": "context", "description": "Amounts owed by customers"},
    "trade_payables": {"name": "Trade Payables", "category": "Working Capital", "good_direction": "context", "description": "Amounts owed to suppliers"},
    
    # Balance Sheet
    "total_assets": {"name": "Total Assets", "category": "Balance Sheet", "good_direction": "up", "description": "Sum of all company assets"},
    "total_liabilities": {"name": "Total Liabilities", "category": "Balance Sheet", "good_direction": "stable", "description": "Sum of all company obligations"},
    "book_value": {"name": "Book Value", "category": "Valuation", "good_direction": "up", "description": "Net asset value per share"},
}


def generate_metric_summary(metric: str, growth_values: Dict[str, float]) -> Dict[str, Any]:
    """
    Generate a pre-built summary for a metric based on its YoY growth pattern.
    """
    # Get metric info or use defaults
    metric_info = METRIC_DESCRIPTIONS.get(metric, {
        "name": metric.replace("_", " ").title(),
        "category": "Other",
        "good_direction": "context",
        "description": f"Financial metric: {metric}"
    })
    
    # Filter out None values for analysis
    valid_values = {k: v for k, v in growth_values.items() if v is not None}
    
    if not valid_values:
        return {
            "name": metric_info["name"],
            "category": metric_info["category"],
            "description": metric_info["description"],
            "trend": "Insufficient data",
            "assessment": "Unable to assess - insufficient historical data",
            "values": growth_values
        }
    
    values_list = list(valid_values.values())
    latest_growth = values_list[0] if values_list else 0
    avg_growth = sum(values_list) / len(values_list)
    
    # Determine trend
    if len(values_list) >= 2:
        if all(v > values_list[i+1] for i, v in enumerate(values_list[:-1])):
            trend = "Accelerating"
        elif all(v < values_list[i+1] for i, v in enumerate(values_list[:-1])):
            trend = "Decelerating"
        elif all(v > 0 for v in values_list):
            trend = "Consistently Growing"
        elif all(v < 0 for v in values_list):
            trend = "Consistently Declining"
        elif values_list[0] > 0 and values_list[-1] < 0:
            trend = "Recovering"
        elif values_list[0] < 0 and values_list[-1] > 0:
            trend = "Deteriorating"
        else:
            trend = "Volatile"
    else:
        trend = "Growing" if latest_growth > 0 else "Declining" if latest_growth < 0 else "Flat"
    
    # Generate assessment based on good_direction
    good_dir = metric_info["good_direction"]
    
    if good_dir == "up":
        if avg_growth > 10:
            assessment = f"Strong growth trajectory. {metric_info['name']} growing at {avg_growth:.1f}% avg - positive for fundamentals."
        elif avg_growth > 0:
            assessment = f"Moderate growth. {metric_info['name']} showing steady improvement at {avg_growth:.1f}% avg."
        elif avg_growth > -5:
            assessment = f"Relatively flat. {metric_info['name']} needs improvement to support growth."
        else:
            assessment = f"Concerning decline. {metric_info['name']} falling at {avg_growth:.1f}% avg - monitor closely."
    elif good_dir == "down":
        if avg_growth < -5:
            assessment = f"Positive trend. {metric_info['name']} declining at {avg_growth:.1f}% avg - improving efficiency."
        elif avg_growth < 5:
            assessment = f"Relatively stable. {metric_info['name']} under control."
        else:
            assessment = f"Rising concern. {metric_info['name']} growing at {avg_growth:.1f}% avg - may pressure margins."
    elif good_dir == "stable":
        if abs(avg_growth) < 10:
            assessment = f"Stable as expected. {metric_info['name']} maintaining consistency at {avg_growth:.1f}% avg."
        elif avg_growth > 15:
            assessment = f"Significant increase. {metric_info['name']} up {avg_growth:.1f}% avg - verify if strategic or concerning."
        else:
            assessment = f"Notable decrease. {metric_info['name']} down {avg_growth:.1f}% avg - check underlying reasons."
    else:  # context-dependent
        if abs(latest_growth) > 20:
            assessment = f"Significant movement. {metric_info['name']} changed {latest_growth:.1f}% recently - context-dependent interpretation needed."
        else:
            assessment = f"Moderate changes. {metric_info['name']} at {avg_growth:.1f}% avg growth - evaluate in business context."
    
    return {
        "name": metric_info["name"],
        "category": metric_info["category"],
        "description": metric_info["description"],
        "trend": trend,
        "latest_yoy": f"{latest_growth:+.2f}%" if latest_growth else "N/A",
        "avg_growth": f"{avg_growth:+.2f}%",
        "assessment": assessment,
        "values": growth_values
    }


def calculate_yoy_growth(fds: List[FinancialYearInput]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate Year-over-Year growth for all metrics across all years.
    Returns metrics in descending year order (newest first) with summaries.
    
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
            yoy_growth[metric] = generate_metric_summary(metric, metric_growth)
    
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
        "architecture": "YAML-driven GenericAgent with LangGraph workflow",
        "endpoints": {
            "/analyze": "POST - Run analysis with specified modules (or all)",
            "/analyze/{module_id}": "POST - Run specific module analysis",
            "/workflow/analyze": "POST - Run analysis with LangGraph workflow (recommended)",
            "/workflow/stream": "POST - Stream workflow execution with real-time updates",
            "/workflow/graph": "GET - Get workflow graph visualization",
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
# LANGGRAPH WORKFLOW ENDPOINTS
# ---------------------------------------------------------

@app.post("/workflow/analyze")
def workflow_analyze(req: AnalyzeRequest):
    """
    Run analysis using LangGraph workflow.
    
    This endpoint uses LangGraph for:
    - State-based workflow management
    - Automatic risk flag aggregation
    - Key insights extraction
    - Comprehensive summary generation
    
    Returns structured output with risk_flags, key_insights, and summary.
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
        
        # Run workflow
        result = workflow.run(
            company=company,
            current_data=current_data,
            historical_data=historical_data,
            modules=req.modules,
            generate_narrative=req.generate_narrative
        )
        
        return {
            "company": company,
            "workflow_status": result.get("workflow_status"),
            "overall_score": result.get("overall_score"),
            "modules_completed": result.get("modules_completed"),
            "modules_failed": result.get("modules_failed"),
            "risk_flags": result.get("risk_flags"),
            "key_insights": result.get("key_insights"),
            "module_results": result.get("module_results"),
            "summary": result.get("summary"),
            "yoy_growth": {"metrics": yoy_growth},
            "errors": result.get("errors"),
        }
        
    except Exception as e:
        import traceback
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status_code=500)


@app.post("/workflow/stream")
async def workflow_stream(req: AnalyzeRequest):
    """
    Stream workflow execution for real-time progress updates.
    
    Returns Server-Sent Events (SSE) with progress after each module.
    """
    from fastapi.responses import StreamingResponse
    import json
    
    company = req.company.upper()
    fds = req.financial_data.financial_years
    
    sorted_fds = sorted(fds, key=lambda x: x.year, reverse=True)
    current_data = financial_year_to_dict(sorted_fds[0])
    historical_data = prepare_historical_data(fds)
    
    async def generate():
        try:
            for state_update in workflow.stream(
                company=company,
                current_data=current_data,
                historical_data=historical_data,
                modules=req.modules,
                generate_narrative=req.generate_narrative
            ):
                # Send state update as SSE
                yield f"data: {json.dumps(state_update)}\n\n"
            
            yield f"data: {json.dumps({'status': 'completed'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


@app.get("/workflow/graph")
def get_workflow_graph():
    """Get a text visualization of the workflow graph"""
    try:
        graph_viz = workflow.get_graph_visualization()
        return {
            "graph": graph_viz,
            "modules": workflow.available_modules
        }
    except Exception as e:
        return {"error": str(e), "modules": workflow.available_modules}


@app.get("/workflow/modules")
def get_available_modules():
    """
    Get list of available modules for workflow execution.
    
    Use these module IDs in the 'modules' field of analyze requests
    to select which agents to run.
    
    Example usage:
    - modules: ["borrowings"] - Run only borrowings analysis
    - modules: ["equity_funding_mix"] - Run only equity funding mix
    - modules: ["borrowings", "equity_funding_mix"] - Run both
    - modules: null or omit - Run all enabled modules
    """
    return {
        "available_modules": workflow.available_modules,
        "total_count": len(workflow.available_modules),
        "usage_examples": {
            "single_module": {
                "modules": ["borrowings"],
                "description": "Run only the borrowings analysis module"
            },
            "multiple_modules": {
                "modules": ["borrowings", "equity_funding_mix"],
                "description": "Run both borrowings and equity_funding_mix modules"
            },
            "all_modules": {
                "modules": None,
                "description": "Run all enabled modules (default behavior)"
            }
        }
    }


# ---------------------------------------------------------
# RUN SERVER
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
