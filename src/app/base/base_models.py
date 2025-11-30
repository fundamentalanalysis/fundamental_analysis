# =============================================================
# src/app/base/base_models.py
# Base models for all analytical modules
# =============================================================

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from abc import ABC


class BaseRuleResult(BaseModel):
    """Base rule result that all modules should extend"""
    rule_id: str
    rule_name: str
    flag: str  # RED, YELLOW, GREEN
    value: Optional[float] = None
    threshold: str
    reason: str


class BaseModuleInput(BaseModel):
    """Base input contract for all modules"""
    company_id: str
    industry_code: str = "GENERAL"


class BaseModuleOutput(BaseModel):
    """Base output schema for all modules"""
    module: str
    sub_score_adjusted: int
    analysis_narrative: List[str]
    red_flags: List[Dict[str, Any]]
    positive_points: List[str]
    rule_results: List[BaseRuleResult]
    metrics: Dict[str, Any]


class RedFlag(BaseModel):
    """Standard red flag structure"""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    title: str
    detail: str
