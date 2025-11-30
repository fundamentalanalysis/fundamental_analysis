# Configurable Multi-Agent Financial Analysis System

## Overview

This system provides a modular, configurable framework for financial analysis with LLM-powered agents. Each module focuses on a specific aspect of fundamental analysis (e.g., Borrowings, Equity & Funding Mix, Liquidity, etc.).

## Architecture

```
src/app/
├── config/
│   ├── __init__.py          # Config exports
│   ├── config_loader.py     # YAML configuration loader
│   └── agents_config.yaml   # Central module configuration
├── base/
│   ├── __init__.py
│   ├── base_agent.py        # Base agent class and registry
│   └── base_models.py       # Shared data models
├── borrowing_module/        # Debt analysis module
├── equity_funding_module/   # Equity & funding mix module
├── module_registry.py       # Module registration hub
└── config.py                # LLM/OpenAI configuration
```

## Quick Start

### Running the API

```bash
cd fundamental_analysis
python -m src.main
```

The API will be available at `http://localhost:8000`

### Endpoints

- `GET /` - API information
- `GET /modules` - List available modules
- `GET /modules/{module_key}` - Get module info
- `POST /analyze` - Run all modules
- `POST /analyze/borrowings` - Run borrowings module only
- `POST /analyze/equity-funding` - Run equity funding module only

## Configuration System

### agents_config.yaml Structure

```yaml
# Global scoring settings
global:
  default_score: 70
  red_penalty: 10
  yellow_penalty: 5
  green_bonus: 1
  min_score: 0
  max_score: 100

modules:
  module_key:
    enabled: true
    name: "Module Display Name"
    description: "What this module analyzes"
    
    agent:
      name: "Agent Name"
      system_prompt: |
        LLM instructions for narrative generation
      output_sections:
        - "Section 1"
        - "Section 2"
    
    benchmarks:
      generic:
        metric1: 0.5
        metric2: 0.3
    
    metrics:
      per_year:
        - name: "metric_name"
          formula: "calculation_formula"
          description: "What this measures"
      trends:
        - name: "trend_name"
          description: "Trend description"
    
    rules:
      - id: "R1"
        name: "Rule Name"
        category: "category"
        metric: "metric_name"
        thresholds:
          red: "> value"
          yellow: "> value"
          green: "<= value"
        reasons:
          red: "Red flag reason"
          yellow: "Yellow flag reason"
          green: "Green flag reason"
```

## Adding a New Module

### Step 1: Add Module Configuration

Edit `src/app/config/agents_config.yaml`:

```yaml
modules:
  # ... existing modules ...
  
  my_new_module:
    enabled: true
    name: "MyNewModule"
    description: "Description of the analysis"
    
    agent:
      name: "My New Agent"
      system_prompt: |
        You are an expert analyst...
      output_sections:
        - "Overview"
        - "Key Findings"
        - "Recommendations"
    
    benchmarks:
      generic:
        threshold1: 0.5
    
    metrics:
      per_year:
        - name: "my_metric"
          formula: "field1 / field2"
          description: "Description"
      trends:
        - name: "my_cagr"
          description: "5-year CAGR"
    
    rules:
      - id: "N1"
        name: "My Rule"
        category: "my_category"
        metric: "my_metric"
        thresholds:
          red: "> 1.0"
          yellow: "> 0.5"
          green: "<= 0.5"
        reasons:
          red: "Critical issue"
          yellow: "Warning"
          green: "Healthy"
```

### Step 2: Create Module Folder

Create `src/app/my_new_module/` with these files:

1. `__init__.py`
2. `models.py` - Data models
3. `metrics.py` - Metric calculations
4. `trend.py` - Trend calculations
5. `rules.py` - Rule engine
6. `llm.py` - LLM narrative generation
7. `orchestrator.py` - Main orchestration

### Step 3: Implement the Module

#### models.py
```python
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class MyYearFinancialInput(BaseModel):
    year: int
    field1: float = 0
    field2: float = 0
    # Add more fields

class MyBenchmarks(BaseModel):
    threshold1: float = 0.5

class MyModuleInput(BaseModel):
    company_id: str
    industry_code: str = "GENERAL"
    financials_5y: List[MyYearFinancialInput]
    benchmarks: MyBenchmarks = MyBenchmarks()

class MyRuleResult(BaseModel):
    rule_id: str
    rule_name: str
    flag: str
    value: Optional[float] = None
    threshold: str
    reason: str

class MyModuleOutput(BaseModel):
    module: str = "MyNewModule"
    sub_score_adjusted: int
    analysis_narrative: List[str]
    red_flags: List[Dict[str, Any]]
    positive_points: List[str]
    rule_results: List[MyRuleResult]
    metrics: Dict[str, Any]
```

#### metrics.py
```python
from typing import Dict, List

def safe_div(a, b):
    return a / b if b and b != 0 else None

def compute_per_year_metrics(financials) -> Dict[int, dict]:
    metrics = {}
    sorted_fin = sorted(financials, key=lambda x: x.year)
    
    for f in sorted_fin:
        metrics[f.year] = {
            "year": f.year,
            "my_metric": safe_div(f.field1, f.field2),
            # Add more metrics
        }
    
    return metrics
```

