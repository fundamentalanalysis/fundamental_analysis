# Fundamental Analysis Multi-Agent Engine - API Documentation

## Overview

The Fundamental Analysis Engine is a FastAPI-based multi-agent system for comprehensive financial analysis. It uses **LangGraph** for workflow orchestration and **YAML-driven configuration** for analysis modules.

**Version:** 4.0  
**Architecture:** LangGraph Workflow with YAML-driven GenericAgents

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [API Endpoints](#api-endpoints)
3. [Request/Response Models](#requestresponse-models)
4. [Module Selection](#module-selection)
5. [Workflow Features](#workflow-features)
6. [Example Requests](#example-requests)

---

## Quick Start

### Installation

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Run the Server

```bash
python -m src.main
```

Server starts at: `http://127.0.0.1:8000`

### OpenAPI Documentation

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

---

## API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API root with available endpoints |
| `/analyze` | POST | Run financial analysis with LangGraph workflow |
| `/analyze/stream` | POST | Stream workflow execution with real-time updates |

### Module Information

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/modules` | GET | List all available analysis modules |
| `/modules/{module_id}` | GET | Get details for a specific module |
| `/modules/{module_id}/fields` | GET | Get required input fields for a module |

### Workflow & Configuration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/graph` | GET | Get workflow graph visualization |
| `/reload-config` | POST | Reload YAML configuration without restart |

---

## Request/Response Models

### AnalyzeRequest

```json
{
  "company": "RELIANCE",
  "financial_data": {
    "financial_years": [
      {
        "year": 2024,
        "revenue": 1000000,
        "ebitda": 200000,
        "short_term_debt": 50000,
        "long_term_debt": 150000,
        ...
      },
      {
        "year": 2023,
        ...
      }
    ]
  },
  "modules": ["borrowings", "equity_funding_mix"],  // Optional: null = all modules
  "generate_narrative": true
}
```

### AnalyzeResponse

```json
{
  "company": "RELIANCE",
  "workflow_status": "completed",
  "overall_score": 58,
  "modules_completed": ["borrowings", "equity_funding_mix"],
  "modules_failed": [],
  "risk_flags": [
    "[BORROWINGS] Debt CAGR vs EBITDA CAGR: Debt growing faster than earnings capacity"
  ],
  "key_insights": [
    "[BORROWINGS] ✓ Revenue growth supporting debt levels"
  ],
  "module_results": {
    "borrowings": {
      "module_name": "Borrowings",
      "score": 65,
      "metrics": {...},
      "rules_results": [...]
    }
  },
  "summary": "# Financial Analysis Summary...",
  "yoy_growth": {
    "metrics": {
      "revenue": {
        "name": "Revenue",
        "category": "Growth",
        "trend": "Consistently Growing",
        "latest_yoy": "+15.50%",
        "avg_growth": "+12.30%",
        "assessment": "Strong growth trajectory...",
        "values": {"MAR 2024": 15.5, "MAR 2023": 9.1}
      }
    }
  },
  "errors": []
}
```

---

## Module Selection

### Available Modules

| Module ID | Name | Description |
|-----------|------|-------------|
| `borrowings` | Borrowings | Debt structure, leverage, maturity profile, and borrowing risk |
| `equity_funding_mix` | Equity Funding Mix | Equity quality, retained earnings, dividend policy, funding mix |

### Selection Options

```json
// Run only borrowings
{"modules": ["borrowings"]}

// Run only equity_funding_mix  
{"modules": ["equity_funding_mix"]}

// Run both modules
{"modules": ["borrowings", "equity_funding_mix"]}

// Run ALL enabled modules (default)
{"modules": null}
```

---

## Workflow Features

### LangGraph Workflow

The engine uses LangGraph for:

1. **State-based workflow management** - Track progress through analysis
2. **Automatic risk flag aggregation** - Collect all RED status rules
3. **Key insights extraction** - Collect all GREEN status rules
4. **Comprehensive summary generation** - Markdown summary with risk assessment
5. **Streaming support** - Real-time progress updates
6. **Checkpointing** - Save/resume workflow state

### Workflow State

```python
AnalysisState = {
    "company": str,
    "current_data": Dict[str, float],
    "historical_data": List[Dict[str, float]],
    "modules_to_run": List[str],
    "modules_completed": List[str],
    "modules_failed": List[str],
    "module_results": Dict[str, Dict],
    "overall_score": int,
    "risk_flags": List[str],      # Critical issues (RED rules)
    "key_insights": List[str],    # Positive findings (GREEN rules)
    "final_summary": str,
    "workflow_status": str        # "running", "completed", "failed"
}
```

### Graph Visualization

On startup, the workflow graph is saved to:
- `graphs/workflow_graph.png` - PNG image
- `graphs/workflow_graph.md` - Mermaid markdown

---

## Example Requests

### Basic Analysis

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "company": "RELIANCE",
    "financial_data": {
      "financial_years": [
        {
          "year": 2024,
          "revenue": 900000,
          "ebitda": 150000,
          "ebit": 120000,
          "pat": 80000,
          "short_term_debt": 50000,
          "long_term_debt": 200000,
          "total_equity": 400000,
          "finance_cost": 20000,
          "share_capital": 10000,
          "reserves_and_surplus": 390000,
          "net_worth": 400000,
          "dividend_paid": -15000,
          "free_cash_flow": 60000
        },
        {
          "year": 2023,
          "revenue": 750000,
          "ebitda": 120000,
          "ebit": 100000,
          "pat": 65000,
          "short_term_debt": 40000,
          "long_term_debt": 180000,
          "total_equity": 350000,
          "finance_cost": 18000,
          "share_capital": 10000,
          "reserves_and_surplus": 340000,
          "net_worth": 350000,
          "dividend_paid": -12000,
          "free_cash_flow": 45000
        }
      ]
    },
    "modules": ["borrowings"],
    "generate_narrative": false
  }'
```

### Stream Analysis

```bash
curl -X POST http://127.0.0.1:8000/analyze/stream \
  -H "Content-Type: application/json" \
  -d '{"company": "TEST", "financial_data": {...}, "modules": null}'
```

Returns Server-Sent Events (SSE):
```
data: {"initialize": {...}}
data: {"router": {...}}
data: {"run_borrowings": {...}}
data: {"status": "completed"}
```

### List Modules

```bash
curl http://127.0.0.1:8000/modules
```

Response:
```json
{
  "total_modules": 2,
  "modules": [
    {"id": "borrowings", "name": "Borrowings", "description": "...", "enabled": true},
    {"id": "equity_funding_mix", "name": "EquityFundingMix", "description": "...", "enabled": true}
  ]
}
```

### Get Workflow Graph

```bash
curl http://127.0.0.1:8000/graph
```

Response:
```json
{
  "graph": "ASCII representation...",
  "modules": ["borrowings", "equity_funding_mix"],
  "usage_examples": {...}
}
```

---

## Input Fields Reference

### Borrowings Module

| Field | Type | Description |
|-------|------|-------------|
| `short_term_debt` | float | Debt maturing within 1 year |
| `long_term_debt` | float | Debt maturing after 1 year |
| `total_equity` | float | Total shareholders' equity |
| `revenue` | float | Total revenue |
| `ebitda` | float | Earnings before interest, tax, depreciation & amortization |
| `ebit` | float | Earnings before interest & tax |
| `finance_cost` | float | Interest expense and finance charges |
| `capex` | float | Capital expenditure |
| `cwip` | float | Capital work in progress |
| `total_debt_maturing_lt_1y` | float | Debt maturing < 1 year |
| `total_debt_maturing_1_3y` | float | Debt maturing 1-3 years |
| `total_debt_maturing_gt_3y` | float | Debt maturing > 3 years |
| `weighted_avg_interest_rate` | float | Weighted average cost of debt |
| `floating_rate_debt` | float | % of debt at floating rates |
| `fixed_rate_debt` | float | % of debt at fixed rates |

### Equity Funding Mix Module

| Field | Type | Description |
|-------|------|-------------|
| `share_capital` | float | Paid-up share capital |
| `reserves_and_surplus` | float | Retained earnings and reserves |
| `net_worth` | float | Total shareholders' equity |
| `pat` | float | Profit after tax |
| `dividend_paid` | float | Cash dividends paid (negative) |
| `free_cash_flow` | float | Operating cash flow - Capex |
| `new_share_issuance` | float | New shares issued during period |
| `debt_equitymix` | float | Total debt for funding mix analysis |

---

## Error Handling

### Common Errors

| Status Code | Error | Cause |
|-------------|-------|-------|
| 404 | Module not found | Invalid `module_id` |
| 500 | Internal error | Processing failure |

### Error Response

```json
{
  "error": "Error message",
  "traceback": "Full traceback for debugging"
}
```

---

## YoY Growth Metrics

The API automatically calculates Year-over-Year growth for all metrics:

```json
"yoy_growth": {
  "metrics": {
    "revenue": {
      "name": "Revenue",
      "category": "Growth",
      "description": "Total sales/income from operations",
      "trend": "Consistently Growing",
      "latest_yoy": "+15.50%",
      "avg_growth": "+12.30%",
      "assessment": "Strong growth trajectory. Revenue growing at 12.30% avg - positive for fundamentals.",
      "values": {
        "MAR 2024": 15.5,
        "MAR 2023": 9.1,
        "MAR 2022": 12.3
      }
    }
  }
}
```

### Trend Interpretations

| Trend | Meaning |
|-------|---------|
| Accelerating | Growth rate increasing each year |
| Decelerating | Growth rate decreasing each year |
| Consistently Growing | Positive growth all years |
| Consistently Declining | Negative growth all years |
| Recovering | Recent positive after negative |
| Deteriorating | Recent negative after positive |
| Volatile | Mixed positive and negative |

---

## Scoring System

### Score Calculation

- Base score: 70
- RED rule: -10 points
- YELLOW rule: -5 points
- GREEN rule: +1 point
- Score range: 0-100

### Score Interpretation

| Score | Status | Meaning |
|-------|--------|---------|
| 80-100 | ✅ Strong | Minimal concerns |
| 60-79 | ⚠️ Attention | Some issues to monitor |
| 40-59 | ⚠️ Caution | Multiple concerns |
| 0-39 | 🚨 Critical | Significant risks |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Server                        │
├─────────────────────────────────────────────────────────┤
│  /analyze  →  LangGraph Workflow                        │
│                    ↓                                     │
│              ┌─────────────┐                            │
│              │  Initialize │                            │
│              └──────┬──────┘                            │
│                     ↓                                    │
│              ┌─────────────┐                            │
│              │   Router    │←──────────────┐            │
│              └──────┬──────┘               │            │
│                     ↓                       │            │
│         ┌──────────────────────┐           │            │
│         │  run_borrowings      │───────────┤            │
│         │  run_equity_funding  │───────────┘            │
│         └──────────────────────┘                        │
│                     ↓                                    │
│              ┌─────────────┐                            │
│              │ Calc Score  │                            │
│              └──────┬──────┘                            │
│                     ↓                                    │
│              ┌─────────────┐                            │
│              │ Gen Summary │                            │
│              └──────┬──────┘                            │
│                     ↓                                    │
│                   END                                    │
└─────────────────────────────────────────────────────────┘
```

---

## Configuration Files

| File | Purpose |
|------|---------|
| `src/app/config/agents_config.yaml` | Module definitions, rules, benchmarks |
| `src/app/schemas.py` | Pydantic input/output models |
| `src/app/agents/workflow.py` | LangGraph workflow definition |
| `src/app/agents/generic_agent.py` | Universal agent implementation |

---

## Support

For issues or questions, refer to:
- API Docs: `/docs`
- Graph Visualization: `/graph`
- Module Details: `/modules/{id}`
