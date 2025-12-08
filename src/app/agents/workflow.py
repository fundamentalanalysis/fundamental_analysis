# =============================================================
# src/app/agents/workflow.py
# LangGraph Workflow Management for Multi-Module Analysis
# =============================================================
"""
LangGraph-based workflow for orchestrating financial analysis modules.

This provides:
1. State-based workflow management
2. Conditional routing between modules
3. Parallel execution where possible
4. Error handling and recovery
5. Streaming/checkpoint support
"""

from typing import Dict, Any, List, Optional, Annotated, TypedDict, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from datetime import datetime
import operator

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from src.app.config import load_agents_config
from .generic_agent import GenericAgent, ModuleOutput


# ---------------------------------------------------------------------------
# State Definitions
# ---------------------------------------------------------------------------

class AnalysisState(TypedDict):
    """State object passed through the workflow"""
    # Input data
    company: str
    year: Optional[int]  # Current financial year
    current_data: Dict[str, float]
    historical_data: List[Dict[str, float]]
    
    # Configuration
    modules_to_run: List[str]
    generate_narrative: bool
    
    # Workflow tracking
    current_module: Optional[str]
    modules_completed: Annotated[List[str], operator.add]  # Accumulates completed modules
    modules_failed: Annotated[List[str], operator.add]     # Accumulates failed modules
    
    # Results
    module_results: Dict[str, Dict]  # Module results stored as dicts
    
    # Aggregated outputs
    overall_score: int
    risk_flags: Annotated[List[str], operator.add]  # Critical issues found
    key_insights: Annotated[List[str], operator.add]  # Important findings
    
    # Error tracking
    errors: Annotated[List[str], operator.add]
    
    # Final output
    final_summary: str
    workflow_status: str  # "running", "completed", "failed"


class WorkflowConfig(BaseModel):
    """Configuration for the workflow"""
    parallel_execution: bool = False  # Run modules in parallel (future)
    stop_on_critical: bool = False    # Stop if critical risk found
    min_modules_for_summary: int = 1  # Minimum modules before generating summary
    enable_checkpoints: bool = True   # Enable state checkpointing


# ---------------------------------------------------------------------------
# Node Functions
# ---------------------------------------------------------------------------

def initialize_workflow(state: AnalysisState) -> Dict[str, Any]:
    """Initialize the workflow state"""
    return {
        "workflow_status": "running",
        "overall_score": 0,
        "module_results": {},
    }


def run_module_node(module_id: str):
    """
    Factory function to create a node for a specific module.
    Returns a function that runs analysis for that module.
    """
    def run_module(state: AnalysisState) -> Dict[str, Any]:
        """Run analysis for a single module"""
        try:
            agent = GenericAgent(module_id)
            
            result = agent.analyze(
                data=state["current_data"],
                historical_data=state.get("historical_data"),
                generate_llm_narrative=state.get("generate_narrative", True),
                company_name=state.get("company"),
                year=state.get("year")
            )
            
            # Extract risk flags from RED rules
            red_rules = [r for r in result.rules if r.flag == "RED"]
            risk_flags = []
            for rule in red_rules:
                flag = f"[{module_id.upper()}] {rule.rule_name}: {rule.reason}"
                risk_flags.append(flag)
            
            # Extract key insights from GREEN rules
            key_insights = []
            green_rules = [r for r in result.rules if r.flag == "GREEN"]
            for rule in green_rules[:2]:  # Top 2 green rules
                if rule.reason:
                    key_insights.append(f"[{module_id.upper()}] ✓ {rule.reason}")
            
            return {
                "module_results": {**state.get("module_results", {}), module_id: result.model_dump()},
                "modules_completed": [module_id],
                "current_module": None,
                "risk_flags": risk_flags,
                "key_insights": key_insights,
            }
            
        except Exception as e:
            return {
                "modules_failed": [module_id],
                "errors": [f"Module {module_id} failed: {str(e)}"],
                "current_module": None,
            }
    
    return run_module


def calculate_overall_score(state: AnalysisState) -> Dict[str, Any]:
    """Calculate overall score from all module results"""
    results = state.get("module_results", {})
    
    if not results:
        return {"overall_score": 0}
    
    scores = [r.get("score", 0) for r in results.values() if isinstance(r, dict)]
    
    if scores:
        overall = sum(scores) // len(scores)
    else:
        overall = 0
    
    return {"overall_score": overall}


