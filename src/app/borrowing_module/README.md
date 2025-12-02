# Borrowings Module Documentation

## Overview

The **Borrowings Module** (also known as Debt/Borrower Analysis Module) is a hybrid analysis system that evaluates a company's capital structure and leverage risk through deterministic metrics and LLM-powered insights.

**Type**: Hybrid (Deterministic Engine + LLM Debt Agent)  
**Parent System**: Balance Sheet Deep Reasoning Multi-Agent System

---

## Objective

Evaluate capital structure & leverage risk by analyzing:

- Level and trend of short-term (ST) & long-term (LT) debt vs EBITDA, Capex, CWIP
- Leverage ratios: Debt/EBITDA, Debt/Equity
- Interest coverage and cost of debt
- Maturity profile (refinancing risk)
- Rate structure: fixed vs floating, weighted average rate
- Covenant proximity & breach risk

---

## Input Schema

### Required Fields (Per Year, Last 5 FYs)

```json
{
  "company_id": "ABC123",
  "industry_code": "CEMENT",
  "financials_5y": [
    {
      "year": 2024,
      "short_term_debt": 1000.0,
      "long_term_debt": 4000.0,
      "total_equity": 2500.0,
      "ebitda": 1800.0,
      "ebit": 1500.0,
      "finance_cost": 300.0,
      "capex": 800.0,
      "cwip": 1200.0,
      "revenue": 6000.0,
      "operating_cash_flow": 1400.0
    }
  ],
  "industry_benchmarks": {
    "target_de_ratio": 1.5,
    "max_safe_de_ratio": 2.5,
    "max_safe_debt_ebitda": 4.0,
    "min_safe_icr": 2.0,
    "high_floating_share": 0.60,
    "high_wacd": 0.12
  },
  "covenant_limits": {
    "de_ratio_limit": 3.0,
    "icr_limit": 2.0,
    "debt_ebitda_limit": 4.0
  }
}
```

### Optional Fields (Per Year)

```json
{
  "total_debt_maturing_lt_1y": 800.0,
  "total_debt_maturing_1_3y": 1500.0,
  "total_debt_maturing_gt_3y": 2700.0,
  "weighted_avg_interest_rate": 0.095,
  "floating_rate_debt": 2000.0,
  "fixed_rate_debt": 3500.0
}
```

---

## Core Metrics Calculated

### Per-Year Metrics

| Metric | Formula | Description |
|--------|---------|-------------|
| `total_debt` | ST Debt + LT Debt | Total borrowings |
| `st_debt_share` | ST Debt / Total Debt | Proportion of short-term debt |
| `debt_to_equity` | Total Debt / Equity | Leverage ratio |
| `debt_to_ebitda` | Total Debt / EBITDA | Debt servicing capacity |
| `interest_coverage` | EBIT / Finance Cost | Ability to cover interest |
| `floating_share` | Floating Debt / Total Debt | Interest rate risk exposure |
| `wacd` | Weighted Avg Interest Rate | Cost of debt |
| `ocf_to_debt` | Operating Cash Flow / Total Debt | Cash generation vs debt |

### Trend Metrics (5-Year)

| Metric | Description |
|--------|-------------|
| `debt_cagr` | Compound annual growth rate of total debt |
| `ebitda_cagr` | CAGR of EBITDA |
| `debt_growth_vs_ebitda` | Debt CAGR - EBITDA CAGR |
| `leverage_trend_increasing` | D/E rising ≥3 consecutive years |
| `icr_trend_declining` | ICR dropping ≥3 consecutive years |

---

## Rules & Flags

### Rule Categories

#### A. Debt Growth & Trends
- **A1**: Debt CAGR vs EBITDA CAGR
- **A2**: ST Debt Surge (>30% YoY for 2 years + weak OCF)
- **A3**: LT Debt vs Revenue Growth
- **A3b**: LT Debt funding CWIP (positive indicator)

#### B. Leverage Ratios
- **B1**: Debt-to-Equity Threshold
- **B2**: Debt-to-EBITDA Threshold

#### C. Interest Coverage & Cost
- **C1**: Interest Coverage Ratio (ICR)
- **C2**: Finance Cost Pressure (rising faster than debt)
- **C2b**: Finance Cost YoY Growth

#### D. Maturity Profile
- **D1**: Refinancing Risk (<1y maturity)
- **D2**: Balanced Maturity Profile

#### E. Interest Rate Structure
- **E1**: Floating Rate Exposure
- **E2**: Weighted Average Cost of Debt (WACD)

#### F. Covenant Compliance
- **F1**: Near Covenant Breach (within 10% buffer)
- **F2**: Covenant Breach

### Flag Levels

| Flag | Meaning | Impact on Score |
|------|---------|-----------------|
| `GREEN` | Healthy / Acceptable | +0 |
| `YELLOW` | Medium Risk / Watchlist | -5 |
| `RED` | High Risk | -10 |

---

## Output Schema

