# models.py

from pydantic import BaseModel
from typing import Any


class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    metric: str
    year: int
    flag: str
    value: Any
    threshold: str
    reason: str