def generate_final_summary(state: AnalysisState) -> Dict[str, Any]:
    """Generate final workflow summary"""
    company = state.get("company", "Company")
    completed = state.get("modules_completed", [])
    failed = state.get("modules_failed", [])
    overall_score = state.get("overall_score", 0)
    risk_flags = state.get("risk_flags", [])
    key_insights = state.get("key_insights", [])
    
    # Build summary
    summary_parts = [
        f"# Financial Analysis Summary: {company}",
        f"\n## Overview",
        f"- **Modules Analyzed**: {len(completed)}",
        f"- **Overall Score**: {overall_score}/100",
        f"- **Status**: {'⚠️ Attention Required' if risk_flags else '✅ Healthy'}",
    ]
    
    if risk_flags:
        summary_parts.append(f"\n## 🚨 Risk Flags ({len(risk_flags)})")
        for flag in risk_flags[:10]:  # Top 10 risks
            summary_parts.append(f"- {flag}")
    
    if key_insights:
        summary_parts.append(f"\n## ✅ Positive Indicators")
        for insight in key_insights[:5]:  # Top 5 positives
            summary_parts.append(f"- {insight}")
    
    if failed:
        summary_parts.append(f"\n## ⚠️ Analysis Warnings")
        summary_parts.append(f"- Failed modules: {', '.join(failed)}")
    
    summary_parts.append(f"\n---\n*Analysis completed at {datetime.utcnow().isoformat()}*")
    
    return {
        "final_summary": "\n".join(summary_parts),
        "workflow_status": "completed"
    }


def should_continue(state: AnalysisState) -> Literal["continue", "summarize"]:
    """Decide whether to continue running modules or summarize"""
    modules_to_run = state.get("modules_to_run", [])
    modules_completed = state.get("modules_completed", [])
    modules_failed = state.get("modules_failed", [])
    
    remaining = set(modules_to_run) - set(modules_completed) - set(modules_failed)
    
    if remaining:
        return "continue"
    return "summarize"


def get_next_module(state: AnalysisState) -> str:
    """Get the next module to run"""
    modules_to_run = state.get("modules_to_run", [])
    modules_completed = state.get("modules_completed", [])
    modules_failed = state.get("modules_failed", [])
    
    processed = set(modules_completed) | set(modules_failed)
    
    for module in modules_to_run:
        if module not in processed:
            return module
    
    return None


# ---------------------------------------------------------------------------
# Dynamic Module Router
# ---------------------------------------------------------------------------

def route_to_module(state: AnalysisState) -> str:
    """Route to the next module node"""
    next_module = get_next_module(state)
    if next_module:
        return f"run_{next_module}"
    return "calculate_score"


# ---------------------------------------------------------------------------
# Workflow Builder
# ---------------------------------------------------------------------------

