# def generate_llm_narrative(company, rules, score):
#     if not rules:
#         return [f"{company} shows no structural risk patterns."], score

#     narrative = [f"{r.rule_name}: {r.reason}" for r in rules]
#     return narrative, score

def generate_llm_narrative(company, trends):
    narrative = []

    # -------------------------------------------------
    # ASSET STRIPPING NARRATIVE
    # -------------------------------------------------
    asset_cmp = trends.get("asset_stripping", {}) \
                      .get("debt_vs_assets", {}) \
                      .get("comparison", {})

    if asset_cmp.get("rule_triggered"):
        narrative.append(
            f"Asset stripping risk identified for {company}: net debt increased while "
            f"fixed assets declined in multiple years ({asset_cmp.get('overlap_years')}). "
            f"This indicates possible hollowing of the asset base."
        )
    else:
        narrative.append(
            f"For {company}, although debt has risen, fixed asset decline was limited "
            f"to isolated years ({asset_cmp.get('assets_falling_years', [])}), "
            f"indicating no sustained asset stripping pattern."
        )

    # -------------------------------------------------
    # LOAN EVERGREENING NARRATIVE
    # -------------------------------------------------
    evergreen_cmp = trends.get("loan_evergreening", {}) \
                          .get("debt_vs_ebitda", {}) \
                          .get("comparison", {})

    if evergreen_cmp.get("rule_triggered"):
        narrative.append(
            f"Loan evergreening risk detected for {company}: debt continued to rise while "
            f"EBITDA stagnated or declined across multiple years "
            f"({evergreen_cmp.get('overlap_years')}). "
            f"This suggests reliance on refinancing rather than earnings-based servicing."
        )
    else:
        narrative.append(
            f"Debt growth at {company} was not accompanied by persistent EBITDA deterioration, "
            f"reducing the likelihood of loan evergreening."
        )

    return narrative
