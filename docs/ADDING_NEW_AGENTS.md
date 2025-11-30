# How to Add New Analysis Agents

This guide explains how to add new analysis modules (agents) to the Fundamental Analysis Engine. The system uses **YAML-driven configuration**, so adding a new agent requires **NO Python code changes** for basic modules.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Quick Start - Add a Module in 5 Minutes](#quick-start---add-a-module-in-5-minutes)
3. [Step-by-Step Guide](#step-by-step-guide)
4. [YAML Configuration Reference](#yaml-configuration-reference)
5. [Rule Configuration](#rule-configuration)
6. [Adding Investor Insights](#adding-investor-insights)
7. [Custom Metric Calculations](#custom-metric-calculations)
8. [Testing Your New Module](#testing-your-new-module)
9. [Examples](#examples)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  agents_config.yaml                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ modules:                                             │    │
│  │   borrowings: {...}                                  │    │
│  │   equity_funding_mix: {...}                          │    │
│  │   YOUR_NEW_MODULE: {...}  ←── Add here!             │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    GenericAgent                              │
│  • Reads config from YAML                                   │
│  • Calculates metrics                                       │
│  • Evaluates rules                                          │
│  • Generates insights                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph Workflow                          │
│  • Auto-detects new modules                                 │
│  • Creates nodes dynamically                                │
│  • Routes to your module                                    │
└─────────────────────────────────────────────────────────────┘
```

**Key Point:** The workflow automatically detects and includes any enabled module in `agents_config.yaml`.

---

## Quick Start - Add a Module in 5 Minutes

### Step 1: Open the YAML config

```
src/app/config/agents_config.yaml
```

### Step 2: Add your module

```yaml
modules:
  # ... existing modules ...
  
  # YOUR NEW MODULE
  liquidity:
    enabled: true
    name: "Liquidity"
    description: "Short-term liquidity and cash position analysis"
    input_fields: [cash_and_equivalents, current_assets, current_liabilities, inventory]
    benchmarks:
      current_ratio_low: 1.0
      quick_ratio_low: 0.8
    metrics:
      current_ratio: "current_assets / current_liabilities"
      quick_ratio: "(current_assets - inventory) / current_liabilities"
    rules:
      - id: L1
        name: "Current Ratio"
        metric: current_ratio
        red: "< 1.0"
        yellow: "< 1.5"
        green: ">= 1.5"
        insights:
          red:
            summary: "Liquidity crisis risk"
            implication: "Current assets don't cover current liabilities"
            investor_action: "Check for immediate funding needs"
            risk_level: "Critical"
          green:
            summary: "Healthy liquidity position"
            implication: "Sufficient current assets to meet obligations"
            investor_action: "No immediate concerns"
            risk_level: "Low"
```

### Step 3: Reload and test

```bash
# Reload config (if server running)
curl -X POST http://127.0.0.1:8000/reload-config

# Or restart server
python -m src.main
```

**Done!** Your new module is now available at `/analyze` with `modules: ["liquidity"]`.

---

## Step-by-Step Guide

### Step 1: Plan Your Module

Before coding, define:

| Item | Example |
|------|---------|
| **Module ID** | `liquidity` (lowercase, snake_case) |
| **Module Name** | `"Liquidity"` (display name) |
| **Description** | What this module analyzes |
| **Input Fields** | What data it needs |
| **Metrics** | What calculations to perform |
| **Rules** | What conditions to evaluate |
| **Benchmarks** | Threshold values for rules |

### Step 2: Define Input Fields

Add required fields to `src/app/schemas.py`:

```python
class FinancialYearInput(BaseModel):
    # ... existing fields ...
    
    # === YOUR NEW MODULE ===
    cash_and_equivalents: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    inventory: Optional[float] = None
```

### Step 3: Add Module to YAML

Open `src/app/config/agents_config.yaml` and add:

```yaml
modules:
  # ... existing modules ...
  
  liquidity:
    enabled: true
    name: "Liquidity"
    description: "Short-term liquidity and cash position analysis"
    
    agent_prompt: |
      You are a liquidity analyst. Evaluate short-term solvency,
      cash adequacy, and working capital management.
    
    output_sections:
      - "Liquidity overview"
      - "Cash position"
      - "Working capital"
      - "Concerns"
      - "Assessment"
    
    input_fields:
      - cash_and_equivalents
      - current_assets
      - current_liabilities
      - inventory
      - daily_operating_expenses
    
    benchmarks:
      current_ratio_low: 1.0
      current_ratio_moderate: 1.5
      quick_ratio_low: 0.8
      cash_ratio_low: 0.2
      cash_days_low: 30
    
    metrics:
      current_ratio: "current_assets / current_liabilities"
      quick_ratio: "(current_assets - inventory) / current_liabilities"
      cash_ratio: "cash_and_equivalents / current_liabilities"
      cash_coverage_days: "cash_and_equivalents / daily_operating_expenses"
    
    trends:
      - current_ratio_trend
      - cash_trend
    
    rules:
      - id: L1
        name: "Current Ratio"
        metric: current_ratio
        red: "< 1.0"
        yellow: "< 1.5"
        green: ">= 1.5"
        insights:
          red:
            summary: "Liquidity crisis risk"
            implication: "Current liabilities exceed current assets. May struggle to meet short-term obligations."
            investor_action: "URGENT: Check for credit line availability, assess near-term maturities."
            risk_level: "Critical"
            peer_context: "Healthy companies maintain current ratio above 1.5x"
          yellow:
            summary: "Tight liquidity position"
            implication: "Just enough current assets to cover liabilities. Limited margin for unexpected needs."
            investor_action: "Monitor cash flow closely. Check for seasonal patterns."
            risk_level: "Medium"
          green:
            summary: "Comfortable liquidity cushion"
            implication: "Sufficient current assets provide buffer for operations and contingencies."
            investor_action: "Healthy position; no immediate concerns."
            risk_level: "Low"
      
      - id: L2
        name: "Quick Ratio"
        metric: quick_ratio
        red: "< 0.5"
        yellow: "< 0.8"
        green: ">= 0.8"
        insights:
          red:
            summary: "Cash and receivables insufficient"
            implication: "Cannot cover liabilities without selling inventory. Inventory-dependent liquidity is risky."
            investor_action: "Check inventory quality and turnover. Assess collection efficiency."
            risk_level: "High"
          green:
            summary: "Strong quick liquidity"
            implication: "Can meet obligations from liquid assets alone."
            investor_action: "Positive indicator of short-term financial health."
            risk_level: "Low"
```

### Step 4: Add Metric Calculation (If Custom Logic Needed)

If your metrics need special calculation logic, add to `src/app/agents/generic_agent.py`:

```python
# In GenericAgent.calculate_metrics()
def calculate_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
    metrics = {}
    
    # ... existing module checks ...
    
    elif self.module_id == "liquidity":
        metrics = self._calc_liquidity_metrics(data)
    
    # ... rest of method ...

# Add the calculation method
def _calc_liquidity_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
    """Calculate liquidity metrics"""
    current_assets = data.get("current_assets", 0) or 0
    current_liabilities = data.get("current_liabilities", 0) or 0
    inventory = data.get("inventory", 0) or 0
    cash = data.get("cash_and_equivalents", 0) or 0
    daily_expenses = data.get("daily_operating_expenses", 0) or 0
    
    return {
        "current_ratio": self._safe_div(current_assets, current_liabilities),
        "quick_ratio": self._safe_div(current_assets - inventory, current_liabilities),
        "cash_ratio": self._safe_div(cash, current_liabilities),
        "cash_coverage_days": self._safe_div(cash, daily_expenses) if daily_expenses > 0 else 0,
    }
```

### Step 5: Test Your Module

```bash
# Restart server
python -m src.main

# Check module is listed
curl http://127.0.0.1:8000/modules

# Test analysis
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "company": "TEST",
    "financial_data": {
      "financial_years": [{
        "year": 2024,
        "current_assets": 100000,
        "current_liabilities": 80000,
        "inventory": 30000,
        "cash_and_equivalents": 20000
      }]
    },
    "modules": ["liquidity"]
  }'
```

---

## YAML Configuration Reference

### Module Structure

```yaml
module_id:                    # Unique identifier (snake_case)
  enabled: true/false         # Enable/disable module
  name: "Display Name"        # Human-readable name
  description: "..."          # Module description
  
  agent_prompt: |             # LLM prompt for narrative generation
    You are a [role]...
  
  output_sections:            # Sections for LLM output
    - "Section 1"
    - "Section 2"
  
  input_fields:               # Required data fields
    - field1
    - field2
  
  benchmarks:                 # Threshold values
    key: value
  
  metrics:                    # Metric formulas (descriptive)
    metric_name: "formula"
  
  trends:                     # Trend calculations
    - trend_name
  
  rules:                      # Evaluation rules
    - id: R1
      name: "Rule Name"
      metric: metric_name
      red: "condition"
      yellow: "condition"
      green: "condition"
      insights:
        red: {...}
        yellow: {...}
        green: {...}
```

### Field Types

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | boolean | Yes | Whether module is active |
| `name` | string | Yes | Display name |
| `description` | string | Yes | What module does |
| `agent_prompt` | string | No | LLM prompt for narratives |
| `input_fields` | list | Yes | Required input data fields |
| `benchmarks` | dict | No | Threshold values for rules |
| `metrics` | dict | Yes | Metric definitions |
| `rules` | list | Yes | Evaluation rules |
| `trends` | list | No | Trend calculations |

---

## Rule Configuration

### Rule Structure

```yaml
rules:
  - id: "R1"                  # Unique rule ID
    name: "Rule Name"         # Display name
    metric: "metric_name"     # Which metric to evaluate
    red: "< 1.0"             # RED condition (critical)
    yellow: "< 2.0"          # YELLOW condition (warning)
    green: ">= 2.0"          # GREEN condition (healthy)
    insights:                 # Optional investor insights
      red:
        summary: "..."
        implication: "..."
        investor_action: "..."
        risk_level: "Critical|High|Medium|Low"
        peer_context: "..."   # Optional
      yellow:
        # ...
      green:
        # ...
```

### Condition Syntax

| Condition | Meaning | Example |
|-----------|---------|---------|
| `> X` | Greater than X | `"> 1.0"` |
| `>= X` | Greater than or equal | `">= 1.5"` |
| `< X` | Less than X | `"< 0.5"` |
| `<= X` | Less than or equal | `"<= 0.8"` |
| `"-"` | Not applicable | Skip this status |

### Status Meanings

| Status | Color | Impact | Meaning |
|--------|-------|--------|---------|
| RED | 🔴 | -10 pts | Critical issue, high risk |
| YELLOW | 🟡 | -5 pts | Warning, needs attention |
| GREEN | 🟢 | +1 pt | Healthy, positive signal |

---

## Adding Investor Insights

Insights make rule results actionable for investors:

```yaml
insights:
  red:
    summary: "One-line headline"
    implication: "What this means for the company"
    investor_action: "What investor should do"
    risk_level: "Critical|High|Medium|Low"
    peer_context: "How this compares to peers (optional)"
  
  yellow:
    summary: "..."
    implication: "..."
    investor_action: "..."
    risk_level: "..."
  
  green:
    summary: "..."
    implication: "..."
    investor_action: "..."
    risk_level: "..."
```

### Example with Full Insights

```yaml
- id: L1
  name: "Current Ratio"
  metric: current_ratio
  red: "< 1.0"
  yellow: "< 1.5"
  green: ">= 1.5"
  insights:
    red:
      summary: "Liquidity crisis risk"
      implication: "Current liabilities exceed current assets. May struggle to meet short-term obligations without additional financing or asset sales."
      investor_action: "URGENT: Check credit line availability, review near-term debt maturities, assess management's liquidity improvement plan."
      risk_level: "Critical"
      peer_context: "Most investment-grade companies maintain current ratio above 1.2x"
    yellow:
      summary: "Tight liquidity position"
      implication: "Just enough current assets to cover liabilities. Limited buffer for unexpected cash needs or seasonal fluctuations."
      investor_action: "Monitor monthly cash flow, check for seasonal patterns, review working capital management."
      risk_level: "Medium"
    green:
      summary: "Comfortable liquidity cushion"
      implication: "Sufficient current assets provide buffer for operations and unexpected needs. Strong short-term financial position."
      investor_action: "Healthy indicator. Check if excess liquidity could be deployed for growth or shareholder returns."
      risk_level: "Low"
```

---

## Custom Metric Calculations

### When to Add Custom Logic

Add Python code if your metrics need:
- Complex calculations
- Conditional logic
- Historical data (CAGR, trends)
- Cross-field validations

### Adding a Custom Calculation

1. **Add module check in `calculate_metrics()`:**

```python
# In src/app/agents/generic_agent.py

def calculate_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
    if self.module_id == "your_module":
        metrics = self._calc_your_module_metrics(data)
    # ...
```

2. **Implement the calculation method:**

```python
def _calc_your_module_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
    """Calculate metrics for your module"""
    
    # Get inputs with safe defaults
    field1 = data.get("field1", 0) or 0
    field2 = data.get("field2", 0) or 0
    
    # Calculate metrics
    ratio = self._safe_div(field1, field2)
    
    # Complex calculations
    if field1 > 0 and field2 > 0:
        complex_metric = (field1 / field2) * 100
    else:
        complex_metric = 0
    
    return {
        "ratio": ratio,
        "complex_metric": complex_metric,
    }
```

3. **Use `_safe_div()` for division:**

```python
# Prevents ZeroDivisionError
result = self._safe_div(numerator, denominator, default=0.0)
```

### Adding CAGR/Trend Calculations

```python
def _calc_cagr(self, values: List[float]) -> float:
    """Calculate Compound Annual Growth Rate"""
    if len(values) < 2:
        return 0
    start_val = values[-1]  # Oldest
    end_val = values[0]     # Newest
    periods = len(values) - 1
    
    if start_val <= 0 or end_val <= 0:
        return 0
    
    return ((end_val / start_val) ** (1 / periods) - 1) * 100
```

---

## Testing Your New Module

### 1. Unit Test

Create `test_your_module.py`:

```python
import sys
sys.path.insert(0, ".")

from src.app.agents import GenericAgent

def test_module():
    # Create agent
    agent = GenericAgent("your_module_id")
    
    # Test data
    test_data = {
        "field1": 100,
        "field2": 50,
        # ... other fields
    }
    
    # Run analysis
    result = agent.analyze(data=test_data, generate_llm_narrative=False)
    
    print(f"Module: {result.module_name}")
    print(f"Score: {result.score}")
    print(f"Metrics: {result.metrics}")
    print(f"Rules: {len(result.rules_results)} evaluated")
    
    for rule in result.rules_results:
        print(f"  {rule.rule_name}: {rule.status} - {rule.summary}")

if __name__ == "__main__":
    test_module()
```

### 2. Integration Test

```python
from src.app.agents import AnalysisWorkflow, create_workflow

workflow = create_workflow()
print(f"Modules available: {workflow.available_modules}")

result = workflow.run(
    company="TEST",
    current_data={"field1": 100, "field2": 50},
    modules=["your_module_id"]
)

print(f"Status: {result['workflow_status']}")
print(f"Score: {result['overall_score']}")
print(f"Risk Flags: {result['risk_flags']}")
```

### 3. API Test

```bash
# Start server
python -m src.main

# Test endpoint
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "company": "TEST",
    "financial_data": {
      "financial_years": [{
        "year": 2024,
        "field1": 100,
        "field2": 50
      }]
    },
    "modules": ["your_module_id"]
  }'
```

---

## Examples

### Example 1: Simple Module (Working Capital)

```yaml
working_capital:
  enabled: true
  name: "Working Capital"
  description: "Working capital efficiency and cash conversion cycle"
  input_fields: [trade_receivables, trade_payables, inventory, revenue, cogs]
  
  benchmarks:
    dso_high: 90
    dio_high: 120
    ccc_high: 90
  
  metrics:
    dso: "(trade_receivables / revenue) * 365"
    dio: "(inventory / cogs) * 365"
    dpo: "(trade_payables / cogs) * 365"
    cash_conversion_cycle: "dso + dio - dpo"
  
  rules:
    - id: W1
      name: "Cash Conversion Cycle"
      metric: cash_conversion_cycle
      red: "> 90"
      yellow: "> 60"
      green: "<= 60"
      insights:
        red:
          summary: "Long cash conversion cycle"
          implication: "Takes 90+ days to convert investments to cash. Working capital intensive."
          investor_action: "Review receivables aging, inventory turnover, and payables terms."
          risk_level: "High"
        green:
          summary: "Efficient cash conversion"
          implication: "Quick conversion of investments to cash. Low working capital needs."
          investor_action: "Competitive advantage; supports growth without proportional capital."
          risk_level: "Low"
```

### Example 2: Module with Trends (Profitability)

```yaml
profitability:
  enabled: true
  name: "Profitability"
  description: "Margin analysis and profitability trends"
  input_fields: [revenue, gross_profit, ebitda, ebit, pat]
  
  benchmarks:
    gross_margin_low: 0.20
    ebitda_margin_low: 0.10
    net_margin_low: 0.05
  
  metrics:
    gross_margin: "gross_profit / revenue"
    ebitda_margin: "ebitda / revenue"
    ebit_margin: "ebit / revenue"
    net_margin: "pat / revenue"
  
  trends:
    - gross_margin_trend
    - ebitda_margin_trend
    - net_margin_trend
  
  rules:
    - id: P1
      name: "Gross Margin"
      metric: gross_margin
      red: "< 0.20"
      yellow: "< 0.30"
      green: ">= 0.30"
      insights:
        red:
          summary: "Low pricing power or high costs"
          implication: "Gross margin below 20% indicates weak competitive position or high input costs."
          investor_action: "Compare with peers. Check for pricing pressure or cost inflation."
          risk_level: "High"
        green:
          summary: "Healthy gross margin"
          implication: "Strong pricing power and/or efficient cost management."
          investor_action: "Positive indicator; supports operating leverage."
          risk_level: "Low"
```

---

## Checklist for New Module

- [ ] Define module ID (snake_case)
- [ ] Add input fields to `schemas.py`
- [ ] Add module config to `agents_config.yaml`
- [ ] Add all required benchmarks
- [ ] Add all metric definitions
- [ ] Add rules with RED/YELLOW/GREEN conditions
- [ ] Add investor insights for each rule status
- [ ] Add custom metric calculation (if needed) in `generic_agent.py`
- [ ] Test with unit test
- [ ] Test with API call
- [ ] Verify in `/modules` endpoint
- [ ] Verify in `/graph` visualization

---

## Troubleshooting

### Module not appearing

1. Check `enabled: true` in YAML
2. Reload config: `POST /reload-config`
3. Restart server

### Metrics showing 0

1. Check input fields are provided
2. Check field names match exactly
3. Add custom calculation in `generic_agent.py`

### Rules not evaluating

1. Check metric name matches
2. Check condition syntax
3. Check for None/null values in data

### Insights not showing

1. Check `insights` section in rule
2. Check status matches (red/yellow/green)
3. Verify YAML indentation

---

## Support

For complex modules or custom requirements:
1. Check existing modules for patterns
2. Review `generic_agent.py` for calculation examples
3. Test incrementally with simple data
