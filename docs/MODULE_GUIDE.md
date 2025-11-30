# Module Configuration Guide v3.0

## New Architecture: YAML-Driven GenericAgent

The system now uses a **single source of truth** (YAML) with a **single GenericAgent class** that handles all 12 modules.

### Key Benefits:
- **1 YAML config file** - All modules defined in one place
- **1 GenericAgent class** - No duplicate code per module
- **1 AgentOrchestrator** - Single entry point for all analysis
- **Add new module** - Just add to YAML, no code changes needed

---

## Quick Start

### Running the API

```bash
cd fundamental_analysis
python -m src.main
```

API available at `http://localhost:8000`

### Run Analysis via API

```bash
# Run single module
POST /analyze/equity_funding_mix
{
    "company": "ACME",
    "financial_data": {...}
}

# Run multiple modules
POST /analyze
{
    "company": "ACME",
    "modules": ["borrowings", "equity_funding_mix", "liquidity"],
    "financial_data": {...}
}

# Run ALL modules
POST /analyze
{
    "company": "ACME",
    "financial_data": {...}
}
```

### Run Analysis via Python

```python
from src.app.agents import AgentOrchestrator, GenericAgent

# Using orchestrator (recommended)
orchestrator = AgentOrchestrator()
result = orchestrator.run("equity_funding_mix", data)

# Or run all modules
results = orchestrator.run_all(data)

# Direct agent usage
agent = GenericAgent("profitability")
result = agent.analyze(data)
```

---

## File Structure (Simplified)

```
src/app/
├── config/
│   ├── agents_config.yaml   # ALL 12 modules defined here
│   ├── config_loader.py     # YAML loader utilities
│   └── __init__.py          # Exports
├── agents/
│   ├── generic_agent.py     # SINGLE class for ALL modules
│   ├── agent_orchestrator.py # SINGLE entry point
│   └── __init__.py          # Exports
└── ...
```

**That's it!** No separate folders per module. No 6 files per module.

---

## All 12 Modules

| Module ID | Name | Description |
|-----------|------|-------------|
| `borrowings` | Borrowings | Debt structure, leverage, and borrowing risk |
| `equity_funding_mix` | Equity Funding Mix | Equity quality, retained earnings, ROE |
| `liquidity` | Liquidity | Short-term liquidity, cash position |
| `working_capital` | Working Capital | WC efficiency, cash conversion cycle |
| `capex_asset_quality` | Capex Asset Quality | Capital expenditure, asset utilization |
| `profitability` | Profitability | Margin analysis, earnings quality |
| `cash_flow` | Cash Flow | OCF, FCF, cash sustainability |
| `solvency` | Solvency | Long-term solvency, financial stability |
| `valuation` | Valuation | P/E, P/B, EV/EBITDA metrics |
| `growth` | Growth | Revenue and earnings trajectory |
| `risk_assessment` | Risk Assessment | Financial and operational risk |
| `credit_rating` | Credit Rating | Credit quality assessment |

---

## Adding a New Module

### Step 1: Add to agents_config.yaml

```yaml
modules:
  # ... existing modules ...
  
  my_new_module:
    enabled: true
    name: "MyNewModule"
    description: "What this module does"
    agent_prompt: |
      You are an expert analyst for this specific domain...
    output_sections: ["Section 1", "Section 2", "Conclusion"]
    input_fields: [field1, field2, field3]
    benchmarks:
      threshold_high: 1.0
      threshold_low: 0.5
    metrics:
      metric_1: "field1 / field2"
      metric_2: "field2 + field3"
    rules:
      - id: M1
        name: "Rule Name"
        metric: metric_1
        red: "> 1.0"
        yellow: "> 0.5"
        green: "<= 0.5"
```

### Step 2: Add Metric Calculation (if complex)

If your metrics need special calculation logic, add a method to `generic_agent.py`:

