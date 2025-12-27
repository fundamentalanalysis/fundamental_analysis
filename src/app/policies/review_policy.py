# =============================================================
# src/app/policies/review_policy.py
# Manual Review Policy
# Layer D - Orchestration & Policy Control Plane
# =============================================================
"""
Determines when manual review is required.

Triggers:
- Disagreement gap exceeds threshold
- Missing benchmark coverage
- Low data quality
- Kill-switch activated
- Anomalies detected
"""

from typing import Dict, Any, List, Tuple, Optional
import logging

from src.app.blackboard.store import Blackboard
from src.app.blackboard.models import (
    Resolution, Override, DataQualityReport, ConsensusState
)

logger = logging.getLogger(__name__)


class ManualReviewPolicy:
    """
    Determines when manual review is required.
    
    Manual review ensures human oversight for high-risk or uncertain analyses.
    """
    
    def __init__(
        self,
        disagreement_gap_threshold: float = 0.3,
        missing_benchmark_threshold: float = 0.2,
        low_data_quality_threshold: float = 0.5,
        max_kill_switches: int = 0,  # Any kill switch triggers review
    ):
        """
        Initialize manual review policy.
        
        Args:
            disagreement_gap_threshold: Max acceptable gap between agent views
            missing_benchmark_threshold: Max acceptable missing benchmark rate
            low_data_quality_threshold: Minimum data quality to avoid review
            max_kill_switches: Max kill-switches before requiring review
        """
        self.disagreement_gap = disagreement_gap_threshold
        self.missing_benchmark = missing_benchmark_threshold
        self.low_data_quality = low_data_quality_threshold
        self.max_kill_switches = max_kill_switches
    
    def requires_review(self, blackboard: Blackboard) -> bool:
        """Check if the analysis requires manual review."""
        _, reasons = self.check_review_triggers(blackboard)
        return len(reasons) > 0
    
    def check_review_triggers(
        self,
        blackboard: Blackboard,
    ) -> Tuple[bool, List[str]]:
        """
        Check all review triggers and return reasons.
        
        Returns:
            Tuple of (requires_review: bool, reasons: List[str])
        """
        reasons = []
        
        # Check disagreement
        disagreement_reason = self._check_disagreement(blackboard)
        if disagreement_reason:
            reasons.append(disagreement_reason)
        
        # Check data quality
        quality_reason = self._check_data_quality(blackboard)
        if quality_reason:
            reasons.append(quality_reason)
        
        # Check kill-switches
        kill_switch_reason = self._check_kill_switches(blackboard)
        if kill_switch_reason:
            reasons.append(kill_switch_reason)
        
        # Check missing benchmarks
        benchmark_reason = self._check_benchmarks(blackboard)
        if benchmark_reason:
            reasons.append(benchmark_reason)
        
        # Check for high-severity attacks
        attack_reason = self._check_critical_attacks(blackboard)
        if attack_reason:
            reasons.append(attack_reason)
        
        requires = len(reasons) > 0
        
        if requires:
            logger.warning(f"Manual review required: {len(reasons)} triggers")
        
        return requires, reasons
    
    def _check_disagreement(self, blackboard: Blackboard) -> Optional[str]:
        """Check if disagreement gap exceeds threshold."""
        resolutions = blackboard.get_resolutions()
        if not resolutions:
            return None
        
        final = resolutions[-1]
        gap = 1.0 - final.convergence_score
        
        if gap > self.disagreement_gap:
            return (
                f"Disagreement gap ({gap:.0%}) exceeds threshold "
                f"({self.disagreement_gap:.0%})"
            )
        return None
    
    def _check_data_quality(self, blackboard: Blackboard) -> Optional[str]:
        """Check if data quality is below threshold."""
        report = blackboard.get_data_quality_report()
        if not report:
            return None
        
        if report.quality_score < self.low_data_quality:
            return (
                f"Data quality ({report.quality_score:.0%}) below threshold "
                f"({self.low_data_quality:.0%})"
            )
        return None
    
    def _check_kill_switches(self, blackboard: Blackboard) -> Optional[str]:
        """Check if kill-switches have been triggered."""
        overrides = blackboard.get_overrides()
        kill_switches = [o for o in overrides if o.action == "kill_switch"]
        
        if len(kill_switches) > self.max_kill_switches:
            names = [k.rule_name for k in kill_switches]
            return f"Kill-switches triggered: {', '.join(names)}"
        return None
    
    def _check_benchmarks(self, blackboard: Blackboard) -> Optional[str]:
        """Check for missing benchmark coverage."""
        facts = blackboard.get_facts()
        benchmark_facts = [f for f in facts if f.key.startswith("benchmark_")]
        
        if not benchmark_facts:
            return "No benchmark data available"
        
        # Check for fallback benchmarks (exclude LLM-generated ones as they're customized)
        fallback_facts = [
            f for f in benchmark_facts 
            if f.metadata.get("is_fallback", False) 
            and not f.metadata.get("is_llm_generated", False)
        ]
        
        if not fallback_facts:
            return None  # No fallback or using LLM-generated = OK
        
        fallback_rate = len(fallback_facts) / len(benchmark_facts)
        if fallback_rate > self.missing_benchmark:
            return (
                f"High fallback benchmark rate ({fallback_rate:.0%}) - "
                f"industry-specific data may be unavailable"
            )
        return None
    
    def _check_critical_attacks(self, blackboard: Blackboard) -> Optional[str]:
        """Check for unresolved critical attacks."""
        attacks = blackboard.get_attacks()
        resolutions = blackboard.get_resolutions()
        
        if not attacks:
            return None
        
        # Get resolved attack IDs
        resolved_ids = set()
        for res in resolutions:
            resolved_ids.update(res.resolved_attacks)
        
        # Find unresolved critical attacks
        from src.app.blackboard.models import Severity
        unresolved_critical = [
            a for a in attacks
            if a.attack_id not in resolved_ids 
            and a.severity == Severity.CRITICAL
        ]
        
        if unresolved_critical:
            return (
                f"{len(unresolved_critical)} critical attacks remain unresolved - "
                f"significant risk concerns flagged by critic"
            )
        return None
    
    def get_review_packet(
        self,
        blackboard: Blackboard,
        reasons: List[str],
    ) -> Dict[str, Any]:
        """
        Build a review packet for human reviewer.
        
        Contains all information needed for informed review.
        """
        return {
            "review_required": True,
            "reasons": reasons,
            "summary": {
                "company": blackboard._company,
                "year": blackboard._year,
                "debate_rounds": blackboard.get_debate_round(),
                "convergence": blackboard.get_convergence_score(),
                "active_hypotheses": blackboard.get_active_hypothesis_count(),
                "attacks": blackboard.get_attack_count(),
            },
            "critical_items": self._get_critical_items(blackboard),
            "evidence_bundle": blackboard.get_evidence_bundle(),
            "recommendations": self._get_recommendations(reasons),
        }
    
    def _get_critical_items(self, blackboard: Blackboard) -> List[Dict[str, Any]]:
        """Get items that need reviewer attention."""
        items = []
        
        # Kill-switches
        for override in blackboard.get_overrides():
            if override.action == "kill_switch":
                items.append({
                    "type": "kill_switch",
                    "name": override.rule_name,
                    "description": override.description,
                    "severity": "critical",
                })
        
        # Unresolved high-severity attacks
        attacks = blackboard.get_attacks()
        for attack in attacks:
            if attack.severity.value in ["high", "critical"]:
                items.append({
                    "type": "attack",
                    "claim": attack.claim,
                    "severity": attack.severity.value,
                })
        
        return items[:10]  # Limit to most critical
    
    def _get_recommendations(self, reasons: List[str]) -> List[str]:
        """Generate recommendations based on review triggers."""
        recommendations = []
        
        for reason in reasons:
            if "disagreement" in reason.lower():
                recommendations.append(
                    "Review unresolved debate items and determine which view is correct"
                )
            if "data quality" in reason.lower():
                recommendations.append(
                    "Verify input data accuracy before relying on analysis"
                )
            if "kill-switch" in reason.lower():
                recommendations.append(
                    "Assess whether kill-switch conditions invalidate the investment thesis"
                )
            if "benchmark" in reason.lower():
                recommendations.append(
                    "Consider using peer comparison for threshold calibration"
                )
        
        return list(set(recommendations))  # Deduplicate
    
    def to_dict(self) -> Dict[str, Any]:
        """Export policy configuration."""
        return {
            "disagreement_gap_threshold": self.disagreement_gap,
            "missing_benchmark_threshold": self.missing_benchmark,
            "low_data_quality_threshold": self.low_data_quality,
            "max_kill_switches": self.max_kill_switches,
        }
