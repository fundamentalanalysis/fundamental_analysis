# =============================================================
# src/app/engines/correlation_engine.py
# Correlation Engine - Cross-Module Rules and Overrides
# Layer A - Deterministic Truth Surface
# =============================================================
"""
Applies deterministic cross-module correlation rules.

The Correlation Engine:
- Detects "double jeopardy" patterns
- Applies score caps, floors, and kill-switches
- Enforces precedence ordering
- Produces Override entries for the Blackboard
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

from src.app.blackboard.models import Fact, Override, Severity
from src.app.blackboard.store import Blackboard

logger = logging.getLogger(__name__)


class CorrelationRule:
    """Definition of a correlation rule."""
    
    def __init__(
        self,
        rule_id: str,
        name: str,
        description: str,
        conditions: List[Dict[str, Any]],
        action: str,
        action_value: Optional[float] = None,
        severity: Severity = Severity.HIGH,
        precedence: int = 100,
    ):
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.conditions = conditions  # List of conditions to check
        self.action = action  # "cap_score", "floor_score", "kill_switch", "flag_spof"
        self.action_value = action_value  # Cap/floor value
        self.severity = severity
        self.precedence = precedence  # Higher = applied later (can override earlier)


class CorrelationEngine:
    """
    Cross-module correlation rules and deterministic overrides.
    
    This engine detects patterns across multiple modules that indicate
    heightened risk, and applies deterministic score adjustments.
    """
    
    SOURCE_ID = "correlation_engine"
    
    def __init__(self):
        """Initialize the correlation engine with default rules."""
        self.rules = self._build_default_rules()
    
    def _build_default_rules(self) -> List[CorrelationRule]:
        """Build the default rulebook (10-15 rules as specified)."""
        return [
            # Terminal Decline Pattern
            CorrelationRule(
                rule_id="CORR_001",
                name="terminal_decline",
                description="Revenue CAGR < -10% AND PAT declining 3 consecutive years",
                conditions=[
                    {"fact_key": "revenue_cagr", "operator": "<", "value": -0.10},
                    {"fact_key": "net_profit_declining_3y", "operator": "==", "value": True},
                ],
                action="cap_score",
                action_value=30,
                severity=Severity.CRITICAL,
                precedence=200,
            ),
            
            # False Growth Capex
            CorrelationRule(
                rule_id="CORR_002",
                name="false_growth_capex",
                description="High CWIP + falling asset turnover + no revenue growth",
                conditions=[
                    {"fact_key": "cwip_pct", "operator": ">", "value": 0.20},
                    {"fact_key": "asset_turnover", "operator": "<", "value": 0.5},
                    {"fact_key": "revenue_cagr", "operator": "<", "value": 0.02},
                ],
                action="flag_spof",
                severity=Severity.HIGH,
                precedence=150,
            ),
            
            # Debt-Funded Dividends
            CorrelationRule(
                rule_id="CORR_003",
                name="debt_funded_dividends",
                description="Dividend payout > 100% AND debt increasing",
                conditions=[
                    {"fact_key": "dividend_payout_ratio", "operator": ">", "value": 1.0},
                    {"fact_key": "total_debt_cagr", "operator": ">", "value": 0.05},
                ],
                action="kill_switch",
                severity=Severity.CRITICAL,
                precedence=250,
            ),
            
            # QoE Cash Conversion Failure + Rising Leverage
            CorrelationRule(
                rule_id="CORR_004",
                name="qoe_leverage_risk",
                description="Quality of Earnings < 0.5 AND D/E ratio increasing",
                conditions=[
                    {"fact_key": "qoe", "operator": "<", "value": 0.5},
                    {"fact_key": "de_ratio", "operator": ">", "value": 1.0},
                ],
                action="cap_score",
                action_value=40,
                severity=Severity.HIGH,
                precedence=180,
            ),
            
            # Receivables Stretch + Margin Spike (Earnings Inflation Risk)
            CorrelationRule(
                rule_id="CORR_005",
                name="earnings_inflation_risk",
                description="DSO increasing significantly while margins improve",
                conditions=[
                    {"fact_key": "dso", "operator": ">", "value": 90},
                    {"fact_key": "receivables_vs_revenue_cagr_diff", "operator": ">", "value": 5},
                ],
                action="flag_spof",
                severity=Severity.HIGH,
                precedence=140,
            ),
            
            # Stranded CWIP + Falling Asset Turnover
            CorrelationRule(
                rule_id="CORR_006",
                name="stranded_cwip",
                description="CWIP increasing 3 years + asset turnover declining",
                conditions=[
                    {"fact_key": "cwip_increasing_3y", "operator": "==", "value": True},
                    {"fact_key": "asset_turnover_declining_3y", "operator": "==", "value": True},
                ],
                action="cap_score",
                action_value=45,
                severity=Severity.HIGH,
                precedence=160,
            ),
            
            # Negative Free Cash Flow + High Dividend
            CorrelationRule(
                rule_id="CORR_007",
                name="unsustainable_dividend",
                description="FCF negative for 2+ years AND dividend payout > 50%",
                conditions=[
                    {"fact_key": "free_cash_flow", "operator": "<", "value": 0},
                    {"fact_key": "dividend_payout_ratio", "operator": ">", "value": 0.5},
                ],
                action="flag_spof",
                severity=Severity.MEDIUM,
                precedence=130,
            ),
            
            # Liquidity Crisis Pattern
            CorrelationRule(
                rule_id="CORR_008",
                name="liquidity_crisis",
                description="Current ratio < 1 AND OCF/Current Liabilities < 0.2",
                conditions=[
                    {"fact_key": "current_ratio", "operator": "<", "value": 1.0},
                    {"fact_key": "ocf_to_current_liabilities", "operator": "<", "value": 0.2},
                ],
                action="kill_switch",
                severity=Severity.CRITICAL,
                precedence=260,
            ),
            
            # Interest Coverage Stress
            CorrelationRule(
                rule_id="CORR_009",
                name="interest_coverage_stress",
                description="Interest coverage < 1.5 AND debt increasing",
                conditions=[
                    {"fact_key": "interest_coverage", "operator": "<", "value": 1.5},
                    {"fact_key": "total_debt_cagr", "operator": ">", "value": 0.05},
                ],
                action="cap_score",
                action_value=35,
                severity=Severity.CRITICAL,
                precedence=220,
            ),
            
            # Intangibles Inflation
            CorrelationRule(
                rule_id="CORR_010",
                name="intangibles_inflation",
                description="Intangibles growing faster than revenue + high intangibles %",
                conditions=[
                    {"fact_key": "intangibles_vs_revenue_cagr_diff", "operator": ">", "value": 10},
                    {"fact_key": "intangible_pct_total_assets", "operator": ">", "value": 0.30},
                ],
                action="flag_spof",
                severity=Severity.MEDIUM,
                precedence=120,
            ),
            
            # Working Capital Deterioration
            CorrelationRule(
                rule_id="CORR_011",
                name="working_capital_deterioration",
                description="Cash conversion cycle increasing + negative working capital",
                conditions=[
                    {"fact_key": "ccc", "operator": ">", "value": 90},
                    {"fact_key": "net_working_capital", "operator": "<", "value": 0},
                ],
                action="cap_score",
                action_value=50,
                severity=Severity.MEDIUM,
                precedence=140,
            ),
            
            # Equity Erosion
            CorrelationRule(
                rule_id="CORR_012",
                name="equity_erosion",
                description="Net worth declining + retained earnings declining",
                conditions=[
                    {"fact_key": "net_worth_declining_3y", "operator": "==", "value": True},
                    {"fact_key": "retained_declining", "operator": "==", "value": True},
                ],
                action="cap_score",
                action_value=35,
                severity=Severity.HIGH,
                precedence=190,
            ),
            
            # Refinancing Risk
            CorrelationRule(
                rule_id="CORR_013",
                name="refinancing_risk",
                description=">50% debt maturing in 1 year + poor interest coverage",
                conditions=[
                    {"fact_key": "maturity_lt_1y_pct", "operator": ">", "value": 0.50},
                    {"fact_key": "interest_coverage", "operator": "<", "value": 2.0},
                ],
                action="kill_switch",
                severity=Severity.CRITICAL,
                precedence=240,
            ),
            
            # Revenue Quality Concern
            CorrelationRule(
                rule_id="CORR_014",
                name="revenue_quality_concern",
                description="Revenue quality < 0.3 + related party sales > 20%",
                conditions=[
                    {"fact_key": "revenue_quality", "operator": "<", "value": 0.3},
                    {"fact_key": "related_party_sales_pct", "operator": ">", "value": 0.20},
                ],
                action="flag_spof",
                severity=Severity.HIGH,
                precedence=170,
            ),
            
            # Healthy Company Override (positive pattern)
            CorrelationRule(
                rule_id="CORR_015",
                name="strong_fundamentals",
                description="High ROE + low leverage + positive FCF",
                conditions=[
                    {"fact_key": "roe", "operator": ">", "value": 0.15},
                    {"fact_key": "de_ratio", "operator": "<", "value": 0.5},
                    {"fact_key": "free_cash_flow", "operator": ">", "value": 0},
                ],
                action="floor_score",
                action_value=60,
                severity=Severity.LOW,
                precedence=50,
            ),
        ]
    
    def apply_overrides(
        self,
        blackboard: Blackboard,
    ) -> List[Override]:
        """
        Apply correlation rules and generate overrides.
        
        Args:
            blackboard: The blackboard containing facts
            
        Returns:
            List of Override objects (also written to blackboard)
        """
        # Get all facts as a dictionary for easier lookup
        facts_dict = blackboard.get_metrics_dict()
        
        # Also get facts by key directly
        facts_by_key = {f.key: f.value for f in blackboard.get_facts()}
        facts_dict.update(facts_by_key)
        
        overrides: List[Override] = []
        
        # Sort rules by precedence (lower first)
        sorted_rules = sorted(self.rules, key=lambda r: r.precedence)
        
        for rule in sorted_rules:
            triggered, triggered_facts = self._evaluate_rule(rule, facts_dict)
            
            if triggered:
                override = Override(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    description=rule.description,
                    action=rule.action,
                    value=rule.action_value,
                    triggered_by=triggered_facts,
                    severity=rule.severity,
                    applied=True,
                )
                
                overrides.append(override)
                blackboard.write_override(override, self.SOURCE_ID)
                
                logger.info(
                    f"Correlation rule triggered: {rule.name} ({rule.action}"
                    f"{f'={rule.action_value}' if rule.action_value else ''})"
                )
        
        logger.info(f"Applied {len(overrides)} correlation overrides")
        return overrides
    
    def _evaluate_rule(
        self,
        rule: CorrelationRule,
        facts: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Evaluate whether a rule's conditions are met.
        
        Returns:
            Tuple of (triggered: bool, triggered_fact_keys: List[str])
        """
        triggered_facts = []
        
        for condition in rule.conditions:
            fact_key = condition.get("fact_key")
            operator = condition.get("operator")
            threshold = condition.get("value")
            
            fact_value = facts.get(fact_key)
            
            if fact_value is None:
                # Can't evaluate condition - treat as not met
                return False, []
            
            if not self._compare(fact_value, operator, threshold):
                return False, []
            
            triggered_facts.append(fact_key)
        
        return True, triggered_facts
    
    def _compare(self, value: Any, operator: str, threshold: Any) -> bool:
        """Compare a value against a threshold using the given operator."""
        try:
            if operator == "<":
                return value < threshold
            elif operator == "<=":
                return value <= threshold
            elif operator == ">":
                return value > threshold
            elif operator == ">=":
                return value >= threshold
            elif operator == "==":
                return value == threshold
            elif operator == "!=":
                return value != threshold
            else:
                logger.warning(f"Unknown operator: {operator}")
                return False
        except (TypeError, ValueError):
            return False
    
    def get_rule_descriptions(self) -> List[Dict[str, Any]]:
        """Get human-readable descriptions of all rules."""
        return [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "description": r.description,
                "action": r.action,
                "action_value": r.action_value,
                "severity": r.severity.value,
            }
            for r in self.rules
        ]
    
    def add_custom_rule(self, rule: CorrelationRule) -> None:
        """Add a custom correlation rule."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.precedence)