```json
{
  "module": "Borrowings",
  "company": "ABC123",
  "key_metrics": {
    "year": 2024,
    "total_debt": 5000.0,
    "st_debt_share": 0.28,
    "debt_to_equity": 2.1,
    "debt_to_ebitda": 4.3,
    "interest_coverage": 1.9,
    "floating_share": 0.65,
    "wacd": 0.115,
    "debt_cagr": 12.0,
    "ebitda_cagr": 6.0
  },
  "trends": {
    "short_term_debt": {
      "values": { "Y": 1000, "Y-1": 900, ... },
      "yoy_growth_pct": { "Y_vs_Y-1": 11.11, ... },
      "insight": "LLM-generated or fallback insight"
    }
  },
  "analysis_narrative": [
    "Total debt CAGR 12% vs EBITDA CAGR 6%.",
    "Debt/EBITDA at 4.3x indicates stressed leverage."
  ],
  "red_flags": [
    {
      "severity": "HIGH",
      "title": "Stressed leverage and weak coverage",
      "detail": "Debt-to-EBITDA above 4x..."
    }
  ],
  "positive_points": [
    "Balanced Maturity: Debt spread across 1-3y and >3y."
  ],
  "rules": [
    {
      "rule_id": "A1",
      "rule_name": "Debt CAGR vs EBITDA",
      "metric": "debt_cagr",
      "year": 2024,
      "flag": "RED",
      "value": 12.0,
      "threshold": ">6.1",
      "reason": "Debt CAGR 12% exceeds EBITDA CAGR 6%..."
    }
  ]
}
```

---

## Module Architecture

### File Structure

```
src/app/borrowing_module/
├── README.md                    # This file
├── debt_models.py              # Pydantic models for input/output
├── debt_config.py              # Configuration loader
├── borrowings_config.py        # Rule thresholds configuration
├── debt_metrics.py             # Per-year metric calculations
├── debt_trend.py               # Trend analysis (CAGR, YoY, patterns)
├── debt_rules.py               # Rule evaluation logic
├── debt_llm.py                 # LLM narrative generation
├── debt_insight_fallback.py    # Fallback insights when LLM unavailable
└── debt_orchestrator.py        # Main orchestrator
```

### Orchestrator Flow

```
BorrowingsModule.run()
  ├─> compute_per_year_metrics()     # Calculate metrics for each year
  ├─> compute_trend_metrics()        # Calculate 5-year trends
  ├─> apply_rules()                  # Evaluate all rules
  ├─> generate_llm_narrative()       # Get LLM insights (optional)
  ├─> generate_fallback_insight()    # Fallback if LLM unavailable
  └─> BorrowingsOutput               # Return structured output
```

---

## Configuration

### Rule Thresholds (`borrowings_config.yaml`)

```yaml
generic:
  high_de_ratio: 2.0
  very_high_de_ratio: 3.0
  high_debt_ebitda: 4.0
  critical_debt_ebitda: 6.0
  low_icr: 2.0
  critical_icr: 1.0
  risky_st_debt_share: 0.5
  risky_debt_lt_1y_pct: 0.5
  high_floating_share: 0.6
  high_wacd: 0.12
  high_debt_cagr_vs_ebitda_gap: 0.10
  high_fin_cost_yoy: 0.25
  covenant_buffer_pct: 0.10
```

---

## Usage Example

### Python

```python
from src.app.borrowing_module.debt_models import (
    BorrowingsInput,
    YearFinancialInput,
    IndustryBenchmarks,
    CovenantLimits,
)
from src.app.borrowing_module.debt_orchestrator import BorrowingsModule

# Prepare input data
financials = [
    YearFinancialInput(
        year=2024, short_term_debt=1000, long_term_debt=4000,
        total_equity=2500, ebitda=1800, ebit=1500, finance_cost=300,
        revenue=6000, operating_cash_flow=1400
    ),
    # ... 4 more years
]

benchmarks = IndustryBenchmarks(
    target_de_ratio=1.5, max_safe_de_ratio=2.5,
    max_safe_debt_ebitda=4.0, min_safe_icr=2.0
)

covenants = CovenantLimits(
    de_ratio_limit=3.0, icr_limit=2.0, debt_ebitda_limit=4.0
)

module_input = BorrowingsInput(
    company_id="ABC123",
    industry_code="CEMENT",
    financials_5y=financials,
    industry_benchmarks=benchmarks,
    covenant_limits=covenants,
)

# Run analysis
engine = BorrowingsModule()
result = engine.run(module_input)

print(f"Score: {result.sub_score_adjusted}")
print(f"Rules evaluated: {len(result.rules)}")
```

### API Endpoint

```bash
POST /borrowings/analyze
Content-Type: application/json

{
  "company": "ABC123",
  "industry_code": "CEMENT",
  "financial_data": {
    "financial_years": [...]
  }
}
```

---

## LLM Integration

The module uses an LLM (default: GPT-4) to generate:
- **Narrative insights** for trend analysis
- **Contextual explanations** for rule violations
- **Adjusted scoring** based on qualitative factors

### Fallback Behavior

If LLM is unavailable (missing API key or package):
- Deterministic analysis proceeds normally
- Fallback insights are generated based on data patterns
- Scoring uses base deterministic logic only

---

## Testing

```bash
# Run module test
python test_all_rules.py

# Expected output:
# - Total rules evaluated: 8-15 (depending on data)
# - Breakdown by flag: GREEN, YELLOW, RED
# - List of all evaluated rules
```

---

## Future Enhancements

- [ ] Industry-specific rule configurations
- [ ] Historical covenant breach tracking
- [ ] Debt restructuring scenario analysis
- [ ] Integration with credit rating models
- [ ] Real-time covenant monitoring alerts

---

## References

- **Specification**: See original spec document for detailed rule definitions
- **Parent System**: Balance Sheet Deep Reasoning Multi-Agent System
- **Related Modules**: Asset Quality, Liquidity, Working Capital
