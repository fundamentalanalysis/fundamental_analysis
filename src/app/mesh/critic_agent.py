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
import json
import re

from .base_agent import BaseMeshAgent, AgentOutput
from src.app.blackboard.models import (
    Hypothesis, Fact, Attack, HypothesisStatus, Severity
)
from src.app.blackboard.store import Blackboard
from src.app.llm.factory import get_debate_provider
from src.app.llm.provider import Message

logger = logging.getLogger(__name__)

# Model for reasoning/debate tasks
DEBATE_MODEL = "magistral-medium-latest"


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
    
    # LLM configuration
    use_llm: bool = True
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        logger.info(f"[Critic] Initializing ShortSellerCriticAgent with config: {config}")
        
        if config and "posture" in config:
            self.posture = config["posture"]
        if config and "use_llm" in config:
            self.use_llm = config["use_llm"]
        
        # Initialize Mistral LLM provider for debate reasoning
        self._llm_provider = None
        logger.info(f"[Critic] use_llm={self.use_llm}")
        if self.use_llm:
            try:
                logger.info("[Critic] Creating LLM provider...")
                self._llm_provider = get_debate_provider()
                logger.info(f"[Critic] ✅ LLM provider ready: {self._llm_provider.provider_type.value}")
            except Exception as e:
                logger.warning(f"[Critic] ❌ Failed to initialize LLM provider: {e}")
                self._llm_provider = None
        else:
            logger.info("[Critic] LLM disabled, using rule-based attacks")
    
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
                # Try LLM-based attack generation first
                if self._llm_provider:
                    try:
                        llm_attacks = self._generate_llm_attacks(hypothesis, facts_dict, all_facts, posture_config)
                        if llm_attacks:
                            logger.info(f"[LLM] Generated {len(llm_attacks)} attacks for hypothesis: {hypothesis.hypothesis_id[:8]}...")
                            hypothesis_attacks = llm_attacks
                        else:
                            # Fallback to rule-based
                            hypothesis_attacks = self.attack_hypothesis(
                                hypothesis, facts_dict, all_facts, posture_config
                            )
                    except Exception as e:
                        logger.warning(f"LLM attack generation failed, using rule-based: {e}")
                        hypothesis_attacks = self.attack_hypothesis(
                            hypothesis, facts_dict, all_facts, posture_config
                        )
                else:
                    # Use rule-based attack generation
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
    
    def _generate_llm_attacks(
        self,
        hypothesis: Hypothesis,
        facts_dict: Dict[str, Any],
        all_facts: List[Fact],
        posture_config: Dict[str, Any],
    ) -> List[Attack]:
        """
        Generate attacks using the Mistral reasoning model.
        
        Uses a reasoning model to analyze the hypothesis claim against
        the financial facts and identify potential weaknesses, contradictions,
        or over-optimistic conclusions.
        """
        if not self._llm_provider:
            return []
        
        # Build facts context
        facts_context = "\n".join([
            f"- {key}: {value}" for key, value in facts_dict.items()
            if value is not None and not isinstance(value, (dict, list))
        ][:30])  # Limit to 30 facts
        
        # Build prompt for the reasoning model
        system_prompt = f"""You are a Short-Seller Critic analyzing financial hypotheses.
Your role is to find weaknesses, contradictions, and over-optimistic claims.

Posture: {self.posture.upper()}
- lenient: Only attack clear issues with strong evidence
- balanced: Moderate skepticism, attack when evidence supports
- strict: Aggressive, challenge all assumptions

For each valid attack, output a JSON object with these fields:
- contradiction_type: one of "data_inconsistency", "missing_evidence", "logical_flaw", "over_optimism"
- severity: one of "LOW", "MEDIUM", "HIGH", "CRITICAL"
- claim: Your attack claim explaining the issue (max 100 chars)
- confidence: Float between 0.0 and 1.0

Output ONLY valid JSON array. No explanations outside JSON.
Example: [{{"contradiction_type": "data_inconsistency", "severity": "HIGH", "claim": "D/E ratio of 1.8x contradicts claim of low leverage", "confidence": 0.85}}]
If no valid attacks, output: []"""

        user_prompt = f"""Analyze this hypothesis for weaknesses:

HYPOTHESIS: {hypothesis.claim}
Hypothesis Confidence: {hypothesis.confidence}
Author: {hypothesis.agent_id}

FINANCIAL FACTS:
{facts_context}

Find contradictions, missing evidence, logical flaws, or over-optimism.
Output JSON array of attacks (max {posture_config['max_attacks_per_hypothesis']} attacks)."""

        try:
            # Use Mistral provider with reasoning model
            messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt),
            ]
            
            response = self._llm_provider.complete(
                messages=messages,
                model=DEBATE_MODEL,
                temperature=0.3,
                max_tokens=1000,
            )
            
            if not response.success:
                logger.warning(f"LLM attack generation failed: {response.error_message}")
                return []
            
            # Parse the response into Attack objects
            attacks = self._parse_llm_attacks(response.content, hypothesis, all_facts)
            return attacks
            
        except Exception as e:
            logger.warning(f"LLM attack generation failed: {e}")
            return []
    
    def _parse_llm_attacks(
        self,
        response_content: str,
        hypothesis: Hypothesis,
        all_facts: List[Fact],
    ) -> List[Attack]:
        """Parse LLM response into Attack objects."""
        attacks = []
        
        try:
            # Handle thinking/reasoning model output that includes text before JSON
            content = response_content.strip()
            
            # Try to extract JSON from code blocks first
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                parts = content.split("```")
                # Look for the part that looks like JSON
                for part in parts[1::2]:  # Odd indices are code block contents
                    if part.strip().startswith("[") or part.strip().startswith("{"):
                        content = part.strip()
                        break
            
            # Try to find JSON array in the content (magistral often outputs thinking before JSON)
            # Look for array pattern containing the expected keys
            json_match = re.search(r'\[\s*\{[^}]*"contradiction_type"[^]]*\]', content, re.DOTALL)
            if json_match:
                content = json_match.group()
            else:
                # Fallback: try to find any JSON array
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    content = json_match.group()
            
            # If content still doesn't start with [ or {, try to find JSON
            if not content.startswith("[") and not content.startswith("{"):
                # Last attempt: find from first [ to last ]
                start_idx = content.find("[")
                end_idx = content.rfind("]")
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    content = content[start_idx:end_idx + 1]
            
            attack_data = json.loads(content)
            
            if not isinstance(attack_data, list):
                attack_data = [attack_data]
            
            severity_map = {
                "LOW": Severity.LOW,
                "MEDIUM": Severity.MEDIUM,
                "HIGH": Severity.HIGH,
                "CRITICAL": Severity.CRITICAL,
            }
            
            for item in attack_data:
                if not isinstance(item, dict):
                    continue
                
                severity_str = item.get("severity", "MEDIUM").upper()
                severity = severity_map.get(severity_str, Severity.MEDIUM)
                
                attack = Attack(
                    critic_id=self.agent_id,
                    target_hypothesis_id=hypothesis.hypothesis_id,
                    contradiction_type=item.get("contradiction_type", "logical_flaw"),
                    severity=severity,
                    claim=item.get("claim", "LLM-generated attack")[:200],
                    evidence_refs=[],
                    counter_facts=[f.fact_id for f in all_facts[:3]],
                    confidence=min(1.0, max(0.0, float(item.get("confidence", 0.7)))),
                )
                attacks.append(attack)
            
            logger.info(f"[LLM] Parsed {len(attacks)} attacks from response")
            return attacks
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse LLM attack response: {e}")
            # Log more context for debugging
            if response_content:
                logger.debug(f"Raw response length: {len(response_content)}")
                # Try to show where JSON might be
                if "[" in response_content:
                    idx = response_content.find("[")
                    logger.debug(f"JSON might start at char {idx}: ...{response_content[max(0,idx-20):idx+100]}...")
            return []
