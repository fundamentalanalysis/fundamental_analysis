# # llm_agent.py

# import json
# from typing import List, Tuple

# from src.app.config import OPENAI_MODEL, get_llm_client
# from .models import RuleResult # adjust import path if needed

# client = get_llm_client()


# def generate_llm_narrative(
#     company_id: str,
#     key_metrics: dict,
#     rule_results: List[RuleResult],
#     deterministic_notes: List[str],
#     base_score: int,
#     trend_data: dict = None,
# ) -> Tuple[List[str], int, dict]:
#     """
#     Capex–CWIP LLM narrative generator aligned with Borrowings LLM interface.
    
#     Returns:
#         narrative_list: [4 narrative sections]
#         adjusted_score: base_score + LLM adjustment (bounded 0–100)
#         trend_insights: insights for each tracked metric
#     """

#     # If no LLM available → deterministic fallback
#     if client is None:
#         return deterministic_notes, base_score, {}

#     # -------------------------
#     # Build structured input (same pattern as reference)
#     # -------------------------
#     payload = {
#         "company_id": company_id,
#         "key_metrics": key_metrics,
#         "rules": [r.dict() for r in rule_results],   # RuleResult → JSON
#         "deterministic_narrative": deterministic_notes,
#         "base_score": base_score,
#         "trend_data": trend_data or {},
#     }

#     # -------------------------
#     # LLM Multi-task prompt
#     # -------------------------
#     prompt = (
#         "You are the Capex & CWIP Agent in a Balance Sheet multi-agent system.\n"
#         "Given the structured analytics below, perform TWO tasks:\n\n"
#         "TASK 1 — Write a concise 4-part narrative:\n"
#         "1. Overall capital investment assessment\n"
#         "2. Key concerns (reference RED/YELLOW rules)\n"
#         "3. Positives / mitigating factors\n"
#         "4. Final capital allocation conclusion (1–2 sentences)\n\n"
#         "TASK 2 — For each provided capex/cwip related trend metric, generate one data-driven insight:\n"
#         "- Look at CAGR direction\n"
#         "- Look at YoY patterns and volatility\n"
#         "- Identify risks (e.g., rising CWIP, low asset turnover, capex/revenue imbalance)\n"
#         "- Identify strategic signals (healthy expansion vs overstretching)\n\n"
#         "Return ONLY valid JSON with structure:\n"
#         "{\n"
#         '   "analysis_narrative": [4 narrative strings],\n'
#         '   "score_adjustment": integer (-5 to +5),\n'
#         '   "trend_insights": {\n'
#         '       "capex": "...",\n'
#         '       "cwip": "...",\n'
#         '       "nfa": "...",\n'
#         '       "revenue": "..."\n'
#         "   }\n"
#         "}\n\n"
#         f"INPUT:\n{json.dumps(payload, ensure_ascii=False)}"
#     )

#     # -------------------------
#     # LLM Call
#     # -------------------------
#     response = client.chat.completions.create(
#         model=OPENAI_MODEL,
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.2,
#     )

#     content = response.choices[0].message.content

#     # -------------------------
#     # JSON Parsing & Score Adjustment
#     # -------------------------
#     try:
#         parsed = json.loads(content)

#         narrative = parsed.get("analysis_narrative") or deterministic_notes
#         score_adj = parsed.get("score_adjustment", 0)
#         trend_insights = parsed.get("trend_insights") or {}

#         if isinstance(score_adj, (int, float)):
#             adjusted_score = max(0, min(100, base_score + int(score_adj)))
#         else:
#             adjusted_score = base_score

#         return narrative, adjusted_score, trend_insights

#     except json.JSONDecodeError:
#         # fallback deterministic version
#         return deterministic_notes, base_score, {}


import json
from typing import List, Tuple

from src.app.config import OPENAI_MODEL, get_llm_client
from .models import RuleResult

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
    "You are the Capex & CWIP Agent in a Balance Sheet multi-agent system.\n"
    "You will receive structured metrics, rule flags, and multi-year trend data for capex, cwip, and net fixed assets.\n\n"

    "TASK 1 — Write a concise narrative with EXACTLY four sections:\n"
    "1. Overall capital investment assessment (capex levels, NFA movement, CWIP trends)\n"
    "2. Key concerns (focus on RED and YELLOW rule flags)\n"
    "3. Positives / mitigating factors\n"
    "4. Final capital allocation conclusion (1–2 sentences)\n\n"

    "TASK 2 — Generate trend insights for EACH metric in trend_data (capex, cwip, nfa):\n"
    "- Use the YoY dictionary (Y_vs_Y-1, etc.)\n"
    "- Use the labeled values (Y, Y-1, Y-2, etc.)\n"
    "- Identify volatility, stability, unusual spikes/drop-offs\n"
    "- Highlight risks (e.g., rising CWIP, falling NFA, volatile capex)\n"
    "- Highlight positives (e.g., stable expansion, improving asset utilization)\n\n"

    "Return ONLY valid JSON:\n"
    "{\n"
    '  "analysis_narrative": [4 strings],\n'
    '  "score_adjustment": integer between -5 and 5,\n'
    '  "trend_insights": {\n'
    '      "capex": "insight...",\n'
    '      "cwip": "insight...",\n'
    '      "nfa": "insight..."\n'
    "  }\n"
    "}\n\n"
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
    