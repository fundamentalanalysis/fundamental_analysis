# wc_llm_agent.py

import json
from openai import OpenAI
from src.app.config import OPENAI_API_KEY

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


LLM_MODEL = "gpt-4o-mini"   # fast + cheap + accurate


# -------------------------------------------------------------------
# 1. Build Prompt Template
# -------------------------------------------------------------------
def build_wc_prompt(company, metrics, trends, flags):
    latest = metrics["latest"]
    latest_year = metrics["latest_year"]

    # --------------------------------------
    # FIX: Extract latest YoY metrics safely
    # --------------------------------------
    def get_latest_yoy(metric):
        yoy_map = trends.get(metric, {}).get("yoy_growth_pct", {})
        return yoy_map.get("Y_vs_Y-1")

    recent_trend_summary = {
        "receivables_yoy": get_latest_yoy("trade_receivables"),
        "inventory_yoy": get_latest_yoy("inventory"),
        "payables_yoy": get_latest_yoy("trade_payables"),
        "revenue_yoy": get_latest_yoy("revenue"),
    }

    prompt = f"""
You are a senior financial analyst specializing in Working Capital & Cash Conversion analysis.

Your job is to read deterministic metrics + rule-based flags and generate a structured output.

===============================
COMPANY: {company}
LATEST YEAR: {latest_year}
===============================

📌 WORKING CAPITAL METRICS (LATEST YEAR)
DSO: {latest['dso']:.2f}
DIO: {latest['dio']:.2f}
DPO: {latest['dpo']:.2f}
CCC: {latest['ccc']:.2f}
NWC: {latest['nwc']:.2f}
NWC Ratio: {latest['nwc_ratio']:.3f}

📌 5-YEAR TRENDS (Latest YoY)
{json.dumps(recent_trend_summary, indent=2)}

📌 TRIGGERED RULE FLAGS
{json.dumps(flags, indent=2)}

=====================================
YOUR TASKS:
=====================================

1. **Summarize the working capital story** in 3–6 crisp bullets.

2. **Identify RED FLAGS**

3. **Identify POSITIVE POINTS**

4. **Generate a SUB-SCORE (0–100)**

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
def run_wc_llm_agent(company, metrics, trends, flags):

    prompt = build_wc_prompt(company, metrics, trends, flags)

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are a financial analyst."},
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
        # Try to extract only the JSON portion
        try:
            cleaned = raw[raw.find("{"): raw.rfind("}") + 1]
            return json.loads(cleaned)
        except:
            # fallback minimal structure
            return {
                "analysis_narrative": [],
                "red_flags": [],
                "positive_points": [],
                "sub_score_adjusted": 50
            }
