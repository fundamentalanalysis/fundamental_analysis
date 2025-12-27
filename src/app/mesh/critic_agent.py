# =============================================================
# src/app/mesh/critic_agent.py
# Short-Seller Critic Agent - Adversarial Analysis
# Layer C - Agentic Mesh
# =============================================================
"""
Short-Seller Critic Agent attacks analyst hypotheses.

Key responsibilities:
- Find weaknesses in analyst claims
- Identify contradictions with facts
- Challenge overly optimistic conclusions
- Apply configurable aggressiveness posture
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import time
import logging

from .base_agent import BaseMeshAgent, AgentOutput
from src.app.blackboard.models import (
    Hypothesis, Fact, Attack, HypothesisStatus, Severity
)
from src.app.blackboard.store import Blackboard

logger = logging.getLogger(__name__)


class ShortSellerCriticAgent(BaseMeshAgent):
    """
    Adversarial agent that attacks analyst hypotheses.
    
    Posture modes:
    - "lenient": Few attacks, only obvious issues
    - "balanced": Moderate skepticism (default)
    - "strict": Aggressive, challenges everything
    """
    
    agent_id = "short_seller_critic"
    agent_name = "Short-Seller Critic"
    description = "Adversarial analyst looking for weaknesses and red flags"
    hypothesis_budget = 10  # Critics can attack more
    
    # Critic posture
    posture: str = "balanced"
    
    # Thresholds by posture
    POSTURE_CONFIG = {
        "lenient": {
            "min_severity_to_attack": Severity.HIGH,
            "confidence_threshold": 0.80,
            "max_attacks_per_hypothesis": 1,
        },
        "balanced": {
            "min_severity_to_attack": Severity.MEDIUM,
            "confidence_threshold": 0.60,
            "max_attacks_per_hypothesis": 2,
        },
        "strict": {
            "min_severity_to_attack": Severity.LOW,
            "confidence_threshold": 0.40,
            "max_attacks_per_hypothesis": 3,
        },
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        if config and "posture" in config:
            self.posture = config["posture"]
    
    def execute(self, blackboard: Blackboard) -> AgentOutput:
        """Execute adversarial analysis and generate attacks."""
        start_time = time.time()
        hypotheses_output = []
        facts_used = []
        
        try:
            # Get all debatable hypotheses (ACTIVE and DEFENDED)
            active_hypotheses = blackboard.get_hypotheses(status=HypothesisStatus.ACTIVE)
            defended_hypotheses = blackboard.get_hypotheses(status=HypothesisStatus.DEFENDED)
            all_debatable = active_hypotheses + defended_hypotheses
            
            if not all_debatable:
                logger.info("No active hypotheses to attack")
                return AgentOutput(
                    agent_id=self.agent_id,
                    hypotheses=[],
                    facts_used=[],
                    execution_time_ms=(time.time() - start_time) * 1000,
                    success=True,
                )
            
            # Get all facts for counter-evidence
            all_facts = blackboard.get_facts()
            facts_dict = {f.key: f.value for f in all_facts}
            facts_used = [f.fact_id for f in all_facts]
            
            # Attack each hypothesis
            attacks = []
            posture_config = self.POSTURE_CONFIG[self.posture]
            
            for hypothesis in all_debatable:
                hypothesis_attacks = self.attack_hypothesis(
                    hypothesis, facts_dict, all_facts, posture_config
                )
                
                for attack in hypothesis_attacks[:posture_config["max_attacks_per_hypothesis"]]:
                    blackboard.write_attack(attack, self.agent_id)
                    attacks.append(attack)
            
            # Generate summary hypothesis about overall skepticism
            if attacks:
                critical_attacks = [a for a in attacks if a.severity in [Severity.HIGH, Severity.CRITICAL]]
                hyp = self.generate_hypothesis(
                    claim=f"Identified {len(attacks)} potential issues in analyst claims, "
                          f"including {len(critical_attacks)} critical concerns that warrant attention.",
                    confidence=0.75,
                    linked_facts=[a.attack_id for a in attacks[:5]],
                )
                if hyp:
                    hypotheses_output.append(hyp)
            
            execution_time = (time.time() - start_time) * 1000
            self.log_execution(True, len(attacks), execution_time)
            
            return AgentOutput(
                agent_id=self.agent_id,
                hypotheses=hypotheses_output,
                facts_used=facts_used,
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
    
    def attack_hypothesis(
        self,
        hypothesis: Hypothesis,
        facts_dict: Dict[str, Any],
        all_facts: List[Fact],
        posture_config: Dict[str, Any],
    ) -> List[Attack]:
        """
        Generate attacks against a single hypothesis.
        
        Attack types:
        - data_inconsistency: Claim contradicts facts
        - missing_evidence: Claim not supported by data
        - logical_flaw: Reasoning has gaps
        - over_optimism: Ignores negative signals
        """
        attacks = []
        
        # Check for contradicting facts
        contradiction_attack = self._check_contradictions(hypothesis, facts_dict, all_facts)
        if contradiction_attack:
            attacks.append(contradiction_attack)
        
        # Check for missing evidence
        evidence_attack = self._check_missing_evidence(hypothesis, all_facts)
        if evidence_attack:
            attacks.append(evidence_attack)
        
        # Check for over-optimism (positive claim but negative signals exist)
        if self._is_optimistic_claim(hypothesis.claim):
            optimism_attack = self._check_over_optimism(hypothesis, facts_dict, all_facts)
            if optimism_attack:
                attacks.append(optimism_attack)
        
        # Filter by posture
        min_severity = posture_config["min_severity_to_attack"]
        severity_order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        min_index = severity_order.index(min_severity)
        
        filtered_attacks = [
            a for a in attacks
            if severity_order.index(a.severity) >= min_index
        ]
        
        return filtered_attacks
    
    def _check_contradictions(
        self,
        hypothesis: Hypothesis,
        facts_dict: Dict[str, Any],
        all_facts: List[Fact],
    ) -> Optional[Attack]:
        """Check if hypothesis contradicts any facts."""
        claim_lower = hypothesis.claim.lower()
        
        # Pattern matching for common contradictions
        contradictions = []
        
        # "Low leverage" but D/E is high
        if "low leverage" in claim_lower or "conservative" in claim_lower:
            de_ratio = facts_dict.get("de_ratio")
            if de_ratio and de_ratio > 1.0:
                contradictions.append(
                    f"Claim of low leverage contradicted by D/E ratio of {de_ratio:.2f}x"
                )
        
        # "Strong liquidity" but current ratio is low
        if "strong liquidity" in claim_lower or "ample cushion" in claim_lower:
            current_ratio = facts_dict.get("current_ratio")
            if current_ratio and current_ratio < 1.2:
                contradictions.append(
                    f"Claim of strong liquidity contradicted by current ratio of {current_ratio:.2f}x"
                )
        
        # "Good cash conversion" but QoE is low
        if "cash conversion" in claim_lower or "well-supported by cash" in claim_lower:
            qoe = facts_dict.get("qoe")
            if qoe and qoe < 0.6:
                contradictions.append(
                    f"Claim of good cash conversion contradicted by QoE ratio of {qoe:.2f}x"
                )
        
        if contradictions:
            counter_facts = [f.fact_id for f in all_facts if f.key in ["de_ratio", "current_ratio", "qoe"]]
            return Attack(
                critic_id=self.agent_id,
                target_hypothesis_id=hypothesis.hypothesis_id,
                contradiction_type="data_inconsistency",
                severity=Severity.HIGH,
                claim=f"Contradiction found: {contradictions[0]}",
                evidence_refs=[],
                counter_facts=counter_facts[:3],
                confidence=0.85,
            )
        
        return None
    
    def _check_missing_evidence(
        self,
        hypothesis: Hypothesis,
        all_facts: List[Fact],
    ) -> Optional[Attack]:
        """Check if hypothesis lacks supporting evidence."""
        if len(hypothesis.linked_facts) < 2:
            return Attack(
                critic_id=self.agent_id,
                target_hypothesis_id=hypothesis.hypothesis_id,
                contradiction_type="missing_evidence",
                severity=Severity.MEDIUM,
                claim=f"Hypothesis has insufficient supporting evidence "
                      f"({len(hypothesis.linked_facts)} linked facts)",
                evidence_refs=[],
                counter_facts=[],
                confidence=0.65,
            )
        return None
    
    def _check_over_optimism(
        self,
        hypothesis: Hypothesis,
        facts_dict: Dict[str, Any],
        all_facts: List[Fact],
    ) -> Optional[Attack]:
        """Check if positive claim ignores negative signals."""
        # List of negative signals to check
        negative_signals = []
        
        if facts_dict.get("de_ratio", 0) > 1.5:
            negative_signals.append("high leverage")
        if facts_dict.get("interest_coverage", 10) < 2.0:
            negative_signals.append("weak interest coverage")
        if facts_dict.get("qoe", 1) < 0.5:
            negative_signals.append("poor earnings quality")
        if facts_dict.get("net_profit_declining_3y"):
            negative_signals.append("declining profits")
        
        if negative_signals:
            return Attack(
                critic_id=self.agent_id,
                target_hypothesis_id=hypothesis.hypothesis_id,
                contradiction_type="over_optimism",
                severity=Severity.MEDIUM,
                claim=f"Positive claim may overlook: {', '.join(negative_signals[:3])}",
                evidence_refs=[],
                counter_facts=[],
                confidence=0.60,
            )
        
        return None
    
    def _is_optimistic_claim(self, claim: str) -> bool:
        """Determine if a claim is generally optimistic."""
        positive_words = [
            "strong", "healthy", "conservative", "favorable", "ample",
            "cushion", "positive", "good", "well", "comfortable",
            "premium", "effective", "improving", "growth"
        ]
        claim_lower = claim.lower()
        return any(word in claim_lower for word in positive_words)
