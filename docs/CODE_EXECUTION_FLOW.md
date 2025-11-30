# Code Execution Flow Documentation

## Complete Technical Deep-Dive: How Analysis Works

This document provides detailed documentation on how the Fundamental Analysis Engine executes analysis, from API request to final response.

---

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Execution Flow Overview](#execution-flow-overview)
3. [Step-by-Step Execution](#step-by-step-execution)
4. [GenericAgent Deep Dive](#genericagent-deep-dive)
5. [LangGraph Workflow Deep Dive](#langgraph-workflow-deep-dive)
6. [Data Flow Diagrams](#data-flow-diagrams)
7. [Class Reference](#class-reference)
8. [Configuration Loading](#configuration-loading)

---

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT REQUEST                                 │
│  POST /analyze                                                             │
│  {company, financial_data, modules, generate_narrative}                    │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI LAYER                                  │
│  main.py                                                                   │
│  • Parse request → AnalyzeRequest                                         │
│  • Extract current_data (latest year)                                      │
│  • Prepare historical_data (all years sorted)                             │
│  • Calculate YoY growth metrics                                            │
│  • Invoke workflow.run()                                                   │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                           LANGGRAPH WORKFLOW                               │
│  workflow.py → AnalysisWorkflow                                           │
│                                                                            │
│  ┌──────────────┐                                                         │
│  │  INITIALIZE  │ Set initial state                                       │
│  └──────┬───────┘                                                         │
│         ▼                                                                  │
│  ┌──────────────┐                                                         │
│  │    ROUTER    │ Determine next module                                   │
│  └──────┬───────┘                                                         │
│         │    ┌─────────────────┐                                          │
│         ├───►│ run_borrowings  │──┐                                       │
│         │    └─────────────────┘  │                                       │
│         │    ┌─────────────────┐  │                                       │
│         ├───►│ run_equity_mix  │──┼──► Back to Router                     │
│         │    └─────────────────┘  │                                       │
│         │         ...             │                                       │
│         ▼                                                                  │
│  ┌──────────────┐                                                         │
│  │ CALC_SCORE   │ Average all module scores                               │
│  └──────┬───────┘                                                         │
│         ▼                                                                  │
│  ┌──────────────┐                                                         │
│  │ GEN_SUMMARY  │ Create markdown summary                                 │
│  └──────┬───────┘                                                         │
│         ▼                                                                  │
│       END                                                                  │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                            GENERIC AGENT                                    │
│  generic_agent.py → GenericAgent.analyze()                                │
│                                                                            │
│  For EACH module:                                                          │
│  1. Load YAML config for module                                           │
│  2. calculate_metrics(data) → metrics dict                                │
│  3. calculate_trends(historical) → trends list                            │
│  4. evaluate_rules(metrics) → rules_results list                          │
│  5. calculate_score(rules_results) → score, interpretation                │
│  6. generate_narrative() → LLM text (optional)                            │
│  7. Return ModuleOutput                                                   │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                              API RESPONSE                                   │
│  {                                                                         │
│    company, workflow_status, overall_score,                               │
│    modules_completed, risk_flags, key_insights,                           │
│    module_results, summary, yoy_growth                                    │
│  }                                                                         │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Execution Flow Overview

### Phase 1: Request Processing (main.py)

```python
# File: src/main.py
# Endpoint: POST /analyze

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    # 1. Extract company name
    company = req.company.upper()
    
    # 2. Get financial years from request
    fds = req.financial_data.financial_years
    
    # 3. Sort by year descending - newest first
    sorted_fds = sorted(fds, key=lambda x: x.year, reverse=True)
    
    # 4. Convert most recent year to dict for current data
    current_data = financial_year_to_dict(sorted_fds[0])
    
    # 5. Prepare historical data (all years)
    historical_data = prepare_historical_data(fds)
    
    # 6. Calculate YoY growth for all metrics
    yoy_growth = calculate_yoy_growth(fds)
    
    # 7. Run LangGraph workflow
    result = workflow.run(
        company=company,
        current_data=current_data,
        historical_data=historical_data,
        modules=req.modules,
        generate_narrative=req.generate_narrative
    )
```

### Phase 2: Workflow Execution (workflow.py)

```python
# File: src/app/agents/workflow.py
# Class: AnalysisWorkflow.run()

def run(self, company, current_data, historical_data, modules, generate_narrative):
    # 1. Determine which modules to run
    if modules:
        modules_to_run = [m for m in modules if m in self.available_modules]
    else:
        modules_to_run = [all enabled modules from YAML]
    
    # 2. Create initial state
    initial_state = {
        "company": company,
        "current_data": current_data,
        "historical_data": historical_data,
        "modules_to_run": modules_to_run,
        # ... other state fields
    }
    
    # 3. Execute LangGraph workflow
    final_state = self.graph.invoke(initial_state, config)
    
    # 4. Return structured result
    return {
        "workflow_status": final_state.get("workflow_status"),
        "overall_score": final_state.get("overall_score"),
        "risk_flags": final_state.get("risk_flags"),
        "key_insights": final_state.get("key_insights"),
        # ...
    }
```

### Phase 3: Module Analysis (generic_agent.py)

```python
# File: src/app/agents/generic_agent.py
# Class: GenericAgent.analyze()

def analyze(self, data, historical_data, generate_llm_narrative):
    # 1. Calculate metrics from input data
    metrics = self.calculate_metrics(data)
    
    # 2. For borrowings: add trend comparison metrics
    if self.module_id == "borrowings" and historical_data:
        trend_metrics = self._calculate_trend_comparison_metrics(historical_data)
        metrics.update(trend_metrics)
    
    # 3. Evaluate rules against metrics
    rules_results = self.evaluate_rules(metrics)
    
    # 4. Calculate trends from historical data
    trends = self.calculate_trends(historical_data)
    
    # 5. Calculate score from rules
    score, interpretation = self.calculate_score(rules_results)
    
    # 6. Generate LLM narrative (optional)
    narrative = self.generate_narrative(metrics, rules_results, trends, score)
    
    # 7. Return complete output
    return ModuleOutput(
        module_name=self.name,
        module_id=self.module_id,
        metrics=metrics,
        rules_results=rules_results,
        trends=trends,
        score=score,
        score_interpretation=interpretation,
        llm_narrative=narrative
    )
```

---

## Step-by-Step Execution

### Step 1: Data Preparation

**Location:** `main.py` → `financial_year_to_dict()`

```python
def financial_year_to_dict(fy: FinancialYearInput) -> Dict[str, float]:
    """Convert Pydantic model to flat dictionary"""
    data = fy.model_dump()  # Get all fields
    
    # Add computed fields
    data["total_debt"] = (
        data.get("short_term_debt", 0) + 
        data.get("long_term_debt", 0)
    )
    
    # Map aliases if not set
    if data.get("revenue_wc", 0) == 0:
        data["revenue_wc"] = data.get("revenue", 0)
    
    return data
```

**Example Transformation:**
```
Input: FinancialYearInput(year=2024, revenue=1000000, short_term_debt=50000, long_term_debt=150000, ...)

Output: {
    "year": 2024,
    "revenue": 1000000,
    "short_term_debt": 50000,
    "long_term_debt": 150000,
    "total_debt": 200000,  # Computed
    "revenue_wc": 1000000,  # Mapped
    ...
}
```

### Step 2: Historical Data Preparation

**Location:** `main.py` → `prepare_historical_data()`

```python
def prepare_historical_data(fds: List[FinancialYearInput]) -> List[Dict[str, float]]:
    """Convert list of financial years to historical data format"""
    # Sort by year ASCENDING (oldest first) for CAGR calculations
    sorted_fds = sorted(fds, key=lambda x: x.year)
    return [financial_year_to_dict(fy) for fy in sorted_fds]
```

**Example:**
```
Input: [FY2024, FY2023, FY2022]

Output (sorted oldest first):
[
    {year: 2022, ...},  # Index 0 - Oldest (Start for CAGR)
    {year: 2023, ...},  # Index 1
    {year: 2024, ...},  # Index 2 - Newest (End for CAGR)
]
```

### Step 3: YoY Growth Calculation

**Location:** `main.py` → `calculate_yoy_growth()`

```python
def calculate_yoy_growth(fds: List[FinancialYearInput]) -> Dict[str, Dict[str, Any]]:
    # 1. Sort descending (newest first)
    sorted_fds = sorted(fds, key=lambda x: x.year, reverse=True)
    
    # 2. For each metric, calculate growth between consecutive years
    for i in range(len(years_data) - 1):
        current_val = years_data[i].get(metric)
        prev_val = years_data[i + 1].get(metric)
        
        # YoY Growth % = (Current - Previous) / |Previous| * 100
        if current_val and prev_val and prev_val != 0:
            growth_pct = ((current_val - prev_val) / abs(prev_val)) * 100
    
    # 3. Generate summary for each metric
    return generate_metric_summary(metric, metric_growth)
```

**Example Output:**
```json
{
    "revenue": {
        "name": "Revenue",
        "category": "Growth",
        "description": "Total sales/income from operations",
        "trend": "Consistently Growing",
        "latest_yoy": "+15.50%",
        "avg_growth": "+12.30%",
        "assessment": "Strong growth trajectory...",
        "values": {"MAR 2024": 15.5, "MAR 2023": 9.1}
    }
}
```

### Step 4: Workflow Initialization

**Location:** `workflow.py` → `initialize_workflow()`

```python
def initialize_workflow(state: AnalysisState) -> Dict[str, Any]:
    """Initialize workflow state"""
    return {
        "workflow_status": "running",
        "overall_score": 0,
        "module_results": {},
    }
```

**State After Initialization:**
```python
{
    "company": "RELIANCE",
    "current_data": {...},
    "historical_data": [...],
    "modules_to_run": ["borrowings", "equity_funding_mix"],
    "modules_completed": [],
    "modules_failed": [],
    "module_results": {},
    "overall_score": 0,
    "risk_flags": [],
    "key_insights": [],
    "workflow_status": "running",
}
```

### Step 5: Module Routing

**Location:** `workflow.py` → `route_to_module()`

```python
def route_to_module(state: AnalysisState) -> str:
    """Route to the next module node"""
    next_module = get_next_module(state)
    if next_module:
        return f"run_{next_module}"  # e.g., "run_borrowings"
    return "calculate_score"  # All modules done
```

**Routing Logic:**
```
modules_to_run: ["borrowings", "equity_funding_mix"]
modules_completed: []
→ Return: "run_borrowings"

After borrowings completes:
modules_completed: ["borrowings"]
→ Return: "run_equity_funding_mix"

After equity completes:
modules_completed: ["borrowings", "equity_funding_mix"]
→ Return: "calculate_score"
```

### Step 6: Module Execution

**Location:** `workflow.py` → `run_module_node()`

```python
def run_module_node(module_id: str):
    """Factory function to create a node for a specific module"""
    
    def run_module(state: AnalysisState) -> Dict[str, Any]:
        # 1. Create agent for this module
        agent = GenericAgent(module_id)
        
        # 2. Run analysis
        result = agent.analyze(
            data=state["current_data"],
            historical_data=state.get("historical_data"),
            generate_llm_narrative=state.get("generate_narrative", True)
        )
        
        # 3. Extract risk flags (RED rules)
        red_rules = [r for r in result.rules_results if r.status == "RED"]
        risk_flags = [f"[{module_id.upper()}] {r.rule_name}: {r.summary}" for r in red_rules]
        
        # 4. Extract key insights (GREEN rules)
        green_rules = [r for r in result.rules_results if r.status == "GREEN"]
        key_insights = [f"[{module_id.upper()}] ✓ {r.summary}" for r in green_rules[:2]]
        
        # 5. Return updated state
        return {
            "module_results": {**state.get("module_results", {}), module_id: result.model_dump()},
            "modules_completed": [module_id],
            "risk_flags": risk_flags,
            "key_insights": key_insights,
        }
    
    return run_module
```

### Step 7: Score Calculation

**Location:** `workflow.py` → `calculate_overall_score()`

```python
def calculate_overall_score(state: AnalysisState) -> Dict[str, Any]:
    """Calculate overall score from all module results"""
    results = state.get("module_results", {})
    
    # Get scores from all modules
    scores = [r.get("score", 0) for r in results.values()]
    
    # Calculate average
    overall = sum(scores) // len(scores) if scores else 0
    
    return {"overall_score": overall}
```

**Example:**
```
borrowings score: 65
equity_funding_mix score: 51

Overall = (65 + 51) / 2 = 58
```

### Step 8: Summary Generation

**Location:** `workflow.py` → `generate_final_summary()`

```python
def generate_final_summary(state: AnalysisState) -> Dict[str, Any]:
    """Generate final workflow summary"""
    
    summary_parts = [
        f"# Financial Analysis Summary: {company}",
        f"\n## Overview",
        f"- **Modules Analyzed**: {len(completed)}",
        f"- **Overall Score**: {overall_score}/100",
        f"- **Status**: {'⚠️ Attention Required' if risk_flags else '✅ Healthy'}",
    ]
    
    if risk_flags:
        summary_parts.append(f"\n## 🚨 Risk Flags ({len(risk_flags)})")
        for flag in risk_flags[:10]:
            summary_parts.append(f"- {flag}")
    
    if key_insights:
        summary_parts.append(f"\n## ✅ Positive Indicators")
        for insight in key_insights[:5]:
            summary_parts.append(f"- {insight}")
    
    return {
        "final_summary": "\n".join(summary_parts),
        "workflow_status": "completed"
    }
```

---

## GenericAgent Deep Dive

### Agent Initialization

```python
class GenericAgent:
    def __init__(self, module_id: str):
        # 1. Load module config from YAML
        self.config = get_module_config(module_id)
        
        # 2. Extract configuration
        self.name = self.config.get("name", module_id)
        self.benchmarks = self.config.get("benchmarks", {})
        self.metric_formulas = self.config.get("metrics", {})
        self.rules = self.config.get("rules", [])
        self.trend_keys = self.config.get("trends", [])
        self.agent_prompt = self.config.get("agent_prompt", "")
        
        # 3. Load global config for scoring
        self.global_config = full_config.get("global", {})
```

### Metrics Calculation

**Location:** `generic_agent.py` → `calculate_metrics()`

```python
def calculate_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
    """Route to module-specific calculation"""
    
    if self.module_id == "borrowings":
        return self._calc_borrowings_metrics(data)
    elif self.module_id == "equity_funding_mix":
        return self._calc_equity_funding_metrics(data)
    # ... other modules
```

**Example: Borrowings Metrics**
```python
def _calc_borrowings_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
    st_debt = data.get("short_term_debt", 0)
    lt_debt = data.get("long_term_debt", 0)
    total_debt = st_debt + lt_debt
    equity = data.get("total_equity", 1)
    ebitda = data.get("ebitda", 1)
    ebit = data.get("ebit", 0)
    finance_cost = data.get("finance_cost", 1)
    
    return {
        "total_debt": total_debt,
        "de_ratio": total_debt / equity,           # D/E Ratio
        "debt_ebitda": total_debt / ebitda,        # Debt/EBITDA
        "interest_coverage": ebit / finance_cost,  # ICR
        "st_debt_share": st_debt / total_debt,     # Short-term %
        "floating_share": floating_rate,            # Floating rate %
        "wacd": weighted_avg_rate,                  # WACD
        "maturity_lt_1y_pct": maturity_lt_1y / total_debt,
        # ... more metrics
    }
```

### Rules Evaluation

**Location:** `generic_agent.py` → `evaluate_rules()`

```python
def evaluate_rules(self, metrics: Dict[str, float]) -> List[RuleResult]:
    results = []
    
    for rule in self.rules:
        # Get rule config
        rule_id = rule.get("id")
        metric_name = rule.get("metric")
        
        # Get metric value
        value = metrics.get(metric_name, 0)
        
        # Evaluate conditions
        status, message, insights = self._evaluate_rule_with_insights(rule, value)
        
        # Create result
        results.append(RuleResult(
            rule_id=rule_id,
            rule_name=rule.get("name"),
            metric_name=metric_name,
            value=value,
            status=status,  # "RED", "YELLOW", or "GREEN"
            message=message,
            summary=insights.get("summary"),
            implication=insights.get("implication"),
            investor_action=insights.get("investor_action"),
            risk_level=insights.get("risk_level"),
        ))
    
    return results
```

### Condition Checking

**Location:** `generic_agent.py` → `_check_condition()`

```python
def _check_condition(self, value: float, condition: str) -> bool:
    """Parse and check condition string"""
    
    # Examples:
    # "> 1.0"  → value > 1.0
    # "< 0.5"  → value < 0.5
    # ">= 3.0" → value >= 3.0
    # "<= 0.8" → value <= 0.8
    # "-"      → False (skip)
    
    if condition.startswith(">="):
        threshold = float(condition[2:].strip())
        return value >= threshold
    elif condition.startswith("<="):
        threshold = float(condition[2:].strip())
        return value <= threshold
    elif condition.startswith(">"):
        threshold = float(condition[1:].strip())
        return value > threshold
    elif condition.startswith("<"):
        threshold = float(condition[1:].strip())
        return value < threshold
```

**Evaluation Order:**
```
1. Check RED condition first
2. If RED matches → Return "RED"
3. Check YELLOW condition
4. If YELLOW matches → Return "YELLOW"
5. Default → Return "GREEN"
```

### CAGR Calculation

**Location:** `generic_agent.py` → `calculate_trends()`

```python
def calculate_trends(self, historical_data: List[Dict[str, float]]) -> List[TrendResult]:
    """Calculate CAGR from historical data"""
    
    n = len(historical_data)  # Number of periods
    
    for trend_key in self.trend_keys:
        # Get values from oldest to newest
        values = [d.get(field) for d in historical_data]
        
        if len(values) >= 2 and values[0] > 0:
            # CAGR Formula: (End/Start)^(1/n) - 1
            cagr = (values[-1] / values[0]) ** (1 / (n - 1)) - 1
            
            # Interpret
            interpretation = (
                "Strong growth" if cagr > 0.15 else
                "Moderate growth" if cagr > 0.05 else
                "Stable" if cagr > -0.05 else
                "Declining"
            )
            
            trends.append(TrendResult(
                name=trend_key,
                value=cagr,
                interpretation=interpretation
            ))
    
    return trends
```

### Score Calculation

**Location:** `generic_agent.py` → `calculate_score()`

```python
def calculate_score(self, rules_results: List[RuleResult]) -> tuple:
    """Calculate module score from rule results"""
    
    # From global config:
    base_score = 70
    red_penalty = 10
    yellow_penalty = 5
    green_bonus = 1
    
    score = base_score
    
    for result in rules_results:
        if result.status == "RED":
            score -= red_penalty    # -10
        elif result.status == "YELLOW":
            score -= yellow_penalty  # -5
        elif result.status == "GREEN":
            score += green_bonus     # +1
    
    # Clamp to 0-100
    score = max(0, min(100, score))
    
    # Interpret
    interpretation = (
        "Excellent" if score >= 80 else
        "Good" if score >= 65 else
        "Fair" if score >= 50 else
        "Poor" if score >= 35 else
        "Critical"
    )
    
    return score, interpretation
```

**Example Calculation:**
```
Base Score: 70
Rules Results:
  - Rule A1: RED    → -10 (score: 60)
  - Rule A3: GREEN  → +1  (score: 61)
  - Rule B1: YELLOW → -5  (score: 56)
  - Rule B2: YELLOW → -5  (score: 51)
  - Rule C1: GREEN  → +1  (score: 52)

Final Score: 52 (Fair)
```

---

## LangGraph Workflow Deep Dive

### Graph Structure

```python
class AnalysisWorkflow:
    def _build_graph(self):
        builder = StateGraph(AnalysisState)
        
        # Add nodes
        builder.add_node("initialize", initialize_workflow)
        builder.add_node("router", router_function)
        builder.add_node("run_borrowings", run_module_node("borrowings"))
        builder.add_node("run_equity_funding_mix", run_module_node("equity_funding_mix"))
        builder.add_node("calculate_score", calculate_overall_score)
        builder.add_node("generate_summary", generate_final_summary)
        
        # Add edges
        builder.add_edge(START, "initialize")
        builder.add_edge("initialize", "router")
        builder.add_conditional_edges("router", route_to_module, {...})
        builder.add_edge("run_borrowings", "router")
        builder.add_edge("run_equity_funding_mix", "router")
        builder.add_edge("calculate_score", "generate_summary")
        builder.add_edge("generate_summary", END)
        
        self.graph = builder.compile(checkpointer=self.checkpointer)
```

### State Accumulation

The `Annotated[List[str], operator.add]` type means values accumulate across nodes:

```python
class AnalysisState(TypedDict):
    modules_completed: Annotated[List[str], operator.add]
    risk_flags: Annotated[List[str], operator.add]
    key_insights: Annotated[List[str], operator.add]
```

**Example Accumulation:**
```
After initialize:
  modules_completed: []

After run_borrowings returns {"modules_completed": ["borrowings"]}:
  modules_completed: [] + ["borrowings"] = ["borrowings"]

After run_equity_funding_mix returns {"modules_completed": ["equity_funding_mix"]}:
  modules_completed: ["borrowings"] + ["equity_funding_mix"] = ["borrowings", "equity_funding_mix"]
```

### Checkpoint Support

```python
# MemorySaver stores state at each step
self.checkpointer = MemorySaver()

# Each run needs a thread_id
config = {"configurable": {"thread_id": str(uuid.uuid4())}}

# State is saved after each node execution
final_state = self.graph.invoke(initial_state, config)
```

---

## Data Flow Diagrams

### Request to Response Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│ API REQUEST                                                              │
│ POST /analyze                                                           │
│ {                                                                        │
│   company: "RELIANCE",                                                  │
│   financial_data: {                                                     │
│     financial_years: [                                                  │
│       {year: 2024, revenue: 900000, ebitda: 150000, ...},             │
│       {year: 2023, revenue: 750000, ebitda: 120000, ...}              │
│     ]                                                                   │
│   },                                                                    │
│   modules: ["borrowings"],                                             │
│   generate_narrative: false                                             │
│ }                                                                        │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ DATA PREPARATION (main.py)                                              │
│                                                                          │
│ current_data = {                                                        │
│   year: 2024, revenue: 900000, ebitda: 150000,                         │
│   total_debt: 250000, ...  (computed fields added)                     │
│ }                                                                        │
│                                                                          │
│ historical_data = [                                                     │
│   {year: 2023, ...},  // Index 0 - oldest                              │
│   {year: 2024, ...}   // Index 1 - newest                              │
│ ]                                                                        │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ WORKFLOW EXECUTION (workflow.py)                                        │
│                                                                          │
│ State Flow:                                                             │
│ {modules_to_run: ["borrowings"], modules_completed: [], ...}           │
│                              │                                          │
│                              ▼                                          │
│ INITIALIZE ─► ROUTER ─► run_borrowings ─► ROUTER ─► calculate_score    │
│                              │                                          │
│                              ▼                                          │
│ {modules_completed: ["borrowings"], module_results: {...}, ...}        │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ MODULE ANALYSIS (generic_agent.py)                                      │
│                                                                          │
│ 1. Calculate Metrics:                                                   │
│    {de_ratio: 0.625, debt_ebitda: 1.67, interest_coverage: 6.0, ...}  │
│                                                                          │
│ 2. Evaluate Rules:                                                      │
│    Rule B1 (D/E): de_ratio=0.625, threshold=0.5 → YELLOW               │
│    Rule B2 (Debt/EBITDA): 1.67, threshold=2.0 → GREEN                  │
│    Rule C1 (ICR): 6.0, threshold=3.0 → GREEN                           │
│                                                                          │
│ 3. Calculate Score:                                                     │
│    Base=70, -5(YELLOW), +1(GREEN), +1(GREEN) = 67                      │
│                                                                          │
│ 4. Return ModuleOutput                                                  │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ API RESPONSE                                                            │
│ {                                                                        │
│   company: "RELIANCE",                                                  │
│   workflow_status: "completed",                                         │
│   overall_score: 67,                                                    │
│   modules_completed: ["borrowings"],                                    │
│   risk_flags: [],                                                       │
│   key_insights: ["[BORROWINGS] ✓ Strong debt coverage"],               │
│   module_results: {                                                     │
│     borrowings: {                                                       │
│       score: 67,                                                        │
│       metrics: {de_ratio: 0.625, ...},                                 │
│       rules_results: [...]                                              │
│     }                                                                    │
│   },                                                                     │
│   summary: "# Financial Analysis Summary...",                          │
│   yoy_growth: {...}                                                     │
│ }                                                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Class Reference

### ModuleOutput

```python
class ModuleOutput(BaseModel):
    """Universal output for any module"""
    module_name: str          # "Borrowings"
    module_id: str            # "borrowings"
    timestamp: str            # ISO timestamp
    metrics: Dict[str, float] # Calculated metrics
    rules_results: List[RuleResult]  # Rule evaluations
    trends: List[TrendResult] # CAGR/trend data
    score: int                # 0-100
    score_interpretation: str # "Excellent", "Good", etc.
    llm_narrative: str        # LLM-generated analysis
```

### RuleResult

```python
class RuleResult(BaseModel):
    """Single rule evaluation result"""
    rule_id: str              # "B1"
    rule_name: str            # "Debt-to-Equity Ratio"
    metric_name: str          # "de_ratio"
    value: float              # 0.625
    status: str               # "RED", "YELLOW", "GREEN"
    benchmark: str            # "Red: > 1.0, Yellow: > 0.5, Green: <= 0.5"
    message: str              # "Moderate leverage levels (Value: 62.50%)"
    
    # Enhanced insights
    summary: str              # "Moderate leverage levels"
    implication: str          # "Leverage is manageable but warrants monitoring"
    investor_action: str      # "Monitor quarterly for any increase"
    risk_level: str           # "Medium"
    peer_context: str         # "Most investment-grade companies..."
```

### TrendResult

```python
class TrendResult(BaseModel):
    """Trend calculation result"""
    name: str           # "debt_cagr"
    value: float        # 0.12 (12%)
    interpretation: str # "Moderate growth"
```

### AnalysisState

```python
class AnalysisState(TypedDict):
    """LangGraph workflow state"""
    # Input
    company: str
    current_data: Dict[str, float]
    historical_data: List[Dict[str, float]]
    
    # Config
    modules_to_run: List[str]
    generate_narrative: bool
    
    # Tracking (accumulating)
    modules_completed: Annotated[List[str], operator.add]
    modules_failed: Annotated[List[str], operator.add]
    risk_flags: Annotated[List[str], operator.add]
    key_insights: Annotated[List[str], operator.add]
    errors: Annotated[List[str], operator.add]
    
    # Results
    module_results: Dict[str, Dict]
    overall_score: int
    final_summary: str
    workflow_status: str
```

---

## Configuration Loading

### YAML Loading

**Location:** `src/app/config/__init__.py`

```python
def load_agents_config() -> Dict[str, Any]:
    """Load YAML configuration"""
    config_path = Path(__file__).parent / "agents_config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def get_module_config(module_id: str) -> Optional[Dict]:
    """Get config for specific module"""
    config = load_agents_config()
    return config.get("modules", {}).get(module_id)
```

### Global Configuration

```yaml
# agents_config.yaml
global:
  default_score: 70     # Starting score
  red_penalty: 10       # Deduction for RED
  yellow_penalty: 5     # Deduction for YELLOW
  green_bonus: 1        # Bonus for GREEN
  min_score: 0          # Minimum score
  max_score: 100        # Maximum score
```

### Module Configuration Structure

```yaml
modules:
  borrowings:
    enabled: true
    name: "Borrowings"
    description: "..."
    
    agent_prompt: |
      You are a senior credit analyst...
    
    output_sections: [...]
    input_fields: [...]
    benchmarks: {...}
    metrics: {...}
    trends: [...]
    rules:
      - id: B1
        name: "Debt-to-Equity Ratio"
        metric: de_ratio
        red: "> 1.0"
        yellow: "> 0.5"
        green: "<= 0.5"
        insights:
          red: {...}
          yellow: {...}
          green: {...}
```

---

## Summary

The execution flow follows these key phases:

1. **Request Processing** → Parse JSON, extract data, prepare historical data
2. **Workflow Initialization** → Set up LangGraph state
3. **Module Routing** → Determine which module to run next
4. **Module Execution** → GenericAgent calculates metrics, evaluates rules, generates insights
5. **Score Aggregation** → Average scores across modules
6. **Summary Generation** → Create markdown summary with risk flags and insights
7. **Response** → Return structured JSON with all results

The system is highly configurable through YAML, with metrics, rules, and insights all defined in configuration rather than code.
