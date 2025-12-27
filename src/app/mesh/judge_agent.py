# =============================================================
# src/app/mesh/judge_agent.py
# Judge Agent - Final Synthesis and Executive Output
# Layer C - Agentic Mesh
# =============================================================
"""
Judge Agent produces the final decision memo.

Key responsibilities:
- Synthesize all agent outputs
- Generate thesis and anti-thesis using LLM
- Identify single point of failure
- Define kill-switch signals
- Produce executive-grade output
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import time
import logging

from .base_agent import BaseMeshAgent, AgentOutput
from src.app.blackboard.models import (
    Hypothesis, Attack, Resolution, Override, FinalDecision,
    Fact, ConsensusState, HypothesisStatus
)
from src.app.blackboard.store import Blackboard
from src.app.llm.factory import get_default_provider
from src.app.llm.provider import Message

logger = logging.getLogger(__name__)


class JudgeAgent(BaseMeshAgent):
    """
    Produces final synthesis, thesis/anti-thesis, and executive memo.
    
    The Judge:
    - NEVER invents the math (uses deterministic scores)
    - Uses LLM for narrative synthesis
    - Identifies SPOF and kill-switches
    - Produces audit-ready output
    """
    
    agent_id = "judge"
    agent_name = "Judge"
    description = "Investment committee level synthesis and final decision"
    hypothesis_budget = 3
    use_llm = True
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        if config and "use_llm" in config:
            self.use_llm = config["use_llm"]
        
        # Initialize LLM provider
        self._llm_provider = None
        if self.use_llm:
            try:
                self._llm_provider = get_default_provider()
                logger.info(f"[Judge] Using LLM provider: {self._llm_provider.provider_type.value}")
            except Exception as e:
                logger.warning(f"[Judge] Failed to initialize LLM provider: {e}")
                self._llm_provider = None
    
    def execute(self, blackboard: Blackboard) -> AgentOutput:
        """Generate final decision."""
        start_time = time.time()
        
        try:
            final_decision = self.synthesize(blackboard)
            blackboard.write_final(final_decision, self.agent_id)
            
            execution_time = (time.time() - start_time) * 1000
            self.log_execution(True, 1, execution_time)
            
            return AgentOutput(
                agent_id=self.agent_id,
                hypotheses=[],  # Judge produces FinalDecision, not hypotheses
                facts_used=[final_decision.decision_id],
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
    
    def synthesize(self, blackboard: Blackboard) -> FinalDecision:
        """
        Generate the final decision from blackboard state.
        """
        # Gather all data
        facts = blackboard.get_facts()
        hypotheses = blackboard.get_hypotheses(include_expired=True)
        attacks = blackboard.get_attacks()
        resolutions = blackboard.get_resolutions()
        overrides = blackboard.get_overrides(applied_only=True)
        data_quality = blackboard.get_data_quality_report()
        
        # Calculate base score from facts
        base_score = self._calculate_base_score(facts)
        
        # Apply consensus adjustments
        consensus_adjustment, state = self._apply_consensus_scoring(resolutions)
        adjusted_score = base_score + consensus_adjustment
        
        # Apply correlation overrides
        final_score, score_adjustments = self._apply_overrides(adjusted_score, overrides)
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            facts, resolutions, data_quality, overrides
        )
        
        # Build thesis and anti-thesis (use LLM if available)
        if self._llm_provider:
            thesis, anti_thesis = self._generate_llm_synthesis(
                facts, hypotheses, attacks, resolutions, overrides, 
                final_score, state, confidence
            )
        else:
            thesis = self._build_thesis(facts, hypotheses, resolutions)
            anti_thesis = self._build_anti_thesis(attacks, overrides)
        
        # Extract key strengths and risks
        strengths, risks = self._extract_strengths_and_risks(hypotheses, attacks)
        
        # Identify SPOF and kill-switches
        spof = self._identify_spof(overrides, attacks)
        kill_switches = self._identify_kill_switches(overrides, facts)
        
        # Check manual review requirement
        manual_review, review_reasons = self._check_manual_review(
            state, resolutions, overrides, data_quality
        )
        
        # Build monitoring checklist
        monitoring = self._build_monitoring_checklist(risks, kill_switches)
        
        # Uncertainty and view changers
        uncertainty = self._explain_uncertainty(resolutions, state)
        view_changers = self._identify_view_changers(risks, kill_switches)
        
        return FinalDecision(
            score=max(0, min(100, int(final_score))),
            confidence=confidence,
            state=state,
            score_breakdown=self._build_score_breakdown(facts),
            overrides_applied=[o.override_id for o in overrides],
            score_adjustments=score_adjustments,
            thesis=thesis,
            anti_thesis=anti_thesis,
            key_strengths=strengths,
            key_risks=risks,
            spof=spof,
            kill_switches=kill_switches,
            manual_review_required=manual_review,
            review_reasons=review_reasons,
            monitoring_checklist=monitoring,
            uncertainty_explanation=uncertainty,
            view_changers=view_changers,
            evidence_summary=blackboard.get_evidence_bundle(),
            unresolved_items=[
                r.unresolved_items for r in resolutions
            ][-1] if resolutions else [],
        )
    
    def _calculate_base_score(self, facts: List[Fact]) -> float:
        """Calculate base score from deterministic facts."""
        facts_dict = {f.key: f.value for f in facts}
        
        # Scoring components (each 0-100, weighted)
        components = []
        
        # Leverage (25%)
        de_ratio = facts_dict.get("de_ratio", 1.0)
        if de_ratio is not None:
            leverage_score = max(0, 100 - (de_ratio * 30))
            components.append(("leverage", leverage_score, 0.25))
        
        # Liquidity (20%)
        current_ratio = facts_dict.get("current_ratio", 1.5)
        if current_ratio is not None:
            liquidity_score = min(100, current_ratio * 40)
            components.append(("liquidity", liquidity_score, 0.20))
        
        # Profitability (25%)
        roe = facts_dict.get("roe", 0.10)
        if roe is not None:
            profit_score = min(100, max(0, roe * 500))
            components.append(("profitability", profit_score, 0.25))
        
        # Quality of Earnings (15%)
        qoe = facts_dict.get("qoe", 1.0)
        if qoe is not None:
            qoe_score = min(100, qoe * 60)
            components.append(("earnings_quality", qoe_score, 0.15))
        
        # Growth (15%)
        revenue_cagr = facts_dict.get("revenue_cagr", 0.05)
        if revenue_cagr is not None:
            growth_score = min(100, max(0, (revenue_cagr + 0.1) * 200))
            components.append(("growth", growth_score, 0.15))
        
        # Calculate weighted score
        if not components:
            return 50.0  # Default neutral score
        
        total_weight = sum(c[2] for c in components)
        weighted_score = sum(c[1] * c[2] for c in components) / total_weight
        
        return weighted_score
    
    def _apply_consensus_scoring(
        self,
        resolutions: List[Resolution],
    ) -> Tuple[float, ConsensusState]:
        """Apply consensus scoring based on debate outcome."""
        if not resolutions:
            return 0.0, ConsensusState.CONSENSUS
        
        final_resolution = resolutions[-1]
        convergence = final_resolution.convergence_score
        
        if convergence >= 0.9:
            return 0.0, ConsensusState.CONSENSUS
        elif convergence >= 0.6:
            # Weighted score - slight penalty for uncertainty
            penalty = (0.9 - convergence) * 10  # Up to 3 points penalty
            return -penalty, ConsensusState.WEIGHTED
        else:
            # Unresolved - larger penalty and pessimistic
            penalty = (0.9 - convergence) * 20  # Up to 12 points penalty
            return -penalty, ConsensusState.UNRESOLVED
    
    def _apply_overrides(
        self,
        score: float,
        overrides: List[Override],
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Apply correlation overrides to final score."""
        adjustments = []
        final_score = score
        
        for override in overrides:
            if override.action == "cap_score" and override.value is not None:
                if final_score > override.value:
                    adjustments.append({
                        "rule": override.rule_name,
                        "action": "cap",
                        "from": final_score,
                        "to": override.value,
                    })
                    final_score = override.value
            
            elif override.action == "floor_score" and override.value is not None:
                if final_score < override.value:
                    adjustments.append({
                        "rule": override.rule_name,
                        "action": "floor",
                        "from": final_score,
                        "to": override.value,
                    })
                    final_score = override.value
            
            elif override.action == "kill_switch":
                # Kill switch caps score at 25
                adjustments.append({
                    "rule": override.rule_name,
                    "action": "kill_switch",
                    "from": final_score,
                    "to": min(final_score, 25),
                })
                final_score = min(final_score, 25)
        
        return final_score, adjustments
    
    def _calculate_confidence(
        self,
        facts: List[Fact],
        resolutions: List[Resolution],
        data_quality: Any,
        overrides: List[Override],
    ) -> float:
        """Calculate overall confidence in the decision."""
        factors = []
        
        # Data quality factor
        if data_quality:
            factors.append(data_quality.quality_score)
        else:
            factors.append(0.7)  # Default moderate confidence
        
        # Debate convergence factor
        if resolutions:
            factors.append(resolutions[-1].convergence_score)
        else:
            factors.append(0.8)  # No debate = assume reasonable confidence
        
        # Evidence density factor (more facts = higher confidence)
        fact_count = len(facts)
        evidence_factor = min(1.0, fact_count / 50)  # Saturates at 50 facts
        factors.append(evidence_factor)
        
        # Override impact (more overrides = more scrutiny needed = lower confidence)
        override_penalty = len(overrides) * 0.05
        factors.append(max(0.5, 1.0 - override_penalty))
        
        return sum(factors) / len(factors)
    
    def _build_thesis(
        self,
        facts: List[Fact],
        hypotheses: List[Hypothesis],
        resolutions: List[Resolution],
    ) -> str:
        """Build the bull thesis from positive signals."""
        facts_dict = {f.key: f.value for f in facts}
        
        positives = []
        
        # Check for positive indicators
        if facts_dict.get("de_ratio", 2) < 0.5:
            positives.append("conservative leverage provides financial flexibility")
        
        if facts_dict.get("interest_coverage", 1) > 5:
            positives.append("strong interest coverage indicates robust debt serviceability")
        
        if facts_dict.get("roe", 0) > 0.15:
            positives.append("above-average returns on equity demonstrate value creation")
        
        if facts_dict.get("revenue_cagr", 0) > 0.10:
            positives.append("healthy revenue growth trajectory")
        
        if facts_dict.get("qoe", 0) > 1.0:
            positives.append("earnings well-supported by operating cash flows")
        
        # Add resolved hypothesis claims
        resolved_hyp_ids = set()
        for res in resolutions:
            resolved_hyp_ids.update(res.resolved_hypotheses)
        
        for hyp in hypotheses:
            if hyp.hypothesis_id in resolved_hyp_ids and hyp.confidence > 0.7:
                # Extract key positive claims
                claim_lower = hyp.claim.lower()
                if any(word in claim_lower for word in ["strong", "healthy", "positive", "cushion"]):
                    positives.append(hyp.claim[:100])
        
        if not positives:
            return "Limited positive signals identified. Investment thesis unclear."
        
        return "BULL CASE: " + "; ".join(positives[:5]) + "."
    
    def _build_anti_thesis(
        self,
        attacks: List[Attack],
        overrides: List[Override],
    ) -> str:
        """Build the bear thesis from critic attacks and overrides."""
        negatives = []
        
        # Add override concerns
        for override in overrides:
            negatives.append(f"{override.rule_name}: {override.description}")
        
        # Add high-severity attacks
        for attack in attacks:
            if attack.severity.value in ["high", "critical"]:
                negatives.append(attack.claim[:100])
        
        if not negatives:
            return "No significant risks identified by critic analysis."
        
        return "BEAR CASE: " + "; ".join(negatives[:5]) + "."
    
    def _extract_strengths_and_risks(
        self,
        hypotheses: List[Hypothesis],
        attacks: List[Attack],
    ) -> Tuple[List[str], List[str]]:
        """Extract key strengths and risks from hypotheses and attacks."""
        strengths = []
        risks = []
        
        # High-confidence positive hypotheses are strengths
        for hyp in hypotheses:
            if hyp.confidence > 0.75:
                claim_lower = hyp.claim.lower()
                if any(word in claim_lower for word in ["strong", "healthy", "positive"]):
                    strengths.append(hyp.claim[:80])
                elif any(word in claim_lower for word in ["risk", "concern", "weak", "stress"]):
                    risks.append(hyp.claim[:80])
        
        # All attacks are risks
        for attack in attacks:
            risks.append(f"[{attack.severity.value.upper()}] {attack.claim[:60]}")
        
        return strengths[:5], risks[:7]
    
    def _identify_spof(
        self,
        overrides: List[Override],
        attacks: List[Attack],
    ) -> Optional[str]:
        """Identify single point of failure."""
        # SPOF from overrides
        spof_overrides = [o for o in overrides if o.action == "flag_spof"]
        if spof_overrides:
            return spof_overrides[0].description
        
        # SPOF from critical attacks
        critical_attacks = [a for a in attacks if a.severity.value == "critical"]
        if critical_attacks:
            return critical_attacks[0].claim
        
        return None
    
    def _identify_kill_switches(
        self,
        overrides: List[Override],
        facts: List[Fact],
    ) -> List[str]:
        """Identify kill-switch signals."""
        kill_switches = []
        
        # From overrides
        for override in overrides:
            if override.action == "kill_switch":
                kill_switches.append(f"{override.rule_name}: {override.description}")
        
        # From critical metrics
        facts_dict = {f.key: f.value for f in facts}
        
        if facts_dict.get("interest_coverage", 10) < 1.0:
            kill_switches.append("Interest coverage below 1x - cannot service debt from operations")
        
        if facts_dict.get("current_ratio", 2) < 0.5:
            kill_switches.append("Current ratio critically low - immediate liquidity concern")
        
        return kill_switches[:5]
    
    def _check_manual_review(
        self,
        state: ConsensusState,
        resolutions: List[Resolution],
        overrides: List[Override],
        data_quality: Any,
    ) -> Tuple[bool, List[str]]:
        """Determine if manual review is required."""
        reasons = []
        
        if state == ConsensusState.UNRESOLVED:
            reasons.append("Debate did not converge - significant disagreement remains")
        
        if len(overrides) >= 3:
            reasons.append(f"{len(overrides)} correlation rules triggered")
        
        kill_switch_overrides = [o for o in overrides if o.action == "kill_switch"]
        if kill_switch_overrides:
            reasons.append("Kill-switch triggered - requires senior review")
        
        if data_quality and data_quality.quality_score < 0.5:
            reasons.append("Low data quality score - analysis may be unreliable")
        
        return len(reasons) > 0, reasons
    
    def _build_monitoring_checklist(
        self,
        risks: List[str],
        kill_switches: List[str],
    ) -> List[str]:
        """Build a monitoring checklist for ongoing surveillance."""
        checklist = []
        
        # Standard items
        checklist.append("Monitor quarterly earnings for trend changes")
        checklist.append("Track credit rating changes and outlook revisions")
        
        # Risk-specific items
        if any("leverage" in r.lower() or "debt" in r.lower() for r in risks):
            checklist.append("Watch D/E ratio and interest coverage trends")
        
        if any("cash" in r.lower() or "liquidity" in r.lower() for r in risks):
            checklist.append("Monitor working capital and cash position")
        
        # Kill-switch monitoring
        for ks in kill_switches[:2]:
            checklist.append(f"CRITICAL: Monitor {ks[:50]}")
        
        return checklist[:8]
    
    def _explain_uncertainty(
        self,
        resolutions: List[Resolution],
        state: ConsensusState,
    ) -> str:
        """Explain sources of uncertainty in the analysis."""
        if state == ConsensusState.CONSENSUS:
            return "High confidence: Analyst hypotheses and critic challenges were fully reconciled."
        
        if state == ConsensusState.WEIGHTED:
            return ("Moderate uncertainty: Some contested items remain. "
                    "Score reflects weighted view across differing perspectives.")
        
        if resolutions and resolutions[-1].unresolved_items:
            count = len(resolutions[-1].unresolved_items)
            return (f"Significant uncertainty: {count} items unresolved. "
                    "Final score is pessimistic pending further analysis.")
        
        return "Unknown uncertainty level."
    
    def _identify_view_changers(
        self,
        risks: List[str],
        kill_switches: List[str],
    ) -> List[str]:
        """Identify what would change the investment view."""
        changers = []
        
        # Positive view changers
        changers.append("Deleveraging: D/E ratio falling below 0.5x")
        changers.append("Improved cash conversion: QoE ratio above 1.2x for 2+ quarters")
        
        # Risk-specific changers
        if any("dividend" in r.lower() for r in risks):
            changers.append("Dividend cut or suspension to preserve capital")
        
        if any("growth" in r.lower() or "revenue" in r.lower() for r in risks):
            changers.append("Revenue growth returning to positive territory")
        
        # Negative changers
        changers.append("Credit rating downgrade to speculative grade")
        changers.append("Material adverse disclosure or restatement")
        
        return changers[:6]
    
    def _build_score_breakdown(self, facts: List[Fact]) -> Dict[str, int]:
        """Build per-module score breakdown."""
        # Simplified - would aggregate by module in production
        facts_dict = {f.key: f.value for f in facts}
        
        breakdown = {}
        
        # Leverage
        de = facts_dict.get("de_ratio", 1.0)
        breakdown["leverage"] = int(max(0, 100 - (de or 1.0) * 30))
        
        # Liquidity
        cr = facts_dict.get("current_ratio", 1.5)
        breakdown["liquidity"] = int(min(100, (cr or 1.5) * 40))
        
        # Profitability
        roe = facts_dict.get("roe", 0.10)
        breakdown["profitability"] = int(min(100, max(0, (roe or 0.10) * 500)))
        
        return breakdown
    
    def _generate_llm_synthesis(
        self,
        facts: List[Fact],
        hypotheses: List[Hypothesis],
        attacks: List[Attack],
        resolutions: List[Resolution],
        overrides: List[Override],
        final_score: float,
        state: ConsensusState,
        confidence: float,
    ) -> Tuple[str, str]:
        """
        Use LLM to generate professional thesis and anti-thesis narratives.
        
        Returns:
            Tuple of (thesis, anti_thesis)
        """
        if not self._llm_provider:
            return self._build_thesis(facts, hypotheses, resolutions), \
                   self._build_anti_thesis(attacks, overrides)
        
        # Build context for LLM
        facts_dict = {f.key: f.value for f in facts}
        
        # Key metrics summary
        key_metrics = []
        if facts_dict.get("de_ratio") is not None:
            key_metrics.append(f"D/E Ratio: {facts_dict['de_ratio']:.2f}x")
        if facts_dict.get("current_ratio") is not None:
            key_metrics.append(f"Current Ratio: {facts_dict['current_ratio']:.2f}x")
        if facts_dict.get("interest_coverage") is not None:
            key_metrics.append(f"Interest Coverage: {facts_dict['interest_coverage']:.2f}x")
        if facts_dict.get("roe") is not None:
            key_metrics.append(f"ROE: {facts_dict['roe']*100:.1f}%")
        if facts_dict.get("qoe") is not None:
            key_metrics.append(f"QoE (CFO/NI): {facts_dict['qoe']:.2f}x")
        
        # Hypothesis summary
        hyp_summary = "\n".join([
            f"- [{h.status.name}] {h.claim[:100]} (conf: {h.confidence:.2f})"
            for h in hypotheses[:10]
        ])
        
        # Attack summary
        attack_summary = "\n".join([
            f"- [{a.severity.name}] {a.claim[:80]}"
            for a in attacks[:5]
        ])
        
        # Override summary
        override_summary = "\n".join([
            f"- {o.rule_name}: {o.description[:60]}"
            for o in overrides
        ])
        
        system_prompt = """You are a senior investment analyst writing an executive summary for an investment committee.

Generate two sections:
1. THESIS (Bull Case): A professional 2-3 sentence investment thesis highlighting the company's strengths
2. ANTI_THESIS (Bear Case): A professional 2-3 sentence counter-argument highlighting key risks

Rules:
- Be concise and professional
- Use specific numbers from the metrics provided
- Thesis should highlight positives, Anti-thesis should highlight concerns
- Output ONLY in this exact JSON format, no other text:
{"thesis": "BULL CASE: ...", "anti_thesis": "BEAR CASE: ..."}"""

        user_prompt = f"""FINAL SCORE: {final_score:.0f}/100
CONFIDENCE: {confidence:.2f}
CONSENSUS STATE: {state.name}

KEY METRICS:
{chr(10).join(key_metrics)}

ANALYST HYPOTHESES:
{hyp_summary if hyp_summary else "No hypotheses"}

CRITIC ATTACKS:
{attack_summary if attack_summary else "No attacks"}

CORRELATION OVERRIDES:
{override_summary if override_summary else "No overrides triggered"}

Generate the thesis and anti_thesis JSON."""

        try:
            messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt),
            ]
            
            response = self._llm_provider.complete(
                messages=messages,
                temperature=0.4,
                max_tokens=500,
            )
            
            if not response.success:
                logger.warning(f"[Judge] LLM synthesis failed: {response.error_message}")
                return self._build_thesis(facts, hypotheses, resolutions), \
                       self._build_anti_thesis(attacks, overrides)
            
            # Track LLM usage
            self._llm_calls += 1
            self._llm_tokens += response.usage.get("total_tokens", 0)
            
            # Parse response
            import json
            import re
            
            content = response.content.strip()
            # Extract JSON from response
            json_match = re.search(r'\{[^{}]*"thesis"[^{}]*"anti_thesis"[^{}]*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group()
            
            result = json.loads(content)
            thesis = result.get("thesis", self._build_thesis(facts, hypotheses, resolutions))
            anti_thesis = result.get("anti_thesis", self._build_anti_thesis(attacks, overrides))
            
            logger.info(f"[Judge] LLM synthesis complete: thesis={len(thesis)} chars, anti_thesis={len(anti_thesis)} chars")
            return thesis, anti_thesis
            
        except Exception as e:
            logger.warning(f"[Judge] LLM synthesis error: {e}")
            return self._build_thesis(facts, hypotheses, resolutions), \
                   self._build_anti_thesis(attacks, overrides)
