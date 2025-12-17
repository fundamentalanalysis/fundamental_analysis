from typing import List


# def generate_fallback_insight(rules):
#     if not rules:
#         return ["No major structural or fraud-related risk scenarios detected."]

#     return [f"{r.rule_name}: {r.reason}" for r in rules]


def generate_fallback_insight(rules):
    if not rules:
        return ["No structural risk patterns detected."]
    return [r.reason for r in rules]
