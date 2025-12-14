import json
from typing import List, Tuple

from src.app.config import OPENAI_MODEL, get_llm_client
from .equity_funding_mix_models import RuleResult

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
    Generate LLM-powered narrative and dynamic trend insights for equity funding mix.
    Returns: (narrative_list, adjusted_score, trend_insights_dict)
    """
    if client is None:
        # Fallback: return deterministic notes, no adjustment, no insights
        return deterministic_notes, base_score, {}

    print("Generating LLM narrative for company:", company_id)

    prompt_payload = {
        "company_id": company_id,
        "key_metrics": key_metrics,
        "rules": [r.dict() for r in rule_results],
        "deterministic_narrative": deterministic_notes,
        "base_score": base_score,
        "trend_data": trend_data or {},
    }

    prompt = (
        "You are the Equity & Funding Mix Agent in a Balance Sheet multi-agent system.\n"
        "Given the structured analytics below, perform two tasks:\n\n"
        "TASK 1: Craft a concise narrative with EXACTLY four sections:\n"
        "1. Overall equity quality and retained earnings assessment\n"
        "2. Key concerns (note RED/YELLOW flags on dividend sustainability, dilution, leverage)\n"
        "3. Positives / mitigating factors\n"
        "4. Final investment/capital structure conclusion (1-2 sentences)\n\n"
        "TASK 2: Analyze the trend_data for each metric (retained_earnings, payout_ratio, roe, equity_growth, debt_growth) "
        "and generate a dynamic, data-driven insight for each based on:\n"
        "- Pattern of growth/decline over 5 years\n"
        "- Sustainability signals (earnings retention vs payout)\n"
        "- Dilution events and their magnitude\n"
        "- Capital structure shifts (equity-funded vs debt-funded growth)\n"
        "- Strategic implications for long-term shareholder value\n\n"
        "Return a JSON object with:\n"
        "{\n"
        '  "analysis_narrative": [list of 4 strings matching the sections],\n'
        '  "score_adjustment": integer between -5 and 5 (can be 0),\n'
        '  "trend_insights": {\n'
        '    "retained_earnings": "data-driven insight string",\n'
        '    "payout_ratio": "data-driven insight string",\n'
        '    "roe": "data-driven insight string",\n'
        '    "equity_growth": "data-driven insight string",\n'
        '    "debt_growth": "data-driven insight string"\n'
        "  }\n"
        "}\n"
        "Only return valid JSON.\n\n"
        f"INPUT:\n{json.dumps(prompt_payload, ensure_ascii=False)}"
    )

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            timeout=30,
        )
        content = response.choices[0].message.content
    except Exception as llm_error:
        # If LLM call fails (timeout, API error, etc.), return deterministic fallback
        return deterministic_notes, base_score, {}

    content = content.strip()

    if content.startswith("```"):
        content = content.removeprefix("```json").removeprefix("```")
        content = content.removesuffix("```").strip()

    # print("LLM response content:", content)

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
        # print("LLM response JSON parsing error. Response content:", content)
        return deterministic_notes, base_score, {}
