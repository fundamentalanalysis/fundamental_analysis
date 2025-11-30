# =============================================================
# src/app/agents/agent_orchestrator.py
# SINGLE ENTRY POINT for all 12 modules
# =============================================================
"""
This is the SINGLE entry point for running any module or all modules.

Usage:
    orchestrator = AgentOrchestrator()
    
    # Run single module
    result = orchestrator.run("equity_funding_mix", data)
    
    # Run all modules
    results = orchestrator.run_all(data)
    
    # Get available modules
    modules = orchestrator.list_modules()
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime

from src.app.config import load_agents_config, get_module_config
from .generic_agent import GenericAgent, ModuleOutput


# ---------------------------------------------------------------------------
# Orchestrator Output Models
# ---------------------------------------------------------------------------

class MultiModuleOutput(BaseModel):
    """Output when running multiple modules"""
    timestamp: str
    modules_run: List[str]
    results: Dict[str, ModuleOutput]
    overall_score: int
    summary: str


class ModuleInfo(BaseModel):
    """Information about an available module"""
    id: str
    name: str
    description: str
    enabled: bool
    input_fields: List[str]


# ---------------------------------------------------------------------------
# Agent Orchestrator
# ---------------------------------------------------------------------------

class AgentOrchestrator:
    """
    Single entry point for all analysis modules.
    
    This orchestrator:
    1. Loads module configuration from YAML
    2. Creates GenericAgent instances on-demand
    3. Routes analysis requests to appropriate agents
    4. Aggregates results from multiple modules
    """
    
    def __init__(self):
        """Initialize orchestrator and load configuration"""
        self.config = load_agents_config()
        self.modules = self.config.get("modules", {})
        self._agent_cache: Dict[str, GenericAgent] = {}
    
    # -----------------------------------------------------------------------
    # MODULE DISCOVERY
    # -----------------------------------------------------------------------
    
    def list_modules(self, include_disabled: bool = False) -> List[ModuleInfo]:
        """
        Get list of available modules.
        
        Args:
            include_disabled: Include modules with enabled=false
            
        Returns:
            List of ModuleInfo objects
        """
        result = []
        
        for module_id, config in self.modules.items():
            enabled = config.get("enabled", True)
            
            if enabled or include_disabled:
                result.append(ModuleInfo(
                    id=module_id,
                    name=config.get("name", module_id),
                    description=config.get("description", ""),
                    enabled=enabled,
                    input_fields=config.get("input_fields", [])
                ))
        
        return result
    
    def get_module_info(self, module_id: str) -> Optional[ModuleInfo]:
        """Get info about a specific module"""
        config = self.modules.get(module_id)
        if not config:
            return None
        
        return ModuleInfo(
            id=module_id,
            name=config.get("name", module_id),
            description=config.get("description", ""),
            enabled=config.get("enabled", True),
            input_fields=config.get("input_fields", [])
        )
    
    def is_module_enabled(self, module_id: str) -> bool:
        """Check if a module is enabled"""
        config = self.modules.get(module_id)
        return config.get("enabled", True) if config else False
    
    # -----------------------------------------------------------------------
    # AGENT MANAGEMENT
    # -----------------------------------------------------------------------
    
    def _get_agent(self, module_id: str) -> GenericAgent:
        """
        Get or create agent for a module (cached).
        """
        if module_id not in self._agent_cache:
            self._agent_cache[module_id] = GenericAgent(module_id)
        return self._agent_cache[module_id]
    
    def clear_cache(self):
        """Clear agent cache (useful after config reload)"""
        self._agent_cache.clear()
    
    def reload_config(self):
        """Reload configuration from YAML"""
        self.config = load_agents_config()
        self.modules = self.config.get("modules", {})
        self.clear_cache()
    
    # -----------------------------------------------------------------------
    # SINGLE MODULE ANALYSIS
    # -----------------------------------------------------------------------
    
    def run(self, module_id: str, data: Dict[str, float], 
            historical_data: Optional[List[Dict[str, float]]] = None,
            generate_narrative: bool = True) -> ModuleOutput:
        """
        Run analysis for a single module.
        
        Args:
            module_id: Module identifier (e.g., "equity_funding_mix")
            data: Current period financial data
            historical_data: Historical data for trend analysis
            generate_narrative: Whether to generate LLM narrative
            
        Returns:
            ModuleOutput with analysis results
            
        Raises:
            ValueError: If module not found or disabled
        """
        # Validate module exists and is enabled
        if module_id not in self.modules:
            raise ValueError(f"Module '{module_id}' not found. Available: {list(self.modules.keys())}")
        
        if not self.is_module_enabled(module_id):
            raise ValueError(f"Module '{module_id}' is disabled in configuration")
        
        # Get agent and run analysis
        agent = self._get_agent(module_id)
        return agent.analyze(data, historical_data, generate_narrative)
    
    # -----------------------------------------------------------------------
    # MULTI-MODULE ANALYSIS
    # -----------------------------------------------------------------------
    
    def run_multiple(self, module_ids: List[str], data: Dict[str, float],
                     historical_data: Optional[List[Dict[str, float]]] = None,
                     generate_narrative: bool = True) -> MultiModuleOutput:
        """
        Run analysis for multiple specified modules.
        
        Args:
            module_ids: List of module identifiers to run
            data: Current period financial data
            historical_data: Historical data for trend analysis
            generate_narrative: Whether to generate LLM narratives
            
        Returns:
            MultiModuleOutput with aggregated results
        """
        results = {}
        scores = []
        modules_run = []
        
        for module_id in module_ids:
            try:
                result = self.run(module_id, data, historical_data, generate_narrative)
                results[module_id] = result
                scores.append(result.score)
                modules_run.append(module_id)
            except ValueError as e:
                # Skip disabled or invalid modules
                print(f"Skipping module {module_id}: {e}")
        
        # Calculate overall score
        overall_score = int(sum(scores) / len(scores)) if scores else 0
        
        # Generate summary
        summary = self._generate_summary(results, overall_score)
        
        return MultiModuleOutput(
            timestamp=datetime.utcnow().isoformat(),
            modules_run=modules_run,
            results=results,
            overall_score=overall_score,
            summary=summary
        )
    
    def run_all(self, data: Dict[str, float],
                historical_data: Optional[List[Dict[str, float]]] = None,
                generate_narrative: bool = True) -> MultiModuleOutput:
        """
        Run analysis for all enabled modules.
        
        Args:
            data: Current period financial data
            historical_data: Historical data for trend analysis
            generate_narrative: Whether to generate LLM narratives
            
        Returns:
            MultiModuleOutput with aggregated results
        """
        enabled_modules = [m.id for m in self.list_modules(include_disabled=False)]
        return self.run_multiple(enabled_modules, data, historical_data, generate_narrative)
    
    def _generate_summary(self, results: Dict[str, ModuleOutput], overall_score: int) -> str:
        """Generate summary across all modules"""
        if not results:
            return "No modules were analyzed."
        
        # Count issues by severity
        red_count = 0
        yellow_count = 0
        green_count = 0
        
        for result in results.values():
            for rule in result.rules_results:
                if rule.status == "RED":
                    red_count += 1
                elif rule.status == "YELLOW":
                    yellow_count += 1
                else:
                    green_count += 1
        
        # Build summary
        total_rules = red_count + yellow_count + green_count
        
        summary = f"Analysis completed for {len(results)} modules. "
        summary += f"Overall Score: {overall_score}/100. "
        summary += f"Rule Results: {red_count} RED, {yellow_count} YELLOW, {green_count} GREEN "
        summary += f"({total_rules} total rules evaluated)."
        
        return summary
    
    # -----------------------------------------------------------------------
    # UTILITY METHODS
    # -----------------------------------------------------------------------
    
    def get_required_fields(self, module_ids: Optional[List[str]] = None) -> List[str]:
        """
        Get all required input fields for specified modules.
        
        Args:
            module_ids: List of module IDs (None = all enabled modules)
            
        Returns:
            Deduplicated list of required field names
        """
        if module_ids is None:
            module_ids = [m.id for m in self.list_modules()]
        
        fields = set()
        for module_id in module_ids:
            config = self.modules.get(module_id, {})
            fields.update(config.get("input_fields", []))
        
        return sorted(list(fields))
    
    def validate_data(self, data: Dict[str, float], module_ids: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        Validate that data contains required fields for modules.
        
        Returns:
            Dict mapping module_id to list of missing fields
        """
        if module_ids is None:
            module_ids = [m.id for m in self.list_modules()]
        
        missing = {}
        for module_id in module_ids:
            config = self.modules.get(module_id, {})
            required = config.get("input_fields", [])
            
            missing_fields = [f for f in required if f not in data]
            if missing_fields:
                missing[module_id] = missing_fields
        
        return missing


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

def analyze(module_id: str, data: Dict[str, float], **kwargs) -> ModuleOutput:
    """
    Convenience function to analyze a single module.
    
    Usage:
        from src.app.agents import analyze
        result = analyze("equity_funding_mix", data)
    """
    orchestrator = AgentOrchestrator()
    return orchestrator.run(module_id, data, **kwargs)


def analyze_all(data: Dict[str, float], **kwargs) -> MultiModuleOutput:
    """
    Convenience function to analyze all modules.
    
    Usage:
        from src.app.agents import analyze_all
        results = analyze_all(data)
    """
    orchestrator = AgentOrchestrator()
    return orchestrator.run_all(data, **kwargs)
