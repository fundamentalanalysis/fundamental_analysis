# models.py

from pydantic import BaseModel
from typing import Any, Optional

class RuleResult(BaseModel):
    rule_id: Optional[str] = None
    rule_name: str
    metric: Optional[str] = None
    year: int
    flag: str
    value: Optional[Any] = None
    threshold: Optional[str] = None
    reason: str
