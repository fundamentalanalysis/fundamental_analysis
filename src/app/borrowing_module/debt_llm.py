import json
from typing import List, Tuple

from src.app.config import OPENAI_MODEL, get_llm_client
from .debt_models import RuleResult

client = get_llm_client()


def generate_llm_narrative(
    company_id: str,
    key_metrics: dict,
    rule_results: List[RuleResult],
    deterministic_notes: List[str],
    base_score: int,
    trend_data: dict = None,
) -> Tuple[List[str], int, dict]:
    """
    Generate LLM-powered narrative and dynamic trend insights.
    Returns: (narrative_list, adjusted_score, trend_insights_dict)
    """
    if client is None:
        # Fallback: return deterministic notes, no adjustment, no insights
        return deterministic_notes, base_score, {}

    prompt_payload = {
        "company_id": company_id,
        "key_metrics": key_metrics,
        "rules": [r.dict() for r in rule_results],
        "deterministic_narrative": deterministic_notes,
        "base_score": base_score,
        "trend_data": trend_data or {},
    }

    prompt = (
        "You are the Debt Agent in a Balance Sheet multi-agent system.\n"
        "Given the structured analytics below, perform two tasks:\n\n"
        "TASK 1: Craft a concise narrative with EXACTLY four sections:\n"
        "1. Overall leverage assessment\n"
        "2. Key concerns (note RED/YELLOW flags)\n"
        "3. Positives / mitigating factors\n"
        "4. Final investment/credit conclusion (1-2 sentences)\n\n"
        "TASK 2: Analyze the trend_data for each metric (short_term_debt, long_term_debt, finance_cost) "
        "and generate a dynamic, data-driven insight for each based on:\n"
        "- Pattern of growth/decline over 5 years\n"
        "- YoY volatility or consistency\n"
        "- Potential vulnerabilities or risks (e.g., accelerating debt, unstable finance costs)\n"
        "- Strategic implications (growth-driven vs stress-driven borrowing)\n\n"
        "Return a JSON object with:\n"
        "{\n"
        '  "analysis_narrative": [list of 4 strings matching the sections],\n'
        '  "score_adjustment": integer between -5 and 5 (can be 0),\n'
        '  "trend_insights": {\n'
        '    "short_term_debt": "data-driven insight string",\n'
        '    "long_term_debt": "data-driven insight string",\n'
        '    "finance_cost": "data-driven insight string"\n'
        "  }\n"
        "}\n"
        "Only return valid JSON.\n\n"
        f"INPUT:\n{json.dumps(prompt_payload, ensure_ascii=False)}"
    )

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    content = response.choices[0].message.content
    try:
        parsed = json.loads(content)
        narrative = parsed.get("analysis_narrative") or deterministic_notes
        score_adj = parsed.get("score_adjustment")
        trend_insights = parsed.get("trend_insights") or {}
        
        if isinstance(score_adj, (int, float)):
            adjusted_score = max(0, min(100, base_score + int(score_adj)))
        else:
            adjusted_score = base_score
        return narrative, adjusted_score, trend_insights
    except json.JSONDecodeError:
        return deterministic_notes, base_score, {}
