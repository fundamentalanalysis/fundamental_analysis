# =============================================================
# src/app/mesh/orchestrator.py
# Mesh Orchestrator - LangGraph-based Mesh Execution
# Layer D - Orchestration & Policy Control Plane
# =============================================================
"""
The Mesh Orchestrator runs the complete Level-5 Agentic Mesh workflow.

Execution stages:
1. Deterministic load (Data Quality, Metrics, Trends)
2. Benchmarking (Industry thresholds)
3. Parallel analyst hypotheses
4. Adversarial debate loop (Critic, Mediator)
5. Correlation overrides
6. Judge synthesis

Uses LangGraph for state management and workflow execution.
"""

from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime
from operator import add
import time
import logging
import asyncio

try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None

from src.app.blackboard.store import Blackboard
from src.app.blackboard.models import FinalDecision, ConsensusState

from src.app.engines.metric_engine import MetricEngine
from src.app.engines.trend_engine import TrendEngine
from src.app.engines.data_quality_engine import DataQualityEngine
from src.app.engines.correlation_engine import CorrelationEngine

from src.app.mesh.analyst_agents import (
    DebtAnalystAgent,
    LiquidityAnalystAgent,
    AssetQualityAnalystAgent,
    QoEAnalystAgent,
    WorkingCapitalAnalystAgent,
    EquityAnalystAgent,
)
from src.app.mesh.benchmarking_agent import BenchmarkingAgent
from src.app.mesh.critic_agent import ShortSellerCriticAgent
from src.app.mesh.mediator_agent import MediatorAgent
from src.app.mesh.judge_agent import JudgeAgent

from src.app.policies.debate_policy import DebateTerminationPolicy, DebateMetrics
from src.app.policies.consensus_policy import ConsensusScoringPolicy
from src.app.policies.review_policy import ManualReviewPolicy

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State Definition
# ---------------------------------------------------------------------------

class MeshState(TypedDict):
    """State for the mesh workflow."""
    # Input
    company: str
    year: int
    industry_code: str
    current_data: Dict[str, Any]
    historical_data: List[Dict[str, Any]]
    
    # Blackboard
    blackboard: Blackboard
    
    # Stage tracking
    current_stage: str
    stages_completed: Annotated[List[str], add]
    
    # Debate tracking
    debate_round: int
    should_continue_debate: bool
    
    # Output
    final_decision: Optional[FinalDecision]
    
    # Execution metadata
    errors: Annotated[List[str], add]
    execution_times: Dict[str, float]


# ---------------------------------------------------------------------------
# Mesh Orchestrator
# ---------------------------------------------------------------------------

