# =============================================================
# src/app/blackboard/models.py
# Blackboard Entry Types with Strict Typing
# Layer B - Shared State & Governance
# =============================================================
"""
Blackboard entry types for the Level-5 Agentic Mesh.

Think of the blackboard as event-sourced state with strict typing:
- Facts: deterministic outputs from engines (immutable)
- Hypotheses: LLM outputs with provenance
- Attacks: Critic contradictions
- Resolutions: Mediator outcomes
- FinalDecision: Judge's synthesis
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import uuid


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EntryType(str, Enum):
    """Types of entries in the blackboard."""
    FACT = "fact"
    HYPOTHESIS = "hypothesis"
    ATTACK = "attack"
    RESOLUTION = "resolution"
    FINAL = "final"


class HypothesisStatus(str, Enum):
    """Status of a hypothesis in the debate cycle."""
    ACTIVE = "active"
    ATTACKED = "attacked"
    DEFENDED = "defended"
    RESOLVED = "resolved"
    EXPIRED = "expired"


class Severity(str, Enum):
    """Severity levels for attacks and findings."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConsensusState(str, Enum):
    """Final decision consensus states."""
    CONSENSUS = "CONSENSUS"      # High convergence (>=90%)
    WEIGHTED = "WEIGHTED"        # Medium convergence (60-90%)
    UNRESOLVED = "UNRESOLVED"    # Low convergence (<60%)


# ---------------------------------------------------------------------------
# Fact - Deterministic outputs (immutable)
# ---------------------------------------------------------------------------

class Fact(BaseModel):
    """
    Deterministic fact computed by engines.
    
    Facts are immutable and can only be written by:
    - metric_engine
    - trend_engine
    - correlation_engine
    - data_quality_engine
    """
    fact_id: str = Field(default_factory=lambda: f"fact_{uuid.uuid4().hex[:8]}")
    key: str  # e.g., "de_ratio", "debt_cagr", "revenue_yoy"
    value: Union[float, int, bool, str, None]
    unit: Optional[str] = None  # e.g., "ratio", "percent", "years"
    period: Optional[int] = None  # Year (e.g., 2024)
    module: Optional[str] = None  # Which module this fact belongs to
    source_engine: str  # "metric_engine", "trend_engine", etc.
    version: int = 1
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data_quality: float = Field(default=1.0, ge=0.0, le=1.0)  # Confidence in data
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        frozen = True  # Immutable


# ---------------------------------------------------------------------------
# Hypothesis - LLM outputs with provenance
# ---------------------------------------------------------------------------

class Hypothesis(BaseModel):
    """
    LLM-generated hypothesis with provenance tracking.
    
    Hypotheses are written by analyst agents and can be:
    - Attacked by the Critic
    - Resolved by the Mediator
    - Used by the Judge for synthesis
    """
    hypothesis_id: str = Field(default_factory=lambda: f"hyp_{uuid.uuid4().hex[:8]}")
    agent_id: str  # e.g., "debt_analyst", "liquidity_analyst"
    claim: str  # The hypothesis statement
    linked_facts: List[str] = Field(default_factory=list)  # fact_ids supporting this
    confidence: float = Field(ge=0.0, le=1.0)  # Agent's confidence in the claim
    evidence_refs: List[str] = Field(default_factory=list)  # References to evidence
    reasoning: Optional[str] = None  # Chain of thought / reasoning
    ttl_rounds: int = Field(default=5)  # Time-to-live in debate rounds
    status: HypothesisStatus = HypothesisStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Provenance tracking
    model_used: Optional[str] = None  # LLM model that generated this
    prompt_hash: Optional[str] = None  # Hash of prompt for reproducibility


# ---------------------------------------------------------------------------
# Attack - Critic contradictions
# ---------------------------------------------------------------------------

class Attack(BaseModel):
    """
    Critic's attack on a hypothesis.
    
    Attacks highlight weaknesses, contradictions, or missing evidence
    in analyst hypotheses.
    """
    attack_id: str = Field(default_factory=lambda: f"atk_{uuid.uuid4().hex[:8]}")
    critic_id: str  # e.g., "short_seller_critic"
    target_hypothesis_id: str  # Which hypothesis is being attacked
    contradiction_type: str  # e.g., "data_inconsistency", "missing_evidence", "logical_flaw"
    severity: Severity = Severity.MEDIUM
    claim: str  # The attack statement
    evidence_refs: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    counter_facts: List[str] = Field(default_factory=list)  # Facts that contradict hypothesis
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Resolution - Mediator outcomes
# ---------------------------------------------------------------------------

