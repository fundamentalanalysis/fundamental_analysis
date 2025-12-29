# =============================================================
# src/app/mesh/benchmarking_agent.py
# Benchmarking Agent - Industry-Relative Thresholds
# Layer C - Agentic Mesh
# =============================================================
"""
Benchmarking Agent retrieves/loads industry medians and builds threshold profiles.

Key responsibilities:
- Load industry-specific benchmarks
- Build threshold profiles for evaluation
- Use LLM to generate dynamic thresholds for unknown industries
- Apply fallback logic for missing benchmarks
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import time
import logging
import json
import re

from .base_agent import BaseMeshAgent, AgentOutput
from src.app.blackboard.models import Hypothesis, Fact
from src.app.blackboard.store import Blackboard
from src.app.llm.factory import get_default_provider
from src.app.llm.provider import Message

logger = logging.getLogger(__name__)


class ThresholdProfile(BaseModel):
    """Industry-specific threshold profile."""
    industry_code: str
    industry_name: str
    
    # Leverage thresholds
    de_ratio_ok: float = 1.0
    de_ratio_warning: float = 1.5
    debt_ebitda_ok: float = 3.0
    debt_ebitda_warning: float = 4.0
    interest_coverage_ok: float = 3.0
    interest_coverage_warning: float = 1.5
    
    # Profitability thresholds
    roe_good: float = 0.15
    roe_acceptable: float = 0.10
    
    # Liquidity thresholds
    current_ratio_safe: float = 1.5
    current_ratio_warning: float = 1.0
    
    # QoE thresholds
    qoe_good: float = 1.0
    qoe_warning: float = 0.5
    
    # Fallback flags
    is_fallback: bool = False
    fallback_reason: Optional[str] = None
    is_llm_generated: bool = False


# Default industry benchmarks
DEFAULT_BENCHMARKS: Dict[str, ThresholdProfile] = {
    "manufacturing": ThresholdProfile(
        industry_code="manufacturing",
        industry_name="Manufacturing",
        de_ratio_ok=0.8,
        de_ratio_warning=1.5,
        current_ratio_safe=1.5,
    ),
    "it_services": ThresholdProfile(
        industry_code="it_services",
        industry_name="IT Services",
        de_ratio_ok=0.3,
        de_ratio_warning=0.7,
        roe_good=0.20,
        current_ratio_safe=2.0,
    ),
    "banking": ThresholdProfile(
        industry_code="banking",
        industry_name="Banking & Financial Services",
        de_ratio_ok=8.0,  # Banks have high leverage by nature
        de_ratio_warning=12.0,
        roe_good=0.12,
    ),
    "utilities": ThresholdProfile(
        industry_code="utilities",
        industry_name="Utilities",
        de_ratio_ok=1.5,
        de_ratio_warning=2.5,
        interest_coverage_ok=2.5,
    ),
    "retail": ThresholdProfile(
        industry_code="retail",
        industry_name="Retail & Consumer",
        de_ratio_ok=0.7,
        de_ratio_warning=1.2,
        current_ratio_safe=1.2,
    ),
    "default": ThresholdProfile(
        industry_code="default",
        industry_name="Default (Cross-Industry)",
        is_fallback=True,
        fallback_reason="No industry-specific benchmark available",
    ),
}


class BenchmarkingAgent(BaseMeshAgent):
    """
    Retrieves and manages industry-relative threshold profiles.
    
    Key features:
    - Industry-specific benchmarks
    - LLM-powered dynamic threshold generation for unknown industries
    - Fallback logic for missing data
    - Dynamic threshold adjustment
    """
    
    agent_id = "benchmarking_agent"
    agent_name = "Benchmarking Agent"
    description = "Retrieves industry medians and builds threshold profiles using LLM for unknown industries"
    hypothesis_budget = 3
    use_llm = True
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.benchmarks = DEFAULT_BENCHMARKS.copy()
        
        if config and "use_llm" in config:
            self.use_llm = config["use_llm"]
        
        # Initialize LLM provider for dynamic benchmark generation
        self._llm_provider = None
        if self.use_llm:
            try:
                self._llm_provider = get_default_provider()
                logger.info(f"[Benchmarking] Using LLM provider: {self._llm_provider.provider_type.value}")
            except Exception as e:
                logger.warning(f"[Benchmarking] Failed to initialize LLM provider: {e}")
                self._llm_provider = None
    
    def execute(self, blackboard: Blackboard) -> AgentOutput:
        """Get benchmark profile and write relevant facts."""
        start_time = time.time()
        hypotheses = []
        facts_used = []
        
        try:
            # Get industry code from blackboard or use default
            industry_code = self.get_fact_value(blackboard, "industry_code", "default")
            
            # Get threshold profile
            profile = self.get_threshold_profile(industry_code)
            
            # Write benchmark facts to blackboard
            benchmark_facts = self._create_benchmark_facts(profile)
            for fact in benchmark_facts:
                blackboard.write_fact(fact, self.agent_id)
                facts_used.append(fact.fact_id)
            
            # Generate hypotheses about benchmark context
            if profile.is_fallback:
                hyp = self.generate_hypothesis(
                    claim=f"Using default industry benchmarks as no specific profile available "
                          f"for '{industry_code}'. Thresholds may not be optimally calibrated.",
                    confidence=0.60,
                    linked_facts=facts_used,
                    reasoning=profile.fallback_reason,
                )
                if hyp:
                    hypotheses.append(hyp)
            else:
                hyp = self.generate_hypothesis(
                    claim=f"Industry-specific benchmarks applied for {profile.industry_name}. "
                          f"Thresholds are calibrated for sector characteristics.",
                    confidence=0.80,
                    linked_facts=facts_used,
                )
                if hyp:
                    hypotheses.append(hyp)
            
            execution_time = (time.time() - start_time) * 1000
            self.log_execution(True, len(hypotheses), execution_time)
            
            return AgentOutput(
                agent_id=self.agent_id,
                hypotheses=hypotheses,
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
    
    def get_threshold_profile(self, industry_code: str) -> ThresholdProfile:
        """
        Get threshold profile for an industry.
        
        Applies fallback logic:
        1. Exact match
        2. Sector proxy (if defined)
        3. LLM-generated thresholds (if LLM available)
        4. Default conservative thresholds
        """
        # Normalize code
        code = industry_code.lower().replace(" ", "_").replace("-", "_")
        
        # Exact match (but skip if it's the fallback default)
        if code in self.benchmarks:
            profile = self.benchmarks[code]
            # For default with LLM available, try to generate better thresholds
            if code == "default" and self._llm_provider and not profile.is_llm_generated:
                logger.info("[Benchmarking] Generating LLM thresholds for general/cross-industry analysis")
                llm_profile = self._generate_llm_thresholds("cross-industry/general")
                if llm_profile:
                    return llm_profile
            return profile
        
        # Try partial match
        for key, profile in self.benchmarks.items():
            if key != "default" and (key in code or code in key):
                logger.info(f"Using partial match '{key}' for industry '{industry_code}'")
                return profile
        
        # Try LLM-generated thresholds for unknown industry
        if self._llm_provider:
            logger.info(f"[Benchmarking] Generating LLM thresholds for industry: {industry_code}")
            llm_profile = self._generate_llm_thresholds(industry_code)
            if llm_profile:
                # Cache the generated profile
                self.benchmarks[code] = llm_profile
                return llm_profile
        
        # Fallback to default
        logger.warning(f"No benchmark found for '{industry_code}', using default")
        return self.benchmarks["default"]
    
    def _generate_llm_thresholds(self, industry_code: str) -> Optional[ThresholdProfile]:
        """
        Use LLM to generate industry-appropriate threshold values.
        
        Returns:
            ThresholdProfile with LLM-generated thresholds, or None if generation fails
        """
        if not self._llm_provider:
            return None
        
        system_prompt = """You are a financial analyst expert. Generate appropriate financial ratio thresholds for company analysis based on the given industry.

