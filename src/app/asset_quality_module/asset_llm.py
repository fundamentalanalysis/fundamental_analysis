import json
from typing import List, Tuple, Dict
from src.app.config import OPENAI_MODEL, get_llm_client
from .asset_models import RuleResult

client = get_llm_client()

def generate_asset_llm_narrative(
    company_id: str,
    metrics: Dict[int, dict],
    trends: Dict[str, any],
    rule_results: List[RuleResult],
    deterministic_notes: List[str],
    base_score: int,
) -> Tuple[List[str], int]:
    if client is None:
        return deterministic_notes, base_score

    # Prepare payload
    latest_year = max(metrics.keys())
    latest = metrics[latest_year]
    
    prompt_payload = {
        "company_id": company_id,
        "latest_metrics": latest,
        "trends": trends,
        "rules": [r.dict() for r in rule_results],
        "deterministic_narrative": deterministic_notes,
        "base_score": base_score,
    }

    prompt = (
        "You are the Asset Quality Agent in a Balance Sheet multi-agent system.\n"
        "Evaluate the quality, productivity, aging, and risk of the company's tangible and intangible assets.\n"
        "Given the structured analytics below, craft a concise narrative with EXACTLY four sections:\n"
        "1. Asset utilization & efficiency assessment\n"
        "2. Key risks (aging, impairment, goodwill concentration)\n"
        "3. Positives / mitigating factors\n"
        "4. Final asset quality conclusion (1-2 sentences)\n\n"
        "Return a JSON object with:\n"
        "{\n"
        '  "analysis_narrative": [list of 4 strings matching the sections],\n'
        '  "score_adjustment": integer between -5 and 5 (can be 0)\n'
        "}\n"
        "Only return valid JSON.\n\n"
        f"INPUT:\n{json.dumps(prompt_payload, ensure_ascii=False, default=str)}"
    )

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)
        narrative = parsed.get("analysis_narrative") or deterministic_notes
        score_adj = parsed.get("score_adjustment")
        
        if isinstance(score_adj, (int, float)):
            adjusted_score = max(0, min(100, base_score + int(score_adj)))
        else:
            adjusted_score = base_score
            
        return narrative, adjusted_score
    except Exception as e:
        # Fallback on error
        return deterministic_notes, base_score
