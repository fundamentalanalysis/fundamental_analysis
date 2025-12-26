# =============================================================
# src/app/agents/generic_agent.py
# Single Generic Agent Class for ALL Modules
# =============================================================
"""
This is a SINGLE class that handles all 12 modules.
The module behavior is entirely driven by YAML config.
No need for separate files per module.
"""

from typing import Dict, Any, List, Optional, Union, Callable
from pydantic import BaseModel
from datetime import datetime
import math
import logging
import os

from src.app.config import load_agents_config, get_module_config, OPENAI_MODEL, get_llm_client


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic Models (shared by all modules)
# ---------------------------------------------------------------------------

class RuleResult(BaseModel):
    """Single rule evaluation result - detailed format"""
    rule_id: str
    rule_name: str
    metric: str
    year: Optional[int] = None
    flag: str  # "RED", "YELLOW", "GREEN", "NEUTRAL"
    value: float
    threshold: str
    reason: str
    # Keep enhanced insight fields as optional
    implication: Optional[str] = None
    investor_action: Optional[str] = None
    risk_level: Optional[str] = None
    peer_context: Optional[str] = None


class TrendDetail(BaseModel):
    """Detailed trend with YoY breakdown"""
    values: Dict[str, Optional[Union[int, float]]]  # {"Y": 100, "Y-1": 90, "Y-2": 80, ...}
    yoy_growth_pct: Dict[str, Optional[float]]  # {"Y_vs_Y-1": 11.1, "Y-1_vs_Y-2": 12.5, ...}
    insight: str


class TrendResult(BaseModel):
    """Trend calculation result"""
    name: str
    value: float
    interpretation: str


class ModuleOutput(BaseModel):
    """Universal output for any module - detailed format"""
    module: str
    company: Optional[str] = None
    year: Optional[int] = None
    key_metrics: Dict[str, Any]
    trends: Dict[str, Any]  # Flexible for different trend formats
    analysis_narrative: List[str]
    red_flags: List[Dict[str, Any]]  # Now supports both simple strings and detailed dicts
    positive_points: List[str]
    rules: List[RuleResult]
    score: int
    score_interpretation: str
    llm_narrative: Optional[str] = None
    
    class Config:
        # Allow flexibility for red_flags to be strings or dicts
        arbitrary_types_allowed = True
    
    def to_module_output_dict(self) -> Dict[str, Any]:
        """Convert to plain dict for JSON serialization"""
        return self.model_dump() if hasattr(self, 'model_dump') else self.dict()
    
    def to_legacy_format(self) -> Dict[str, Any]:
        """Convert to legacy module-specific output format (e.g., EquityFundingOutput)"""
        return {
            "module": self.module,
            "company": self.company,
            "key_metrics": self.key_metrics,
            "trends": self.trends,
            "analysis_narrative": self.analysis_narrative,
            "red_flags": self.red_flags,
            "positive_points": self.positive_points,
            "rules": [r.model_dump() if hasattr(r, 'model_dump') else r.dict() for r in self.rules],
            "score": self.score,
            "score_interpretation": self.score_interpretation,
        }

    def to_metrics_trends_dict(self) -> Dict[str, Any]:
        """Return only key_metrics + trends (no rules engine outputs)."""
        return {
            "module": self.module,
            "company": self.company,
            "year": self.year,
            "key_metrics": self.key_metrics,
            "trends": self.trends,
        }


# ---------------------------------------------------------------------------
# Generic Agent Class
# ---------------------------------------------------------------------------