class AnalysisWorkflow:
    """
    LangGraph-based workflow for financial analysis.
    
    Usage:
        workflow = AnalysisWorkflow()
        
        # Run analysis
        result = workflow.run(
            company="RELIANCE",
            current_data={...},
            historical_data=[...],
            modules=["borrowings", "equity_funding_mix"]
        )
    """
    
    def __init__(self, config: Optional[WorkflowConfig] = None):
        """Initialize the workflow"""
        self.config = config or WorkflowConfig()
        self.agents_config = load_agents_config()
        self.available_modules = list(self.agents_config.get("modules", {}).keys())
        self.graph = None
        self.checkpointer = MemorySaver() if self.config.enable_checkpoints else None
        
        # Build the graph
        self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph workflow"""
        # Create state graph
        builder = StateGraph(AnalysisState)
        
        # Add nodes
        builder.add_node("initialize", initialize_workflow)
        
        # Add module nodes dynamically
        for module_id in self.available_modules:
            module_config = self.agents_config["modules"].get(module_id, {})
            if module_config.get("enabled", True):
                builder.add_node(f"run_{module_id}", run_module_node(module_id))
        
        builder.add_node("calculate_score", calculate_overall_score)
        builder.add_node("generate_summary", generate_final_summary)
        
        # Add router node
        builder.add_node("router", lambda state: {"current_module": get_next_module(state)})
        
        # Add edges
        builder.add_edge(START, "initialize")
        builder.add_edge("initialize", "router")
        
        # Add conditional routing from router to modules
        module_routes = {f"run_{m}": f"run_{m}" for m in self.available_modules 
                        if self.agents_config["modules"].get(m, {}).get("enabled", True)}
        module_routes["calculate_score"] = "calculate_score"
        
        builder.add_conditional_edges(
            "router",
            route_to_module,
            module_routes
        )
        
        # After each module, go back to router
        for module_id in self.available_modules:
            if self.agents_config["modules"].get(module_id, {}).get("enabled", True):
                builder.add_edge(f"run_{module_id}", "router")
        
        # After score calculation, generate summary
        builder.add_edge("calculate_score", "generate_summary")
        builder.add_edge("generate_summary", END)
        
        # Compile
        self.graph = builder.compile(checkpointer=self.checkpointer)
    
    def run(
        self,
        company: str,
        current_data: Dict[str, float],
        historical_data: Optional[List[Dict[str, float]]] = None,
        modules: Optional[List[str]] = None,
        generate_narrative: bool = True,
        thread_id: Optional[str] = None,
        year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run the analysis workflow.
        
        Args:
            company: Company name
            current_data: Current period financial data
            historical_data: Historical data for trends
            modules: List of modules to run (None = all enabled)
            generate_narrative: Whether to generate LLM narratives
            thread_id: Thread ID for checkpointing
            year: Current financial year (e.g., 2024)
            
        Returns:
            Complete analysis result
        """
        # Determine modules to run
        if modules:
            # Filter to only enabled modules
            modules_to_run = [m for m in modules if m in self.available_modules]
        else:
            # Run all enabled modules
            modules_to_run = [
                m for m, cfg in self.agents_config["modules"].items()
                if cfg.get("enabled", True)
            ]
        
        # Initial state
        initial_state: AnalysisState = {
            "company": company,
            "year": year,
            "current_data": current_data,
            "historical_data": historical_data or [],
            "modules_to_run": modules_to_run,
            "generate_narrative": generate_narrative,
            "current_module": None,
            "modules_completed": [],
            "modules_failed": [],
            "module_results": {},
            "overall_score": 0,
            "risk_flags": [],
            "key_insights": [],
            "errors": [],
            "final_summary": "",
            "workflow_status": "pending",
        }
        
        # Run configuration - always provide thread_id for checkpointer
        config = {}
        if self.checkpointer:
            # Generate thread_id if not provided
            import uuid
            tid = thread_id or str(uuid.uuid4())
            config["configurable"] = {"thread_id": tid}
        
        # Execute workflow
        final_state = self.graph.invoke(initial_state, config)
        
        return {
            "company": company,
            "year": year,
            "workflow_status": final_state.get("workflow_status"),
            "modules_completed": final_state.get("modules_completed", []),
            "modules_failed": final_state.get("modules_failed", []),
            "overall_score": final_state.get("overall_score", 0),
            "risk_flags": final_state.get("risk_flags", []),
            "key_insights": final_state.get("key_insights", []),
            "module_results": final_state.get("module_results", {}),
            "summary": final_state.get("final_summary", ""),
            "errors": final_state.get("errors", []),
        }
    
    async def arun(
        self,
        company: str,
        current_data: Dict[str, float],
        historical_data: Optional[List[Dict[str, float]]] = None,
        modules: Optional[List[str]] = None,
        generate_narrative: bool = True,
        thread_id: Optional[str] = None,
        year: Optional[int] = None
    ) -> Dict[str, Any]:
        """Async version of run"""
        import uuid
        
        if modules:
            modules_to_run = [m for m in modules if m in self.available_modules]
        else:
            modules_to_run = [
                m for m, cfg in self.agents_config["modules"].items()
                if cfg.get("enabled", True)
            ]
        
        initial_state: AnalysisState = {
            "company": company,
            "year": year,
            "current_data": current_data,
            "historical_data": historical_data or [],
            "modules_to_run": modules_to_run,
            "generate_narrative": generate_narrative,
            "current_module": None,
            "modules_completed": [],
            "modules_failed": [],
            "module_results": {},
            "overall_score": 0,
            "risk_flags": [],
            "key_insights": [],
            "errors": [],
            "final_summary": "",
            "workflow_status": "pending",
        }
        
        config = {}
        if self.checkpointer:
            tid = thread_id or str(uuid.uuid4())
            config["configurable"] = {"thread_id": tid}
        
        final_state = await self.graph.ainvoke(initial_state, config)
        
        return {
            "company": company,
            "year": year,
            "workflow_status": final_state.get("workflow_status"),
            "modules_completed": final_state.get("modules_completed", []),
            "modules_failed": final_state.get("modules_failed", []),
            "overall_score": final_state.get("overall_score", 0),
            "risk_flags": final_state.get("risk_flags", []),
            "key_insights": final_state.get("key_insights", []),
            "module_results": final_state.get("module_results", {}),
            "summary": final_state.get("final_summary", ""),
            "errors": final_state.get("errors", []),
        }
    
    def stream(
        self,
        company: str,
        current_data: Dict[str, float],
        historical_data: Optional[List[Dict[str, float]]] = None,
        modules: Optional[List[str]] = None,
        generate_narrative: bool = True,
        thread_id: Optional[str] = None,
        year: Optional[int] = None
    ):
        """
        Stream workflow execution, yielding state after each step.
        
        Useful for real-time progress updates.
        """
        import uuid
        
        if modules:
            modules_to_run = [m for m in modules if m in self.available_modules]
        else:
            modules_to_run = [
                m for m, cfg in self.agents_config["modules"].items()
                if cfg.get("enabled", True)
            ]
        
        initial_state: AnalysisState = {
            "company": company,
            "year": year,
            "current_data": current_data,
            "historical_data": historical_data or [],
            "modules_to_run": modules_to_run,
            "generate_narrative": generate_narrative,
            "current_module": None,
            "modules_completed": [],
            "modules_failed": [],
            "module_results": {},
            "overall_score": 0,
            "risk_flags": [],
            "key_insights": [],
            "errors": [],
            "final_summary": "",
            "workflow_status": "pending",
        }
        
        config = {}
        if self.checkpointer:
            tid = thread_id or str(uuid.uuid4())
            config["configurable"] = {"thread_id": tid}
        
        # Stream execution
        for state in self.graph.stream(initial_state, config):
            yield state
    
    def get_graph_visualization(self) -> str:
        """Get a text representation of the workflow graph"""
        if not self.graph:
            return "Graph not built"
        
        try:
            return self.graph.get_graph().draw_ascii()
        except:
            return "Graph visualization not available"
    
    def save_graph_image(
        self, 
        output_path: str = "workflow_graph.png",
        format: str = "png"
    ) -> str:
        """
        Save the workflow graph as an image file.
        
        Args:
            output_path: Path to save the image (default: workflow_graph.png)
            format: Output format - 'png', 'jpeg', or 'svg' (default: png)
            
        Returns:
            Path to the saved image file
        """
        if not self.graph:
            raise ValueError("Graph not built")
        
        try:
            # Get the graph image as bytes
            graph = self.graph.get_graph()
            
            # draw_mermaid_png requires additional dependencies
            # Using draw_png which uses graphviz
            if format.lower() == "png":
                image_data = graph.draw_mermaid_png()
            else:
                raise ValueError(f"Unsupported format: {format}. Use 'png'.")
            
            # Save to file
            with open(output_path, "wb") as f:
                f.write(image_data)
            
            return output_path
            
        except ImportError as e:
            raise ImportError(
                f"Missing dependency for graph visualization: {e}. "
                "Install with: pip install grandalf"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to save graph image: {e}")


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

def create_workflow(
    parallel: bool = False,
    stop_on_critical: bool = False,
    enable_checkpoints: bool = True
) -> AnalysisWorkflow:
    """Create a configured workflow instance"""
    config = WorkflowConfig(
        parallel_execution=parallel,
        stop_on_critical=stop_on_critical,
        enable_checkpoints=enable_checkpoints
    )
    return AnalysisWorkflow(config)


# Export
__all__ = [
    "AnalysisWorkflow",
    "AnalysisState", 
    "WorkflowConfig",
    "create_workflow"
]