class Resolution(BaseModel):
    """
    Mediator's resolution of a debate.
    
    Resolutions track which items were resolved, which remain unresolved,
    and the overall quality of the debate.
    """
    resolution_id: str = Field(default_factory=lambda: f"res_{uuid.uuid4().hex[:8]}")
    round_number: int
    resolved_hypotheses: List[str] = Field(default_factory=list)  # hypothesis_ids
    resolved_attacks: List[str] = Field(default_factory=list)  # attack_ids
    unresolved_items: List[str] = Field(default_factory=list)  # Items still in dispute
    rationale: str  # Explanation of resolution
    convergence_score: float = Field(ge=0.0, le=1.0)  # How much agreement
    debate_quality: float = Field(ge=0.0, le=1.0)  # Quality of the debate
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Override - Correlation engine overrides
# ---------------------------------------------------------------------------

class Override(BaseModel):
    """
    Deterministic override from correlation engine.
    
    Overrides can cap scores, set floors, or trigger kill-switches
    based on cross-module patterns.
    """
    override_id: str = Field(default_factory=lambda: f"ovr_{uuid.uuid4().hex[:8]}")
    rule_id: str  # e.g., "CORR_001"
    rule_name: str  # e.g., "terminal_decline"
    description: str
    action: str  # "cap_score", "floor_score", "kill_switch", "flag_spof"
    value: Optional[float] = None  # Cap/floor value if applicable
    triggered_by: List[str] = Field(default_factory=list)  # fact_ids that triggered this
    severity: Severity = Severity.HIGH
    applied: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# FinalDecision - Judge's synthesis
# ---------------------------------------------------------------------------

class FinalDecision(BaseModel):
    """
    Judge's final decision and executive summary.
    
    This is the ultimate output of the mesh, containing:
    - Score and confidence
    - Thesis and anti-thesis
    - Single point of failure
    - Kill-switch signals
    - Manual review flags
    """
    decision_id: str = Field(default_factory=lambda: f"final_{uuid.uuid4().hex[:8]}")
    
    # Core scoring
    score: int = Field(ge=0, le=100)  # 0-100 scale
    confidence: float = Field(ge=0.0, le=1.0)
    state: ConsensusState
    score_breakdown: Dict[str, int] = Field(default_factory=dict)  # Per-module scores
    
    # Overrides applied
    overrides_applied: List[str] = Field(default_factory=list)  # override_ids
    score_adjustments: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Investment thesis
    thesis: str  # Bull case
    anti_thesis: str  # Bear case
    key_strengths: List[str] = Field(default_factory=list)
    key_risks: List[str] = Field(default_factory=list)
    
    # Critical signals
    spof: Optional[str] = None  # Single Point of Failure
    kill_switches: List[str] = Field(default_factory=list)  # Critical warning signals
    
    # Review and monitoring
    manual_review_required: bool = False
    review_reasons: List[str] = Field(default_factory=list)
    monitoring_checklist: List[str] = Field(default_factory=list)
    
    # Uncertainty and what would change the view
    uncertainty_explanation: Optional[str] = None
    view_changers: List[str] = Field(default_factory=list)
    
    # Audit trail
    evidence_summary: Dict[str, Any] = Field(default_factory=dict)
    unresolved_items: List[str] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Event - Audit log entry
# ---------------------------------------------------------------------------

class Event(BaseModel):
    """
    Audit log event for blackboard operations.
    
    Every write to the blackboard creates an event for full traceability.
    """
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    event_type: str  # e.g., "FACT_WRITTEN", "HYPOTHESIS_WRITTEN", "ATTACK_CREATED"
    entry_type: EntryType
    entry_id: str  # ID of the entry that was created/modified
    agent_id: Optional[str] = None  # Who made this write
    source: str  # Engine or agent that triggered this
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)
    
    # Hash for immutability verification
    previous_event_hash: Optional[str] = None
    event_hash: Optional[str] = None


# ---------------------------------------------------------------------------
# DataQualityReport - From Data Quality Engine
# ---------------------------------------------------------------------------

class DataQualityReport(BaseModel):
    """
    Data quality assessment report.
    
    Generated by the Data Quality Engine to assess input data quality.
    """
    report_id: str = Field(default_factory=lambda: f"dqr_{uuid.uuid4().hex[:8]}")
    
    # Overall score
    quality_score: float = Field(ge=0.0, le=1.0)
    
    # Missing data
    missing_fields: List[str] = Field(default_factory=list)
    missing_rate: float = Field(ge=0.0, le=1.0)
    
    # Anomalies and outliers
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    outliers: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Confidence penalties
    confidence_penalties: Dict[str, float] = Field(default_factory=dict)
    
    # Recommendations
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
