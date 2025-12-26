# =============================================================
# src/app/mesh/mediator_agent.py
# Mediator Agent - Debate Controller and Resolution
# Layer C - Agentic Mesh
# =============================================================
"""
Mediator Agent controls debate and proposes resolutions.

Key responsibilities:
- Run debate rounds between analysts and critic
- Check for convergence
- Mark items as resolved or unresolved
- Provide debate quality metrics
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import time
import logging

from .base_agent import BaseMeshAgent, AgentOutput
from src.app.blackboard.models import (
    Hypothesis, Attack, Resolution, HypothesisStatus
)
from src.app.blackboard.store import Blackboard

logger = logging.getLogger(__name__)


class MediatorAgent(BaseMeshAgent):
    """
    Controls debate between analysts and critic, proposes resolutions.
    
    Key features:
    - Bounded debate rounds
    - Convergence detection
    - Resolution quality metrics
    """
    
    agent_id = "mediator"
    agent_name = "Mediator"
    description = "Debate controller that resolves conflicts between analysts and critic"
    hypothesis_budget = 2
    
    # Debate configuration
    max_rounds: int = 5
    convergence_threshold: float = 0.8
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        if config:
            self.max_rounds = config.get("max_rounds", self.max_rounds)
            self.convergence_threshold = config.get("convergence_threshold", self.convergence_threshold)
    
    def execute(self, blackboard: Blackboard) -> AgentOutput:
        """Run a debate round and attempt resolution."""
        start_time = time.time()
        hypotheses = []
        facts_used = []
        
        try:
            current_round = blackboard.get_debate_round() + 1
            
            # Get active hypotheses and attacks
            active_hypotheses = blackboard.get_hypotheses(status=HypothesisStatus.ACTIVE)
            attacked_hypotheses = blackboard.get_hypotheses(status=HypothesisStatus.ATTACKED)
            all_attacks = blackboard.get_attacks()
            
            # Run resolution logic
            resolution = self.run_debate_round(
                round_number=current_round,
                hypotheses=active_hypotheses + attacked_hypotheses,
                attacks=all_attacks,
            )
            
            # Write resolution to blackboard
            blackboard.write_resolution(resolution, self.agent_id)
            
            # Generate summary hypothesis
            if resolution.convergence_score >= self.convergence_threshold:
                hyp = self.generate_hypothesis(
                    claim=f"Debate round {current_round} achieved convergence "
                          f"({resolution.convergence_score:.0%}). "
                          f"{len(resolution.resolved_hypotheses)} items resolved.",
                    confidence=0.80,
                    linked_facts=[resolution.resolution_id],
                )
            else:
                hyp = self.generate_hypothesis(
                    claim=f"Debate round {current_round} partial resolution. "
                          f"{len(resolution.unresolved_items)} items remain contested.",
                    confidence=0.70,
                    linked_facts=[resolution.resolution_id],
                )
            
            if hyp:
                hypotheses.append(hyp)
            
            execution_time = (time.time() - start_time) * 1000
            self.log_execution(True, len(hypotheses), execution_time)
            
            return AgentOutput(
                agent_id=self.agent_id,
                hypotheses=hypotheses,
                facts_used=[resolution.resolution_id],
                execution_time_ms=execution_time,
                success=True,
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return AgentOutput(
                agent_id=self.agent_id,
                hypotheses=[],
                facts_used=[],
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e),
            )
    
    def run_debate_round(
        self,
        round_number: int,
        hypotheses: List[Hypothesis],
        attacks: List[Attack],
    ) -> Resolution:
        """
        Run a single debate round and produce resolution.
        
        Resolution logic:
        1. Hypotheses with no attacks -> resolved
        2. Hypotheses with weak attacks -> resolved (in favor of hypothesis)
        3. Hypotheses with strong attacks -> need examination
        4. Attacked hypotheses with counter-evidence -> may remain unresolved
        """
        resolved_hypotheses = []
        resolved_attacks = []
        unresolved_items = []
        
        # Build attack map: hypothesis_id -> List[Attack]
        attack_map: Dict[str, List[Attack]] = {}
        for attack in attacks:
            target = attack.target_hypothesis_id
            if target not in attack_map:
                attack_map[target] = []
            attack_map[target].append(attack)
        
        # Evaluate each hypothesis
        for hypothesis in hypotheses:
            hyp_attacks = attack_map.get(hypothesis.hypothesis_id, [])
            
            if not hyp_attacks:
                # No attacks - hypothesis stands
                resolved_hypotheses.append(hypothesis.hypothesis_id)
                continue
            
            # Evaluate attack strength
            strongest_attack = max(hyp_attacks, key=lambda a: a.confidence)
            
            # Resolution decision
            if hypothesis.confidence - strongest_attack.confidence > 0.2:
                # Hypothesis confidence significantly higher - resolve in favor
                resolved_hypotheses.append(hypothesis.hypothesis_id)
                resolved_attacks.extend([a.attack_id for a in hyp_attacks])
            elif strongest_attack.confidence - hypothesis.confidence > 0.2:
                # Attack confidence significantly higher - mark hypothesis weak
                resolved_attacks.append(strongest_attack.attack_id)
                unresolved_items.append(hypothesis.hypothesis_id)
            else:
                # Close call - remains contested
                unresolved_items.append(hypothesis.hypothesis_id)
                unresolved_items.extend([a.attack_id for a in hyp_attacks])
        
        # Calculate convergence and quality
        total_items = len(hypotheses) + len(attacks)
        resolved_count = len(resolved_hypotheses) + len(resolved_attacks)
        convergence_score = resolved_count / total_items if total_items > 0 else 1.0
        
        # Debate quality based on meaningfulness of resolutions
        debate_quality = self._assess_debate_quality(
            hypotheses, attacks, resolved_hypotheses, resolved_attacks
        )
        
        # Generate rationale
        rationale = self._generate_rationale(
            round_number, resolved_hypotheses, resolved_attacks, unresolved_items
        )
        
        return Resolution(
            round_number=round_number,
            resolved_hypotheses=resolved_hypotheses,
            resolved_attacks=resolved_attacks,
            unresolved_items=unresolved_items,
            rationale=rationale,
            convergence_score=convergence_score,
            debate_quality=debate_quality,
        )
    
    def check_convergence(self, blackboard: Blackboard) -> float:
        """Calculate current convergence score."""
        resolutions = blackboard.get_resolutions()
        if not resolutions:
            return 0.0
        return resolutions[-1].convergence_score
    
    def should_continue_debate(self, blackboard: Blackboard) -> bool:
        """Determine if debate should continue."""
        current_round = blackboard.get_debate_round()
        
        # Stop if max rounds reached
        if current_round >= self.max_rounds:
            logger.info(f"Debate terminated: max rounds ({self.max_rounds}) reached")
            return False
        
        # Stop if convergence achieved
        convergence = self.check_convergence(blackboard)
        if convergence >= self.convergence_threshold:
            logger.info(f"Debate terminated: convergence ({convergence:.0%}) achieved")
            return False
        
        # Stop if stagnating (no improvement in last 2 rounds)
        resolutions = blackboard.get_resolutions()
        if len(resolutions) >= 2:
            recent = resolutions[-1].convergence_score
            previous = resolutions[-2].convergence_score
            improvement = recent - previous
            if improvement < 0.05:
                logger.info(f"Debate terminated: stagnation (improvement={improvement:.1%})")
                return False
        
        return True
    
    def _assess_debate_quality(
        self,
        hypotheses: List[Hypothesis],
        attacks: List[Attack],
        resolved_hyps: List[str],
        resolved_attacks: List[str],
    ) -> float:
        """
        Assess quality of the debate based on:
        - Evidence linkage
        - Confidence levels
        - Resolution meaningfulness
        """
        if not hypotheses:
            return 1.0
        
        # Factor 1: Average evidence per hypothesis
        avg_evidence = sum(len(h.linked_facts) for h in hypotheses) / len(hypotheses)
        evidence_score = min(1.0, avg_evidence / 3.0)
        
        # Factor 2: Attack relevance (attacks with counter-facts are better)
        attacks_with_evidence = sum(1 for a in attacks if a.counter_facts)
        attack_quality = attacks_with_evidence / len(attacks) if attacks else 1.0
        
        # Factor 3: Resolution rate
        resolution_rate = (len(resolved_hyps) + len(resolved_attacks)) / max(
            len(hypotheses) + len(attacks), 1
        )
        
        # Weighted average
        quality = 0.3 * evidence_score + 0.3 * attack_quality + 0.4 * resolution_rate
        return quality
    
    def _generate_rationale(
        self,
        round_number: int,
        resolved_hyps: List[str],
        resolved_attacks: List[str],
        unresolved: List[str],
    ) -> str:
        """Generate human-readable rationale for the resolution."""
        parts = [f"Round {round_number} resolution:"]
        
        if resolved_hyps:
            parts.append(f"- {len(resolved_hyps)} hypotheses accepted as supported by evidence")
        if resolved_attacks:
            parts.append(f"- {len(resolved_attacks)} attacks addressed or dismissed")
        if unresolved:
            parts.append(f"- {len(unresolved)} items remain contested, requiring further analysis")
        
        if not unresolved:
            parts.append("Full convergence achieved.")
        
        return " ".join(parts)
