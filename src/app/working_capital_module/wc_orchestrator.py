from src.app.working_capital_module.wc_llm import run_wc_llm_agent
from src.app.working_capital_module.wc_models import WorkingCapitalInput
from src.app.working_capital_module.wc_rules import wc_rule_engine
from src.app.working_capital_module.wc_aggregator import build_metrics
from src.app.working_capital_module.wc_trend import compute_yoy_trends
from .wc_models import WorkingCapitalRules

def extract_year_from_obj(obj):
    return int(obj.year.split()[-1])   # works for "Mar 2025"
    

def run_working_capital_module(payload: dict):
    data = WorkingCapitalInput(**payload)
    
    rules = WorkingCapitalRules()  # Default rules can be customized if needed

    financials_sorted = sorted(
        data.financial_data.financial_years,
        key=lambda x: extract_year_from_obj(x) , reverse=True
    )
    # Step 1: Deterministic metrics
    metrics = build_metrics(financials_sorted)

    # Step 2: Trends
    trends = compute_yoy_trends(financials_sorted)

    # Step 3: Rule Engine
    flags = wc_rule_engine(metrics, trends, rules)
    print("Flags from WC Orchestrator:", flags)
    # Step 4: LLM Narrative (OpenAI)
    llm_output = run_wc_llm_agent(data.company, metrics, trends, flags)

    return {
        "module": "WorkingCapital",
        "company": data.company,
        "metrics": metrics,
        "trends": trends,
        "flags": flags,
        "analysis_narrative": llm_output["analysis_narrative"],
        "red_flags": llm_output["red_flags"],
        "positive_points": llm_output["positive_points"],
        "sub_score_adjusted": llm_output["sub_score_adjusted"]
    }
