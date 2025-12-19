from typing import Dict, List, Any


def _call_llm(prompt: str) -> str:
    """
    Replace this body with OpenAI / Azure / Gemini call.
    MUST return only analyst conclusions (no instructions, no JSON echo).
    """

    # ⚠️ TEMP SAFE FALLBACK (NO PROMPT ECHO)
    return """
• Operating cash flows have been insufficient to cover interest expenses for multiple years, indicating reliance on refinancing.
• Net debt increased while profitability weakened, suggesting a developing debt spiral.
• Borrowings have consistently exceeded repayments, pointing to loan evergreening risk.
• Revenue growth without corresponding cash flow support raises concerns of circular trading.
• One-off income materially impacted profits, reducing earnings quality.
    """


def generate_llm_narrative(
    company_id: str,
    trends: Dict[str, Any],
    rules: List[Any],
) -> List[str]:
    """
    Generates a clean, human-readable financial risk narrative.
    """

    # -----------------------------
    # Build structured prompt
    # -----------------------------
    prompt = f"""
You are a senior financial risk analyst.

Company: {company_id}

Summarize the key financial risks based ONLY on the trends and rules provided.
Do NOT repeat raw data.
Do NOT include instructions.
Return concise bullet points only.

RISK TRENDS:
{trends}

TRIGGERED RULES:
{[r.dict() for r in rules]}
"""

    # -----------------------------
    # LLM call
    # -----------------------------
    raw = _call_llm(prompt)

    # -----------------------------
    # Clean & normalize output
    # -----------------------------
    lines = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        line = line.lstrip("-• ").strip()
        if line:
            lines.append(line)

    # -----------------------------
    # Final safety fallback
    # -----------------------------
    if not lines:
        return ["No material financial risk signals identified based on available data."]

    return lines