#### rules.py
```python
from typing import List, Dict
from .models import MyRuleResult, MyBenchmarks

def make_rule(flag, rule_id, name, value, threshold, reason):
    return MyRuleResult(
        rule_id=rule_id,
        rule_name=name,
        flag=flag,
        value=value,
        threshold=threshold,
        reason=reason,
    )

def apply_rules(financials, metrics, trends, benchmarks) -> List[MyRuleResult]:
    results = []
    last_year = max(metrics.keys())
    m = metrics[last_year]
    
    # Example rule
    my_metric = m.get("my_metric")
    if my_metric is not None:
        if my_metric > 1.0:
            results.append(make_rule("RED", "N1", "My Rule", my_metric, "> 1.0", "Critical"))
        elif my_metric > 0.5:
            results.append(make_rule("YELLOW", "N1", "My Rule", my_metric, "0.5-1.0", "Warning"))
        else:
            results.append(make_rule("GREEN", "N1", "My Rule", my_metric, "<= 0.5", "Healthy"))
    
    return results
```

#### orchestrator.py
```python
from collections import Counter
from .metrics import compute_per_year_metrics
from .trend import compute_trend_metrics
from .rules import apply_rules
from .llm import generate_llm_narrative
from .models import MyModuleInput, MyModuleOutput

def compute_sub_score(rule_results):
    c = Counter([r.flag for r in rule_results])
    score = 70 - 10 * c.get("RED", 0) - 5 * c.get("YELLOW", 0) + c.get("GREEN", 0)
    return max(0, min(100, score))

def run_my_new_module(input_data: MyModuleInput) -> MyModuleOutput:
    per_year_metrics = compute_per_year_metrics(input_data.financials_5y)
    trend_metrics = compute_trend_metrics(input_data.financials_5y, per_year_metrics)
    rule_results = apply_rules(
        input_data.financials_5y, per_year_metrics, trend_metrics, input_data.benchmarks
    )
    
    score = compute_sub_score(rule_results)
    # ... rest of orchestration
    
    return MyModuleOutput(
        module="MyNewModule",
        sub_score_adjusted=score,
        # ... other fields
    )
```

### Step 4: Register the Module

Edit `src/app/module_registry.py`:

```python
from src.app.my_new_module.orchestrator import run_my_new_module

def initialize_registry():
    # ... existing registrations ...
    
    AgentRegistry.register(
        module_key="my_new_module",
        runner=run_my_new_module
    )
```

### Step 5: Add to Main API

Edit `src/main.py` to add:
1. Import statements
2. Input builder function
3. API endpoint

## Existing Modules

### 1. Borrowings Module (`borrowings`)
Analyzes debt structure, leverage, and borrowing risk.

**Key Metrics:**
- Debt-to-Equity ratio
- Debt-to-EBITDA
- Interest coverage ratio
- Short-term debt share
- Floating rate exposure

### 2. Equity Funding Mix Module (`equity_funding_mix`)
Analyzes equity quality, retained earnings, dividend policy, and capital structure.

**Key Metrics:**
- Return on Equity (ROE)
- Retained earnings growth
- Dividend payout ratio
- Dividend to FCF ratio
- Equity dilution percentage
- Debt-to-Equity ratio
- Equity ratio

**Rule Categories:**
- A: Retained Earnings & Internal Capital Formation
- B: ROE Quality
- C: Dividend Policy & Sustainability
- D: Equity Dilution & Capital Raising
- E: Funding Mix (Debt vs Equity)

## Switching Between Modules

### Via API Request

```json
{
  "company": "RELIANCE",
  "financial_data": { ... },
  "modules": ["borrowings"]  // Only run borrowings
}
```

```json
{
  "company": "RELIANCE", 
  "financial_data": { ... },
  "modules": ["equity_funding_mix"]  // Only run equity
}
```

```json
{
  "company": "RELIANCE",
  "financial_data": { ... }
  // No modules specified = run all enabled modules
}
```

### Enabling/Disabling Modules

In `agents_config.yaml`:

```yaml
modules:
  borrowings:
    enabled: true   # Module is active
  
  equity_funding_mix:
    enabled: false  # Module is disabled
```

## Scoring System

Each module produces a sub-score using this formula:

```
score = 70 (base)
      - 10 × (RED flags)
      - 5 × (YELLOW flags)
      + 1 × (GREEN flags)
      
Final score clamped to [0, 100]
```

These weights are configurable in `agents_config.yaml`:

```yaml
global:
  default_score: 70
  red_penalty: 10
  yellow_penalty: 5
  green_bonus: 1
```

## LLM Integration

Each module can generate narrative analysis using an LLM. The system prompt and output sections are configured in YAML:

```yaml
agent:
  system_prompt: |
    You are a senior analyst specializing in...
  output_sections:
    - "Section 1"
    - "Section 2"
```

The LLM receives:
- Computed metrics
- Rule flags and results
- Trend analysis
- Company context

## Testing

Run the test script:
```bash
python test_equity_funding_module.py
```

## Future Modules (Planned)

- Liquidity Module
- Working Capital Module
- Capex & Asset Quality Module
- Risk Assessment Module
