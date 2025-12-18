from typing import List

def generate_fallback_insight(rules):
    if not rules:
        return ["No structural risk patterns detected."]
    return [r.reason for r in rules]
