# Red Flag Aggregator Module

## Overview

The Red Flag Aggregator Module is the **nervous system** of the fundamental analysis system. It:

1. **Standardizes** risk signals from all upstream modules
2. **Quantifies** risk into a single, interpretable index
3. **Detects** structural failure patterns
4. **Enforces** hard reality checks on optimism

## Architecture

```
Upstream Modules (borrowings, liquidity, QoE, etc.)
         |
         v
    Red Flags
   (standardized)
         |
         v
  [Orchestrator]
  - Validate
  - Flatten
  - Count
  - Baseline penalty
  - Category mapping
  - Pattern detection
  - Scenario detection
  - Overrides
  - Capping
         |
         v
   [Output]
   - Severity Score
   - Red Flag Index
   - Category Risks
   - Score Caps
   - Narrative
```

## Files

| File | Purpose |
|------|---------|
| `red_flag_aggregator_models.py` | `RedFlag` dataclass, `Severity` enum, `RiskCategory` enum, validation |
| `red_flag_aggregator_config.py` | Weights, pattern rules, scenario overrides, score caps |
| `red_flag_aggregator_orchestrator.py` | Main execution flow and aggregation logic |
| `red_flag_aggregator_llm.py` | Deterministic narrative generator (optional LLM wrapper) |
| `red_flag_definitions.py` | Complete specification of 6 risk themes with thresholds |
| `red_flag_factory_examples.py` | Examples: how upstream modules should emit flags |
| `RED_FLAG_CONTRACT.py` | **BINDING SPECIFICATION** for all module authors |

## Quick Start

### For Aggregator Callers

```python
from app.red_flag_aggregator_module.red_flag_aggregator_orchestrator import aggregate_red_flags

payload = {
    "company_id": "ACME",
    "module_red_flags": {
        "borrowings": [...],  # list of red flag dicts
        "liquidity": [...],
        "quality_of_earnings": [...],
    }
}

result = aggregate_red_flags(payload)
# Returns: {
#   "severity_score": int,
#   "red_flag_index": int,
#   "counts": {...},
#   "category_risks": {...},
#   "scenarios": {...},
#   "score_cap": int or None,
#   "top_critical_issues": [...],
#   "flags": [...],
#   "narrative": str or None,
# }
```

### For Upstream Module Authors

**IMPORTANT**: Every red flag MUST include `risk_category` explicitly. No inference.

Canonical categories:
- `liquidity`
- `leverage`
- `earnings_quality`
- `working_capital`
- `governance_fraud`
- `asset_utilization`

Example (borrowings module):

```python
from app.red_flag_aggregator_module.red_flag_definitions import generate_red_flag

flag = generate_red_flag(
    module="borrowings",
    category="leverage",  # Risk category
    metric_key="de_ratio",
    value=5.5,  # Actual D/E ratio
    period="FY2024"
)
# Returns: {
#   "module": "borrowings",
#   "severity": "CRITICAL",  # Automatically determined
#   "title": "Debt-to-Equity Ratio (D/E) > 3",
#   "detail": "Indicates excessive reliance on debt...",
#   "risk_category": "leverage",
#   "metric": "de_ratio",
#   "value": 5.5,
#   ...
# }
```

For **qualitative flags** (fraud, governance):

```python
flag = {
    "module": "governance",
    "severity": "CRITICAL",  # You decide
    "title": "Circular Trading Detected",
    "detail": "Repetitive trades with same counterparty lacking economic substance.",
    "risk_category": "governance_fraud",
    "metric": "circular_trading",
    "value": None,  # No numeric metric
    "period": "FY2024",
}
```

## Red Flag Contract

**Read [RED_FLAG_CONTRACT.py](RED_FLAG_CONTRACT.py) before emitting any red flags.**

Key rules:

1. **risk_category is REQUIRED** and must be one of the 6 canonical values
2. **Severity must match the condition** (GREEN for healthy, CRITICAL for structural failure)
3. **CRITICAL is rare** — use only for fraud, insolvency, or non-linear risk
4. **All required fields must be present**:
   - `module`
   - `severity`
   - `title`
   - `detail`
   - `risk_category`

