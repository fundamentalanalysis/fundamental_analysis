# lfr_llm_agent.py

import json
from openai import OpenAI
from src.app.config import OPENAI_API_KEY

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

LLM_MODEL = "gpt-4o-mini"   # fast + cheap + accurate


# -------------------------------------------------------------------
# SAFE FORMATTER (FIX FOR NoneType FORMAT ERROR)
# -------------------------------------------------------------------
def fmt(val, precision=2):
    if val is None:
        return "NA"
    try:
        return f"{val:.{precision}f}"
    except:
        return "NA"


# -------------------------------------------------------------------
# 1. Build Prompt Template
# -------------------------------------------------------------------
def build_lfr_prompt(company, metrics, trends, flags):
    latest = metrics["latest"]
    latest_year = metrics["latest_year"]

    # --------------------------------------
    # Extract latest YoY metrics safely
    # --------------------------------------
    def get_latest_yoy(metric):
        yoy_map = trends.get(metric, {}).get("yoy_growth_pct", {})
        return yoy_map.get("Y_vs_Y-1")

    recent_trend_summary = {
        "total_debt_yoy": get_latest_yoy("total_debt"),
        "ebitda_yoy": get_latest_yoy("ebitda"),
        "interest_coverage_yoy": get_latest_yoy("interest_coverage_ratio"),
        "short_term_debt_ratio_yoy": get_latest_yoy("short_term_debt_ratio"),
    }

    prompt = f"""
You are a senior financial risk analyst specializing in leverage, debt sustainability,
and credit risk assessment (Fitch / S&P style).

Your job is to read deterministic leverage metrics + rule-based flags and
generate a structured financial risk assessment.

===============================
COMPANY: {company}
LATEST YEAR: {latest_year}
===============================

📌 LEVERAGE & DEBT METRICS (LATEST YEAR)
Debt-to-Equity: {fmt(latest.get('de_ratio'))}
Debt / EBITDA: {fmt(latest.get('debt_ebitda'))}
Net Debt / EBITDA: {fmt(latest.get('net_debt_ebitda'))}
Interest Coverage Ratio: {fmt(latest.get('icr'))}
Short-Term Debt Ratio: {fmt(latest.get('st_debt_ratio'))}

📌 5-YEAR TRENDS (Latest YoY)
{json.dumps(recent_trend_summary, indent=2)}

📌 TRIGGERED RULE FLAGS
{json.dumps(flags, indent=2)}

=====================================
YOUR TASKS:
=====================================

1. **Summarize the leverage & financial risk profile** in 3–6 crisp bullets.

2. **Identify RED FLAGS** (credit stress, refinancing risk, servicing weakness).

3. **Identify POSITIVE POINTS** (balance sheet strengths, improving metrics).

4. **Generate a SUB-SCORE (0–100)** where:
   - 80–100 = Low financial risk
   - 60–79 = Moderate risk
   - 40–59 = High risk
   - <40 = Severe financial stress

5. OUTPUT STRICT JSON EXACTLY IN THIS FORMAT:

{{
  "analysis_narrative": ["...", "..."],
  "red_flags": [
      {{
         "severity": "CRITICAL",
         "title": "...",
         "detail": "..."
      }}
  ],
  "positive_points": ["...", "..."],
  "sub_score_adjusted": 0
}}

STRICT RULES:
- JSON only.
- No markdown.
- No explanation.
- No extra commentary.
"""
    return prompt


# -------------------------------------------------------------------
# 2. Call OpenAI LLM (Chat Completion)
# -------------------------------------------------------------------
def run_lfr_llm_agent(company, metrics, trends, flags):

    prompt = build_lfr_prompt(company, metrics, trends, flags)

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are a financial risk analyst."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
    )

    raw_output = response.choices[0].message.content
    print("Raw LLM Output:", raw_output)
    return safe_json_parse(raw_output)


# -------------------------------------------------------------------
# 3. Safe JSON Parser
# -------------------------------------------------------------------
def safe_json_parse(raw):
    try:
        return json.loads(raw)
    except:
        try:
            cleaned = raw[raw.find("{"): raw.rfind("}") + 1]
            return json.loads(cleaned)
        except:
            return {
                "analysis_narrative": [],
                "red_flags": [],
                "positive_points": [],
                "sub_score_adjusted": 50
            }
