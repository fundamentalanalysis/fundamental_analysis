# =============================================================
# src/app/agents/generic_agent.py
# Single Generic Agent Class for ALL Modules
# =============================================================
"""
This is a SINGLE class that handles all 12 modules.
The module behavior is entirely driven by YAML config.
No need for separate files per module.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime
import math

from src.app.config import load_agents_config, get_module_config, OPENAI_MODEL, get_llm_client


# ---------------------------------------------------------------------------
# Pydantic Models (shared by all modules)
# ---------------------------------------------------------------------------

class RuleResult(BaseModel):
    """Single rule evaluation result with investor insights"""
    rule_id: str
    rule_name: str
    metric_name: str
    value: float
    status: str  # "RED", "YELLOW", "GREEN"
    benchmark: Optional[str] = None
    message: str
    # Enhanced insight fields
    summary: Optional[str] = None
    implication: Optional[str] = None
    investor_action: Optional[str] = None
    risk_level: Optional[str] = None
    peer_context: Optional[str] = None


class TrendResult(BaseModel):
    """Trend calculation result"""
    name: str
    value: float
    interpretation: str


class ModuleOutput(BaseModel):
    """Universal output for any module"""
    module_name: str
    module_id: str
    timestamp: str
    metrics: Dict[str, float]
    rules_results: List[RuleResult]
    trends: List[TrendResult]
    score: int
    score_interpretation: str
    llm_narrative: str


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
        """
        Initialize agent for a specific module.
        
        Args:
            module_id: The module key from agents_config.yaml (e.g., "borrowings", "equity_funding_mix")
        """
        self.module_id = module_id
        self.config = get_module_config(module_id)
        if not self.config:
            raise ValueError(f"Module '{module_id}' not found in configuration")
        
        self.name = self.config.get("name", module_id)
        self.description = self.config.get("description", "")
        self.benchmarks = self.config.get("benchmarks", {})
        self.metric_formulas = self.config.get("metrics", {})
        self.rules = self.config.get("rules", [])
        self.trend_keys = self.config.get("trends", [])
        self.agent_prompt = self.config.get("agent_prompt", "")
        self.output_sections = self.config.get("output_sections", [])
        
        # Load global config
        full_config = load_agents_config()
        self.global_config = full_config.get("global", {})
    
    # -----------------------------------------------------------------------
    # METRICS CALCULATION
    # -----------------------------------------------------------------------
    
    def calculate_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate all metrics for this module using formulas from config.
        
        The formulas in YAML are descriptive - actual computation is done here.
        """
        metrics = {}
        
        # Module-specific metric calculations
        if self.module_id == "equity_funding_mix":
            metrics = self._calc_equity_funding_metrics(data)
        elif self.module_id == "borrowings":
            metrics = self._calc_borrowings_metrics(data)
        elif self.module_id == "liquidity":
            metrics = self._calc_liquidity_metrics(data)
        elif self.module_id == "working_capital":
            metrics = self._calc_working_capital_metrics(data)
        elif self.module_id == "capex_asset_quality":
            metrics = self._calc_capex_metrics(data)
        elif self.module_id == "profitability":
            metrics = self._calc_profitability_metrics(data)
        elif self.module_id == "cash_flow":
            metrics = self._calc_cash_flow_metrics(data)
        elif self.module_id == "solvency":
            metrics = self._calc_solvency_metrics(data)
        elif self.module_id == "valuation":
            metrics = self._calc_valuation_metrics(data)
        elif self.module_id == "growth":
            metrics = self._calc_growth_metrics(data)
        elif self.module_id == "risk_assessment":
            metrics = self._calc_risk_metrics(data)
        elif self.module_id == "credit_rating":
            metrics = self._calc_credit_rating_metrics(data)
        else:
            # Fallback: try to compute basic metrics from formulas
            metrics = self._calc_generic_metrics(data)
        
        return metrics
    
    def _safe_div(self, a: float, b: float, default: float = 0.0) -> float:
        """Safe division avoiding ZeroDivisionError"""
        if b == 0 or b is None:
            return default
        return a / b
    
    def _calc_equity_funding_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate equity & funding mix metrics"""
        share_capital = data.get("share_capital", 0)
        reserves = data.get("reserves_and_surplus", 0)
        net_worth = data.get("net_worth", share_capital + reserves)
        pat = data.get("pat", 0)
        dividend_paid = abs(data.get("dividend_paid", 0))
        fcf = data.get("free_cash_flow", 1)
        new_shares = data.get("new_share_issuance", 0)
        debt = data.get("debt_equitymix", 0)
        
        # Prior period values for YoY
        prior_reserves = data.get("prior_reserves_and_surplus", reserves * 0.9)
        prior_share_capital = data.get("prior_share_capital", share_capital)
        
        # Average equity for ROE
        prior_net_worth = data.get("prior_net_worth", net_worth * 0.9)
        avg_equity = (net_worth + prior_net_worth) / 2 if prior_net_worth else net_worth
        
        return {
            "retained_earnings": reserves,
            "re_growth_yoy": self._safe_div(reserves - prior_reserves, abs(prior_reserves)) if prior_reserves else 0,
            "dividend_payout_ratio": self._safe_div(dividend_paid, pat) if pat > 0 else 0,
            "dividend_to_fcf": self._safe_div(dividend_paid, fcf) if fcf > 0 else 0,
            "roe": self._safe_div(pat, avg_equity),
            "equity_dilution_pct": self._safe_div(new_shares, prior_share_capital) if prior_share_capital else 0,
            "debt_to_equity": self._safe_div(debt, net_worth),
            "equity_ratio": self._safe_div(net_worth, net_worth + debt),
        }
    
    def _calc_borrowings_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate borrowings metrics - comprehensive version matching original module"""
        st_debt = data.get("short_term_debt", 0)
        lt_debt = data.get("long_term_debt", 0)
        total_debt = data.get("total_debt", st_debt + lt_debt)
        if total_debt == 0:
            total_debt = st_debt + lt_debt
            
        equity = data.get("total_equity", 1)
        ebitda = data.get("ebitda", 1)
        ebit = data.get("ebit", 0)
        finance_cost = data.get("finance_cost", 1)
        cwip = data.get("cwip", 0)
        revenue = data.get("revenue", 0)
        
        # Maturity profile
        maturity_lt_1y = data.get("total_debt_maturing_lt_1y", 0)
        maturity_1_3y = data.get("total_debt_maturing_1_3y", 0)
        maturity_gt_3y = data.get("total_debt_maturing_gt_3y", 0)
        
        # Interest rate profile
        floating_rate = data.get("floating_rate_debt", 0)
        wacd = data.get("weighted_avg_interest_rate", 0)
        
        # Total assets proxy for CWIP ratio
        total_assets = equity + total_debt
        
        # Calculate maturity percentages
        maturity_lt_1y_pct = self._safe_div(maturity_lt_1y, total_debt)
        maturity_1_3y_pct = self._safe_div(maturity_1_3y, total_debt)
        maturity_gt_3y_pct = self._safe_div(maturity_gt_3y, total_debt)
        
        # Balanced maturity check (>=30% 1-3y AND >=20% >3y = positive)
        maturity_balance = 1 if (maturity_1_3y_pct >= 0.30 and maturity_gt_3y_pct >= 0.20) else 0
        
        # Handle floating rate - could be ratio or amount
        if floating_rate <= 1 and floating_rate > 0:
            floating_share = floating_rate  # Already a ratio
        else:
            floating_share = self._safe_div(floating_rate, total_debt)
        
        return {
            "total_debt": total_debt,
            "de_ratio": self._safe_div(total_debt, equity),
            "debt_ebitda": self._safe_div(total_debt, ebitda),
            "interest_coverage": self._safe_div(ebit, finance_cost),
            "st_debt_share": self._safe_div(st_debt, total_debt) if total_debt > 0 else 0,
            "cwip_to_assets": self._safe_div(cwip, total_assets),
            "floating_share": floating_share,
            "wacd": wacd,
            "maturity_lt_1y_pct": maturity_lt_1y_pct,
            "maturity_1_3y_pct": maturity_1_3y_pct,
            "maturity_gt_3y_pct": maturity_gt_3y_pct,
            "maturity_balance": maturity_balance,
            # Trend comparison metrics - will be set by trends calculation
            "debt_vs_ebitda_cagr": 0,  # Placeholder - set from trends
            "lt_debt_vs_revenue": 0,    # Placeholder - set from trends
            "finance_cost_vs_debt": 0,  # Placeholder - set from trends
        }
    
    def _calc_liquidity_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate liquidity metrics"""
        cash = data.get("cash_and_equivalents", 0)
        securities = data.get("marketable_securities", 0)
        ca = data.get("current_assets", 0)
        cl = data.get("current_liabilities", 1)
        inventory = data.get("inventory", 0)
        daily_opex = data.get("daily_operating_expenses", 1)
        
        return {
            "current_ratio": self._safe_div(ca, cl),
            "quick_ratio": self._safe_div(ca - inventory, cl),
            "cash_ratio": self._safe_div(cash + securities, cl),
            "cash_coverage_days": self._safe_div(cash, daily_opex),
        }
    
    def _calc_working_capital_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate working capital metrics"""
        receivables = data.get("trade_receivables", 0)
        payables = data.get("trade_payables", 0)
        inventory = data.get("inventory_wc", 0)
        revenue = data.get("revenue_wc", 1)
        cogs = data.get("cogs", 1)
        
        dso = self._safe_div(receivables, revenue) * 365
        dio = self._safe_div(inventory, cogs) * 365
        dpo = self._safe_div(payables, cogs) * 365
        
        return {
            "dso": dso,
            "dio": dio,
            "dpo": dpo,
            "cash_conversion_cycle": dso + dio - dpo,
        }
    
    def _calc_capex_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate capex & asset quality metrics"""
        nfa = data.get("net_fixed_assets", 1)
        gross_block = data.get("gross_block", 1)
        accum_dep = data.get("accumulated_depreciation", 0)
        cwip = data.get("cwip_asset", 0)
        capex = data.get("capex", 0)
        revenue = data.get("revenue", 1)
        ocf = data.get("operating_cash_flow", 1)
        
        return {
            "asset_turnover": self._safe_div(revenue, nfa),
            "capex_to_revenue": self._safe_div(capex, revenue),
            "capex_to_ocf": self._safe_div(capex, ocf),
            "asset_age_ratio": self._safe_div(accum_dep, gross_block),
            "cwip_ratio": self._safe_div(cwip, gross_block),
        }
    
    def _calc_profitability_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate profitability metrics"""
        revenue = data.get("revenue", 1)
        ebitda = data.get("ebitda", 0)
        ebit = data.get("ebit", 0)
        pat = data.get("pat", 0)
        ocf = data.get("operating_cash_flow", 0)
        
        return {
            "ebitda_margin": self._safe_div(ebitda, revenue),
            "ebit_margin": self._safe_div(ebit, revenue),
            "pat_margin": self._safe_div(pat, revenue),
            "ocf_to_pat": self._safe_div(ocf, pat) if pat > 0 else 0,
        }
    
    def _calc_cash_flow_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate cash flow metrics"""
        ocf = data.get("operating_cash_flow", 0)
        capex = data.get("capex", 0)
        pat = data.get("pat", 1)
        debt = data.get("total_debt", 1)
        revenue = data.get("revenue", 1)
        
        fcf = ocf - capex
        
        return {
            "fcf": fcf,
            "fcf_margin": self._safe_div(fcf, revenue),
            "ocf_to_debt": self._safe_div(ocf, debt),
            "fcf_to_pat": self._safe_div(fcf, pat) if pat > 0 else 0,
        }
    
    def _calc_solvency_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate solvency metrics"""
        total_assets = data.get("total_assets", 1)
        total_liabilities = data.get("total_liabilities", 0)
        total_equity = data.get("total_equity", 0)
        lt_debt = data.get("long_term_debt", 0)
        
        return {
            "equity_to_assets": self._safe_div(total_equity, total_assets),
            "debt_to_assets": self._safe_div(total_liabilities, total_assets),
            "lt_debt_to_equity": self._safe_div(lt_debt, total_equity),
        }
    
    def _calc_valuation_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate valuation metrics"""
        mcap = data.get("market_cap", 0)
        pat = data.get("pat", 1)
        book_value = data.get("book_value", 1)
        ebitda = data.get("ebitda", 1)
        fcf = data.get("free_cash_flow", 0)
        debt = data.get("total_debt", 0)
        cash = data.get("cash_and_equivalents", 0)
        
        ev = mcap + debt - cash
        
        return {
            "pe_ratio": self._safe_div(mcap, pat) if pat > 0 else 0,
            "pb_ratio": self._safe_div(mcap, book_value),
            "ev_ebitda": self._safe_div(ev, ebitda),
            "fcf_yield": self._safe_div(fcf, mcap) if mcap > 0 else 0,
        }
    
    def _calc_growth_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate growth metrics"""
        rev_t = data.get("revenue", 0)
        rev_t1 = data.get("revenue_prior", rev_t * 0.9)
        pat_t = data.get("pat", 0)
        pat_t1 = data.get("pat_prior", pat_t * 0.9)
        ebitda_t = data.get("ebitda", 0)
        ebitda_t1 = data.get("ebitda_prior", ebitda_t * 0.9)
        
        return {
            "revenue_growth": self._safe_div(rev_t - rev_t1, abs(rev_t1)) if rev_t1 else 0,
            "pat_growth": self._safe_div(pat_t - pat_t1, abs(pat_t1)) if pat_t1 else 0,
            "ebitda_growth": self._safe_div(ebitda_t - ebitda_t1, abs(ebitda_t1)) if ebitda_t1 else 0,
        }
    
    def _calc_risk_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate risk assessment metrics"""
        assets = data.get("risk_assets_total", data.get("total_assets", 1))
        equity = data.get("total_equity", 1)
        ebit = data.get("risk_ebit", data.get("ebit", 0))
        interest = data.get("risk_interest", data.get("finance_cost", 1))
        capex = data.get("risk_capex", data.get("capex", 0))
        revenue = data.get("risk_revenue", data.get("revenue", 1))
        
        return {
            "financial_leverage": self._safe_div(assets, equity),
            "interest_burden": self._safe_div(interest, ebit) if ebit > 0 else 0,
            "capex_intensity": self._safe_div(capex, revenue),
        }
    
    def _calc_credit_rating_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
        """Calculate credit rating metrics"""
        debt = data.get("total_debt", 0)
        ebitda = data.get("ebitda", 1)
        interest = data.get("interest_expense", data.get("finance_cost", 1))
        ocf = data.get("operating_cash_flow", 0)
        
        return {
            "debt_ebitda": self._safe_div(debt, ebitda),
            "ebitda_interest": self._safe_div(ebitda, interest),
            "ffo_debt": self._safe_div(ocf + interest, debt) if debt > 0 else 0,
        }
    
    def _calc_generic_metrics(self, data: Dict[str, float]) -> Dict[str, float]:
        """Fallback: compute metrics generically (limited functionality)"""
        # This is a fallback - modules should have specific implementations
        return {}
    
    # -----------------------------------------------------------------------
    # RULES EVALUATION
    # -----------------------------------------------------------------------
    
    def evaluate_rules(self, metrics: Dict[str, float]) -> List[RuleResult]:
        """
        Evaluate all rules from config against calculated metrics.
        Returns rich insights for each rule based on status.
        """
        results = []
        
        for rule in self.rules:
            rule_id = rule.get("id", "")
            rule_name = rule.get("name", "")
            metric_name = rule.get("metric", "")
            
            # Get metric value
            value = metrics.get(metric_name, 0)
            
            # Evaluate thresholds and get insights
            status, message, insights = self._evaluate_rule_with_insights(rule, value)
            
            results.append(RuleResult(
                rule_id=rule_id,
                rule_name=rule_name,
                metric_name=metric_name,
                value=round(value, 4),
                status=status,
                benchmark=f"Red: {rule.get('red', '-')}, Yellow: {rule.get('yellow', '-')}, Green: {rule.get('green', '-')}",
                message=message,
                summary=insights.get("summary"),
                implication=insights.get("implication"),
                investor_action=insights.get("investor_action"),
                risk_level=insights.get("risk_level"),
                peer_context=insights.get("peer_context")
            ))
        
        return results
    
    def _evaluate_rule_with_insights(self, rule: Dict, value: float) -> tuple:
        """
        Evaluate a single rule and return (status, message, insights dict).
        Extracts rich insights from YAML config based on status.
        """
        red_cond = rule.get("red", "")
        yellow_cond = rule.get("yellow", "")
        green_cond = rule.get("green", "")
        insights_config = rule.get("insights", {})
        
        # Check RED condition first
        if self._check_condition(value, red_cond):
            insights = insights_config.get("red", {})
            summary = insights.get("summary", f"{rule.get('name', '')} is in critical zone")
            return "RED", f"{summary} (Value: {self._format_value(value)})", insights
        
        # Check YELLOW condition
        if self._check_condition(value, yellow_cond):
            insights = insights_config.get("yellow", {})
            summary = insights.get("summary", f"{rule.get('name', '')} needs attention")
            return "YELLOW", f"{summary} (Value: {self._format_value(value)})", insights
        
        # Default to GREEN
        insights = insights_config.get("green", {})
        summary = insights.get("summary", f"{rule.get('name', '')} is healthy")
        return "GREEN", f"{summary} (Value: {self._format_value(value)})", insights
    
    def _format_value(self, value: float) -> str:
        """Format value appropriately based on magnitude"""
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
        except (ValueError, IndexError):
            pass
        
        return False
    
    # -----------------------------------------------------------------------
    # TRENDS CALCULATION
    # -----------------------------------------------------------------------
    
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
    
    def _calculate_trend_comparison_metrics(self, historical_data: List[Dict[str, float]]) -> Dict[str, float]:
        """
        Calculate comparison metrics based on trends (for borrowings module).
        
        Returns dict with:
        - debt_vs_ebitda_cagr: debt_cagr - ebitda_cagr (positive = debt growing faster)
        - lt_debt_vs_revenue: lt_debt_cagr - revenue_cagr (for A3 rule)
        - finance_cost_vs_debt: finance_cost_cagr - debt_cagr (for C2 rule)
        """
        if not historical_data or len(historical_data) < 2:
            return {}
        
        n = len(historical_data)
        
        # Calculate total_debt if not present
        for d in historical_data:
            if "total_debt" not in d or d.get("total_debt", 0) == 0:
                d["total_debt"] = d.get("short_term_debt", 0) + d.get("long_term_debt", 0)
        
        def get_cagr(field: str) -> float:
            values = [d.get(field, 0) for d in historical_data]
            if values[0] and values[0] > 0 and values[-1]:
                return ((values[-1] / values[0]) ** (1 / (n - 1)) - 1) * 100  # As percentage
            return 0
        
        debt_cagr = get_cagr("total_debt")
        ebitda_cagr = get_cagr("ebitda")
        lt_debt_cagr = get_cagr("long_term_debt")
        revenue_cagr = get_cagr("revenue")
        finance_cost_cagr = get_cagr("finance_cost")
        
        return {
            "debt_vs_ebitda_cagr": debt_cagr - ebitda_cagr,  # Positive = debt growing faster (RED)
            "lt_debt_vs_revenue": 1 if (lt_debt_cagr > 10 and revenue_cagr < 5) else 0,  # A3 rule
            "finance_cost_vs_debt": finance_cost_cagr - debt_cagr,  # C2 rule (>5 = YELLOW)
            "debt_cagr": debt_cagr,
            "ebitda_cagr": ebitda_cagr,
            "lt_debt_cagr": lt_debt_cagr,
            "revenue_cagr": revenue_cagr,
            "finance_cost_cagr": finance_cost_cagr,
        }
    
    # -----------------------------------------------------------------------
    # SCORING
    # -----------------------------------------------------------------------
    
    def calculate_score(self, rules_results: List[RuleResult]) -> tuple:
        """
        Calculate overall module score based on rule results.
        
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
            if result.status == "RED":
                score -= red_penalty
            elif result.status == "YELLOW":
                score -= yellow_penalty
            elif result.status == "GREEN":
                score += green_bonus
        
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
                          trends: List[TrendResult], score: int) -> str:
        """
        Generate LLM narrative using configured agent prompt.
        """
        try:
            client = get_llm_client()
            
            # Build context
            metrics_str = "\n".join([f"- {k}: {v:.4f}" for k, v in metrics.items()])
            rules_str = "\n".join([f"- {r.rule_name}: {r.status} ({r.message})" for r in rules_results])
            trends_str = "\n".join([f"- {t.name}: {t.value:.2%} ({t.interpretation})" for t in trends]) if trends else "No trend data"
            
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
    # MAIN ANALYZE METHOD
    # -----------------------------------------------------------------------
    
    def analyze(self, data: Dict[str, float], historical_data: Optional[List[Dict[str, float]]] = None,
                generate_llm_narrative: bool = True) -> ModuleOutput:
        """
        Main entry point: Run complete analysis for this module.
        
        Args:
            data: Current period financial data
            historical_data: List of historical periods (oldest first)
            generate_llm_narrative: Whether to generate LLM narrative
            
        Returns:
            ModuleOutput with all analysis results
        """
        # 1. Calculate metrics
        metrics = self.calculate_metrics(data)
        
        # 2. For borrowings module, calculate trend-based comparison metrics
        if self.module_id == "borrowings" and historical_data and len(historical_data) >= 2:
            trend_metrics = self._calculate_trend_comparison_metrics(historical_data)
            metrics.update(trend_metrics)
        
        # 3. Evaluate rules
        rules_results = self.evaluate_rules(metrics)
        
        # 4. Calculate trends
        trends = self.calculate_trends(historical_data) if historical_data else []
        
        # 5. Calculate score
        score, interpretation = self.calculate_score(rules_results)
        
        # 6. Generate narrative
        narrative = ""
        if generate_llm_narrative:
            narrative = self.generate_narrative(metrics, rules_results, trends, score)
        
        return ModuleOutput(
            module_name=self.name,
            module_id=self.module_id,
            timestamp=datetime.utcnow().isoformat(),
            metrics=metrics,
            rules_results=rules_results,
            trends=trends,
            score=score,
            score_interpretation=interpretation,
            llm_narrative=narrative
        )
