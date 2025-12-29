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
import json
import re

from .base_agent import BaseMeshAgent, AgentOutput
from src.app.blackboard.models import (
    Hypothesis, Attack, Resolution, HypothesisStatus
)
from src.app.blackboard.store import Blackboard
from src.app.llm.factory import get_debate_provider
from src.app.llm.provider import Message

logger = logging.getLogger(__name__)

# Model for reasoning/debate tasks
DEBATE_MODEL = "magistral-medium-latest"


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
    use_llm: bool = True
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        if config:
            self.max_rounds = config.get("max_rounds", self.max_rounds)
            self.convergence_threshold = config.get("convergence_threshold", self.convergence_threshold)
            if "use_llm" in config:
                self.use_llm = config["use_llm"]
        
        # Initialize Mistral LLM provider for debate resolution
        self._llm_provider = None
        if self.use_llm:
            try:
                self._llm_provider = get_debate_provider()
                logger.info(f"[Mediator] Using LLM provider for resolution: {self._llm_provider.provider_type.value}")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM provider: {e}")
                self._llm_provider = None
    
    def execute(self, blackboard: Blackboard) -> AgentOutput:
        """Run a debate round and attempt resolution."""
        start_time = time.time()
        hypotheses = []
        facts_used = []
        
        try:
            current_round = blackboard.get_debate_round() + 1
            
            # Get all debatable hypotheses (ACTIVE and DEFENDED can be debated)
            active_hypotheses = blackboard.get_hypotheses(status=HypothesisStatus.ACTIVE)
            defended_hypotheses = blackboard.get_hypotheses(status=HypothesisStatus.DEFENDED)
            all_attacks = blackboard.get_attacks()
            
            # Combine for debate - both active and defended hypotheses participate
            debatable = active_hypotheses + defended_hypotheses
            
            # Run resolution logic
            resolution = self.run_debate_round(
                round_number=current_round,
                hypotheses=debatable,
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
        
        Resolution logic (rule-based fallback):
        1. Hypotheses with no attacks -> resolved
        2. Hypotheses with weak attacks -> resolved (in favor of hypothesis)
        3. Hypotheses with strong attacks -> need examination
        4. Attacked hypotheses with counter-evidence -> may remain unresolved
        
        If LLM is available, uses reasoning model for more nuanced resolution.
        """
        llm_rationale = ""
        
        # Try LLM-based resolution first
        logger.info(f"[Mediator] LLM provider available: {self._llm_provider is not None}")
        if self._llm_provider:
            try:
                logger.info(f"[Mediator] Calling LLM for resolution...")
                llm_resolved_hyps, llm_resolved_attacks, llm_unresolved, llm_rationale = \
                    self._generate_llm_resolution(round_number, hypotheses, attacks)
                
                logger.info(f"[Mediator] LLM returned: {len(llm_resolved_hyps)} resolved hyps, {len(llm_resolved_attacks)} resolved attacks, {len(llm_unresolved)} unresolved")
                if llm_resolved_hyps or llm_resolved_attacks or llm_unresolved:
                    logger.info(f"[LLM] Using reasoning model for debate resolution")
                    
                    # Use LLM resolution results
                    resolved_hypotheses = llm_resolved_hyps
                    resolved_attacks = llm_resolved_attacks
                    unresolved_items = llm_unresolved
                    
                    # Calculate convergence and quality
                    total_items = len(hypotheses) + len(attacks)
                    resolved_count = len(resolved_hypotheses) + len(resolved_attacks)
                    convergence_score = resolved_count / total_items if total_items > 0 else 1.0
                    
                    debate_quality = self._assess_debate_quality(
                        hypotheses, attacks, resolved_hypotheses, resolved_attacks
                    )
                    
                    rationale = self._generate_rationale(
                        round_number, resolved_hypotheses, resolved_attacks, unresolved_items, llm_rationale
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
            except Exception as e:
                logger.warning(f"LLM resolution failed, using rule-based: {e}")
        
        # Fall back to rule-based resolution
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
        llm_rationale: Optional[str] = None,
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
        
        # Add LLM-generated reasoning if available
        if llm_rationale:
            parts.append(f"\n\n[LLM Analysis] {llm_rationale}")
        
        return " ".join(parts)
    
    def _generate_llm_resolution(
        self,
        round_number: int,
        hypotheses: List[Hypothesis],
        attacks: List[Attack],
    ) -> Tuple[List[str], List[str], List[str], str]:
        """
        Use the Mistral reasoning model to determine debate resolution.
        
        Returns:
            Tuple of (resolved_hypotheses, resolved_attacks, unresolved_items, rationale)
        """
        if not self._llm_provider:
            return [], [], [], ""
        
        # Build context for the reasoning model
        hypotheses_context = "\n".join([
            f"- HYP_{h.hypothesis_id[:8]}: \"{h.claim}\" (confidence: {h.confidence:.2f}, author: {h.agent_id})"
            for h in hypotheses
        ])
        
        attacks_context = "\n".join([
            f"- ATK_{a.attack_id[:8]} -> HYP_{a.target_hypothesis_id[:8]}: \"{a.claim}\" "
            f"(type: {a.contradiction_type}, severity: {a.severity.name}, confidence: {a.confidence:.2f})"
            for a in attacks
        ])
        
        system_prompt = """You are a Debate Mediator analyzing financial analysis hypotheses and attacks.
Your role is to:
1. Determine which hypotheses are well-supported and should be RESOLVED (accepted)
2. Determine which attacks are valid and which should be DISMISSED
3. Identify items that remain CONTESTED and need more analysis

Output a JSON object with:
- resolved_hypotheses: list of hypothesis IDs (e.g., ["HYP_abc12345"])
- resolved_attacks: list of attack IDs to dismiss (e.g., ["ATK_xyz98765"])
- unresolved: list of contested item IDs
- rationale: Brief explanation of your reasoning (max 200 chars)

Consider:
- Hypothesis with no attacks -> resolved
- Strong hypothesis vs weak attack -> hypothesis resolved, attack dismissed
- Strong attack vs weak hypothesis -> attack stands, hypothesis unresolved
- Close confidence scores -> both unresolved

Output ONLY valid JSON. No explanations outside JSON."""

        user_prompt = f"""DEBATE ROUND {round_number}

HYPOTHESES:
{hypotheses_context if hypotheses_context else "No hypotheses"}

ATTACKS:
{attacks_context if attacks_context else "No attacks"}

Analyze and determine resolution. Output JSON only."""

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
                max_tokens=1500,
            )
            
            if not response.success:
                logger.warning(f"LLM resolution failed: {response.error_message}")
                return [], [], [], ""
            
            # Parse the response
            return self._parse_llm_resolution(response.content, hypotheses, attacks)
            
        except Exception as e:
            logger.warning(f"LLM resolution generation failed: {e}")
            return [], [], [], ""
    
    def _parse_llm_resolution(
        self,
        response_content: str,
        hypotheses: List[Hypothesis],
        attacks: List[Attack],
    ) -> Tuple[List[str], List[str], List[str], str]:
        """Parse LLM resolution response."""
        try:
            # Extract JSON from response
            content = response_content.strip()
            if "```json" in content:
                content = content.split("```json")[-1].split("```")[0].strip()
            elif "```" in content:
                parts = content.split("```")
                for part in parts[1::2]:
                    if part.strip().startswith("{") or part.strip().startswith("["):
                        content = part.strip()
                        break
            
            # For reasoning models, find the JSON object with balanced braces
            json_found = False
            start_idx = content.find("{")
            if start_idx != -1:
                brace_count = 0
                for i, char in enumerate(content[start_idx:], start_idx):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            content = content[start_idx:i+1]
                            json_found = True
                            break
            
            if not json_found or not content.strip().startswith("{"):
                logger.debug(f"No valid JSON found in mediator response")
                return [], [], [], ""
            
            data = json.loads(content)
            
            # Map short IDs back to full IDs
            hyp_map = {f"HYP_{h.hypothesis_id[:8]}": h.hypothesis_id for h in hypotheses}
            atk_map = {f"ATK_{a.attack_id[:8]}": a.attack_id for a in attacks}
            
            resolved_hyps = []
            for h_id in data.get("resolved_hypotheses", []):
                if h_id in hyp_map:
                    resolved_hyps.append(hyp_map[h_id])
                elif h_id.startswith("HYP_"):
                    # Try partial match
                    for short_id, full_id in hyp_map.items():
                        if h_id in short_id or short_id in h_id:
                            resolved_hyps.append(full_id)
                            break
            
            resolved_attacks = []
            for a_id in data.get("resolved_attacks", []):
                if a_id in atk_map:
                    resolved_attacks.append(atk_map[a_id])
                elif a_id.startswith("ATK_"):
                    # Try partial match
                    for short_id, full_id in atk_map.items():
                        if a_id in short_id or short_id in a_id:
                            resolved_attacks.append(full_id)
                            break
            
            unresolved = data.get("unresolved", [])
            rationale = data.get("rationale", "")[:500]
            
            logger.info(f"[LLM] Resolution: {len(resolved_hyps)} hypotheses resolved, "
                       f"{len(resolved_attacks)} attacks dismissed, {len(unresolved)} contested")
            
            return resolved_hyps, resolved_attacks, unresolved, rationale
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse LLM resolution response: {e}")
            logger.debug(f"Raw response: {response_content[:500]}")
            return [], [], [], ""

