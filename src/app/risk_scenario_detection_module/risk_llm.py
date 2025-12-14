from src.app.config import get_llm_client, OPENAI_MODEL


class RiskScenarioAgentLLM:

    def __init__(self):
        self.client = get_llm_client()

    async def interpret(self, rules_triggered, red_flags):
        print(rules_triggered)
        text_rules = "\n".join([f"- {r["rule_name"]}: {r["reason"]}" for r in rules_triggered])

        prompt = f"""
You are the Risk Scenario Agent.
Interpret the following risk scenario rule triggers:

RULES:
{text_rules}

Other module red flags:
{red_flags}

Produce:
1. Scenario classification
2. Severity (Low / Moderate / High / Critical)
3. A narrative explaining the interactions
"""
        print("before response")

        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        print("LLM response:", response)

        return response.choices[0].message.content
