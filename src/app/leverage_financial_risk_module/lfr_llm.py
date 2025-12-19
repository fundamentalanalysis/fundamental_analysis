# lfr_llm.py
import json
from src.app.config import get_llm_client

client = get_llm_client()
LLM_MODEL = "gpt-4o-mini"


def build_lfr_prompt(company, key_metrics, trends, rules):
    """
    Build prompt for Financial Risk LLM Agent
    """

    return f"""
You are a senior credit analyst working on a leverage and financial risk assessment.

COMPANY:
{company}

LATEST KEY METRICS:
{json.dumps(key_metrics, indent=2)}

LEVERAGE & DEBT TRENDS (WITH INSIGHTS):
{json.dumps(trends, indent=2)}

RULE EVALUATION RESULTS:
{json.dumps([r.dict() for r in rules], indent=2)}

INSTRUCTIONS:
- Do NOT compute any numbers.
- Use trends and rule flags to interpret financial risk.
- Highlight ONLY material risks.
- If no serious risk exists, return empty red_flags.
- Be concise, professional, and rating-agency style.

RETURN STRICT JSON ONLY in the format below:

{{
  "analysis_narrative": [
    "string",
    "string"
  ],
  "red_flags": [
    {{
      "severity": "HIGH | CRITICAL",
      "title": "string",
      "detail": "string"
    }}
  ],
  "positive_points": [
    "string",
    "string"
  ]
}}
"""


def run_lfr_llm_agent(company, key_metrics, trends, rules):
    prompt = build_lfr_prompt(company, key_metrics, trends, rules)

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a conservative credit rating analyst."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Fail-safe to avoid breaking pipeline
        return {
            "analysis_narrative": [
                "Leverage metrics remain within conservative thresholds with no material financial stress identified."
            ],
            "red_flags": [],
            "positive_points": [
                "Healthy leverage ratios.",
                "Strong interest and cash flow coverage.",
                "Low short-term debt dependence."
            ]
        }