## Severity Doctrine

| Level | Penalty | Meaning | Examples |
|-------|---------|---------|----------|
| GREEN | 0 | No material risk | Healthy metrics |
| YELLOW | 5 | Early stress | Trends worsening, minor breaches |
| RED | 10 | Material risk | Solvency threat, valuation impact |
| CRITICAL | 20 | Structural failure | Fraud, insolvency, asset stripping |

## Execution Flow (14 Steps)

1. **Input validation** → Validate structure and required fields
2. **Flattening** → Merge all module flags into single list
3. **Severity counting** → Count CRITICAL, RED, YELLOW flags
4. **Baseline penalty** → Sum: CRITICAL×20 + RED×10 + YELLOW×5
5. **Category mapping** → Group flags by risk_category
6. **Pattern detection** → Apply deterministic rules per category
7. **Scenario detection** → Scan for non-linear risk patterns
8. **Scenario overrides** → Raise penalty for detected scenarios
9. **Severity capping** → Cap at 100
10. **Red Flag Index** → Normalized 0-100 pressure gauge
11. **Score caps** → Impose hard ceilings on final ratings
12. **Critical extraction** → List CRITICAL issues by priority
13. **Narrative generation** → Optional LLM summary (non-authoritative)
14. **Output assembly** → Return structured result

## Key Design Decisions

### Why risk_category is Required

- **Deterministic**: No inference needed
- **Explicit**: Modules declare their intent
- **Safe**: Prevents silent misclassification
- **Auditable**: Every flag has clear category

### Why Severity is a Penalty, Not a Score

- Two RED flags = twice as bad as one RED
- CRITICAL is qualitatively different (≠ just a large RED)
- Weights are tunable; meaning is fixed

### Why Overrides Exist

Some risks don't scale linearly:
- Fraud → jump to high risk regardless of other metrics
- Evergreening → force score reduction
- Asset stripping → always CRITICAL

### Why There's a Score Cap

Prevents:
- Large companies being unfairly punished for volume
- Data glitches destroying scores
- "Very bad" ≠ "catastrophic" in practice

## Testing

```bash
cd src
python -m app.red_flag_aggregator_module.red_flag_factory_examples

# Or run the test snippet from docstrings
```

## Integration with Master Scoring Engine

The aggregator returns:
- `red_flag_index`: Direct input to scoring models
- `score_cap`: Hard ceiling enforced downstream
- `scenarios`: Risk categorization for reports
- `narrative`: Human-readable context

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Missing required red-flag fields: ['risk_category']` | Forgot to add risk_category | Add it explicitly |
| `Unknown risk_category: X` | Misspelled or custom category | Use exact canonical value |
| `Unknown severity: X` | Invalid severity string | Use GREEN, YELLOW, RED, or CRITICAL |
| `Cannot determine risk category` | Old code path (pre-fix) | Update to provide risk_category |

## FAQ

**Q: Can a module emit multiple categories?**
A: No. Each flag belongs to exactly one category. Split into separate flags if needed.

**Q: Can I infer risk_category from module name?**
A: No. Always provide it explicitly. Module names change. This breaks.

**Q: What if my risk doesn't fit the 6 categories?**
A: Your analysis is wrong. Refocus. All material risks fit one of these 6.

**Q: Can I emit CRITICAL for a soft warning?**
A: No. CRITICAL means structural failure. Use RED.

**Q: How do I add a custom risk category?**
A: You don't. File a spec issue and update the canonical enum first.

## References

- [RED_FLAG_CONTRACT.py](RED_FLAG_CONTRACT.py) — Binding spec for module authors
- [red_flag_definitions.py](red_flag_definitions.py) — Complete metric definitions & thresholds
- [red_flag_factory_examples.py](red_flag_factory_examples.py) — Usage examples
