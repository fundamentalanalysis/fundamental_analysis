# =============================================================
# src/app/mesh/base_agent.py
# Base Mesh Agent - Abstract base for all mesh agents
# Layer C - Agentic Mesh
# =============================================================
"""
Base class for all agents in the agentic mesh.

Provides common functionality for:
- Blackboard interaction
- Hypothesis budget management
- Confidence thresholds
- Configurable LLM integration (Mistral, OpenAI, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from src.app.blackboard.models import Hypothesis, Fact, HypothesisStatus
from src.app.blackboard.store import Blackboard

logger = logging.getLogger(__name__)

# LLM provider singleton (initialized lazily)
_llm_provider = None


def get_llm_provider():
    """Get the default LLM provider (lazy initialization)."""
    global _llm_provider
    if _llm_provider is None:
        try:
            from src.app.llm import get_default_provider
            _llm_provider = get_default_provider()
        except Exception as e:
            logger.warning(f"Failed to initialize LLM provider: {e}")
            return None
    return _llm_provider


def set_llm_provider(provider):
    """Set the default LLM provider for all agents."""
    global _llm_provider
    _llm_provider = provider


class AgentOutput(BaseModel):
    """Standard output from an agent execution."""
    agent_id: str
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    facts_used: List[str] = Field(default_factory=list)
    execution_time_ms: float = 0
    success: bool = True
    error_message: Optional[str] = None
    
    # LLM usage tracking
    llm_calls: int = 0
    llm_tokens_used: int = 0


class BaseMeshAgent(ABC):
    """
    Abstract base class for all agents in the agentic mesh.
    
    Key features:
    - Hypothesis budget: Limits hypothesis generation
    - Minimum confidence: Filters low-confidence outputs
    - Blackboard integration: Read/write with ACL
    - Configurable LLM integration: Supports multiple providers
    """
    
    # Agent identity
    agent_id: str = "base_agent"
    agent_name: str = "Base Agent"
    description: str = "Base mesh agent"
    
    # System prompt for LLM (override in subclasses)
    system_prompt: str = "You are a financial analyst."
    
    # Constraints
    hypothesis_budget: int = 5  # Max hypotheses per execution
    min_confidence: float = 0.4  # Minimum confidence to output
    
    # LLM settings
    use_llm: bool = True
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1000
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the agent.
        
        Args:
            config: Optional configuration overrides
        """
        self.config = config or {}
        
        # Apply config overrides
        if "hypothesis_budget" in self.config:
            self.hypothesis_budget = self.config["hypothesis_budget"]
        if "min_confidence" in self.config:
            self.min_confidence = self.config["min_confidence"]
        if "use_llm" in self.config:
            self.use_llm = self.config["use_llm"]
        if "llm_temperature" in self.config:
            self.llm_temperature = self.config["llm_temperature"]
        if "llm_max_tokens" in self.config:
            self.llm_max_tokens = self.config["llm_max_tokens"]
        if "system_prompt" in self.config:
            self.system_prompt = self.config["system_prompt"]
        
        # Track LLM usage
        self._llm_calls = 0
        self._llm_tokens = 0
    
    @abstractmethod
    def execute(self, blackboard: Blackboard) -> AgentOutput:
        """
        Execute the agent's primary function.
        
        Args:
            blackboard: The shared blackboard state
            
        Returns:
            AgentOutput with hypotheses and metadata
        """
        pass
    
    def generate_hypothesis(
        self,
        claim: str,
        confidence: float,
        linked_facts: List[str],
        evidence_refs: Optional[List[str]] = None,
        reasoning: Optional[str] = None,
    ) -> Optional[Hypothesis]:
        """
        Create a hypothesis if it meets confidence threshold.
        
        Args:
            claim: The hypothesis claim
            confidence: Confidence score (0-1)
            linked_facts: List of fact_ids supporting this
            evidence_refs: Optional additional evidence
            reasoning: Optional chain of thought
            
        Returns:
            Hypothesis if confidence is sufficient, None otherwise
        """
        if confidence < self.min_confidence:
            logger.debug(
                f"Hypothesis rejected: confidence {confidence} < {self.min_confidence}"
            )
            return None
        
        return Hypothesis(
            agent_id=self.agent_id,
            claim=claim,
            confidence=confidence,
            linked_facts=linked_facts,
            evidence_refs=evidence_refs or [],
            reasoning=reasoning,
            status=HypothesisStatus.ACTIVE,
        )
    
    def get_relevant_facts(
        self,
        blackboard: Blackboard,
        key_prefixes: Optional[List[str]] = None,
        module: Optional[str] = None,
    ) -> List[Fact]:
        """
        Get facts relevant to this agent from the blackboard.
        
        Args:
            blackboard: The blackboard to read from
            key_prefixes: Optional list of key prefixes to filter
            module: Optional module name to filter
            
        Returns:
            List of relevant facts
        """
        facts = blackboard.get_facts(module=module)
        
        if key_prefixes:
            facts = [
                f for f in facts
                if any(f.key.startswith(prefix) for prefix in key_prefixes)
            ]
        
        return facts
    
    def get_fact_value(
        self,
        blackboard: Blackboard,
        key: str,
        default: Any = None,
    ) -> Any:
        """Get a specific fact value from the blackboard."""
        fact = blackboard.get_fact_by_key(key)
        return fact.value if fact else default
    
    def call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """
        Call the LLM with a prompt.
        
        This is the main LLM interface for agents. Uses the configured
        LLM provider (Mistral, OpenAI, etc.).
        
        Args:
            prompt: The user prompt
            system_prompt: Override default system prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens
            
        Returns:
            LLM response text or None if failed/disabled
        """
        if not self.use_llm:
            logger.debug(f"LLM disabled for agent {self.agent_id}")
            return None
        
        provider = get_llm_provider()
        if provider is None:
            logger.warning(f"No LLM provider available for {self.agent_id}")
            return None
        
        try:
            response = provider.generate(
                prompt=prompt,
                system_prompt=system_prompt or self.system_prompt,
                temperature=temperature or self.llm_temperature,
                max_tokens=max_tokens or self.llm_max_tokens,
            )
            
            if response.success:
                self._llm_calls += 1
                self._llm_tokens += response.usage.get("total_tokens", 0)
                logger.debug(
                    f"LLM call for {self.agent_id}: "
                    f"{response.usage.get('total_tokens', 0)} tokens, "
                    f"{response.latency_ms:.0f}ms"
                )
                return response.content
            else:
                logger.warning(f"LLM call failed: {response.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"LLM error for {self.agent_id}: {e}")
            return None
    
    def generate_llm_insights(
        self,
        prompt: str,
        facts: List[Fact],
        max_tokens: int = 500,
    ) -> Optional[str]:
        """
        Use LLM to generate insights from facts.
        
        Args:
            prompt: The prompt template
            facts: Facts to include in context
            max_tokens: Maximum response tokens
            
        Returns:
            LLM response or None if disabled/failed
        """
        if not self.use_llm:
            return None
        
        # Build fact context
        facts_context = "\n".join([
            f"- {f.key}: {f.value}" + (f" ({f.unit})" if f.unit else "")
            for f in facts[:20]  # Limit context size
        ])
        
        full_prompt = f"{prompt}\n\nFacts:\n{facts_context}"
        
        return self.call_llm(
            prompt=full_prompt,
            system_prompt=f"You are {self.agent_name}. {self.description}",
            max_tokens=max_tokens,
        )
    
    def generate_llm_hypothesis(
        self,
        facts: List[Fact],
        analysis_focus: str,
        context: Optional[str] = None,
    ) -> Optional[Hypothesis]:
        """
        Use LLM to generate a hypothesis from analysis.
        
        Args:
            facts: Relevant facts for analysis
            analysis_focus: What aspect to analyze
            context: Additional context
            
        Returns:
            Generated hypothesis or None
        """
        if not self.use_llm or not facts:
            return None
        
        facts_context = "\n".join([
            f"- {f.key}: {f.value}" + (f" ({f.unit})" if f.unit else "")
            for f in facts[:15]
        ])
        
        prompt = f"""Analyze the following financial data and provide a single key insight.

Focus: {analysis_focus}
{f"Context: {context}" if context else ""}

Financial Facts:
{facts_context}

Provide your analysis in exactly this format:
CLAIM: [A single, specific claim about the company's financial position]
CONFIDENCE: [A number between 0.0 and 1.0]
REASONING: [Brief explanation of your reasoning, 1-2 sentences]
"""
        
        response = self.call_llm(prompt, max_tokens=300)
        
        if not response:
            return None
        
        # Parse response
        try:
            claim = ""
            confidence = 0.6
            reasoning = ""
            
            for line in response.strip().split("\n"):
                line = line.strip()
                if line.startswith("CLAIM:"):
                    claim = line[6:].strip()
                elif line.startswith("CONFIDENCE:"):
                    try:
                        confidence = float(line[11:].strip())
                        confidence = max(0.0, min(1.0, confidence))
                    except ValueError:
                        confidence = 0.6
                elif line.startswith("REASONING:"):
                    reasoning = line[10:].strip()
            
            if claim:
                return self.generate_hypothesis(
                    claim=claim,
                    confidence=confidence,
                    linked_facts=[f.fact_id for f in facts[:5]],
                    reasoning=reasoning,
                )
        except Exception as e:
            logger.warning(f"Failed to parse LLM hypothesis: {e}")
        
        return None
    
    def generate_llm_synthesis(
        self,
        facts_summary: str,
        analysis_focus: str,
        existing_hypotheses: Optional[List[Hypothesis]] = None,
    ) -> Optional[Hypothesis]:
        """
        Generate an LLM-synthesized hypothesis based on facts.
        
        This method can be called by any agent to get LLM-enhanced insights.
        
        Args:
            facts_summary: Summary of key facts to analyze
            analysis_focus: What aspect to focus on (e.g., "debt sustainability")
            existing_hypotheses: Optional list of existing hypotheses for context
            
        Returns:
            A synthesized Hypothesis or None if LLM is disabled/failed
        """
        if not self.use_llm:
            return None
        
        # Build context from existing hypotheses
        context = ""
        if existing_hypotheses:
            claims = [h.claim[:100] for h in existing_hypotheses[:3]]
            context = f"\nExisting findings:\n" + "\n".join(f"- {c}" for c in claims)
        
        prompt = f"""As a {self.description}, analyze the following metrics and provide ONE key insight.

Focus Area: {analysis_focus}

Key Metrics:
{facts_summary}
{context}

Provide your response in this EXACT format:
CLAIM: [One specific, actionable insight]
CONFIDENCE: [0.0-1.0 as a number]
REASONING: [1-2 sentences explaining your logic]"""

        response = self.call_llm(prompt, max_tokens=300)
        
        if not response:
            return None
        
        return self._parse_llm_synthesis_response(response)
    
    def _parse_llm_synthesis_response(self, response: str) -> Optional[Hypothesis]:
        """Parse LLM synthesis response into a hypothesis."""
        try:
            claim = ""
            confidence = 0.65
            reasoning = ""
            
            for line in response.strip().split("\n"):
                line = line.strip()
                if line.upper().startswith("CLAIM:"):
                    claim = line[6:].strip()
                elif line.upper().startswith("CONFIDENCE:"):
                    try:
                        conf_str = line[11:].strip()
                        if "%" in conf_str:
                            confidence = float(conf_str.replace("%", "")) / 100
                        else:
                            confidence = float(conf_str)
                        confidence = max(0.0, min(1.0, confidence))
                    except ValueError:
                        confidence = 0.65
                elif line.upper().startswith("REASONING:"):
                    reasoning = line[10:].strip()
            
            if claim:
                return self.generate_hypothesis(
                    claim=claim,
                    confidence=confidence,
                    linked_facts=[],
                    reasoning=f"[LLM] {reasoning}" if reasoning else "[LLM-generated]",
                )
        except Exception as e:
            logger.warning(f"Failed to parse LLM synthesis: {e}")
        
        return None
    
    def assess_confidence(
        self,
        base_confidence: float,
        data_quality: float,
        evidence_strength: float,
    ) -> float:
        """
        Calculate adjusted confidence based on multiple factors.
        
        Args:
            base_confidence: Initial confidence (0-1)
            data_quality: Data quality score (0-1)
            evidence_strength: Strength of supporting evidence (0-1)
            
        Returns:
            Adjusted confidence (0-1)
        """
        # Weighted average with emphasis on data quality
        weights = [0.4, 0.35, 0.25]
        factors = [base_confidence, data_quality, evidence_strength]
        
        confidence = sum(w * f for w, f in zip(weights, factors))
        return min(1.0, max(0.0, confidence))
    
    def log_execution(
        self,
        success: bool,
        hypotheses_count: int,
        execution_time_ms: float,
        error: Optional[str] = None,
    ) -> None:
        """Log agent execution for monitoring."""
        if success:
            logger.info(
                f"Agent {self.agent_id} executed: {hypotheses_count} hypotheses "
                f"in {execution_time_ms:.0f}ms "
                f"(LLM: {self._llm_calls} calls, {self._llm_tokens} tokens)"
            )
        else:
            logger.error(
                f"Agent {self.agent_id} failed: {error} "
                f"(after {execution_time_ms:.0f}ms)"
            )
    
    def get_llm_usage(self) -> Dict[str, int]:
        """Get LLM usage statistics for this agent."""
        return {
            "calls": self._llm_calls,
            "tokens": self._llm_tokens,
        }
    
    def reset_llm_usage(self) -> None:
        """Reset LLM usage counters."""
        self._llm_calls = 0
        self._llm_tokens = 0

