# =============================================================
# src/app/policies/consensus_policy.py
# Consensus Scoring Policy
# Layer D - Orchestration & Policy Control Plane
# =============================================================
"""
Determines final score under disagreement.

States:
- CONSENSUS: High convergence (>=90%), use consensus score
- WEIGHTED: Medium convergence (60-90%), confidence-weighted score
- UNRESOLVED: Low convergence (<60%), pessimistic score + manual review
"""

from typing import Dict, Any, List, Tuple
from pydantic import BaseModel, Field
import logging

from src.app.blackboard.models import Resolution, ConsensusState

logger = logging.getLogger(__name__)


class ConsensusScoringPolicy:
    """
    Determines final score based on debate outcomes and disagreement levels.
    """
    
    def __init__(
        self,
        high_convergence_threshold: float = 0.9,
        medium_convergence_threshold: float = 0.6,
        pessimism_factor: float = 0.8,  # Applied to unresolved cases
    ):
        """
        Initialize consensus scoring policy.
        
        Args:
            high_convergence_threshold: Threshold for CONSENSUS state
            medium_convergence_threshold: Threshold for WEIGHTED state (below = UNRESOLVED)
            pessimism_factor: Multiplier for score in UNRESOLVED state
        """
        self.high_convergence = high_convergence_threshold
        self.medium_convergence = medium_convergence_threshold
        self.pessimism_factor = pessimism_factor
    
    def compute_state(self, convergence: float) -> ConsensusState:
        """Determine consensus state from convergence score."""
        if convergence >= self.high_convergence:
            return ConsensusState.CONSENSUS
        elif convergence >= self.medium_convergence:
            return ConsensusState.WEIGHTED
        else:
            return ConsensusState.UNRESOLVED
    
    def compute_score(
        self,
        base_score: float,
        resolutions: List[Resolution],
    ) -> Tuple[float, ConsensusState]:
        """
        Compute final score based on resolutions.
        
        Args:
            base_score: Initial score from deterministic calculations
            resolutions: List of debate resolutions
            
        Returns:
            Tuple of (adjusted_score, consensus_state)
        """
        if not resolutions:
            # No debate = treat as consensus
            return base_score, ConsensusState.CONSENSUS
        
        # Get final convergence
        final_resolution = resolutions[-1]
        convergence = final_resolution.convergence_score
        state = self.compute_state(convergence)
        
        # Apply scoring rules
        if state == ConsensusState.CONSENSUS:
            # Full agreement - use base score
            return base_score, state
        
        elif state == ConsensusState.WEIGHTED:
            # Moderate disagreement - small adjustment based on debate quality
            quality = final_resolution.debate_quality
            adjustment = (1.0 - convergence) * (1.0 - quality) * 10
            adjusted = base_score - adjustment
            return max(0, adjusted), state
        
        else:  # UNRESOLVED
            # Significant disagreement - apply pessimism
            adjusted = base_score * self.pessimism_factor
            
            # Additional penalty for many unresolved items
            unresolved_count = len(final_resolution.unresolved_items)
            if unresolved_count > 5:
                adjusted -= (unresolved_count - 5) * 2
            
            return max(0, adjusted), state
    
    def get_score_confidence(
        self,
        state: ConsensusState,
        convergence: float,
    ) -> float:
        """
        Get confidence in the score based on consensus state.
        
        Returns value between 0 and 1.
        """
        if state == ConsensusState.CONSENSUS:
            return 0.9 + (convergence - 0.9) * 0.5  # 0.9-1.0
        elif state == ConsensusState.WEIGHTED:
            return 0.6 + (convergence - 0.6) * 0.75  # 0.6-0.825
        else:
            return 0.3 + convergence * 0.5  # 0.3-0.6
    
    def explain_scoring(self, state: ConsensusState) -> str:
        """Get human-readable explanation of scoring approach."""
        explanations = {
            ConsensusState.CONSENSUS: (
                "High agreement among agents. Score reflects deterministic analysis "
                "with full endorsement from debate process."
            ),
            ConsensusState.WEIGHTED: (
                "Moderate disagreement exists. Score is adjusted to account for "
                "unresolved debates, with weighting based on evidence quality."
            ),
            ConsensusState.UNRESOLVED: (
                "Significant disagreement remains unresolved. Score is pessimistic "
                "due to uncertainty. Manual review recommended."
            ),
        }
        return explanations.get(state, "Unknown state")
    
    def to_dict(self) -> Dict[str, Any]:
        """Export policy configuration."""
        return {
            "high_convergence_threshold": self.high_convergence,
            "medium_convergence_threshold": self.medium_convergence,
            "pessimism_factor": self.pessimism_factor,
        }