Consider industry-specific characteristics:
- Capital-intensive industries typically have higher acceptable D/E ratios
- Asset-light/tech industries should have lower leverage thresholds
- Financial services have naturally high leverage (regulated differently)
- Growth industries may have lower profitability expectations but higher growth

Output ONLY valid JSON with these fields:
{
  "industry_name": "Human readable industry name",
  "de_ratio_ok": 1.0,  // D/E ratio below this is healthy
  "de_ratio_warning": 1.5,  // D/E ratio above this is concerning
  "debt_ebitda_ok": 3.0,  // Debt/EBITDA below this is healthy
  "debt_ebitda_warning": 4.0,  // Debt/EBITDA above this is concerning
  "interest_coverage_ok": 3.0,  // Interest coverage above this is healthy
  "interest_coverage_warning": 1.5,  // Interest coverage below this is concerning
  "roe_good": 0.15,  // ROE above this is good (as decimal)
  "roe_acceptable": 0.10,  // ROE above this is acceptable (as decimal)
  "current_ratio_safe": 1.5,  // Current ratio above this is safe
  "current_ratio_warning": 1.0,  // Current ratio below this is warning
  "qoe_good": 1.0,  // Quality of earnings (CFO/NI) above this is good
  "qoe_warning": 0.5  // Quality of earnings below this is warning
}"""

        user_prompt = f"""Generate appropriate financial ratio thresholds for the industry: "{industry_code}"

