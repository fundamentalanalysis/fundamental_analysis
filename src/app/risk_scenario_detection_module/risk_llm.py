
# def generate_llm_narrative(company, trends):
#     narrative = []

#     for section, metrics in trends.items():
#         for name, block in metrics.items():
#             if isinstance(block, dict):
#                 insight = (
#                     block.get("comparison", {}).get("insight")
#                     or block.get("insight")
#                 )
#                 if insight:
#                     narrative.append(f"{company}: {insight}")

#     if not narrative:
#         narrative.append(f"No material risk patterns detected for {company}.")

#     return narrative


def generate_llm_narrative(company, trends):
    narrative = []

    z = trends["zombie_company"]
    if z["cfo_vs_interest"]["comparison"]["rule_triggered"]:
        narrative.append(
            f"{company} shows signs of financial stress, with operating cash flows failing to cover interest obligations across multiple years."
        )

    if z["debt_vs_profit"]["comparison"]["rule_triggered"]:
        narrative.append(
            "Rising leverage alongside weakening profitability indicates a developing debt spiral."
        )

    if trends["loan_evergreening"]["loan_rollover"]["comparison"]["rule_triggered"]:
        narrative.append(
            "The company appears reliant on loan refinancing rather than organic debt reduction."
        )

    if trends["circular_trading"]["sales_up_cfo_down"]["comparison"]["rule_triggered"]:
        narrative.append(
            "Revenue quality concerns are evident, as sales growth is not supported by operating cash flows."
        )

    if trends["circular_trading"]["receivables_vs_revenue"]["comparison"]["rule_triggered"]:
        narrative.append(
            "Receivables expansion ahead of revenue growth suggests aggressive revenue recognition."
        )

    if not narrative:
        narrative.append(f"No material financial risk patterns detected for {company}.")

    return narrative