```python
def _calc_my_new_module_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
    """Calculate my_new_module metrics"""
    field1 = data.get("field1", 0)
    field2 = data.get("field2", 1)
    field3 = data.get("field3", 0)
    
    return {
        "metric_1": self._safe_div(field1, field2),
        "metric_2": field2 + field3,
    }
```

And add the case to `calculate_metrics()`:
```python
elif self.module_id == "my_new_module":
    metrics = self._calc_my_new_module_metrics(data)
```

### Step 3: Test

```python
from src.app.agents import analyze

result = analyze("my_new_module", {
    "field1": 100,
    "field2": 200,
    "field3": 50,
})
print(result.score, result.metrics)
```

**Done!** No new files needed.

---

## YAML Configuration Reference

### Module Structure

```yaml
module_id:
  enabled: true/false           # Toggle module on/off
  name: "DisplayName"           # Human-readable name
  description: "..."            # Module description
  agent_prompt: |               # LLM system prompt
    You are...
  output_sections: [...]        # Sections for LLM output
  input_fields: [...]           # Required input fields
  benchmarks:                   # Threshold constants
    key: value
  metrics:                      # Metric definitions
    metric_name: "formula"
  trends: [...]                 # Trend calculations (CAGR)
  rules:                        # Evaluation rules
    - id: XX
      name: "..."
      metric: "..."
      red: "condition"
      yellow: "condition"
      green: "condition"
```

### Rule Conditions

```yaml
# Comparison operators
red: "> 1.0"        # Greater than
yellow: ">= 0.5"    # Greater than or equal
green: "< 0.3"      # Less than
green: "<= 0.2"     # Less than or equal

# Special
yellow: "declining" # For trend-based (not auto-evaluated)
```

---

## API Reference

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API info |
| GET | `/modules` | List all modules |
| GET | `/modules/{id}` | Module details |
| GET | `/modules/{id}/required-fields` | Required input fields |
| POST | `/analyze` | Run all/selected modules |
| POST | `/analyze/{module_id}` | Run specific module |
| POST | `/reload-config` | Reload YAML config |

### Response Format

```json
{
  "company": "ACME",
  "analysis": {
    "module_name": "EquityFundingMix",
    "module_id": "equity_funding_mix",
    "timestamp": "2024-01-15T10:30:00",
    "metrics": {
      "roe": 0.1397,
      "dividend_payout_ratio": 0.125
    },
    "rules_results": [
      {
        "rule_id": "B1",
        "rule_name": "Return on Equity",
        "metric_name": "roe",
        "value": 0.1397,
        "status": "YELLOW",
        "message": "Return on Equity is in YELLOW zone (13.97%)"
      }
    ],
    "score": 63,
    "score_interpretation": "Fair",
    "llm_narrative": "..."
  }
}
```

---

## Scoring System

- **Base Score**: 70
- **RED**: -10 points per rule
- **YELLOW**: -5 points per rule
- **GREEN**: +1 point per rule
- **Range**: 0-100

| Score | Interpretation |
|-------|----------------|
| 80+ | Excellent |
| 65-79 | Good |
| 50-64 | Fair |
| 35-49 | Poor |
| <35 | Critical |

---

## Sample Request Body

```json
{
  "company": "TESTCO",
  "generate_narrative": false,
  "modules": ["borrowings", "equity_funding_mix"],
  "financial_data": {
    "financial_years": [
      {
        "year": 2024,
        "short_term_debt": 500,
        "long_term_debt": 1500,
        "total_equity": 3000,
        "revenue": 10000,
        "ebitda": 2000,
        "ebit": 1500,
        "finance_cost": 200,
        "share_capital": 1000,
        "reserves_and_surplus": 2000,
        "net_worth": 3000,
        "pat": 800,
        "dividend_paid": -100,
        "free_cash_flow": 600
      }
    ]
  }
}
```

---

## Migration from Old Architecture

If you have existing module files (like `equity_funding_module/`), you can keep them for backward compatibility, but the new `GenericAgent` approach is recommended for new modules.

The old modules still work and can be called directly if needed.
