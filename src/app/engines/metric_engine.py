# =============================================================
# src/app/engines/metric_engine.py
# Metric Engine - Deterministic Metric Computation
# Layer A - Deterministic Truth Surface
# =============================================================
"""
Computes financial metrics with full reproducibility and audit trail.

The Metric Engine:
- Calculates ratios, coverage, cash conversion, leverage metrics
- Produces immutable Facts for the Blackboard
- Integrates with existing GenericAgent metric calculations
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import math
import logging

from src.app.blackboard.models import Fact
from src.app.config import get_module_config, load_agents_config

logger = logging.getLogger(__name__)


class MetricEngine:
    """
    Deterministic metric computation engine.
    
    Leverages existing YAML-defined metric formulas from agents_config.yaml
    and produces Fact entries for the Blackboard.
    """
    
    SOURCE_ID = "metric_engine"
    
    def __init__(self):
        """Initialize the metric engine."""
        self.config = load_agents_config()
        self.global_config = self.config.get("global", {})
        self._safe_functions = self._build_safe_functions()
    
    def compute_metrics(
        self,
        data: Dict[str, Any],
        modules: Optional[List[str]] = None,
        year: Optional[int] = None,
        prev_data: Optional[Dict[str, Any]] = None,
    ) -> List[Fact]:
        """
        Compute metrics for all specified modules.
        
        Args:
            data: Current period financial data
            modules: List of module IDs to compute (None = all enabled)
            year: Financial year for the data
            prev_data: Previous year data for YoY calculations
            
        Returns:
            List of Fact objects with computed metrics
        """
        facts: List[Fact] = []
        modules_config = self.config.get("modules", {})
        
        # Determine which modules to process
        if modules is None:
            modules = [
                m for m, cfg in modules_config.items()
                if cfg.get("enabled", True)
            ]
        
        for module_id in modules:
            module_config = modules_config.get(module_id)
            if not module_config or not module_config.get("enabled", True):
                continue
            
            # Prepare data with computed fields
            prepared_data = self._prepare_data(data, module_config, prev_data)
            
            # Compute metrics for this module
            module_facts = self._compute_module_metrics(
                module_id=module_id,
                module_config=module_config,
                data=prepared_data,
                year=year,
                prev_data=prev_data,
            )
            facts.extend(module_facts)
        
        logger.info(f"Computed {len(facts)} facts across {len(modules)} modules")
        return facts
    
    def compute_module_metrics(
        self,
        module_id: str,
        data: Dict[str, Any],
        year: Optional[int] = None,
        prev_data: Optional[Dict[str, Any]] = None,
    ) -> List[Fact]:
        """
        Compute metrics for a single module.
        
        Args:
            module_id: The module to compute metrics for
            data: Financial data
            year: Financial year
            prev_data: Previous year data
            
        Returns:
            List of Fact objects
        """
        module_config = get_module_config(module_id)
        if not module_config:
            logger.warning(f"Module {module_id} not found in config")
            return []
        
        prepared_data = self._prepare_data(data, module_config, prev_data)
        return self._compute_module_metrics(
            module_id=module_id,
            module_config=module_config,
            data=prepared_data,
            year=year,
            prev_data=prev_data,
        )
    
    def _compute_module_metrics(
        self,
        module_id: str,
        module_config: Dict[str, Any],
        data: Dict[str, Any],
        year: Optional[int],
        prev_data: Optional[Dict[str, Any]],
    ) -> List[Fact]:
        """Internal method to compute metrics for a module."""
        facts: List[Fact] = []
        metric_formulas = module_config.get("metrics", {})
        
        if not metric_formulas:
            return facts
        
        # Build evaluation context
        ctx = self._build_context(data, prev_data)
        
        for metric_name, formula in metric_formulas.items():
            try:
                value = self._evaluate_formula(formula, ctx)
                
                # Create Fact
                fact = Fact(
                    key=metric_name,
                    value=self._round_value(value),
                    unit=self._infer_unit(metric_name),
                    period=year,
                    module=module_id,
                    source_engine=self.SOURCE_ID,
                    data_quality=self._assess_data_quality(value, metric_name),
                    metadata={
                        "formula": formula[:100] if len(formula) > 100 else formula,
                    }
                )
                facts.append(fact)
                
            except Exception as e:
                logger.debug(f"Failed to compute {metric_name}: {e}")
                # Create fact with None value for missing metrics
                fact = Fact(
                    key=metric_name,
                    value=None,
                    period=year,
                    module=module_id,
                    source_engine=self.SOURCE_ID,
                    data_quality=0.0,
                    metadata={"error": str(e)},
                )
                facts.append(fact)
        
        return facts
    
    def _prepare_data(
        self,
        data: Dict[str, Any],
        module_config: Dict[str, Any],
        prev_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Prepare data by applying computed_fields definitions from config.
        """
        prepared = dict(data)
        computed_fields = module_config.get("computed_fields", {})
        
        for target_field, computation_rules in computed_fields.items():
            if prepared.get(target_field) is not None:
                continue
            
            for rule in computation_rules:
                try:
                    ctx = self._build_context(prepared, prev_data)
                    value = self._evaluate_formula(rule, ctx)
                    prepared[target_field] = value
                    break
                except Exception:
                    continue
        
        return prepared
    
    def _build_context(
        self,
        data: Dict[str, Any],
        prev_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build evaluation context with data and safe functions."""
        from collections import defaultdict
        
        ctx = defaultdict(lambda: 0)
        ctx.update(self._safe_functions)
        ctx.update({k: (0 if v is None else v) for k, v in data.items()})
        ctx["prev"] = prev_data or {}
        
        return dict(ctx)
    
    def _build_safe_functions(self) -> Dict[str, Any]:
        """Build dictionary of safe functions for formula evaluation."""
        
        def safe_div(a: Any, b: Any) -> Optional[float]:
            if a is None or b in (None, 0):
                return None
            return a / b
        
        return {
            "safe_div": safe_div,
            "abs": abs,
            "min": min,
            "max": max,
            "round": round,
            "math": math,
        }
    
    def _evaluate_formula(self, formula: str, ctx: Dict[str, Any]) -> Any:
        """Safely evaluate a formula string."""
        safe_globals = {
            "__builtins__": {},
            **self._safe_functions,
        }
        return eval(formula, safe_globals, ctx)
    
    def _round_value(self, value: Any) -> Any:
        """Round numeric values appropriately."""
        if value is None:
            return None
        if isinstance(value, (int, bool)):
            return value
        if isinstance(value, float):
            if abs(value) < 0.0001:
                return round(value, 6)
            elif abs(value) < 1:
                return round(value, 4)
            else:
                return round(value, 2)
        return value
    
    def _infer_unit(self, metric_name: str) -> Optional[str]:
        """Infer unit based on metric name."""
        if "ratio" in metric_name or metric_name.endswith("_ratio"):
            return "ratio"
        if "pct" in metric_name or "percent" in metric_name or metric_name.endswith("_share"):
            return "percent"
        if "days" in metric_name or metric_name.startswith("dso") or metric_name.startswith("dio"):
            return "days"
        if "coverage" in metric_name or metric_name == "interest_coverage":
            return "times"
        return None
    
    def _assess_data_quality(self, value: Any, metric_name: str) -> float:
        """Assess data quality for a computed metric."""
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            if math.isnan(value) or math.isinf(value):
                return 0.0
        return 1.0
