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
- LLM integration
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from src.app.blackboard.models import Hypothesis, Fact, HypothesisStatus
from src.app.blackboard.store import Blackboard
from src.app.config import get_llm_client, OPENAI_MODEL

logger = logging.getLogger(__name__)


class AgentOutput(BaseModel):
    """Standard output from an agent execution."""
    agent_id: str
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    facts_used: List[str] = Field(default_factory=list)
    execution_time_ms: float = 0
    success: bool = True
    error_message: Optional[str] = None


class BaseMeshAgent(ABC):
    """
    Abstract base class for all agents in the agentic mesh.
    
    Key features:
    - Hypothesis budget: Limits hypothesis generation
    - Minimum confidence: Filters low-confidence outputs
    - Blackboard integration: Read/write with ACL
    - LLM integration: Optional narrative generation
    """
    
    # Agent identity
    agent_id: str = "base_agent"
    agent_name: str = "Base Agent"
    description: str = "Base mesh agent"
    
    # Constraints
    hypothesis_budget: int = 5  # Max hypotheses per execution
    min_confidence: float = 0.4  # Minimum confidence to output
    
    # LLM settings
    use_llm: bool = True
    llm_model: str = OPENAI_MODEL
    llm_temperature: float = 0.7
    
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
        
        try:
            client = get_llm_client()
            
            # Build fact context
            facts_context = "\n".join([
                f"- {f.key}: {f.value}" + (f" ({f.unit})" if f.unit else "")
                for f in facts[:20]  # Limit context size
            ])
            
            full_prompt = f"{prompt}\n\nFacts:\n{facts_context}"
            
            response = client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": f"You are {self.agent_name}. {self.description}"},
                    {"role": "user", "content": full_prompt},
                ],
                temperature=self.llm_temperature,
                max_tokens=max_tokens,
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.warning(f"LLM call failed for {self.agent_id}: {e}")
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
                f"in {execution_time_ms:.0f}ms"
            )
        else:
            logger.error(
                f"Agent {self.agent_id} failed: {error} "
                f"(after {execution_time_ms:.0f}ms)"
            )
