# aiqm_llm.py

import json
from openai import OpenAI
# from src.app.config import OPENAI_API_KEY
from src.app.config import get_llm_client, OPENAI_MODEL


# Initialize OpenAI client
client = get_llm_client()

LLM_MODEL = "gpt-4o-mini"   # fast + cost efficient


# -------------------------------------------------------------------
# 1. BUILD PROMPT FOR AIQM
# -------------------------------------------------------------------
def build_aiqm_prompt(company, metrics, trends, flags):
    latest = metrics["latest"]
    latest_year = metrics["latest_year"]

    # -----------------------------------------------------------
    # Extract latest YoY trend metrics (same logic as WC module)
    # -----------------------------------------------------------
    def get_latest_yoy(metric):
        yoy_map = trends.get(metric, {}).get("yoy_growth_pct", {})
        return yoy_map.get("Y_vs_Y-1")

    recent_trend_summary = {
        "asset_turnover_yoy": get_latest_yoy("asset_turnover"),
        "asset_age_proxy_yoy": get_latest_yoy("asset_age_proxy"),
        "intangibles_yoy": get_latest_yoy("intangibles"),
        "revenue_yoy": get_latest_yoy("revenue"),
    }

    # -----------------------------------------------------------
    # Prompt Template
    # -----------------------------------------------------------
    prompt = f"""
You are a senior financial analyst specializing in **Asset Quality, Intangible Assets, and Impairment Risk Assessment**.

Your job is to read deterministic metrics + rule-based flags and generate a clean JSON summary.

===============================
COMPANY: {company}
LATEST YEAR: {latest_year}
===============================

📌 ASSET & INTANGIBLE METRICS (LATEST YEAR)
Asset Turnover: {latest.get('asset_turnover')}
Asset Age Proxy: {latest.get('asset_age_proxy')}
Intangible % of Total Assets: {latest.get('intangible_pct_total_assets')}
Intangible Growth YoY: {latest.get('intangible_growth_yoy')}
Amortization Ratio: {latest.get('amortization_ratio')}
R&D to Intangible Additions Ratio: {latest.get('r_and_d_intangible_ratio')}

📌 5-YEAR TREND HIGHLIGHTS (Latest YoY)
{json.dumps(recent_trend_summary, indent=2)}

📌 RULE FLAGS TRIGGERED
{json.dumps(flags, indent=2)}

=================================================
YOUR TASKS:
=================================================

1. **Summarize the asset & intangible quality story** in 3–6 crisp bullets.
   - Mention asset productivity
   - Asset aging condition
   - Intangible trends & concentration
   - Any impairment or capitalization concerns

2. **Identify RED FLAGS** based on rule outputs  
3. **Identify POSITIVE POINTS**  
4. **Generate a SUB-SCORE (0–100)** representing asset & intangible quality  
   - Higher is better quality & lower impairment risk

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
- JSON only
- No markdown
- No extra commentary
- No explanation outside JSON
"""

    return prompt



# -------------------------------------------------------------------
# 2. CALL OPENAI LLM (Chat Completion)
# -------------------------------------------------------------------
def run_aiqm_llm_agent(company, metrics, trends, flags):

    prompt = build_aiqm_prompt(company, metrics, trends, flags)

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are a financial analyst for asset & intangible quality assessment."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    raw_output = response.choices[0].message.content
    print("Raw AIQM LLM Output:", raw_output)
    return safe_json_parse(raw_output)



# -------------------------------------------------------------------
# 3. SAFE JSON PARSER (Same as WC module)
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