class MeshOrchestrator:
    """
    Orchestrates the Level-5 Agentic Mesh workflow.
    
    Key features:
    - LangGraph-based state management
    - Policy-driven debate control
    - Full audit trail via Blackboard
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the orchestrator.
        
        Args:
            config: Optional configuration overrides
        """
        self.config = config or {}
        
        # Initialize engines
        self.metric_engine = MetricEngine()
        self.trend_engine = TrendEngine()
        self.data_quality_engine = DataQualityEngine()
        self.correlation_engine = CorrelationEngine()
        
        # Initialize agents
        self.analyst_agents = [
            DebtAnalystAgent(self.config.get("debt_analyst")),
            LiquidityAnalystAgent(self.config.get("liquidity_analyst")),
            AssetQualityAnalystAgent(self.config.get("asset_quality_analyst")),
            QoEAnalystAgent(self.config.get("qoe_analyst")),
            WorkingCapitalAnalystAgent(self.config.get("working_capital_analyst")),
            EquityAnalystAgent(self.config.get("equity_analyst")),
        ]
        
        self.benchmarking_agent = BenchmarkingAgent(self.config.get("benchmarking"))
        self.critic_agent = ShortSellerCriticAgent(self.config.get("critic"))
        self.mediator_agent = MediatorAgent(self.config.get("mediator"))
        self.judge_agent = JudgeAgent(self.config.get("judge"))
        
        # Initialize policies
        debate_config = self.config.get("debate", {})
        self.debate_policy = DebateTerminationPolicy(
            max_rounds=debate_config.get("max_rounds", 5),
            max_time_seconds=debate_config.get("max_time_seconds", 60),
            stagnation_threshold=debate_config.get("stagnation_threshold", 0.05),
            convergence_threshold=debate_config.get("convergence_threshold", 0.8),
        )
        
        consensus_config = self.config.get("consensus", {})
        self.consensus_policy = ConsensusScoringPolicy(
            high_convergence_threshold=consensus_config.get("high_convergence", 0.9),
            medium_convergence_threshold=consensus_config.get("medium_convergence", 0.6),
        )
        
        review_config = self.config.get("review", {})
        self.review_policy = ManualReviewPolicy(
            disagreement_gap_threshold=review_config.get("disagreement_gap", 0.3),
            missing_benchmark_threshold=review_config.get("missing_benchmark", 0.2),
            low_data_quality_threshold=review_config.get("low_data_quality", 0.5),
        )
        
        # Build workflow graph
        self.graph = self._build_graph() if LANGGRAPH_AVAILABLE else None
        self.checkpointer = MemorySaver() if LANGGRAPH_AVAILABLE else None
    
    def run(
        self,
        company: str,
        current_data: Dict[str, Any],
        historical_data: Optional[List[Dict[str, Any]]] = None,
        year: Optional[int] = None,
        industry_code: str = "default",
    ) -> FinalDecision:
        """
        Run the complete mesh workflow synchronously.
        
        Args:
            company: Company identifier
            current_data: Current period financial data
            historical_data: Historical data for trend analysis
            year: Financial year
            industry_code: Industry for benchmarking
            
        Returns:
            FinalDecision with score, thesis, and audit trail
        """
        # Always use sequential execution because Blackboard is not serializable
        # and LangGraph's checkpointer requires msgpack-serializable state
        return self._run_sequential(
            company, current_data, historical_data, year, industry_code
        )
    
    async def arun(
        self,
        company: str,
        current_data: Dict[str, Any],
        historical_data: Optional[List[Dict[str, Any]]] = None,
        year: Optional[int] = None,
        industry_code: str = "default",
    ) -> FinalDecision:
        """Async version of run."""
        # For now, run synchronously in executor
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.run(company, current_data, historical_data, year, industry_code)
        )
    
    def _run_sequential(
        self,
        company: str,
        current_data: Dict[str, Any],
        historical_data: Optional[List[Dict[str, Any]]],
        year: Optional[int],
        industry_code: str,
    ) -> FinalDecision:
        """Run workflow without LangGraph (sequential execution)."""
        start_time = time.time()
        execution_times = {}
        
        logger.info(f"\n{'='*60}")
        logger.info(f"MESH ANALYSIS STARTED: {company} ({year})")
        logger.info(f"{'='*60}")
        
        # Initialize blackboard
        blackboard = Blackboard()
        blackboard.initialize(company, year or datetime.now().year)
        
        # Stage 1: Data Quality
        stage_start = time.time()
        report = self.data_quality_engine.assess_quality(current_data)
        blackboard.write_data_quality_report(report, "data_quality_engine")
        execution_times["data_quality"] = time.time() - stage_start
        logger.info(f"Stage 1 (Data Quality) complete: score={report.quality_score:.2f}")
        
        # Stage 2: Metrics
        stage_start = time.time()
        metric_facts = self.metric_engine.compute_metrics(
            current_data, year=year, prev_data=historical_data[-1] if historical_data else None
        )
        for fact in metric_facts:
            blackboard.write_fact(fact, "metric_engine")
        execution_times["metrics"] = time.time() - stage_start
        logger.info(f"Stage 2 (Metrics) complete: {len(metric_facts)} facts computed")
        
        # Stage 3: Trends
        stage_start = time.time()
        if historical_data and len(historical_data) >= 2:
            trend_facts = self.trend_engine.compute_trends(historical_data)
            for fact in trend_facts:
                blackboard.write_fact(fact, "trend_engine")
            logger.info(f"Stage 3 (Trends) complete: {len(trend_facts)} trend facts")
        execution_times["trends"] = time.time() - stage_start
        
        # Stage 4: Benchmarking
        stage_start = time.time()
        self.benchmarking_agent.execute(blackboard)
        execution_times["benchmarking"] = time.time() - stage_start
        
        # Stage 5: Analyst Hypotheses
        stage_start = time.time()
        total_llm_calls = 0
        total_llm_tokens = 0
        logger.info(f"\n--- Stage 5: Analyst Agents ---")
        for agent in self.analyst_agents:
            output = agent.execute(blackboard)
            for hyp in output.hypotheses:
                blackboard.write_hypothesis(hyp, agent.agent_id)
            # Track LLM usage
            if hasattr(agent, '_llm_calls'):
                total_llm_calls += agent._llm_calls
                total_llm_tokens += agent._llm_tokens
            logger.info(f"  {agent.agent_id}: {len(output.hypotheses)} hypotheses (LLM: {getattr(agent, '_llm_calls', 0)} calls)")
        execution_times["analysts"] = time.time() - stage_start
        logger.info(f"Stage 5 complete: {blackboard.get_active_hypothesis_count()} hypotheses, {total_llm_calls} LLM calls, {total_llm_tokens} tokens")
        
        # Stage 6: Adversarial Debate Loop
        stage_start = time.time()
        logger.info(f"\n--- Stage 6: Adversarial Debate ---")
        self.debate_policy.start_debate()
        debate_round = 0
        
        while True:
            debate_round += 1
            logger.info(f"\n  [Round {debate_round}]")
            
            # Critic attacks
            critic_output = self.critic_agent.execute(blackboard)
            attacks_count = len(blackboard.get_attacks()) if hasattr(blackboard, 'get_attacks') else 0
            logger.info(f"    Critic: generated attacks (total: {attacks_count})")
            if hasattr(self.critic_agent, '_llm_calls'):
                logger.info(f"    Critic LLM: {self.critic_agent._llm_calls} calls, {self.critic_agent._llm_tokens} tokens")
            
            # Mediator resolves
            mediator_output = self.mediator_agent.execute(blackboard)
            resolutions_count = len(blackboard.get_resolutions()) if hasattr(blackboard, 'get_resolutions') else 0
            logger.info(f"    Mediator: proposed resolutions (total: {resolutions_count})")
            if hasattr(self.mediator_agent, '_llm_calls'):
                logger.info(f"    Mediator LLM: {self.mediator_agent._llm_calls} calls, {self.mediator_agent._llm_tokens} tokens")
            
            # Check termination
            metrics = DebateMetrics(
                round=blackboard.get_debate_round(),
                elapsed_seconds=self.debate_policy.get_elapsed_seconds(),
                convergence_score=blackboard.get_convergence_score(),
                hypotheses_active=blackboard.get_active_hypothesis_count(),
            )
            
            logger.info(f"    Convergence: {metrics.convergence_score:.2f}, Active hypotheses: {metrics.hypotheses_active}")
            
            if self.debate_policy.should_terminate(metrics):
                reason = self.debate_policy.get_termination_reason(metrics)
                logger.info(f"  Debate terminated after {debate_round} rounds: {reason}")
                break
        
        execution_times["debate"] = time.time() - stage_start
        
        # Stage 7: Correlation Overrides
        stage_start = time.time()
        logger.info(f"\n--- Stage 7: Correlation Engine ---")
        overrides = self.correlation_engine.apply_overrides(blackboard)
        for ovr in overrides:
            desc = ovr.description[:60] if ovr.description else ovr.rule_name
            logger.info(f"  Override: {ovr.rule_id} ({ovr.action}) - {desc}...")
        execution_times["correlation"] = time.time() - stage_start
        logger.info(f"Stage 7 complete: {len(overrides)} overrides applied")
        
        # Stage 8: Judge Synthesis
        stage_start = time.time()
        logger.info(f"\n--- Stage 8: Judge Synthesis ---")
        self.judge_agent.execute(blackboard)
        if hasattr(self.judge_agent, '_llm_calls'):
            logger.info(f"  Judge LLM: {self.judge_agent._llm_calls} calls, {self.judge_agent._llm_tokens} tokens")
        execution_times["judge"] = time.time() - stage_start
        
        final_decision = blackboard.get_final()
        
        # Check manual review
        if self.review_policy.requires_review(blackboard):
            _, reasons = self.review_policy.check_review_triggers(blackboard)
            if final_decision:
                final_decision = final_decision.model_copy(update={
                    "manual_review_required": True,
                    "review_reasons": reasons,
                })
        
        total_time = time.time() - start_time
        logger.info(f"Mesh workflow complete in {total_time:.2f}s")
        
        return final_decision
    
    def _run_with_langgraph(
        self,
        company: str,
        current_data: Dict[str, Any],
        historical_data: Optional[List[Dict[str, Any]]],
        year: Optional[int],
        industry_code: str,
    ) -> FinalDecision:
        """Run workflow using LangGraph."""
        # Build initial state
        blackboard = Blackboard()
        blackboard.initialize(company, year or datetime.now().year)
        
        initial_state = MeshState(
            company=company,
            year=year or datetime.now().year,
            industry_code=industry_code,
            current_data=current_data,
            historical_data=historical_data or [],
            blackboard=blackboard,
            current_stage="init",
            stages_completed=[],
            debate_round=0,
            should_continue_debate=True,
            final_decision=None,
            errors=[],
            execution_times={},
        )
        
        # Run graph
        app = self.graph.compile(checkpointer=self.checkpointer)
        config = {"configurable": {"thread_id": f"{company}_{year}"}}
        
        result = app.invoke(initial_state, config)
        return result["final_decision"]
    
    def _build_graph(self):
        """Build the LangGraph workflow."""
        if not LANGGRAPH_AVAILABLE:
            return None
        
        # Define nodes
        def data_quality_node(state: MeshState) -> MeshState:
            report = self.data_quality_engine.assess_quality(state["current_data"])
            state["blackboard"].write_data_quality_report(report, "data_quality_engine")
            return {
                **state,
                "current_stage": "data_quality",
                "stages_completed": ["data_quality"],
            }
        
        def metrics_node(state: MeshState) -> MeshState:
            facts = self.metric_engine.compute_metrics(
                state["current_data"], 
                year=state["year"]
            )
            for fact in facts:
                state["blackboard"].write_fact(fact, "metric_engine")
            return {
                **state,
                "current_stage": "metrics",
                "stages_completed": ["metrics"],
            }
        
        def trends_node(state: MeshState) -> MeshState:
            if state["historical_data"] and len(state["historical_data"]) >= 2:
                facts = self.trend_engine.compute_trends(state["historical_data"])
                for fact in facts:
                    state["blackboard"].write_fact(fact, "trend_engine")
            return {
                **state,
                "current_stage": "trends",
                "stages_completed": ["trends"],
            }
        
        def benchmarking_node(state: MeshState) -> MeshState:
            self.benchmarking_agent.execute(state["blackboard"])
            return {
                **state,
                "current_stage": "benchmarking",
                "stages_completed": ["benchmarking"],
            }
        
        def analysts_node(state: MeshState) -> MeshState:
            for agent in self.analyst_agents:
                output = agent.execute(state["blackboard"])
                for hyp in output.hypotheses:
                    state["blackboard"].write_hypothesis(hyp, agent.agent_id)
            return {
                **state,
                "current_stage": "analysts",
                "stages_completed": ["analysts"],
            }
        
        def critic_node(state: MeshState) -> MeshState:
            self.critic_agent.execute(state["blackboard"])
            return {
                **state,
                "current_stage": "critic",
                "stages_completed": ["critic"],
            }
        
        def mediator_node(state: MeshState) -> MeshState:
            self.mediator_agent.execute(state["blackboard"])
            
            # Check if debate should continue
            metrics = DebateMetrics(
                round=state["blackboard"].get_debate_round(),
                convergence_score=state["blackboard"].get_convergence_score(),
            )
            should_continue = not self.debate_policy.should_terminate(metrics)
            
            return {
                **state,
                "current_stage": "mediator",
                "stages_completed": ["mediator"],
                "debate_round": state["debate_round"] + 1,
                "should_continue_debate": should_continue,
            }
        
        def correlation_node(state: MeshState) -> MeshState:
            self.correlation_engine.apply_overrides(state["blackboard"])
            return {
                **state,
                "current_stage": "correlation",
                "stages_completed": ["correlation"],
            }
        
        def judge_node(state: MeshState) -> MeshState:
            self.judge_agent.execute(state["blackboard"])
            final = state["blackboard"].get_final()
            
            # Check manual review
            if self.review_policy.requires_review(state["blackboard"]):
                _, reasons = self.review_policy.check_review_triggers(state["blackboard"])
                if final:
                    final = final.model_copy(update={
                        "manual_review_required": True,
                        "review_reasons": reasons,
                    })
            
            return {
                **state,
                "current_stage": "complete",
                "stages_completed": ["judge"],
                "final_decision": final,
            }
        
        # Routing function for debate loop
        def should_continue_debate(state: MeshState) -> str:
            if state["should_continue_debate"]:
                return "continue"
            return "end_debate"
        
        # Build graph
        builder = StateGraph(MeshState)
        
        # Add nodes
        builder.add_node("data_quality", data_quality_node)
        builder.add_node("metrics", metrics_node)
        builder.add_node("trends", trends_node)
        builder.add_node("benchmarking", benchmarking_node)
        builder.add_node("analysts", analysts_node)
        builder.add_node("critic", critic_node)
        builder.add_node("mediator", mediator_node)
        builder.add_node("correlation", correlation_node)
        builder.add_node("judge", judge_node)
        
        # Add edges (main flow)
        builder.set_entry_point("data_quality")
        builder.add_edge("data_quality", "metrics")
        builder.add_edge("metrics", "trends")
        builder.add_edge("trends", "benchmarking")
        builder.add_edge("benchmarking", "analysts")
        builder.add_edge("analysts", "critic")
        builder.add_edge("critic", "mediator")
        
        # Debate loop
        builder.add_conditional_edges(
            "mediator",
            should_continue_debate,
            {
                "continue": "critic",
                "end_debate": "correlation",
            }
        )
        
        builder.add_edge("correlation", "judge")
        builder.add_edge("judge", END)
        
        return builder
    
    def get_workflow_diagram(self) -> str:
        """Get a text representation of the workflow."""
        return """
Level-5 Agentic Mesh Workflow
=============================

    ┌─────────────────┐
    │  Data Quality   │  Stage 1
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Metric Engine   │  Stage 2
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Trend Engine    │  Stage 3
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │  Benchmarking   │  Stage 4
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Analyst Agents  │  Stage 5
    │ (6 in parallel) │
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │  Short-Seller   │◄───┐
    │    Critic       │    │
    └────────┬────────┘    │ Debate
             │             │  Loop
    ┌────────▼────────┐    │
    │   Mediator      │────┘  Stage 6
    └────────┬────────┘
             │ (until convergence)
    ┌────────▼────────┐
    │  Correlation    │  Stage 7
    │    Engine       │
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │     Judge       │  Stage 8
    │ (Final Output)  │
    └─────────────────┘
"""
    
    def get_mermaid_diagram(self) -> str:
        """Get a Mermaid diagram representation of the mesh workflow."""
        return """```mermaid
flowchart TD
    subgraph "Layer A: Deterministic Truth Surface"
        DQ[🔍 Data Quality Engine]
        ME[📊 Metric Engine]
        TE[📈 Trend Engine]
        CE[🔗 Correlation Engine]
    end
    
    subgraph "Layer B: Blackboard"
        BB[(📋 Blackboard<br/>Facts, Hypotheses, Attacks)]
    end
    
    subgraph "Layer C: Agentic Mesh"
        BM[🏭 Benchmarking Agent]
        
        subgraph "Analyst Agents"
            DA[💰 Debt Analyst]
            LA[💧 Liquidity Analyst]
            AQ[🏢 Asset Quality]
            QE[📝 QoE Analyst]
            WC[🔄 Working Capital]
            EA[📈 Equity Analyst]
        end
        
        CR[🐻 Short-Seller Critic]
        MD[⚖️ Mediator]
        JD[👨‍⚖️ Judge]
    end
    
    subgraph "Layer D: Orchestration"
        OR[🎯 Mesh Orchestrator]
        DP[📜 Debate Policy]
        CP[🤝 Consensus Policy]
        RP[👁️ Review Policy]
    end
    
    %% Flow
    DQ --> BB
    ME --> BB
    TE --> BB
    
    BB --> BM
    BB --> DA & LA & AQ & QE & WC & EA
    
    DA & LA & AQ & QE & WC & EA --> BB
    
    BB --> CR
    CR --> BB
    
    BB --> MD
    MD --> BB
    
    MD -->|continue| CR
    MD -->|converged| CE
    
    CE --> BB
    BB --> JD
    JD --> |Final Decision| Output[📊 Score + Thesis]
    
    OR -.->|controls| DP & CP & RP
    DP & CP & RP -.->|policies| MD
    
    style BB fill:#f9f,stroke:#333,stroke-width:2px
    style JD fill:#ff9,stroke:#333,stroke-width:2px
    style Output fill:#9f9,stroke:#333,stroke-width:2px
```"""
    
    def save_workflow_diagram(self, output_dir: str = "graphs") -> Dict[str, str]:
        """
        Save the mesh workflow diagram as PNG and Mermaid markdown.
        
        Args:
            output_dir: Directory to save diagrams (default: graphs/)
            
        Returns:
            Dict with paths to saved files
        """
        import os
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        saved_files = {}
        
        # Save Mermaid markdown
        mermaid_path = os.path.join(output_dir, "mesh_workflow.md")
        with open(mermaid_path, "w", encoding="utf-8") as f:
            f.write("# Level-5 Agentic Mesh Workflow\n\n")
            f.write(self.get_mermaid_diagram())
            f.write("\n\n## Stages\n\n")
            f.write("1. **Data Quality**: Assess input data quality\n")
            f.write("2. **Metrics**: Compute financial ratios and metrics\n")
            f.write("3. **Trends**: Calculate CAGR, YoY growth, patterns\n")
            f.write("4. **Benchmarking**: Compare against industry thresholds\n")
            f.write("5. **Analyst Hypotheses**: 6 specialist analysts generate claims\n")
            f.write("6. **Adversarial Debate**: Critic attacks, Mediator resolves\n")
            f.write("7. **Correlation Overrides**: Cross-module kill-switches\n")
            f.write("8. **Judge Synthesis**: Final score, thesis, and audit trail\n")
        saved_files["mermaid"] = mermaid_path
        logger.info(f"✅ Mesh workflow mermaid saved to: {mermaid_path}")
        
        # Try to save PNG using LangGraph's built-in visualization
        if LANGGRAPH_AVAILABLE and self.graph:
            try:
                png_path = os.path.join(output_dir, "mesh_workflow.png")
                # Compile the graph first
                app = self.graph.compile()
                # Get the graph image
                png_data = app.get_graph().draw_mermaid_png()
                with open(png_path, "wb") as f:
                    f.write(png_data)
                saved_files["png"] = png_path
                logger.info(f"✅ Mesh workflow PNG saved to: {png_path}")
            except Exception as e:
                logger.warning(f"Could not save PNG diagram: {e}")
        
        return saved_files
