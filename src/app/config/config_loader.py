# =============================================================
# src/app/config/config_loader.py
# YAML configuration loader and module registry
# =============================================================

import os
import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AgentConfig:
    """Configuration for an LLM agent"""
    name: str
    system_prompt: str
    output_sections: List[str]


@dataclass
class MetricDefinition:
    """Definition of a metric to compute"""
    name: str
    formula: str
    description: str


@dataclass
class RuleThresholds:
    """Threshold definitions for a rule"""
    red: Optional[str] = None
    yellow: Optional[str] = None
    green: Optional[str] = None


@dataclass
class RuleReasons:
    """Reason templates for each flag level"""
    red: Optional[str] = None
    yellow: Optional[str] = None
    green: Optional[str] = None


@dataclass
class RuleDefinition:
    """Definition of a deterministic rule"""
    id: str
    name: str
    category: str
    metric: Optional[str] = None
    condition: Optional[str] = None
    flag: Optional[str] = None
    threshold_desc: Optional[str] = None
    reason_template: Optional[str] = None
    thresholds: Optional[RuleThresholds] = None
    reasons: Optional[RuleReasons] = None


@dataclass
class ModuleConfig:
    """Configuration for an analytical module"""
    name: str
    enabled: bool
    description: str
    agent: AgentConfig
    benchmarks: Dict[str, Dict[str, float]]
    per_year_metrics: List[MetricDefinition]
    trend_metrics: List[Dict[str, str]]
    rules: List[RuleDefinition]


@dataclass
class GlobalConfig:
    """Global configuration settings"""
    default_score: int = 70
    red_penalty: int = 10
    yellow_penalty: int = 5
    green_bonus: int = 1
    min_score: int = 0
    max_score: int = 100


class ConfigLoader:
    """Loads and manages module configurations from YAML"""
    
    _instance = None
    _config: Dict[str, Any] = None
    _modules: Dict[str, ModuleConfig] = {}
    _global: GlobalConfig = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """Load configuration from YAML file"""
        config_path = Path(__file__).parent / "agents_config.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)
        
        # Parse global config
        global_cfg = self._config.get('global', {})
        self._global = GlobalConfig(
            default_score=global_cfg.get('default_score', 70),
            red_penalty=global_cfg.get('red_penalty', 10),
            yellow_penalty=global_cfg.get('yellow_penalty', 5),
            green_bonus=global_cfg.get('green_bonus', 1),
            min_score=global_cfg.get('min_score', 0),
            max_score=global_cfg.get('max_score', 100),
        )
        
        # Parse module configs
        modules_cfg = self._config.get('modules', {})
        for module_key, module_data in modules_cfg.items():
            if module_data.get('enabled', True):
                self._modules[module_key] = self._parse_module(module_key, module_data)
    
    def _parse_module(self, key: str, data: Dict) -> ModuleConfig:
        """Parse a module configuration"""
        # Parse agent config
        agent_data = data.get('agent', {})
        agent = AgentConfig(
            name=agent_data.get('name', f'{key} Agent'),
            system_prompt=agent_data.get('system_prompt', ''),
            output_sections=agent_data.get('output_sections', []),
        )
        
        # Parse metrics
        metrics_data = data.get('metrics', {})
        per_year_metrics = [
            MetricDefinition(
                name=m.get('name'),
                formula=m.get('formula', ''),
                description=m.get('description', ''),
            )
            for m in metrics_data.get('per_year', [])
        ]
        trend_metrics = metrics_data.get('trends', [])
        
        # Parse rules
        rules = []
        for rule_data in data.get('rules', []):
            thresholds = None
            reasons = None
            
            if 'thresholds' in rule_data:
                t = rule_data['thresholds']
                thresholds = RuleThresholds(
                    red=t.get('red'),
                    yellow=t.get('yellow'),
                    green=t.get('green'),
                )
            
            if 'reasons' in rule_data:
                r = rule_data['reasons']
                reasons = RuleReasons(
                    red=r.get('red'),
                    yellow=r.get('yellow'),
                    green=r.get('green'),
                )
            
            rules.append(RuleDefinition(
                id=rule_data.get('id'),
                name=rule_data.get('name'),
                category=rule_data.get('category'),
                metric=rule_data.get('metric'),
                condition=rule_data.get('condition'),
                flag=rule_data.get('flag'),
                threshold_desc=rule_data.get('threshold_desc'),
                reason_template=rule_data.get('reason_template'),
                thresholds=thresholds,
                reasons=reasons,
            ))
        
        return ModuleConfig(
            name=data.get('name', key),
            enabled=data.get('enabled', True),
            description=data.get('description', ''),
            agent=agent,
            benchmarks=data.get('benchmarks', {}),
            per_year_metrics=per_year_metrics,
            trend_metrics=trend_metrics,
            rules=rules,
        )
    
    def get_global_config(self) -> GlobalConfig:
        """Get global configuration"""
        return self._global
    
    def get_module_config(self, module_key: str) -> Optional[ModuleConfig]:
        """Get configuration for a specific module"""
        return self._modules.get(module_key)
    
    def get_all_modules(self) -> Dict[str, ModuleConfig]:
        """Get all enabled module configurations"""
        return self._modules
    
    def get_enabled_module_names(self) -> List[str]:
        """Get list of enabled module keys"""
        return list(self._modules.keys())
    
    def reload_config(self):
        """Reload configuration from YAML file"""
        self._modules = {}
        self._load_config()


# Singleton accessor
def get_config_loader() -> ConfigLoader:
    """Get the configuration loader singleton"""
    return ConfigLoader()
