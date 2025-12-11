# qoe_llm_agent.py

import json
from openai import OpenAI
from src.app.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)
LLM_MODEL = "gpt-4o-mini"


# ------------------------------------------------------------
# Helper: Safely get YoY from trends (new structure)
# ------------------------------------------------------------
def get_latest_yoy(trends, key):
    block = trends.get(key, {})
    yoy_map = block.get("yoy_growth_pct", {})
    return yoy_map.get("Y_vs_Y-1")


# ------------------------------------------------------------
# 1. Build Prompt (UPDATED TO MATCH NEW METRICS)
# ------------------------------------------------------------
def build_qoe_prompt(company, metrics, trends, rule_flags):

    latest = metrics["latest"]
    latest_year = metrics["latest_year"]

    # Extract YoY from updated trends
    recent_trends = {
        "qoe_yoy": get_latest_yoy(trends, "qoe"),
        "accruals_yoy": get_latest_yoy(trends, "accruals"),
        "ocf_yoy": get_latest_yoy(trends, "operating_cash_flow"),
        "net_income_yoy": get_latest_yoy(trends, "net_income"),
        "revenue_quality_yoy": get_latest_yoy(trends, "ocf_to_revenue"),   # mapped from old label
        "dso_yoy": get_latest_yoy(trends, "dso")
    }

    prompt = f"""
You are a senior financial analyst specializing in **Quality of Earnings (QoE)**.

You will analyze deterministic QoE metrics, trend maps, and rule-engine flags and produce a structured JSON OUTPUT ONLY.

===============================
COMPANY: {company}
LATEST YEAR: {latest_year}
===============================

📌 QoE METRICS (LATEST YEAR)
QoE Ratio: {latest['qoe']}
Accruals Ratio: {latest['accruals_ratio']}
Operating Cash Flow: {latest['operating_cash_flow']}
Net Income: {latest['net_income']}
Revenue Quality (OCF/Revenue): {latest['revenue_quality']}
DSO: {latest['dso']}
Other Income Ratio: {latest['other_income_ratio']}

📌 5-YEAR TREND SNAPSHOT (Latest YoY Shifts)
{json.dumps(recent_trends, indent=2)}

📌 RULE FLAGS (Deterministic Output from Rule Engine)
{json.dumps(rule_flags, indent=2)}

=====================================
YOUR TASKS:
=====================================

1. Summarize the complete Quality of Earnings story in **3–6 crisp bullets**.
2. Identify **RED FLAGS**, including:
   - deteriorating QoE
   - rising accruals
   - PAT vs OCF divergence
   - rising DSO / revenue-aggressive patterns
   - heavy dependence on non-core income
3. Identify **POSITIVE POINTS**, such as:
   - improved cash conversion
   - stable accrual behavior
   - improving OCF/Revenue
4. Generate a **QoE SUB-SCORE (0–100)** representing overall earnings quality.

=====================================
OUTPUT FORMAT (STRICT):
=====================================

Return ONLY valid JSON in this format:

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
- NO markdown
- NO text outside JSON
- NO commentary
"""
    return prompt


# ------------------------------------------------------------
# 2. Run LLM Agent
# ------------------------------------------------------------
def run_qoe_llm_agent(company, metrics, trends, flags):

    prompt = build_qoe_prompt(company, metrics, trends, flags)

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are a financial analyst specializing in earnings quality."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.15,
    )

    raw_output = response.choices[0].message.content
    print("Raw QoE LLM Output:", raw_output)
    return safe_json_parse(raw_output)


# ------------------------------------------------------------
# 3. Safe JSON Parse (Same as WC)
# ------------------------------------------------------------
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
