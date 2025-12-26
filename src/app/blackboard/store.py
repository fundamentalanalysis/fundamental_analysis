# =============================================================
# src/app/blackboard/store.py
# Blackboard Store with Versioning, Provenance, ACL
# Layer B - Shared State & Governance
# =============================================================
"""
Event-sourced blackboard store with:
- Immutability for facts
- Versioning for all entries
- Write ACL (access control)
- TTL/staleness for hypotheses and benchmarks
- Append-only audit log
"""

from typing import List, Optional, Dict, Any, Callable
from datetime import datetime, timedelta
import hashlib
import json
import logging

from .models import (
    EntryType,
    Fact,
    Hypothesis,
    Attack,
    Resolution,
    Override,
    FinalDecision,
    Event,
    HypothesisStatus,
    DataQualityReport,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ACL Definitions
# ---------------------------------------------------------------------------

# Which sources can write which entry types
WRITE_ACL: Dict[EntryType, List[str]] = {
    EntryType.FACT: [
        "metric_engine",
        "trend_engine",
        "correlation_engine",
        "data_quality_engine",
    ],
    EntryType.HYPOTHESIS: [
        "debt_analyst",
        "liquidity_analyst",
        "asset_quality_analyst",
        "qoe_analyst",
        "working_capital_analyst",
        "equity_analyst",
        "benchmarking_agent",
    ],
    EntryType.ATTACK: [
        "short_seller_critic",
        "critic",
    ],
    EntryType.RESOLUTION: [
        "mediator",
    ],
    EntryType.FINAL: [
        "judge",
    ],
}


class BlackboardError(Exception):
    """Base exception for blackboard errors."""
    pass


class PermissionError(BlackboardError):
    """Raised when a source doesn't have permission to write."""
    pass


class ValidationError(BlackboardError):
    """Raised when entry validation fails."""
    pass


class StaleDataError(BlackboardError):
    """Raised when accessing stale/expired data."""
    pass


# ---------------------------------------------------------------------------
# Blackboard Store
# ---------------------------------------------------------------------------

class Blackboard:
    """
    Shared state store with immutability, provenance, ACL, and versioning.
    
    The blackboard is the central communication mechanism for the agentic mesh.
    All agents read from and write to the blackboard following strict rules.
    
    Key Properties:
    - Facts are immutable (no updates, only new versions)
    - All writes are logged to an append-only event log
    - Write permissions are enforced via ACL
    - Hypotheses and benchmarks have TTL/staleness
    - Full audit trail for regulatory compliance
    """
    
    def __init__(self):
        # Storage
        self._facts: Dict[str, Fact] = {}  # fact_id -> Fact
        self._hypotheses: Dict[str, Hypothesis] = {}  # hypothesis_id -> Hypothesis
        self._attacks: Dict[str, Attack] = {}  # attack_id -> Attack
        self._resolutions: Dict[str, Resolution] = {}  # resolution_id -> Resolution
        self._overrides: Dict[str, Override] = {}  # override_id -> Override
        self._final: Optional[FinalDecision] = None
        self._data_quality_report: Optional[DataQualityReport] = None
        
        # Event log (append-only)
        self._event_log: List[Event] = []
        self._last_event_hash: Optional[str] = None
        
        # Metadata
        self._created_at: datetime = datetime.utcnow()
        self._company: Optional[str] = None
        self._year: Optional[int] = None
        
        # TTL configuration (in minutes)
        self._hypothesis_ttl_minutes: int = 60
        self._benchmark_ttl_minutes: int = 1440  # 24 hours
        
        # Debate round tracking
        self._current_round: int = 0
    
    # -----------------------------------------------------------------------
    # Initialization
    # -----------------------------------------------------------------------
    
    def initialize(self, company: str, year: int) -> None:
        """Initialize blackboard for a new analysis run."""
        self._company = company
        self._year = year
        self._log_event("BLACKBOARD_INITIALIZED", EntryType.FACT, "system", "system", {
            "company": company,
            "year": year,
        })
    
    # -----------------------------------------------------------------------
    # Write Methods (with ACL enforcement)
    # -----------------------------------------------------------------------
    
    def write_fact(self, fact: Fact, source: str) -> str:
        """
        Write a fact to the blackboard.
        
        Facts can only be written by deterministic engines.
        Facts are immutable - updates create new versions.
        
        Args:
            fact: The fact to write
            source: The source engine writing the fact
            
        Returns:
            The fact_id of the written fact
            
        Raises:
            PermissionError: If source is not authorized to write facts
        """
        self._check_write_permission(EntryType.FACT, source)
        
        # Check for existing fact with same key and period
        existing = self._find_fact_by_key(fact.key, fact.period)
        if existing:
            # Create new version
            fact = fact.model_copy(update={"version": existing.version + 1})
        
        self._facts[fact.fact_id] = fact
        self._log_event("FACT_WRITTEN", EntryType.FACT, fact.fact_id, source, {
            "key": fact.key,
            "value": fact.value,
            "version": fact.version,
        })
        
        logger.debug(f"Fact written: {fact.fact_id} ({fact.key}={fact.value})")
        return fact.fact_id
    
    def write_facts(self, facts: List[Fact], source: str) -> List[str]:
        """Write multiple facts at once."""
        return [self.write_fact(f, source) for f in facts]
    
    def write_hypothesis(self, hypothesis: Hypothesis, agent_id: str) -> str:
        """
        Write a hypothesis to the blackboard.
        
        Hypotheses can only be written by analyst agents.
        
        Args:
            hypothesis: The hypothesis to write
            agent_id: The agent writing the hypothesis
            
        Returns:
            The hypothesis_id
            
        Raises:
            PermissionError: If agent is not authorized
            ValidationError: If confidence is below threshold
        """
        self._check_write_permission(EntryType.HYPOTHESIS, agent_id)
        
        # Validate minimum confidence
        if hypothesis.confidence < 0.3:
            raise ValidationError(
                f"Hypothesis confidence {hypothesis.confidence} is below minimum threshold 0.3"
            )
        
        # Set TTL based on current debate round
        hypothesis = hypothesis.model_copy(update={
            "agent_id": agent_id,
            "ttl_rounds": self._current_round + 5,  # Expires in 5 rounds
        })
        
        self._hypotheses[hypothesis.hypothesis_id] = hypothesis
        self._log_event("HYPOTHESIS_WRITTEN", EntryType.HYPOTHESIS, 
                       hypothesis.hypothesis_id, agent_id, {
            "claim": hypothesis.claim[:100],  # Truncate for log
            "confidence": hypothesis.confidence,
            "linked_facts_count": len(hypothesis.linked_facts),
        })
        
        logger.debug(f"Hypothesis written: {hypothesis.hypothesis_id} by {agent_id}")
        return hypothesis.hypothesis_id
    
    def write_attack(self, attack: Attack, critic_id: str) -> str:
        """
        Write an attack to the blackboard.
        
        Attacks can only be written by critic agents.
        """
        self._check_write_permission(EntryType.ATTACK, critic_id)
        
        # Validate target hypothesis exists
        if attack.target_hypothesis_id not in self._hypotheses:
            raise ValidationError(
                f"Target hypothesis {attack.target_hypothesis_id} does not exist"
            )
        
        # Update target hypothesis status
        target = self._hypotheses[attack.target_hypothesis_id]
        self._hypotheses[attack.target_hypothesis_id] = target.model_copy(update={
            "status": HypothesisStatus.ATTACKED,
            "updated_at": datetime.utcnow(),
        })
        
        attack = attack.model_copy(update={"critic_id": critic_id})
        self._attacks[attack.attack_id] = attack
        self._log_event("ATTACK_WRITTEN", EntryType.ATTACK, attack.attack_id, critic_id, {
            "target": attack.target_hypothesis_id,
            "severity": attack.severity.value,
            "contradiction_type": attack.contradiction_type,
        })
        
        logger.debug(f"Attack written: {attack.attack_id} targeting {attack.target_hypothesis_id}")
        return attack.attack_id
    
    def write_resolution(self, resolution: Resolution, mediator_id: str = "mediator") -> str:
        """
        Write a resolution to the blackboard.
        
        Resolutions can only be written by the mediator.
        """
        self._check_write_permission(EntryType.RESOLUTION, mediator_id)
        
        # Update resolved hypotheses
        for hyp_id in resolution.resolved_hypotheses:
            if hyp_id in self._hypotheses:
                hyp = self._hypotheses[hyp_id]
                self._hypotheses[hyp_id] = hyp.model_copy(update={
                    "status": HypothesisStatus.RESOLVED,
                    "updated_at": datetime.utcnow(),
                })
        
        self._resolutions[resolution.resolution_id] = resolution
        self._current_round = resolution.round_number
        
        self._log_event("RESOLUTION_WRITTEN", EntryType.RESOLUTION,
                       resolution.resolution_id, mediator_id, {
            "round": resolution.round_number,
            "resolved_count": len(resolution.resolved_hypotheses),
            "unresolved_count": len(resolution.unresolved_items),
            "convergence": resolution.convergence_score,
        })
        
        logger.debug(f"Resolution written: round {resolution.round_number}, "
                    f"convergence={resolution.convergence_score:.2f}")
        return resolution.resolution_id
    
    def write_override(self, override: Override, source: str = "correlation_engine") -> str:
        """
        Write a correlation override to the blackboard.
        """
        self._check_write_permission(EntryType.FACT, source)  # Overrides use FACT ACL
        
        self._overrides[override.override_id] = override
        self._log_event("OVERRIDE_WRITTEN", EntryType.FACT, override.override_id, source, {
            "rule_id": override.rule_id,
            "rule_name": override.rule_name,
            "action": override.action,
            "severity": override.severity.value,
        })
        
        logger.info(f"Override written: {override.rule_name} ({override.action})")
        return override.override_id
    
    def write_final(self, decision: FinalDecision, judge_id: str = "judge") -> str:
        """
        Write the final decision to the blackboard.
        
        Only the Judge can write the final decision.
        """
        self._check_write_permission(EntryType.FINAL, judge_id)
        
        self._final = decision
        self._log_event("FINAL_WRITTEN", EntryType.FINAL, decision.decision_id, judge_id, {
            "score": decision.score,
            "confidence": decision.confidence,
            "state": decision.state.value,
            "manual_review_required": decision.manual_review_required,
        })
        
        logger.info(f"Final decision written: score={decision.score}, state={decision.state.value}")
        return decision.decision_id
    
    def write_data_quality_report(self, report: DataQualityReport, 
                                   source: str = "data_quality_engine") -> str:
        """Write data quality report to the blackboard."""
        self._check_write_permission(EntryType.FACT, source)
        
        self._data_quality_report = report
        self._log_event("DATA_QUALITY_REPORT_WRITTEN", EntryType.FACT, 
                       report.report_id, source, {
            "quality_score": report.quality_score,
            "missing_rate": report.missing_rate,
            "anomaly_count": len(report.anomalies),
        })
        
        return report.report_id
    
    # -----------------------------------------------------------------------
    # Read Methods
    # -----------------------------------------------------------------------
    
    def get_facts(self, module: Optional[str] = None, 
                  key_prefix: Optional[str] = None) -> List[Fact]:
        """Get all facts, optionally filtered by module or key prefix."""
        facts = list(self._facts.values())
        
        if module:
            facts = [f for f in facts if f.module == module]
        if key_prefix:
            facts = [f for f in facts if f.key.startswith(key_prefix)]
        
        return facts
    
    def get_fact(self, fact_id: str) -> Optional[Fact]:
        """Get a specific fact by ID."""
        return self._facts.get(fact_id)
    
    def get_fact_by_key(self, key: str, period: Optional[int] = None) -> Optional[Fact]:
        """Get the latest version of a fact by key and optional period."""
        return self._find_fact_by_key(key, period)
    
    def get_hypotheses(self, status: Optional[HypothesisStatus] = None,
                       agent_id: Optional[str] = None,
                       include_expired: bool = False) -> List[Hypothesis]:
        """Get hypotheses, optionally filtered by status or agent."""
        hypotheses = list(self._hypotheses.values())
        
        # Filter expired (based on TTL rounds)
        if not include_expired:
            hypotheses = [h for h in hypotheses if h.ttl_rounds >= self._current_round]
        
        if status:
            hypotheses = [h for h in hypotheses if h.status == status]
        if agent_id:
            hypotheses = [h for h in hypotheses if h.agent_id == agent_id]
        
        return hypotheses
    
    def get_attacks(self, target_hypothesis_id: Optional[str] = None) -> List[Attack]:
        """Get attacks, optionally filtered by target hypothesis."""
        attacks = list(self._attacks.values())
        
        if target_hypothesis_id:
            attacks = [a for a in attacks if a.target_hypothesis_id == target_hypothesis_id]
        
        return attacks
    
    def get_resolutions(self) -> List[Resolution]:
        """Get all resolutions, ordered by round number."""
        return sorted(self._resolutions.values(), key=lambda r: r.round_number)
    
    def get_overrides(self, applied_only: bool = False) -> List[Override]:
        """Get overrides, optionally only those that were applied."""
        overrides = list(self._overrides.values())
        
        if applied_only:
            overrides = [o for o in overrides if o.applied]
        
        return overrides
    
    def get_final(self) -> Optional[FinalDecision]:
        """Get the final decision."""
        return self._final
    
    def get_data_quality_report(self) -> Optional[DataQualityReport]:
        """Get the data quality report."""
        return self._data_quality_report
    
    def get_audit_log(self) -> List[Event]:
        """Get the full audit event log."""
        return self._event_log.copy()
    
    # -----------------------------------------------------------------------
    # Aggregate Methods
    # -----------------------------------------------------------------------
    
    def get_metrics_dict(self) -> Dict[str, Any]:
        """Get all facts as a dictionary keyed by fact key."""
        result = {}
        for fact in self._facts.values():
            key = fact.key
            if fact.period:
                key = f"{fact.key}_{fact.period}"
            result[key] = fact.value
        return result
    
    def get_active_hypothesis_count(self) -> int:
        """Get count of currently active hypotheses."""
        return len(self.get_hypotheses(status=HypothesisStatus.ACTIVE))
    
    def get_attack_count(self) -> int:
        """Get total number of attacks."""
        return len(self._attacks)
    
    def get_convergence_score(self) -> float:
        """Get latest convergence score from resolutions."""
        resolutions = self.get_resolutions()
        if not resolutions:
            return 0.0
        return resolutions[-1].convergence_score
    
    def get_debate_round(self) -> int:
        """Get current debate round."""
        return self._current_round
    
    # -----------------------------------------------------------------------
    # Snapshot & Serialization
    # -----------------------------------------------------------------------
    
    def to_snapshot(self) -> Dict[str, Any]:
        """Create a full snapshot of the blackboard state."""
        return {
            "company": self._company,
            "year": self._year,
            "created_at": self._created_at.isoformat(),
            "current_round": self._current_round,
            "facts": [f.model_dump() for f in self._facts.values()],
            "hypotheses": [h.model_dump() for h in self._hypotheses.values()],
            "attacks": [a.model_dump() for a in self._attacks.values()],
            "resolutions": [r.model_dump() for r in self._resolutions.values()],
            "overrides": [o.model_dump() for o in self._overrides.values()],
            "final": self._final.model_dump() if self._final else None,
            "data_quality_report": (
                self._data_quality_report.model_dump() 
                if self._data_quality_report else None
            ),
            "event_log": [e.model_dump() for e in self._event_log],
        }
    
    def get_evidence_bundle(self) -> Dict[str, Any]:
        """
        Get an audit bundle suitable for regulatory review.
        
        Contains:
        - Timeline of events
        - All facts with provenance
        - Hypothesis -> Attack -> Resolution chain
        - Override triggers
        - Final decision with evidence links
        """
        return {
            "metadata": {
                "company": self._company,
                "year": self._year,
                "analysis_date": self._created_at.isoformat(),
                "debate_rounds": self._current_round,
            },
            "facts_summary": {
                "total": len(self._facts),
                "by_source": self._count_by_field(self._facts.values(), "source_engine"),
            },
            "debate_summary": {
                "hypotheses_total": len(self._hypotheses),
                "hypotheses_active": self.get_active_hypothesis_count(),
                "attacks_total": len(self._attacks),
                "resolutions": len(self._resolutions),
                "final_convergence": self.get_convergence_score(),
            },
            "overrides_summary": {
                "total": len(self._overrides),
                "applied": len([o for o in self._overrides.values() if o.applied]),
                "by_rule": self._count_by_field(self._overrides.values(), "rule_name"),
            },
            "timeline": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "event": e.event_type,
                    "entry_type": e.entry_type.value,
                    "source": e.source,
                }
                for e in self._event_log[-50:]  # Last 50 events
            ],
        }
    
    # -----------------------------------------------------------------------
    # Private Methods
    # -----------------------------------------------------------------------
    
    def _check_write_permission(self, entry_type: EntryType, source: str) -> None:
        """Check if source has permission to write entry type."""
        allowed_sources = WRITE_ACL.get(entry_type, [])
        if source not in allowed_sources:
            raise PermissionError(
                f"Source '{source}' is not authorized to write {entry_type.value}. "
                f"Allowed sources: {allowed_sources}"
            )
    
    def _find_fact_by_key(self, key: str, period: Optional[int]) -> Optional[Fact]:
        """Find the latest version of a fact by key and period."""
        matching = [
            f for f in self._facts.values()
            if f.key == key and (period is None or f.period == period)
        ]
        if not matching:
            return None
        return max(matching, key=lambda f: f.version)
    
    def _log_event(self, event_type: str, entry_type: EntryType,
                   entry_id: str, source: str, details: Dict[str, Any]) -> None:
        """Log an event to the append-only audit log."""
        event = Event(
            event_type=event_type,
            entry_type=entry_type,
            entry_id=entry_id,
            source=source,
            details=details,
            previous_event_hash=self._last_event_hash,
        )
        
        # Compute event hash for chain integrity
        event_data = json.dumps({
            "event_id": event.event_id,
            "event_type": event.event_type,
            "entry_id": event.entry_id,
            "timestamp": event.timestamp.isoformat(),
            "previous_hash": self._last_event_hash,
        }, sort_keys=True)
        event_hash = hashlib.sha256(event_data.encode()).hexdigest()[:16]
        
        event = event.model_copy(update={"event_hash": event_hash})
        self._event_log.append(event)
        self._last_event_hash = event_hash
    
    def _count_by_field(self, items: Any, field: str) -> Dict[str, int]:
        """Count items grouped by a field value."""
        counts: Dict[str, int] = {}
        for item in items:
            value = getattr(item, field, "unknown")
            counts[value] = counts.get(value, 0) + 1
        return counts
