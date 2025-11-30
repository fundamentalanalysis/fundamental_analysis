# =============================================================
# src/app/agents/__init__.py
# Single Entry Point for All Agents
# =============================================================

from .generic_agent import GenericAgent
from .workflow import AnalysisWorkflow, WorkflowConfig, create_workflow

__all__ = [
    "GenericAgent", 
    "AnalysisWorkflow",
    "WorkflowConfig",
    "create_workflow"
]
