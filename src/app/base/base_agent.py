# =============================================================
# src/app/base/base_agent.py
# Base agent class and registry for configurable modules
# =============================================================

from abc import ABC, abstractmethod
from typing import Dict, List, Type, Any, Optional, Callable
from collections import Counter

from src.app.config.config_loader import get_config_loader, ModuleConfig, GlobalConfig


class BaseAnalyticalAgent(ABC):
    """
    Abstract base class for all analytical agents.
    
    Each module should implement:
    - compute_metrics()
    - compute_trends()
    - apply_rules()
    - generate_narrative()
    - run()
    """
    
    module_key: str = ""  # Override in subclass
    
    def __init__(self):
        self.config_loader = get_config_loader()
        self._module_config: Optional[ModuleConfig] = None
        self._global_config: Optional[GlobalConfig] = None
    
    @property
    def module_config(self) -> Optional[ModuleConfig]:
        """Get module configuration from YAML"""
        if self._module_config is None and self.module_key:
            self._module_config = self.config_loader.get_module_config(self.module_key)
        return self._module_config
    
    @property
    def global_config(self) -> GlobalConfig:
        """Get global configuration"""
        if self._global_config is None:
            self._global_config = self.config_loader.get_global_config()
        return self._global_config
    
    def compute_sub_score(self, rule_results: List) -> int:
        """
        Compute adjusted sub-score based on rule flags.
        Uses global config for scoring weights.
        """
        c = Counter([r.flag for r in rule_results])
        
        gc = self.global_config
        score = gc.default_score
        score -= gc.red_penalty * c.get("RED", 0)
        score -= gc.yellow_penalty * c.get("YELLOW", 0)
        score += gc.green_bonus * c.get("GREEN", 0)
        
        return max(gc.min_score, min(gc.max_score, score))
    
    def summarize_flags(self, results: List) -> tuple:
        """
        Summarize rule results into red flags and positive points.
        Returns: (red_flags, positives)
        """
        red_flags = []
        positives = []
        
        for r in results:
            if r.flag == "RED":
                red_flags.append({
                    "severity": "HIGH",
                    "title": r.rule_name,
                    "detail": r.reason,
                })
            elif r.flag == "GREEN":
                positives.append(f"{r.rule_name}: {r.reason}")
        
        return red_flags, positives
    
    def reshape_metrics(self, per_year: Dict[int, dict]) -> Dict:
        """
        Reshape metrics from per-year dict to per-metric dict with year labels.
        """
        reshaped = {}
        
        for year in sorted(per_year.keys(), reverse=True):
            label = f"Mar {year}"
            metrics = per_year[year]
            
            for metric_key, metric_value in metrics.items():
                if metric_key not in reshaped:
                    reshaped[metric_key] = {}
                
                if metric_value is None:
                    reshaped[metric_key][label] = None
                elif isinstance(metric_value, float):
                    if abs(metric_value) <= 10:
                        reshaped[metric_key][label] = round(metric_value, 4)
                    else:
                        reshaped[metric_key][label] = round(metric_value, 2)
                else:
                    reshaped[metric_key][label] = metric_value
        
        return reshaped
    
    @abstractmethod
    def compute_metrics(self, financials: List) -> Dict[int, dict]:
        """Compute per-year metrics"""
        pass
    
    @abstractmethod
    def compute_trends(self, financials: List, metrics: Dict) -> Dict:
        """Compute trend metrics"""
        pass
    
    @abstractmethod
    def apply_rules(self, financials: List, metrics: Dict, trends: Dict, benchmarks: Any) -> List:
        """Apply deterministic rules"""
        pass
    
    @abstractmethod
    def generate_narrative(self, company_id: str, metrics: Dict, rules: List, trends: Dict) -> str:
        """Generate LLM narrative"""
        pass
    
    @abstractmethod
    def run(self, input_data: Any) -> Any:
        """Main entry point to run the module"""
        pass


class AgentRegistry:
    """
    Registry for dynamically managing analytical agents.
    
    Allows:
    - Registration of new agents
    - Retrieval of agents by module key
    - Listing available agents
    - Dynamic agent creation based on YAML config
    """
    
    _instance = None
    _agents: Dict[str, Type[BaseAnalyticalAgent]] = {}
    _runners: Dict[str, Callable] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register(cls, module_key: str, agent_class: Type[BaseAnalyticalAgent] = None, 
                 runner: Callable = None):
        """
        Register an agent or runner function for a module.
        
        Args:
            module_key: Unique identifier for the module (matches YAML config)
            agent_class: Agent class that extends BaseAnalyticalAgent
            runner: Alternative runner function for modules not using class-based agents
        """
        if agent_class:
            cls._agents[module_key] = agent_class
        if runner:
            cls._runners[module_key] = runner
    
    @classmethod
    def get_agent(cls, module_key: str) -> Optional[BaseAnalyticalAgent]:
        """Get an instance of the agent for a module"""
        agent_class = cls._agents.get(module_key)
        if agent_class:
            return agent_class()
        return None
    
    @classmethod
    def get_runner(cls, module_key: str) -> Optional[Callable]:
        """Get the runner function for a module"""
        return cls._runners.get(module_key)
    
    @classmethod
    def run_module(cls, module_key: str, input_data: Any) -> Any:
        """
        Run a module by its key.
        
        First tries the runner function, then falls back to agent.run()
        """
        runner = cls.get_runner(module_key)
        if runner:
            return runner(input_data)
        
        agent = cls.get_agent(module_key)
        if agent:
            return agent.run(input_data)
        
        raise ValueError(f"No agent or runner registered for module: {module_key}")
    
    @classmethod
    def list_modules(cls) -> List[str]:
        """List all registered module keys"""
        all_keys = set(cls._agents.keys()) | set(cls._runners.keys())
        return sorted(all_keys)
    
    @classmethod
    def get_enabled_modules(cls) -> List[str]:
        """Get modules that are both registered and enabled in config"""
        config_loader = get_config_loader()
        enabled_in_config = set(config_loader.get_enabled_module_names())
        registered = set(cls._agents.keys()) | set(cls._runners.keys())
        return sorted(enabled_in_config & registered)
    
    @classmethod
    def is_registered(cls, module_key: str) -> bool:
        """Check if a module is registered"""
        return module_key in cls._agents or module_key in cls._runners


# Convenience function for registration decorator
def register_agent(module_key: str):
    """
    Decorator to register an agent class.
    
    Usage:
        @register_agent("my_module")
        class MyAgent(BaseAnalyticalAgent):
            ...
    """
    def decorator(cls):
        cls.module_key = module_key
        AgentRegistry.register(module_key, agent_class=cls)
        return cls
    return decorator


def register_runner(module_key: str):
    """
    Decorator to register a runner function.
    
    Usage:
        @register_runner("my_module")
        def run_my_module(input_data):
            ...
    """
    def decorator(func):
        AgentRegistry.register(module_key, runner=func)
        return func
    return decorator
