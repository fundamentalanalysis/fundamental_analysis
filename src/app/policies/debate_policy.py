# =============================================================
# src/app/policies/debate_policy.py
# Debate Termination Policy
# Layer D - Orchestration & Policy Control Plane
# =============================================================
"""
Controls when debate should terminate.

Termination conditions:
1. Max rounds reached
2. Max time exceeded
3. Convergence achieved
4. Stagnation detected
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DebateMetrics(BaseModel):
    """Metrics for evaluating debate state."""
    round: int = 0
    elapsed_seconds: float = 0
    convergence_score: float = 0
    previous_convergence: float = 0
    hypotheses_active: int = 0
    hypotheses_resolved: int = 0
    attacks_total: int = 0
    attacks_addressed: int = 0


class DebateTerminationPolicy:
    """
    Controls when debate should terminate.
    
    Guarantees bounded execution - no infinite loops.
    """
    
    def __init__(
        self,
        max_rounds: int = 5,
        max_time_seconds: float = 60.0,
        stagnation_threshold: float = 0.05,
        convergence_threshold: float = 0.8,
    ):
        """
        Initialize debate termination policy.
        
        Args:
            max_rounds: Maximum number of debate rounds
            max_time_seconds: Maximum wall-clock time for debate
            stagnation_threshold: Minimum improvement required per round
            convergence_threshold: Convergence score to consider debate resolved
        """
        self.max_rounds = max_rounds
        self.max_time_seconds = max_time_seconds
        self.stagnation_threshold = stagnation_threshold
        self.convergence_threshold = convergence_threshold
        
        # Tracking
        self._start_time: Optional[datetime] = None
        self._round_history: list = []
    
    def start_debate(self) -> None:
        """Mark the start of a new debate session."""
        self._start_time = datetime.utcnow()
        self._round_history = []
        logger.info("Debate session started")
    
    def record_round(self, metrics: DebateMetrics) -> None:
        """Record metrics for a debate round."""
        self._round_history.append(metrics)
    
    def should_terminate(self, metrics: DebateMetrics) -> bool:
        """
        Determine if debate should terminate.
        
        Returns True if any termination condition is met.
        """
        reason = self.get_termination_reason(metrics)
        return reason is not None
    
    def get_termination_reason(self, metrics: DebateMetrics) -> Optional[str]:
        """
        Get the reason for termination, or None if should continue.
        """
        # Check round limit
        if metrics.round >= self.max_rounds:
            return f"Max rounds ({self.max_rounds}) reached"
        
        # Check time limit
        if metrics.elapsed_seconds >= self.max_time_seconds:
            return f"Max time ({self.max_time_seconds}s) exceeded"
        
        # Check convergence
        if metrics.convergence_score >= self.convergence_threshold:
            return f"Convergence ({metrics.convergence_score:.0%}) achieved"
        
        # Check stagnation (need at least 2 rounds)
        if metrics.round >= 2 and metrics.previous_convergence > 0:
            improvement = metrics.convergence_score - metrics.previous_convergence
            if improvement < self.stagnation_threshold:
                return f"Stagnation detected (improvement={improvement:.1%})"
        
        return None
    
    def get_elapsed_seconds(self) -> float:
        """Get elapsed time since debate started."""
        if self._start_time is None:
            return 0.0
        delta = datetime.utcnow() - self._start_time
        return delta.total_seconds()
    
    def get_remaining_rounds(self, current_round: int) -> int:
        """Get remaining rounds before termination."""
        return max(0, self.max_rounds - current_round)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export policy configuration."""
        return {
            "max_rounds": self.max_rounds,
            "max_time_seconds": self.max_time_seconds,
            "stagnation_threshold": self.stagnation_threshold,
            "convergence_threshold": self.convergence_threshold,
        }
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "DebateTerminationPolicy":
        """Create policy from configuration dictionary."""
        return cls(
            max_rounds=config.get("max_rounds", 5),
            max_time_seconds=config.get("max_time_seconds", 60),
            stagnation_threshold=config.get("stagnation_threshold", 0.05),
            convergence_threshold=config.get("convergence_threshold", 0.8),
        )