Consider what makes sense for this specific industry. Be precise with the values based on industry norms.
Output JSON only."""

        try:
            messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt),
            ]
            
            response = self._llm_provider.complete(
                messages=messages,
                temperature=0.3,
                max_tokens=500,
            )
            
            if not response.success:
                logger.warning(f"[Benchmarking] LLM threshold generation failed: {response.error_message}")
                return None
            
            # Track LLM usage
            self._llm_calls += 1
            self._llm_tokens += response.usage.get("total_tokens", 0)
            
            # Parse JSON response
            content = response.content.strip()
            
            # Remove markdown code fences if present
            if "```json" in content:
                content = content.split("```json")[-1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Extract JSON object (handle nested braces)
            brace_count = 0
            start_idx = content.find('{')
            if start_idx != -1:
                for i, char in enumerate(content[start_idx:], start_idx):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            content = content[start_idx:i+1]
                            break
            
            thresholds = json.loads(content)
            
            profile = ThresholdProfile(
                industry_code=industry_code.lower().replace(" ", "_"),
                industry_name=thresholds.get("industry_name", industry_code.replace("_", " ").title()),
                de_ratio_ok=float(thresholds.get("de_ratio_ok", 1.0)),
                de_ratio_warning=float(thresholds.get("de_ratio_warning", 1.5)),
                debt_ebitda_ok=float(thresholds.get("debt_ebitda_ok", 3.0)),
                debt_ebitda_warning=float(thresholds.get("debt_ebitda_warning", 4.0)),
                interest_coverage_ok=float(thresholds.get("interest_coverage_ok", 3.0)),
                interest_coverage_warning=float(thresholds.get("interest_coverage_warning", 1.5)),
                roe_good=float(thresholds.get("roe_good", 0.15)),
                roe_acceptable=float(thresholds.get("roe_acceptable", 0.10)),
                current_ratio_safe=float(thresholds.get("current_ratio_safe", 1.5)),
                current_ratio_warning=float(thresholds.get("current_ratio_warning", 1.0)),
                qoe_good=float(thresholds.get("qoe_good", 1.0)),
                qoe_warning=float(thresholds.get("qoe_warning", 0.5)),
                is_llm_generated=True,
            )
            
            logger.info(f"[Benchmarking] LLM generated thresholds for {industry_code}: D/E OK={profile.de_ratio_ok}, ROE good={profile.roe_good}")
            return profile
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[Benchmarking] Failed to parse LLM threshold response: {e}")
            return None
        except Exception as e:
            logger.warning(f"[Benchmarking] LLM threshold generation error: {e}")
            return None
    
    def _create_benchmark_facts(self, profile: ThresholdProfile) -> List[Fact]:
        """Create facts from threshold profile."""
        facts = []
        
        # Create a fact for each threshold
        threshold_mappings = [
            ("benchmark_de_ratio_ok", profile.de_ratio_ok),
            ("benchmark_de_ratio_warning", profile.de_ratio_warning),
            ("benchmark_debt_ebitda_ok", profile.debt_ebitda_ok),
            ("benchmark_roe_good", profile.roe_good),
            ("benchmark_current_ratio_safe", profile.current_ratio_safe),
            ("benchmark_qoe_good", profile.qoe_good),
        ]
        
        for key, value in threshold_mappings:
            facts.append(Fact(
                key=key,
                value=value,
                source_engine="benchmarking_agent",
                metadata={
                    "industry_code": profile.industry_code,
                    "is_fallback": profile.is_fallback,
                    "is_llm_generated": profile.is_llm_generated,
                },
            ))
        
        return facts
    
    def add_custom_benchmark(self, industry_code: str, profile: ThresholdProfile) -> None:
        """Add or update a custom industry benchmark."""
        self.benchmarks[industry_code.lower()] = profile
        logger.info(f"Added custom benchmark for {industry_code}")
