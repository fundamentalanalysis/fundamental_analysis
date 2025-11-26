# debt_llm.py
# src/app/borrowing_module/debt_llm.py


from src.app.config import  OPENAI_MODEL
from src.app.config import get_llm_client

client = get_llm_client()
model = OPENAI_MODEL


def generate_llm_narrative(company_id, metrics, rules):

    prompt = f"""
You are a senior credit analyst.

Generate a structured Borrowings (Debt) Analysis for company {company_id}.

Metrics:
{metrics}

Rule Flags:
{[r.model_dump() for r in rules]}

Write ONLY these 4 sections:
1. Overall leverage assessment
2. Key concerns (red/yellow flags)
3. Positives
4. Final investment/credit conclusion
"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    return response.choices[0].message.content