class GenericAgent:
    """
    A single configurable agent that can run any module.
    
    Usage:
        agent = GenericAgent("equity_funding_mix")
        result = agent.analyze(data, historical_data)
    """
    
    def __init__(self, module_id: str):
        """Initialize agent for a specific module.

        Args:
            module_id: The module key from agents_config.yaml (e.g., "borrowings", "equity_funding_mix")
        """
        self.module_id = module_id
        self.config = get_module_config(module_id)
        if not self.config:
            raise ValueError(f"Module '{module_id}' not found in agents_config.yaml")

        self.name = self.config.get("name", module_id)
        self.description = self.config.get("description", "")
        self.benchmarks = self.config.get("benchmarks", {})
        self.metric_formulas = self.config.get("metrics", {})
        self.rules = self.config.get("rules", [])
        self.agent_prompt = self.config.get("agent_prompt", "")
        self.output_sections = self.config.get("output_sections", [])

        # Load global config
        full_config = load_agents_config()
        self.global_config = full_config.get("global", {})

        # Registry of special trend blocks (YAML-driven; algorithms live in code).
        self.special_trend_handlers: Dict[str, Callable[[List[Dict[str, float]]], Dict[str, Any]]] = {
            "receivables_vs_revenue": self._special_trend_receivables_vs_revenue,
            "aiqm_capitalization": self._special_trend_aiqm_capitalization,
            "aiqm_cwip_vs_capitalization": self._special_trend_aiqm_cwip_vs_capitalization,
            "risk_scenarios": self._special_trend_risk_scenarios,
            "leverage_financial_risk": self._special_trend_leverage_financial_risk,
        }

    # -----------------------------------------------------------------------
    # METRICS CALCULATION
    # -----------------------------------------------------------------------

    def calculate_metrics(self, data: Dict[str, float], prev_data: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Calculate all metrics for this module from YAML `metrics:` formulas.

        `prev_data` is exposed to formulas as `prev` (a dict) for YoY / average calculations.
        """
        if self._metrics_logging_enabled():
            keys_preview = list(self.metric_formulas.keys())
            logger.info(
                "metrics_eval_start module=%s metric_count=%d metrics=%s",
                self.module_id,
                len(keys_preview),
                keys_preview,
            )

        metrics = self._calc_generic_metrics(data, prev_data=prev_data)

        if self._metrics_logging_enabled():
            computed = [k for k, v in metrics.items() if v is not None]
            missing = [k for k, v in metrics.items() if v is None]
            logger.info(
                "metrics_eval_done module=%s computed=%d missing=%d",
                self.module_id,
                len(computed),
                len(missing),
            )

        return metrics
    
    def _calc_generic_metrics(self, data: Dict[str, float], prev_data: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Fallback: compute metrics generically from YAML formulas.

        New modules can be added by configuring `metrics:` expressions in YAML.
        Expressions are evaluated with a restricted namespace.
        """
        if not self.metric_formulas:
            if self._metrics_logging_enabled():
                logger.info("metrics_eval_skip module=%s reason=no_metric_formulas", self.module_id)
            return {}

        from collections import defaultdict

        def safe_div(a: Any, b: Any) -> Optional[float]:
            if a is None or b in (None, 0):
                return None
            return a / b

        def parse_tax_rate(tax_value: Any) -> float:
            """Convert tax inputs to a decimal rate.

            Supports:
            - "19%" -> 0.19
            - 19 or 19.0 -> 0.19 (schema stores percent-like numbers)
            - 0.19 -> 0.19
            """
            if tax_value is None:
                return 0.0
            if isinstance(tax_value, str):
                s = tax_value.strip()
                if not s:
                    return 0.0
                if "%" in s:
                    try:
                        return float(s.replace("%", "").strip()) / 100.0
                    except ValueError:
                        return 0.0
                try:
                    # allow "19" as string
                    v = float(s)
                except ValueError:
                    return 0.0
                return (v / 100.0) if v > 1 else v
            if isinstance(tax_value, (int, float)):
                v = float(tax_value)
                return (v / 100.0) if v > 1 else v
            return 0.0

        ctx = defaultdict(lambda: 0)
        ctx.update({
            "abs": abs,
            "min": min,
            "max": max,
            "round": round,
        })
        ctx.update({k: (0 if v is None else v) for k, v in data.items()})
        # Optional previous year context for metrics that require deltas (e.g., debt_funded_capex)
        ctx["prev"] = prev_data or {}

        # Prevent defaultdict from creating 0-valued placeholders for callable names
        # (which would shadow the global function and cause "int is not callable").
        ctx["safe_div"] = safe_div
        ctx["parse_tax_rate"] = parse_tax_rate
        ctx["math"] = math

        safe_globals = {
            "__builtins__": {},
            "math": math,
            "safe_div": safe_div,
            "parse_tax_rate": parse_tax_rate,
            "abs": abs,
            "min": min,
            "max": max,
            "round": round,
        }

        metrics: Dict[str, Any] = {}
        log_enabled = self._metrics_logging_enabled()
        for metric_name, expr in self.metric_formulas.items():
            if log_enabled and logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "metrics_eval_metric_start module=%s metric=%s expr=%s",
                    self.module_id,
                    metric_name,
                    expr,
                )
            try:
                value = eval(expr, safe_globals, ctx)
                metrics[metric_name] = value
                if log_enabled and logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "metrics_eval_metric_done module=%s metric=%s value=%s",
                        self.module_id,
                        metric_name,
                        value,
                    )
            except (ZeroDivisionError, TypeError, ValueError, SyntaxError) as e:
                metrics[metric_name] = None
                if log_enabled:
                    logger.warning(
                        "metrics_eval_metric_failed module=%s metric=%s error=%s",
                        self.module_id,
                        metric_name,
                        e,
                    )

        return metrics

    def _metrics_logging_enabled(self) -> bool:
        """Opt-in logging for YAML metrics evaluation.

        Enabled when either:
        - env var `FA_METRICS_LOG` is truthy (1/true/yes/on)
        - global config contains `enable_metrics_logging: true`
        """
        try:
            if self.global_config.get("enable_metrics_logging") is True:
                return True
        except Exception:
            pass

        v = os.getenv("FA_METRICS_LOG", "").strip().lower()
        return v in {"1", "true", "yes", "y", "on"}

    def _enrich_historical_with_metrics_if_needed(
        self,
        prepared_historical: List[Dict[str, float]],
        required_fields: List[str],
    ) -> List[Dict[str, float]]:
        """Ensure `prepared_historical` contains the `required_fields`.

        For some modules (e.g., QoE), trend fields are derived metrics (qoe, accruals_ratio, etc)
        that don't exist in raw financial statements. In such cases we compute metrics per year
        and merge them into each year's dict.
        """
        if not prepared_historical:
            return prepared_historical

        missing_any = False
        for field in required_fields:
            if field and field not in prepared_historical[0]:
                missing_any = True
                break

        if not missing_any:
            return prepared_historical

        enriched: List[Dict[str, float]] = []
        for idx, year_data in enumerate(prepared_historical):
            prev_year_data = prepared_historical[idx - 1] if idx > 0 else None
            year_metrics = self.calculate_metrics(year_data, prev_data=prev_year_data)
            merged = dict(year_data)
            merged.update(year_metrics)
            enriched.append(merged)
        return enriched
    
    # -----------------------------------------------------------------------
    # RULES EVALUATION
    # -----------------------------------------------------------------------
    
    def evaluate_rules(self, metrics: Dict[str, float], year: Optional[int] = None) -> List[RuleResult]:
        """
        Evaluate all rules from config against calculated metrics.
        Returns detailed rule results with threshold and reason.
        All rules are included in response, even if no condition is met.
        """
        results = []
        
        for rule in self.rules:
            rule_id = rule.get("id", "")
            rule_name = rule.get("name", "")
            metric_name = rule.get("metric", "")
            
            # Get metric value - default to 0 if None
            value = metrics.get(metric_name, 0)
            if value is None:
                value = 0
            
            # Evaluate thresholds and get insights
            flag, threshold_str, reason, insights = self._evaluate_rule_with_insights(rule, value, metrics)
            
            results.append(RuleResult(
                rule_id=rule_id,
                rule_name=rule_name,
                metric=metric_name,
                year=year,
                flag=flag,
                value=round(value, 6) if isinstance(value, (int, float)) else value,
                threshold=threshold_str,
                reason=reason,
                implication=insights.get("implication"),
                investor_action=insights.get("investor_action"),
                risk_level=insights.get("risk_level"),
                peer_context=insights.get("peer_context")
            ))
        
        return results
    
    def _evaluate_rule_with_insights(self, rule: Dict, value: float, metrics: Dict[str, float] = None) -> tuple:
        """
        Evaluate a single rule and return (flag, threshold_str, reason, insights dict).
        Extracts rich insights from YAML config based on status.
        Always returns a result even if no conditions are met.
        """
        red_cond = rule.get("red", "")
        yellow_cond = rule.get("yellow", "")
        green_cond = rule.get("green", "")
        insights_config = rule.get("insights", {})
        rule_name = rule.get("name", "")
        
        # Helper to get peer_context with fallback to other status levels
        def get_peer_context(primary_insights: Dict) -> str:
            if primary_insights.get("peer_context"):
                return primary_insights["peer_context"]
            for status in ["red", "yellow", "green"]:
                status_insights = insights_config.get(status, {})
                if status_insights.get("peer_context"):
                    return status_insights["peer_context"]
            return f"Compare with industry peers for {rule_name}"
        
        # Build threshold string
        def build_threshold_str(triggered_cond: str) -> str:
            return triggered_cond if triggered_cond and triggered_cond != "-" else "N/A"
        
        # Check RED condition first
        if self._check_condition(value, red_cond):
            insights = insights_config.get("red", {}).copy()
            insights["peer_context"] = get_peer_context(insights)
            reason = insights.get("summary", f"{rule_name} is in critical zone")
            return "RED", build_threshold_str(red_cond), reason, insights
        
        # Check YELLOW condition
        if self._check_condition(value, yellow_cond):
            insights = insights_config.get("yellow", {}).copy()
            insights["peer_context"] = get_peer_context(insights)
            reason = insights.get("summary", f"{rule_name} needs attention")
            return "YELLOW", build_threshold_str(yellow_cond), reason, insights
        
        # Check GREEN condition explicitly
        if self._check_condition(value, green_cond):
            insights = insights_config.get("green", {}).copy()
            insights["peer_context"] = get_peer_context(insights)
            reason = insights.get("summary", f"{rule_name} is healthy")
            return "GREEN", build_threshold_str(green_cond), reason, insights
        
        # No condition met - return NEUTRAL status
        return "NEUTRAL", "No threshold triggered", f"Value: {self._format_value(value)}", {
            "implication": "Value does not match any defined threshold conditions",
            "investor_action": "Review threshold configuration",
            "risk_level": "Not Assessed",
            "peer_context": get_peer_context({})
        }
    
    def _format_value(self, value: float) -> str:
        """Format value appropriately based on magnitude"""
        if value is None or not isinstance(value, (int, float)):
            return "N/A"
        if abs(value) < 0.01:
            return f"{value:.4f}"
        elif abs(value) < 10:
            return f"{value:.2%}" if abs(value) <= 1 else f"{value:.2f}x"
        else:
            return f"{value:.2f}"
    
    def _check_condition(self, value: float, condition: str) -> bool:
        """
        Parse and check a condition string like "> 1.0", "< 0.5", ">= 0.15"
        """
        if not condition or condition == "-":
            return False
        
        # Handle None or non-numeric values
        if value is None or not isinstance(value, (int, float)):
            return False
        
        condition = condition.strip()
        
        # Handle special cases
        if condition.lower() in ["declining", "growing"]:
            return False  # Can't evaluate without trend data
        
        try:
            if condition.startswith(">="):
                threshold = float(condition[2:].strip())
                return value >= threshold
            elif condition.startswith("<="):
                threshold = float(condition[2:].strip())
                return value <= threshold
            elif condition.startswith(">"):
                threshold = float(condition[1:].strip())
                return value > threshold
            elif condition.startswith("<"):
                threshold = float(condition[1:].strip())
                return value < threshold
            elif condition.startswith("==") or condition.startswith("="):
                threshold = float(condition.lstrip("=").strip())
                return abs(value - threshold) < 0.0001
        except (ValueError, IndexError, TypeError):
            pass
        
        return False
    
    # -----------------------------------------------------------------------
    # TRENDS CALCULATION & UTILITIES
    # -----------------------------------------------------------------------
    
    def _compute_cagr(self, start: float, end: float, years: int) -> Optional[float]:
        """Compute CAGR handling None, zero, and mixed signs. Returns percentage or None."""
        if start is None or end is None or years <= 0:
            return None
        if start == 0:
            return None  # CAGR undefined when start is zero
        
        # Same sign case (both positive OR both negative)
        if start * end > 0:
            cagr = (abs(end) / abs(start)) ** (1 / years) - 1
            # If both negative, return magnitude of loss growth
            return cagr * 100
        
        # Mixed signs (negative to positive or vice versa) → undefined CAGR
        return None
    
    def _compute_yoy(self, current: float, previous: float) -> Optional[float]:
        """Compute year-over-year growth rate as percentage."""
        if previous in (None, 0) or current is None:
            return None
        return (current - previous) / previous * 100
    
    def _series(self, years: List[int], yearly: Dict[int, dict], key: str) -> List[Optional[float]]:
        """Extract series of values for a key across years."""
        return [yearly.get(y, {}).get(key) for y in years]
    
    def _has_consecutive_trend(self, values: List[Optional[float]], direction: str, span: int) -> bool:
        """Check for consecutive trend (up/down) across span years."""
        if len(values) < span:
            return False
        cmp = (lambda a, b: a > b) if direction == "up" else (lambda a, b: a < b)
        streak = 0
        for prev, curr in zip(values, values[1:]):
            if prev is None or curr is None:
                streak = 0
                continue
            if cmp(curr, prev):
                streak += 1
                if streak >= span - 1:
                    return True
            else:
                streak = 0
        return False
    
    def calculate_trends(self, historical_data: List[Dict[str, float]]) -> List[TrendResult]:
        """
        Calculate trend metrics (CAGR, etc.) from historical data.
        
        Args:
            historical_data: List of dictionaries with yearly data, oldest first
            
        Returns:
            List of TrendResult objects
        """
        if not historical_data or len(historical_data) < 2:
            return []
        
        trends = []
        n = len(historical_data)
        
        # Field mappings for trend calculations
        field_mappings = {
            "debt": ["total_debt"],
            "ebitda": ["ebitda"],
            "lt_debt": ["long_term_debt"],
            "revenue": ["revenue", "revenue_wc"],
            "retained_earnings": ["reserves_and_surplus", "retained_earnings"],
            "networth": ["net_worth"],
            "pat": ["pat"],
            "equity": ["total_equity", "net_worth"],
            "finance_cost": ["finance_cost", "interest_expense"],
            "st_debt": ["short_term_debt"],
        }
        
        # Calculate total_debt if not present
        for d in historical_data:
            if "total_debt" not in d or d.get("total_debt", 0) == 0:
                d["total_debt"] = d.get("short_term_debt", 0) + d.get("long_term_debt", 0)
        
        for trend_key in self.trend_keys:
            # Skip YoY growth calculations (handled separately)
            if "yoy" in trend_key.lower():
                continue
                
            # Map trend key to data field
            base_key = trend_key.replace("_cagr", "").replace("_growth", "")
            
            # Try to find data
            values = []
            for mapping in field_mappings.get(base_key, [base_key]):
                if all(mapping in d for d in historical_data):
                    values = [d[mapping] for d in historical_data]
                    break
            
            if len(values) >= 2 and values[0] and values[0] > 0:
                # Calculate CAGR: (End/Start)^(1/n) - 1
                cagr = (values[-1] / values[0]) ** (1 / (n - 1)) - 1
                
                interpretation = "Strong growth" if cagr > 0.15 else \
                                "Moderate growth" if cagr > 0.05 else \
                                "Stable" if cagr > -0.05 else "Declining"
                
                trends.append(TrendResult(
                    name=trend_key,
                    value=round(cagr, 4),
                    interpretation=interpretation
                ))
        
        return trends
    
    def _calculate_module_trends(self, historical_data: List[Dict[str, float]]) -> Dict[str, Any]:
        """
        UNIFIED trend calculation method that reads trend logic from YAML config.
        Replaces module-specific _calculate_equity_funding_trends() and _calculate_trend_comparison_metrics().
        
        This method is driven by the trend_metrics section in the module's YAML config:
        - cagr_fields: List of fields to calculate CAGR for
        - yoy_fields: List of fields to track YoY growth for
        - comparison_metrics: Dict of comparison metric names and field pairs to compare
        - special_trends: List of special trend calculations (dilution, declining trends, etc)
        
        Args:
            historical_data: List of dicts with year and metrics (oldest first)
            
        Returns:
            Dict with CAGR metrics, YoY growth arrays, and special trend metrics
        """
        if not historical_data or len(historical_data) < 2:
            return {}
        
        trend_config = self.config.get("trend_metrics", {})
        if not trend_config:
            return {}
        
        n = len(historical_data)
        results = {}
        
        # Helper: Compute CAGR safely (supports same-sign negative series)
        def compute_cagr(start: float, end: float, years: int) -> Optional[float]:
            return self._compute_cagr(start, end, years)
        
        # Helper: Get field values from historical data
        def get_field_values(field: str) -> List[Optional[float]]:
            return [d.get(field) for d in historical_data]
        
        # ===== 1. CALCULATE CAGR METRICS =====
        cagr_fields = trend_config.get("cagr_fields", [])
        cagr_values = {}  # Store computed CAGRs for later comparison metrics
        
        for field in cagr_fields:
            values = get_field_values(field)
            cagr_field_name = f"{field}_cagr"
            if values[0] is not None and values[-1] is not None:
                cagr = compute_cagr(values[0], values[-1], n - 1)
                if cagr is not None:
                    cagr_values[field] = cagr  # Store for comparison metrics
                    results[cagr_field_name] = round(cagr, 2)
                else:
                    results[cagr_field_name] = None
            else:
                results[cagr_field_name] = None
        
        # ===== 2. CALCULATE COMPARISON METRICS =====
        # Format: metric_name: [field1, field2] => field1_cagr - field2_cagr
        comparison_metrics = trend_config.get("comparison_metrics", {})
        
        for comp_metric_name, field_pair in comparison_metrics.items():
            if isinstance(field_pair, list) and len(field_pair) == 2:
                field1, field2 = field_pair
                cagr1 = cagr_values.get(field1)
                cagr2 = cagr_values.get(field2)
                
                if cagr1 is not None and cagr2 is not None:
                    results[comp_metric_name] = round(cagr1 - cagr2, 2)
                else:
                    results[comp_metric_name] = 0
        
        # ===== 3. CALCULATE YoY GROWTH ARRAYS =====
        yoy_fields = trend_config.get("yoy_fields", [])
        
        for field in yoy_fields:
            yoy_array = []
            for i in range(len(historical_data) - 1):
                prev_val = historical_data[i].get(field)
                curr_val = historical_data[i + 1].get(field)
                
                if prev_val is not None and prev_val != 0 and curr_val is not None:
                    yoy = ((curr_val - prev_val) / abs(prev_val)) * 100
                    yoy_array.append(yoy)
                else:
                    yoy_array.append(None)
            
            yoy_field_name = f"{field}_yoy_growth"
            results[yoy_field_name] = yoy_array
        
        # ===== 4. HANDLE SPECIAL TRENDS (module-specific logic) =====
        special_trends = trend_config.get("special_trends", [])
        
        # Build yearly dict for special trend calculations
        yearly = {}
        for d in historical_data:
            year = d.get("year")
            if year:
                yearly[year] = d
        
        if len(yearly) >= 2 and special_trends:
            years = sorted(yearly.keys())
            
            # Special trend: dilution_pct detection
            if "dilution_pct" in special_trends:
                dilution_events = []
                for year in years:
                    dilution = yearly[year].get("dilution_pct")
                    if dilution is not None and dilution > 0:
                        dilution_events.append({
                            "year": year,
                            "dilution_pct": dilution
                        })
                results["dilution_events"] = dilution_events
            
            # Special trend: declining trend detection (3-year consecutive decline)
            if "retained_declining" in special_trends:
                retained_series = [yearly[y].get("retained_earnings") for y in years]
                retained_declining = self._has_consecutive_trend(retained_series, "down", 3)
                results["retained_declining"] = retained_declining
            
            if "roe_declining" in special_trends:
                roe_series = [yearly[y].get("roe") for y in years]
                roe_declining = self._has_consecutive_trend(roe_series, "down", 3)
                results["roe_declining"] = roe_declining

            # Special trends: increasing trend flags (3y consecutive rise)
            if "cwip_increasing_3y" in special_trends:
                cwip_series = [yearly[y].get("cwip") for y in years]
                results["cwip_increasing_3y"] = self._has_consecutive_trend(cwip_series, "up", 3)
            if "capex_increasing_3y" in special_trends:
                capex_series = [yearly[y].get("capex") for y in years]
                results["capex_increasing_3y"] = self._has_consecutive_trend(capex_series, "up", 3)
            if "nfa_increasing_3y" in special_trends:
                nfa_series = [yearly[y].get("nfa") for y in years]
                results["nfa_increasing_3y"] = self._has_consecutive_trend(nfa_series, "up", 3)
        
        return results
    
    # -----------------------------------------------------------------------
    # SCORING
    # -----------------------------------------------------------------------
    
    def calculate_score(self, rules_results: List[RuleResult]) -> tuple:
        """
        Calculate overall module score based on rule results.
        
        NEUTRAL status rules don't impact scoring.
        
        Returns:
            (score, interpretation)
        """
        base_score = self.global_config.get("default_score", 70)
        red_penalty = self.global_config.get("red_penalty", 10)
        yellow_penalty = self.global_config.get("yellow_penalty", 5)
        green_bonus = self.global_config.get("green_bonus", 1)
        min_score = self.global_config.get("min_score", 0)
        max_score = self.global_config.get("max_score", 100)
        
        score = base_score
        
        for result in rules_results:
            if result.flag == "RED":
                score -= red_penalty
            elif result.flag == "YELLOW":
                score -= yellow_penalty
            elif result.flag == "GREEN":
                score += green_bonus
            # NEUTRAL - no scoring impact
        
        score = max(min_score, min(max_score, score))
        
        interpretation = "Excellent" if score >= 80 else \
                        "Good" if score >= 65 else \
                        "Fair" if score >= 50 else \
                        "Poor" if score >= 35 else "Critical"
        
        return int(score), interpretation
    
    # -----------------------------------------------------------------------
    # LLM NARRATIVE
    # -----------------------------------------------------------------------
    
    def generate_narrative(self, metrics: Dict[str, float], rules_results: List[RuleResult], 
                          trends: Dict[str, TrendDetail], score: int) -> str:
        """
        Generate LLM narrative using configured agent prompt.
        """
        try:
            client = get_llm_client()
            
            # Build context
            metrics_str = "\n".join([f"- {k}: {v:.4f}" if isinstance(v, float) else f"- {k}: {v}" for k, v in metrics.items()])
            rules_str = "\n".join([f"- {r.rule_name}: {r.flag} - {r.reason}" for r in rules_results])
            
            # Format trends
            if trends:
                trends_str = "\n".join([f"- {name}: {detail.insight}" for name, detail in trends.items()])
            else:
                trends_str = "No trend data"
            
            sections_guidance = "\n".join([f"- {s}" for s in self.output_sections]) if self.output_sections else ""
            
            user_prompt = f"""
Module: {self.name}
Score: {score}/100

Calculated Metrics:
{metrics_str}

Rule Evaluations:
{rules_str}

Trends:
{trends_str}

Please provide a structured analysis covering these sections:
{sections_guidance}

Keep the analysis concise but insightful.
"""
            
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.agent_prompt or f"You are a financial analyst for {self.name} module."},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"[Narrative generation failed: {str(e)}]"
    
    # -----------------------------------------------------------------------
    # INPUT PREPARATION
    # -----------------------------------------------------------------------
    
    def _prepare_input(self, data: Dict[str, float]) -> Dict[str, float]:
        """
        Prepare input by computing derived fields based on module config.
        
        Reads 'computed_fields' from module config and safely evaluates expressions.
        Example: debt = "short_term_debt + long_term_debt + (lease_liabilities or 0)"
        
        Args:
            data: Raw financial data dictionary
            
        Returns:
            Prepared data dictionary with computed fields filled in
        """
        prepared = dict(data)  # Copy input data
        
        computed_fields = self.config.get("computed_fields", {})
        required_fields = self.config.get("input_fields", [])
        
        # Build a safe namespace for expression evaluation
        # Use a custom defaultdict so any undefined field defaults to 0
        from collections import defaultdict
        safe_dict_base = defaultdict(lambda: 0)
        
        # Populate with required fields (ensuring all are present)
        for field in required_fields:
            safe_dict_base[field] = prepared.get(field) or 0
        
        # Populate with all fields from input data
        safe_dict_base.update({k: v or 0 for k, v in prepared.items()})
        
        # Apply field computations
        for target_field, computation_rules in computed_fields.items():
            # Skip if field already exists in input
            if prepared.get(target_field) is not None:
                continue
            
            # Try each computation rule in order (fallback support)
            for rule in computation_rules:
                # Avoid a common YAML pattern that includes the target field name as a "fallback".
                # When inputs are missing, required fields default to 0 in the safe dict and this
                # would short-circuit computed fields to 0.
                if isinstance(rule, str) and rule.strip() == target_field:
                    continue
                try:
                    # Evaluate expression with limited builtins
                    # The defaultdict will provide 0 for any undefined fields
                    computed_value = eval(rule, {"__builtins__": {}}, safe_dict_base)
                    prepared[target_field] = computed_value
                    safe_dict_base[target_field] = computed_value  # Update for next computations
                    break  # Use first successful rule
                    
                except (KeyError, TypeError, ZeroDivisionError, SyntaxError, ValueError) as e:
                    # Rule failed, try next one
                    # NameError is not caught here because we're using defaultdict
                    continue
        
        # Ensure all required fields exist in prepared (default to 0)
        for field in required_fields:
            if prepared.get(field) is None:
                prepared[field] = 0.0
        
        return prepared
    
    # -----------------------------------------------------------------------
    # MAIN ANALYZE METHOD
    # -----------------------------------------------------------------------
    
    def analyze(self, data: Dict[str, float], historical_data: Optional[List[Dict[str, float]]] = None,
                generate_llm_narrative: bool = True, company_name: Optional[str] = None,
                year: Optional[int] = None, include_rules: bool = True) -> ModuleOutput:
        """
        Main entry point: Run complete analysis for this module.
        
        Args:
            data: Current period financial data
            historical_data: List of historical periods (oldest first) - Y-4, Y-3, Y-2, Y-1, Y
            generate_llm_narrative: Whether to generate LLM narrative
            company_name: Name of the company being analyzed
            year: Current financial year (e.g., 2024)
            
        Returns:
            ModuleOutput with detailed analysis results
        """
        # 0. Prepare input - compute derived fields based on module config
        prepared_data = self._prepare_input(data)
        
        # Prepare historical data as well
        prepared_historical = None
        if historical_data:
            prepared_historical = [self._prepare_input(h) for h in historical_data]
        
        # 1. Calculate metrics (optionally pass previous year context)
        prev_for_current = None
        if prepared_historical and len(prepared_historical) >= 2:
            # `prepared_historical` is oldest-first; most recent is last
            prev_for_current = prepared_historical[-2]
        metrics = self.calculate_metrics(prepared_data, prev_data=prev_for_current)
        
        # 2. UNIFIED TREND CALCULATION (reads from YAML trend_metrics config)
        # This single method replaces:
        #   - _calculate_trend_comparison_metrics() for borrowings
        #   - _calculate_equity_funding_trends() for equity_funding_mix
        #   - Custom logic for other modules
        module_trends = {}
        if prepared_historical and len(prepared_historical) >= 2:
            trend_config = self.config.get("trend_metrics", {})
            required_for_module_trends: List[str] = []
            if trend_config:
                required_for_module_trends.extend(trend_config.get("cagr_fields", []) or [])
                required_for_module_trends.extend(trend_config.get("yoy_fields", []) or [])
                for pair in (trend_config.get("comparison_metrics", {}) or {}).values():
                    if isinstance(pair, list) and len(pair) == 2:
                        required_for_module_trends.extend(pair)

            historical_for_module_trends = self._enrich_historical_with_metrics_if_needed(
                prepared_historical,
                required_for_module_trends,
            )
            module_trends = self._calculate_module_trends(historical_for_module_trends)
            metrics.update(module_trends)
        
        # 3. Evaluate rules with year (optional)
        rules_results: List[RuleResult] = []
        if include_rules:
            rules_results = self.evaluate_rules(metrics, year)
        
        # 4. Calculate detailed trends with YoY breakdown
        # For detailed trends, ensure derived fields exist if configured as trend fields
        detailed_trends = {}
        if prepared_historical:
            required_for_detailed_trends = list(self._get_trend_fields().keys())
            historical_for_detailed_trends = self._enrich_historical_with_metrics_if_needed(
                prepared_historical,
                required_for_detailed_trends,
            )
            detailed_trends = self._calculate_detailed_trends(historical_for_detailed_trends)

            # Liquidity: compute YoY-latest fields from unrounded enriched series
            if self.module_id == "liquidity":
                metrics.update(self._calculate_liquidity_latest_yoy(historical_for_detailed_trends))
        
        # 5. Calculate CAGR trends for key_metrics
        cagr_trends = self._calculate_cagr_metrics(prepared_historical) if prepared_historical else {}
        
        # 6. Calculate score (optional)
        score = 0
        interpretation = ""
        if include_rules:
            score, interpretation = self.calculate_score(rules_results)
        
        # 7. Build key_metrics with year and CAGRs
        key_metrics = {"year": year} if year else {}
        key_metrics.update(metrics)
        key_metrics.update(cagr_trends)

        # Liquidity: enforce the requested key_metrics contract
        if self.module_id == "liquidity":
            allowed = {
                "year",
                "cash",
                "marketable_securities",
                "current_ratio",
                "quick_ratio",
                "defensive_interval_ratio_days",
                "cash_ratio",
                "ocf_to_cl",
                "ocf_to_total_debt",
                "interest_coverage_ocf",
                "cash_coverage_st_debt",
                "current_ratio_yoy_latest",
                "cash_yoy_latest",
                "ocf_yoy_latest",
            }
            key_metrics = {k: v for k, v in key_metrics.items() if k in allowed}
        
        # 8. Generate analysis narrative bullets (optional)
        analysis_narrative: List[str] = []
        if include_rules:
            analysis_narrative = self._generate_analysis_narrative(metrics, cagr_trends, rules_results)
        
        # 9. Extract red_flags and positive_points from rules (optional)
        red_flags: List[Dict[str, Any]] = []
        positive_points: List[str] = []
        if include_rules:
            for r in rules_results:
                if r.flag == "RED":
                    red_flags.append({
                        "rule_id": r.rule_id,
                        "rule_name": r.rule_name,
                        "metric": r.metric,
                        "year": r.year,
                        "flag": r.flag,
                        "value": r.value,
                        "threshold": r.threshold,
                        "reason": r.reason,
                        "implication": r.implication,
                        "risk_level": r.risk_level
                    })
            positive_points = [r.reason for r in rules_results if r.flag == "GREEN"]
        
        # 10. Generate LLM narrative if requested (and rules enabled)
        narrative = None
        if include_rules and generate_llm_narrative:
            # narrative = self.generate_narrative(metrics, rules_results, detailed_trends, score)
            narrative = "[LLM narrative generation is currently disabled.]"
        
        return ModuleOutput(
            module=self.name,
            company=company_name,
            year=year,
            key_metrics=key_metrics,
            trends=detailed_trends,
            analysis_narrative=analysis_narrative,
            red_flags=red_flags,
            positive_points=positive_points,
            rules=rules_results,
            score=score,
            score_interpretation=interpretation,
            llm_narrative=narrative
        )

    def _calculate_detailed_trends(self, historical_data: List[Dict[str, float]]) -> Dict[str, TrendDetail]:
        """Calculate detailed trends with YoY breakdown for each metric."""
        if not historical_data or len(historical_data) < 2:
            return {}

        detailed_trends: Dict[str, Any] = {}

        # Fields to track for trends based on module
        trend_fields = self._get_trend_fields()

        for field_name, display_name in trend_fields.items():
            values: Dict[str, Any] = {}
            yoy_growth: Dict[str, Any] = {}

            # Extract values for each year (reverse so Y is current)
            for i, data in enumerate(reversed(historical_data)):
                year_label = "Y" if i == 0 else f"Y-{i}"
                val = data.get(field_name, 0)

                # Liquidity formatting to match expected response examples.
                if self.module_id == "liquidity":
                    if field_name == "current_ratio" and isinstance(val, (int, float)):
                        val = round(float(val), 2)
                    elif isinstance(val, float) and val.is_integer():
                        val = int(val)

                values[year_label] = val

            # Calculate YoY growth
            year_labels = list(values.keys())
            for i in range(len(year_labels) - 1):
                current_label = year_labels[i]
                prev_label = year_labels[i + 1]
                current_val = values[current_label]
                prev_val = values[prev_label]

                if prev_val and prev_val != 0:
                    growth = ((current_val - prev_val) / abs(prev_val)) * 100
                    yoy_growth[f"{current_label}_vs_{prev_label}"] = round(growth, 2)

            # Generate insight
            insight = self._generate_trend_insight(display_name, values, yoy_growth)

            if values and any(v not in (None, 0) for v in values.values()):
                detailed_trends[field_name] = TrendDetail(
                    values=values,
                    yoy_growth_pct=yoy_growth,
                    insight=insight,
                )

        # Optional nested / special trends (YAML-driven; code-dispatched via registry)
        detailed_special_trends = self.config.get("detailed_special_trends", []) or []
        for trend_name in detailed_special_trends:
            handler = self.special_trend_handlers.get(trend_name)
            if not handler:
                continue
            try:
                detailed_trends.update(handler(historical_data))
            except Exception:
                # Special trends should never crash the module output.
                continue

        return detailed_trends

    def _special_trend_receivables_vs_revenue(self, historical_data: List[Dict[str, float]]) -> Dict[str, Any]:
        # Build newest-first series
        recv_new = [
            d.get("receivables") if d.get("receivables") is not None else d.get("trade_receivables")
            for d in reversed(historical_data)
        ]
        rev_new = [d.get("revenue") for d in reversed(historical_data)]

        recv_yoy = self._compute_yoy_map_pct(recv_new)
        rev_yoy = self._compute_yoy_map_pct(rev_new)

        ratio_list: List[Optional[float]] = []
        for rcv, rev in zip(recv_new, rev_new):
            if rev in (0, None) or rcv is None:
                ratio_list.append(None)
            else:
                ratio_list.append(rcv / rev)

        ratio_yoy = self._compute_yoy_map_pct(ratio_list)
        return {
            "receivables_vs_revenue": {
                "receivable_yoy": recv_yoy,
                "revenue_yoy": rev_yoy,
                "receivable_to_revenue_pct": self._build_values_dict(ratio_list),
                "receivable_to_revenue_yoy": ratio_yoy,
                "insight": self._generate_recv_vs_revenue_insight(recv_yoy, rev_yoy, ratio_list),
            }
        }

    def _aiqm_cap_and_cwip_series_newest_first(
        self, historical_data: List[Dict[str, float]]
    ) -> tuple[List[Optional[float]], List[Optional[float]]]:
        # Oldest-first series
        gb_old = [d.get("gross_block") for d in historical_data]
        cwip_old = [d.get("cwip") for d in historical_data]

        capitalization_old: List[Optional[float]] = [None]
        for i in range(1, len(historical_data)):
            gb0, gb1 = gb_old[i - 1], gb_old[i]
            cw0, cw1 = cwip_old[i - 1], cwip_old[i]
            if gb0 is None or gb1 is None or cw0 is None or cw1 is None:
                capitalization_old.append(None)
                continue
            capitalization_old.append((gb1 - gb0) - (cw1 - cw0))

        # Newest-first for labeling
        cap_new = list(reversed(capitalization_old))
        cwip_new = list(reversed(cwip_old))
        return cap_new, cwip_new

    def _special_trend_aiqm_capitalization(self, historical_data: List[Dict[str, float]]) -> Dict[str, Any]:
        cap_new, _cwip_new = self._aiqm_cap_and_cwip_series_newest_first(historical_data)
        cap_yoy = self._compute_yoy_map_pct(cap_new)
        cap_values = self._build_values_dict(cap_new)
        cap_insight = self._generate_trend_insight("Capitalization", cap_values, cap_yoy)
        return {
            "capitalization": {
                "values": cap_values,
                "yoy_growth_pct": cap_yoy,
                "insight": cap_insight,
            }
        }

    def _special_trend_aiqm_cwip_vs_capitalization(self, historical_data: List[Dict[str, float]]) -> Dict[str, Any]:
        cap_new, cwip_new = self._aiqm_cap_and_cwip_series_newest_first(historical_data)
        ratio_new: List[Optional[float]] = []
        for cw, cap in zip(cwip_new, cap_new):
            if cw is None or cap in (None, 0):
                ratio_new.append(None)
            else:
                ratio_new.append(cw / cap)
        return {
            "cwip_vs_capitalization": {
                "values": self._build_values_dict(ratio_new),
                "insight": "CWIP vs Capitalization ratio evaluated.",
            }
        }

    def _special_trend_risk_scenarios(self, historical_data: List[Dict[str, float]]) -> Dict[str, Any]:
        return self._calculate_risk_scenarios(historical_data)

    def _special_trend_leverage_financial_risk(self, historical_data: List[Dict[str, float]]) -> Dict[str, Any]:
        return self._calculate_leverage_financial_risk_trends(historical_data)

    def _calculate_leverage_financial_risk_trends(self, historical_data: List[Dict[str, float]]) -> Dict[str, Any]:
        """Nested leverage trend block matching the provided lfr_trends.py structure."""
        if not historical_data:
            return {}

        def parse_tax_rate(tax_value: Any) -> float:
            if tax_value is None:
                return 0.0
            if isinstance(tax_value, str):
                s = tax_value.strip()
                if not s:
                    return 0.0
                if "%" in s:
                    try:
                        return float(s.replace("%", "").strip()) / 100.0
                    except ValueError:
                        return 0.0
                try:
                    v = float(s)
                except ValueError:
                    return 0.0
                return (v / 100.0) if v > 1 else v
            if isinstance(tax_value, (int, float)):
                v = float(tax_value)
                return (v / 100.0) if v > 1 else v
            return 0.0

        # Build per-year canonical metrics
        per_year: Dict[int, Dict[str, Any]] = {}
        for d in historical_data:
            year = d.get("year")
            if year is None:
                continue

            total_debt = d.get("borrowings")
            if total_debt is None:
                total_debt = (d.get("short_term_debt") or 0) + (d.get("long_term_debt") or 0) + (d.get("lease_liabilities") or 0)
            total_debt = total_debt or 0

            short_term_debt = d.get("short_term_debt") or 0
            cash = d.get("cash_equivalents")
            if cash is None:
                cash = d.get("cash_and_equivalents")
            cash = cash or 0

            equity = d.get("equity")
            if equity is None:
                equity = d.get("total_equity")
            equity = equity or 0

            ebit = d.get("operating_profit")
            if ebit is None:
                ebit = d.get("ebit")
            ebit = ebit or 0

            depreciation = d.get("depreciation") or 0
            ebitda = ebit + depreciation

            interest_cost = d.get("interest")
            if interest_cost is None:
                interest_cost = d.get("finance_cost")
            interest_cost = interest_cost or 0

            profit_before_tax = d.get("profit_before_tax") or 0
            tax_rate = parse_tax_rate(d.get("tax"))
            tax_amount = round(profit_before_tax * tax_rate, 2)

            net_debt = total_debt - cash
            ffo = ebitda - interest_cost - tax_amount

            de_ratio = (total_debt / equity) if equity else 0.0
            debt_ebitda = (total_debt / ebitda) if ebitda else 0.0
            net_debt_ebitda = (net_debt / ebitda) if ebitda else 0.0
            interest_coverage = (ebit / interest_cost) if interest_cost else 0.0
            st_debt_ratio = (short_term_debt / total_debt) if total_debt else 0.0
            ffo_coverage = (ffo / interest_cost) if interest_cost else 0.0

            per_year[int(year)] = {
                "year": int(year),
                "total_debt": round(total_debt, 2),
                "short_term_debt": round(short_term_debt, 2),
                "cash": round(cash, 2),
                "equity": round(equity, 2),
                "ebit": round(ebit, 2),
                "ebitda": round(ebitda, 2),
                "interest_cost": round(interest_cost, 2),
                "taxes": tax_amount,
                "net_debt": round(net_debt, 2),
                "ffo": round(ffo, 2),
                "de_ratio": round(de_ratio, 6),
                "debt_ebitda": round(debt_ebitda, 6),
                "net_debt_ebitda": round(net_debt_ebitda, 6),
                "interest_coverage": round(interest_coverage, 6),
                "st_debt_ratio": round(st_debt_ratio, 6),
                "ffo_coverage": round(ffo_coverage, 6),
            }

        if not per_year:
            return {}

        def _build_values(key: str) -> Dict[str, float]:
            years = sorted(per_year.keys(), reverse=True)
            labels = ["Y", "Y-1", "Y-2", "Y-3", "Y-4"]
            values: Dict[str, float] = {}
            for i, label in enumerate(labels):
                if i < len(years):
                    y = years[i]
                    values[label] = round(float(per_year[y].get(key, 0.0) or 0.0), 4)
                else:
                    values[label] = 0.0
            return values

        def _generate_trend_insight(values: Dict[str, float], metric_name: str) -> str:
            series = list(values.values())
            latest = series[0]
            oldest = series[-1]
            if latest < oldest:
                return f"{metric_name} has improved over the past five years, indicating strengthening financial profile."
            if latest > oldest:
                return f"{metric_name} has increased over the past five years, indicating rising leverage or risk."
            return f"{metric_name} has remained broadly stable over the period."

        # BASIC
        de_ratio = _build_values("de_ratio")
        debt_ebitda = _build_values("debt_ebitda")
        interest_cov = _build_values("interest_coverage")

        # ADVANCED
        net_debt = _build_values("net_debt")
        net_debt_ebitda = _build_values("net_debt_ebitda")
        ffo_cov = _build_values("ffo_coverage")
        st_ratio = _build_values("st_debt_ratio")

        return {
            "basic leverage metrics": {
                "debt_to_equity": {
                    "total_debt": {"values": _build_values("total_debt")},
                    "equity": {"values": _build_values("equity")},
                    "debt to equity": {"values": de_ratio},
                    "insight": _generate_trend_insight(de_ratio, "Debt-to-Equity"),
                },
                "debt_to_ebitda": {
                    "total_debt": {"values": _build_values("total_debt")},
                    "ebitda": {"values": _build_values("ebitda")},
                    "debt to ebitda": {"values": debt_ebitda},
                    "insight": _generate_trend_insight(debt_ebitda, "Debt-to-EBITDA"),
                },
                "interest_coverage": {
                    "ebit": {"values": _build_values("ebit")},
                    "interest_cost": {"values": _build_values("interest_cost")},
                    "interest coverage ratio": {"values": interest_cov},
                    "insight": _generate_trend_insight(interest_cov, "Interest Coverage"),
                },
            },
            "advanced fitch / s&p style metrics": {
                "net_debt": {
                    "total_debt": {"values": _build_values("total_debt")},
                    "cash": {"values": _build_values("cash")},
                    "net debt": {"values": net_debt},
                    "insight": _generate_trend_insight(net_debt, "Net Debt"),
                },
                "net_debt_to_ebitda": {
                    "net_debt": {"values": _build_values("net_debt")},
                    "ebitda": {"values": _build_values("ebitda")},
                    "net debt to ebitda": {"values": net_debt_ebitda},
                    "insight": _generate_trend_insight(net_debt_ebitda, "Net Debt-to-EBITDA"),
                },
                "ffo_coverage": {
                    "ebitda": {"values": _build_values("ebitda")},
                    "interest_cost": {"values": _build_values("interest_cost")},
                    "taxes": {"values": _build_values("taxes")},
                    "ffo": {"values": _build_values("ffo")},
                    "ffo coverage": {"values": ffo_cov},
                    "insight": _generate_trend_insight(ffo_cov, "FFO Coverage"),
                },
                "debt_service_burden": {
                    "short_term_debt": {"values": _build_values("short_term_debt")},
                    "total_debt": {"values": _build_values("total_debt")},
                    "debt service burden": {"values": st_ratio},
                    "insight": _generate_trend_insight(st_ratio, "Debt Service Burden"),
                },
            },
            "short-term debt dependence": {
                "short_term_debt": {"values": _build_values("short_term_debt")},
                "total_debt": {"values": _build_values("total_debt")},
                "st debt share": {"values": st_ratio},
                "insight": _generate_trend_insight(st_ratio, "Short-Term Debt Dependence"),
            },
        }

    def _calculate_risk_scenarios(self, historical_data: List[Dict[str, float]]) -> Dict[str, Any]:
        """Compute risk scenario detection output from 5Y historical data.

        Produces nested blocks matching the provided reference structure:
        - zombie_company
        - window_dressing
        - asset_stripping
        - loan_evergreening
        - circular_trading
        """
        if not historical_data or len(historical_data) < 2:
            return {}

        # Historical data is oldest-first
        years = [d.get("year") for d in historical_data if d.get("year") is not None]
        if not years:
            return {}

        # Build per-year normalized metrics
        yearly: Dict[int, Dict[str, Any]] = {}
        for d in historical_data:
            year = d.get("year")
            if year is None:
                continue

            revenue = d.get("revenue") or 0
            ebit = d.get("operating_profit") if d.get("operating_profit") is not None else (d.get("ebit") or 0)
            interest = d.get("interest") if d.get("interest") is not None else (d.get("finance_cost") or 0)
            net_profit = d.get("net_profit") if d.get("net_profit") is not None else (d.get("pat") or 0)
            other_income = d.get("other_income") or 0
            depreciation = d.get("depreciation") or 0
            ebitda = (ebit or 0) + (depreciation or 0)

            cfo = d.get("cash_from_operating_activity")
            if cfo is None:
                cfo = d.get("operating_cash_flow")
            cfo = cfo or 0

            dividends_paid = d.get("dividends_paid")
            if dividends_paid is None:
                dividends_paid = d.get("dividend_paid")
            dividends_paid = dividends_paid or 0

            fixed_assets = d.get("fixed_assets") or 0
            total_assets = d.get("total_assets") or 0
            receivables = d.get("trade_receivables") or 0

            cash = d.get("cash_equivalents")
            if cash is None:
                cash = d.get("cash_and_equivalents")
            cash = cash or 0

            borrowings = d.get("borrowings")
            if borrowings is None:
                # Try total debt rollup
                borrowings = d.get("total_debt")
            if borrowings is None:
                borrowings = (d.get("short_term_debt") or 0) + (d.get("long_term_debt") or 0) + (d.get("lease_liabilities") or 0)
            borrowings = borrowings or 0
            net_debt = borrowings - cash

            proceeds_from_borrowings = d.get("proceeds_from_borrowings") or 0
            repayment_of_borrowings = abs(d.get("repayment_of_borrowings") or 0)

            interest_paid = abs(d.get("interest_paid_fin") or 0)
            interest_capitalized = d.get("interest_capitalized") or 0
            short_term_debt = d.get("short_term_debt") or 0

            rpt_sales = d.get("related_party_sales") or 0
            rpt_receivables = d.get("related_party_receivables") or 0

            yearly[int(year)] = {
                "revenue": revenue,
                "ebit": ebit or 0,
                "interest": interest or 0,
                "net_profit": net_profit or 0,
                "other_income": other_income,
                "depreciation": depreciation,
                "ebitda": ebitda,
                "cfo": cfo,
                "dividends_paid": dividends_paid,
                "fixed_assets": fixed_assets,
                "total_assets": total_assets,
                "receivables": receivables,
                "cash": cash,
                "net_debt": net_debt,
                "proceeds_from_borrowings": proceeds_from_borrowings,
                "repayment_of_borrowings": repayment_of_borrowings,
                "interest_paid": interest_paid,
                "interest_capitalized": interest_capitalized,
                "short_term_debt": short_term_debt,
                "rpt_sales": rpt_sales,
                "rpt_receivables": rpt_receivables,
            }

        years_sorted = sorted(yearly.keys())
        if len(years_sorted) < 2:
            return {}

        def ym(key: str) -> Dict[str, Any]:
            # Map latest to Y, previous to Y-1, etc. Supports <5 years gracefully.
            out: Dict[str, Any] = {}
            for idx, y in enumerate(reversed(years_sorted[-5:])):
                out["Y" if idx == 0 else f"Y-{idx}"] = yearly[y].get(key)
            return out

        # ============================
        # 3.1 ZOMBIE COMPANY
        # ============================
        ebit_below, cfo_below, debt_profit = [], [], []
        for i in range(1, len(years_sorted)):
            y, p = years_sorted[i], years_sorted[i - 1]

            if yearly[y]["ebit"] < yearly[y]["interest"]:
                ebit_below.append(y)
            if yearly[y]["cfo"] < yearly[y]["interest"]:
                cfo_below.append(y)
            if yearly[y]["net_debt"] > yearly[p]["net_debt"] and yearly[y]["net_profit"] < yearly[p]["net_profit"]:
                debt_profit.append(y)

        zombie_company = {
            "ebit_vs_interest": {
                "values": {"ebit": ym("ebit"), "interest": ym("interest")},
                "comparison": {
                    "years_below": ebit_below,
                    "rule_triggered": len(ebit_below) >= 2,
                    "insight": (
                        "EBIT has been insufficient to cover interest for multiple years."
                        if len(ebit_below) >= 2
                        else "EBIT consistently exceeds interest expense, indicating sufficient accounting-level debt servicing capacity."
                    ),
                },
            },
            "cfo_vs_interest": {
                "values": {"cfo": ym("cfo"), "interest": ym("interest")},
                "comparison": {
                    "years_below": cfo_below,
                    "rule_triggered": len(cfo_below) >= 2,
                    "insight": (
                        "Operating cash flows failed to cover interest obligations for multiple years, indicating reliance on refinancing."
                        if len(cfo_below) >= 2
                        else "Operating cash flows are sufficient to service interest."
                    ),
                },
            },
            "debt_vs_profit": {
                "values": {"net_debt": ym("net_debt"), "net_profit": ym("net_profit")},
                "comparison": {
                    "overlap_years": debt_profit,
                    "rule_triggered": len(debt_profit) >= 2,
                    "insight": (
                        "Debt increased while profitability weakened, signaling a developing debt spiral."
                        if len(debt_profit) >= 2
                        else "Debt and profitability trends remain aligned."
                    ),
                },
            },
        }

        # ============================
        # 3.2 WINDOW DRESSING
        # ============================
        cash_spike, profit_spike, recv_profit, one_off = [], [], [], []
        for i in range(1, len(years_sorted)):
            y, p = years_sorted[i], years_sorted[i - 1]

            if yearly[p]["cash"] > 0 and (yearly[y]["cash"] - yearly[p]["cash"]) / yearly[p]["cash"] > 0.30:
                cash_spike.append(y)
            if yearly[p]["net_profit"] > 0 and (yearly[y]["net_profit"] - yearly[p]["net_profit"]) / yearly[p]["net_profit"] > 0.25:
                profit_spike.append(y)
            if yearly[y]["receivables"] < yearly[p]["receivables"] and yearly[y]["net_profit"] > yearly[p]["net_profit"]:
                recv_profit.append(y)
            if yearly[y].get("other_income", 0) and yearly[y]["net_profit"] != 0:
                if abs(yearly[y]["other_income"]) / abs(yearly[y]["net_profit"]) > 0.20:
                    one_off.append(y)

        window_dressing = {
            "cash_spike": {
                "comparison": {
                    "flagged_years": cash_spike,
                    "rule_triggered": bool(cash_spike),
                    "insight": (
                        "Sudden year-end cash spikes suggest possible window dressing."
                        if cash_spike
                        else "No abnormal year-end cash spikes were observed."
                    ),
                }
            },
            "profit_spike": {
                "comparison": {
                    "flagged_years": profit_spike,
                    "rule_triggered": bool(profit_spike),
                    "insight": (
                        "Sharp profit increases without proportional revenue growth may indicate earnings beautification."
                        if profit_spike
                        else "Profit growth appears consistent with business performance."
                    ),
                }
            },
            "one_off_income": {
                "comparison": {
                    "flagged_years": one_off,
                    "rule_triggered": bool(one_off),
                    "insight": (
                        "One-off income materially impacted reported profits."
                        if one_off
                        else "One-off income did not materially distort reported profits."
                    ),
                }
            },
            "receivable_decline_profit_spike": {
                "comparison": {
                    "flagged_years": recv_profit,
                    "rule_triggered": bool(recv_profit),
                    "insight": (
                        "Profit growth alongside receivable decline suggests possible cosmetic working-capital management."
                        if recv_profit
                        else "Receivables and profit trends remain consistent."
                    ),
                }
            },
            "last_quarter_volatility": {
                "status": "NOT_AVAILABLE",
                "insight": "Quarterly financial data is not available, preventing volatility assessment."
            },
        }

        # ============================
        # 3.3 ASSET STRIPPING
        # ============================
        asset_decline, debt_asset = [], []
        for i in range(1, len(years_sorted)):
            y, p = years_sorted[i], years_sorted[i - 1]
            if yearly[y]["fixed_assets"] < yearly[p]["fixed_assets"]:
                asset_decline.append(y)
            if yearly[y]["net_debt"] > yearly[p]["net_debt"] and yearly[y]["fixed_assets"] < yearly[p]["fixed_assets"]:
                debt_asset.append(y)

        asset_stripping = {
            "fixed_asset_decline": {
                "comparison": {
                    "flagged_years": asset_decline,
                    "rule_triggered": len(asset_decline) >= 2,
                    "insight": (
                        "Sustained multi-year decline in fixed assets indicates potential asset stripping."
                        if len(asset_decline) >= 2
                        else "No sustained multi-year decline in fixed assets was observed."
                    ),
                }
            },
            "debt_vs_assets": {
                "comparison": {
                    "flagged_years": debt_asset,
                    "rule_triggered": len(debt_asset) >= 2,
                    "insight": (
                        "Debt increased while assets shrank, indicating asset base hollowing."
                        if len(debt_asset) >= 2
                        else "Debt movements remain broadly aligned with asset levels."
                    ),
                }
            },
            "dividends_vs_assets": {
                "status": "NOT_APPLICABLE",
                "insight": "Dividend payouts are not significant enough to indicate asset stripping.",
            },
            "promoter_extraction": {
                "status": "DATA_LIMITED",
                "insight": "No direct data on promoter withdrawals beyond related-party disclosures.",
            },
        }

        # ============================
        # 3.4 LOAN EVERGREENING
        # ============================
        rollover, debt_ebitda = [], []
        for i in range(1, len(years_sorted)):
            y, p = years_sorted[i], years_sorted[i - 1]
            if yearly[y]["proceeds_from_borrowings"] > yearly[y]["repayment_of_borrowings"]:
                rollover.append(y)
            if yearly[y]["net_debt"] > yearly[p]["net_debt"] and yearly[y]["ebitda"] <= yearly[p]["ebitda"]:
                debt_ebitda.append(y)

        loan_evergreening = {
            "loan_rollover": {
                "values": {
                    "borrowings_proceeds": ym("proceeds_from_borrowings"),
                    "borrowings_repaid": ym("repayment_of_borrowings"),
                },
                "comparison": {
                    "flagged_years": rollover,
                    "rule_triggered": bool(rollover),
                    "insight": (
                        "New borrowings consistently exceeded repayments, indicating refinancing-driven debt servicing."
                        if rollover
                        else "Borrowings appear to be repaid in a disciplined manner."
                    ),
                },
            },
            "debt_vs_ebitda": {
                "values": {"net_debt": ym("net_debt"), "ebitda": ym("ebitda")},
                "comparison": {
                    "overlap_years": debt_ebitda,
                    "rule_triggered": len(debt_ebitda) >= 2,
                    "insight": (
                        "Debt increased while EBITDA stagnated, indicating evergreening risk."
                        if len(debt_ebitda) >= 2
                        else "Debt growth has largely been supported by EBITDA expansion."
                    ),
                },
            },
            "principal_repayment": {
                "status": "NOT_COMPUTABLE",
                "insight": "Short-term and long-term principal repayment split is not disclosed.",
            },
            "interest_capitalization": {
                "status": "NOT_COMPUTABLE",
                "insight": "No disclosure of interest capitalization into assets or CWIP.",
            },
        }

        # ============================
        # 3.5 CIRCULAR TRADING
        # ============================
        sales_cfo, recv_rev = [], []
        for i in range(1, len(years_sorted)):
            y, p = years_sorted[i], years_sorted[i - 1]
            if yearly[y]["revenue"] > yearly[p]["revenue"] and yearly[y]["cfo"] < yearly[p]["cfo"]:
                sales_cfo.append(y)
            if (yearly[y]["receivables"] - yearly[p]["receivables"]) > (yearly[y]["revenue"] - yearly[p]["revenue"]):
                recv_rev.append(y)

        circular_trading = {
            "sales_up_cfo_down": {
                "comparison": {
                    "flagged_years": sales_cfo,
                    "rule_triggered": bool(sales_cfo),
                    "insight": (
                        "Revenue growth without operating cash flow support suggests potential revenue inflation."
                        if sales_cfo
                        else "Revenue growth is supported by operating cash flows."
                    ),
                }
            },
            "receivables_vs_revenue": {
                "comparison": {
                    "flagged_years": recv_rev,
                    "rule_triggered": bool(recv_rev),
                    "insight": (
                        "Receivables increased faster than revenue, indicating aggressive revenue recognition."
                        if recv_rev
                        else "Receivables growth is aligned with revenue."
                    ),
                }
            },
            "rpt_sales_spike": {
                "status": "DATA_LIMITED",
                "insight": "Insufficient related-party sales data to assess abnormal spikes.",
            },
            "rpt_receivables_high": {
                "status": "DATA_LIMITED",
                "insight": "Related-party receivable disclosure is insufficient for threshold analysis.",
            },
            "rpt_balance_rising": {
                "status": "DATA_LIMITED",
                "insight": "Long-term trend in related-party balances cannot be reliably established.",
            },
        }

        return {
            "zombie_company": zombie_company,
            "window_dressing": window_dressing,
            "asset_stripping": asset_stripping,
            "loan_evergreening": loan_evergreening,
            "circular_trading": circular_trading,
        }
    
    def _get_trend_fields(self) -> Dict[str, str]:
        """Get fields to track for trends based on module type"""
        # If the module explicitly defines `detailed_trend_fields` in YAML,
        # respect it even when it's empty (allows modules to opt out).
        if "detailed_trend_fields" in (self.config or {}):
            config_fields = self.config.get("detailed_trend_fields")
            if isinstance(config_fields, dict):
                return {str(k): str(v) for k, v in config_fields.items()}

        if self.module_id == "borrowings":
            return {
                "short_term_debt": "Short Term Debt",
                "long_term_debt": "Long Term Debt",
                "finance_cost": "Finance Cost",
                "total_debt": "Total Debt",
                "ebitda": "EBITDA"
            }
        elif self.module_id == "equity_funding_mix":
            return {
                "reserves": "Retained Earnings",
                "net_worth": "Net Worth",
                "pat": "PAT",
                "share_capital": "Share Capital"
            }
        else:
            # Default fields
            return {
                "revenue": "Revenue",
                "pat": "PAT",
                "ebitda": "EBITDA"
            }

    def _compute_yoy_map_pct(self, newest_first: List[Optional[float]]) -> Dict[str, Optional[float]]:
        """Compute YoY % changes for a newest-first series using labels Y_vs_Y-1, etc."""
        yoy: Dict[str, Optional[float]] = {}
        for idx in range(len(newest_first) - 1):
            curr = newest_first[idx]
            prev = newest_first[idx + 1]
            left = "Y" if idx == 0 else f"Y-{idx}"
            right = f"Y-{idx+1}"
            key = f"{left}_vs_{right}"
            if prev in (None, 0) or curr is None:
                yoy[key] = None
            else:
                yoy[key] = round(((curr - prev) / abs(prev)) * 100, 2)
        return yoy

    def _build_values_dict(self, newest_first: List[Optional[float]]) -> Dict[str, Optional[float]]:
        out: Dict[str, Optional[float]] = {}
        for i, v in enumerate(newest_first):
            out["Y" if i == 0 else f"Y-{i}"] = v
        return out

    def _generate_recv_vs_revenue_insight(
        self,
        recv_yoy: Dict[str, Optional[float]],
        rev_yoy: Dict[str, Optional[float]],
        ratio_list: List[Optional[float]],
    ) -> str:
        recv_vals = [v for v in recv_yoy.values() if v is not None]
        rev_vals = [v for v in rev_yoy.values() if v is not None]
        ratio_vals = [v for v in ratio_list if v is not None]

        if not recv_vals or not rev_vals:
            return "Insufficient data for receivables vs revenue analysis."

        avg_recv = sum(recv_vals) / len(recv_vals)
        avg_rev = sum(rev_vals) / len(rev_vals)
        avg_ratio = (sum(ratio_vals) / len(ratio_vals)) if ratio_vals else None
        spread = avg_recv - avg_rev

        # avg_recv/avg_rev are YoY% already.
        spread_pct = round(spread, 2)

        if avg_recv > 0 and avg_rev < 0:
            return f"Receivables rising while revenue falling — major collection stress (spread: {spread_pct} pp)."
        if spread > 10:
            return f"Receivables growing much faster than revenue — collection risk increasing (spread: {spread_pct} pp)."
        if 3 < spread <= 10:
            return f"Receivables slightly outpacing revenue (spread: {spread_pct} pp). Monitor working capital."
        if -3 <= spread <= 3:
            return "Receivables growth aligned with revenue — stable collection efficiency."
        if spread < -3:
            return "Receivables growing slower than revenue — collection efficiency improving."
        if avg_ratio is not None:
            return f"Receivables vs revenue trend appears mixed (avg receivables/revenue: {avg_ratio:.2f})."
        return "Receivables vs revenue trend appears mixed."
    
    def _generate_trend_insight(self, metric_name: str, values: Dict[str, float], 
                                yoy_growth: Dict[str, float]) -> str:
        """Generate insight text for a trend"""
        if not yoy_growth:
            return f"Insufficient data for {metric_name} trend analysis."

        growth_values = [v for v in yoy_growth.values() if v is not None]
        if not growth_values:
            return f"Insufficient data for {metric_name} trend analysis."
        avg_growth = sum(growth_values) / len(growth_values)
        
        # Determine pattern
        if len(growth_values) >= 2:
            if growth_values[0] > growth_values[-1] + 2:
                pattern = "accelerating growth"
            elif growth_values[0] < growth_values[-1] - 2:
                pattern = "decelerating growth"
            elif all(g > 0 for g in growth_values):
                pattern = "consistent growth"
            elif all(g < 0 for g in growth_values):
                pattern = "consistent decline"
            else:
                pattern = "mixed trend"
        else:
            pattern = "limited data"
        
        return f"{metric_name} shows {pattern} pattern (avg: {avg_growth:.1f}%)."

    def _calculate_liquidity_latest_yoy(self, enriched_historical: List[Dict[str, float]]) -> Dict[str, Optional[float]]:
        """Compute YoY % for the latest year for selected liquidity series.

        Uses unrounded values from the last two periods.
        """
        if not enriched_historical or len(enriched_historical) < 2:
            return {}

        prev = enriched_historical[-2]
        curr = enriched_historical[-1]

        def yoy(curr_val: Any, prev_val: Any) -> Optional[float]:
            if prev_val in (None, 0) or curr_val is None:
                return None
            try:
                return ((float(curr_val) - float(prev_val)) / float(prev_val)) * 100.0
            except (TypeError, ValueError, ZeroDivisionError):
                return None

        return {
            "current_ratio_yoy_latest": yoy(curr.get("current_ratio"), prev.get("current_ratio")),
            "cash_yoy_latest": yoy(curr.get("cash_and_equivalents"), prev.get("cash_and_equivalents")),
            "ocf_yoy_latest": yoy(curr.get("operating_cash_flow"), prev.get("operating_cash_flow")),
        }
    
    def _calculate_cagr_metrics(self, historical_data: List[Dict[str, float]]) -> Dict[str, float]:
        """Calculate CAGR for key metrics, aggregated by module"""
        if not historical_data or len(historical_data) < 2:
            return {}

        # Liquidity output contract should not include generic CAGRs.
        if self.module_id == "liquidity":
            return {}
        
        cagr_metrics = {}
        n = len(historical_data)
        
        # Module-specific CAGR aggregation - maps output names to field names
        if self.module_id == "equity_funding_mix":
            # For equity module, aggregate from specific fields
            agg_mapping = {
                "equity_cagr": "share_capital",  # Proxy for equity
                "debt_cagr": "debt",
                "retained_cagr": "retained_earnings",
                "roe_cagr": "roe",
                "pat_cagr": "pat"
            }
        elif self.module_id == "borrowings":
            # For borrowings module
            agg_mapping = {
                "debt_cagr": "total_debt",
                "ebitda_cagr": "ebitda",
                "revenue_cagr": "revenue",
                "finance_cost_cagr": "finance_cost"
            }
        elif self.module_id == "quality_of_earnings":
            agg_mapping = {
                "ocf_cagr": "operating_cash_flow",
                "net_income_cagr": "net_income",
                "receivables_cagr": "receivables",
                "revenue_cagr": "revenue",
            }
        elif self.module_id == "asset_intangible_quality":
            agg_mapping = {
                "intangible_cagr": "intangible_assets",
                "revenue_cagr": "revenue",
                "operating_asset_cagr": "gross_block",
            }
        else:
            # Generic mapping for other modules
            agg_mapping = {
                "revenue_cagr": "revenue",
                "pat_cagr": "pat",
                "ebitda_cagr": "ebitda",
                "debt_cagr": "total_debt"
            }
        
        # Calculate CAGRs
        for cagr_name, field in agg_mapping.items():
            start_val = historical_data[0].get(field, 0)
            end_val = historical_data[-1].get(field, 0)
            
            # Skip if start is 0 or None, or if end is 0 or None
            if not start_val or start_val <= 0 or not end_val or end_val <= 0:
                cagr_metrics[cagr_name] = None
                continue
            
            # For ROE with mixed signs, skip CAGR
            if field == "roe" and start_val * end_val <= 0:
                cagr_metrics[cagr_name] = None
                continue
            
            try:
                cagr = ((end_val / start_val) ** (1 / (n - 1)) - 1) * 100
                cagr_metrics[cagr_name] = round(cagr, 2)
            except (ZeroDivisionError, ValueError):
                cagr_metrics[cagr_name] = None

        # Derived comparison CAGR (only when both are available)
        if self.module_id == "asset_intangible_quality":
            ic = cagr_metrics.get("intangible_cagr")
            rc = cagr_metrics.get("revenue_cagr")
            cagr_metrics["intangible_cagr_vs_revenue_cagr"] = (round(ic - rc, 2) if ic is not None and rc is not None else None)
        
        return cagr_metrics
    
    def _generate_analysis_narrative(self, metrics: Dict[str, float], cagr_metrics: Dict[str, float],
                                     rules_results: List[RuleResult]) -> List[str]:
        """Generate bullet-point analysis narrative"""
        narrative = []
        
        if self.module_id == "borrowings":
            debt_cagr = cagr_metrics.get("debt_cagr", 0)
            ebitda_cagr = cagr_metrics.get("ebitda_cagr", 0)
            debt_ebitda = metrics.get("debt_ebitda", 0) or 0
            icr = metrics.get("interest_coverage", 0) or 0
            maturity_lt_1y = (metrics.get("maturity_lt_1y_pct") or 0) * 100
            floating = (metrics.get("floating_share") or 0) * 100
            
            narrative.append(f"Total debt CAGR {debt_cagr:.1f}% vs EBITDA CAGR {ebitda_cagr:.1f}%.")
            narrative.append(f"Debt/EBITDA at {debt_ebitda:.1f}x.")
            narrative.append(f"Interest coverage at {icr:.1f}x.")
            narrative.append(f"{maturity_lt_1y:.0f}% of debt matures within one year.")
            narrative.append(f"Floating rate exposure at {floating:.0f}%.")
            
        elif self.module_id == "equity_funding_mix":
            roe = metrics.get("roe", 0) * 100 if metrics.get("roe") else 0
            payout = metrics.get("payout_ratio", 0) * 100 if metrics.get("payout_ratio") else 0
            de_ratio = metrics.get("debt_to_equity", 0) or 0
            roe_cagr = cagr_metrics.get("roe_cagr", 0) or 0
            retained_cagr = cagr_metrics.get("retained_cagr", 0) or 0
            pat_cagr = cagr_metrics.get("pat_cagr", 0) or 0
            
            narrative.append(f"ROE at {roe:.1f}% (CAGR: {roe_cagr:.1f}%).")
            narrative.append(f"Retained earnings CAGR: {retained_cagr:.1f}%.")
            narrative.append(f"PAT CAGR: {pat_cagr:.1f}%.")
            narrative.append(f"Dividend payout ratio at {payout:.1f}%.")
            narrative.append(f"Debt-to-Equity ratio at {de_ratio:.2f}x.")
        
        return narrative
