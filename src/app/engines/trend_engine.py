# =============================================================
# src/app/engines/trend_engine.py
# Trend Engine - Multi-year Pattern Detection
# Layer A - Deterministic Truth Surface
# =============================================================
"""
Computes YoY / multi-year trends with deterministic outputs.

The Trend Engine:
- Calculates CAGR, YoY growth rates
- Detects patterns (declining, increasing, volatile)
- Produces immutable Facts for the Blackboard
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

from src.app.blackboard.models import Fact

logger = logging.getLogger(__name__)


class TrendEngine:
    """
    Multi-year trend detection engine.
    
    Computes CAGR, YoY growth, and pattern detection for historical data.
    """
    
    SOURCE_ID = "trend_engine"
    
    def __init__(self):
        """Initialize the trend engine."""
        pass
    
    def compute_trends(
        self,
        historical_data: List[Dict[str, Any]],
        fields: Optional[List[str]] = None,
    ) -> List[Fact]:
        """
        Compute trend facts from historical data.
        
        Args:
            historical_data: List of yearly data dicts (oldest first)
            fields: Optional list of fields to compute trends for
            
        Returns:
            List of Fact objects with trend metrics
        """
        if not historical_data or len(historical_data) < 2:
            return []
        
        facts: List[Fact] = []
        n_years = len(historical_data)
        
        # Get the latest year for period tagging
        latest_year = historical_data[-1].get("year")
        
        # Determine fields to compute
        if fields is None:
            # Get all numeric fields from the latest year
            fields = [
                k for k, v in historical_data[-1].items()
                if isinstance(v, (int, float)) and k != "year"
            ]
        
        for field in fields:
            # Extract time series
            values = [d.get(field) for d in historical_data]
            years = [d.get("year") for d in historical_data]
            
            # Compute CAGR
            cagr = self._compute_cagr(values)
            if cagr is not None:
                facts.append(Fact(
                    key=f"{field}_cagr",
                    value=round(cagr, 4),
                    unit="percent",
                    period=latest_year,
                    source_engine=self.SOURCE_ID,
                    metadata={
                        "start_year": years[0] if years else None,
                        "end_year": years[-1] if years else None,
                        "n_years": n_years,
                    }
                ))
            
            # Compute YoY growth rates
            yoy_rates = self._compute_yoy_series(values)
            if yoy_rates:
                # Latest YoY
                facts.append(Fact(
                    key=f"{field}_yoy",
                    value=round(yoy_rates[-1], 4) if yoy_rates[-1] is not None else None,
                    unit="percent",
                    period=latest_year,
                    source_engine=self.SOURCE_ID,
                    metadata={"yoy_series": yoy_rates}
                ))
                
                # Average YoY
                valid_rates = [r for r in yoy_rates if r is not None]
                if valid_rates:
                    avg_yoy = sum(valid_rates) / len(valid_rates)
                    facts.append(Fact(
                        key=f"{field}_avg_yoy",
                        value=round(avg_yoy, 4),
                        unit="percent",
                        period=latest_year,
                        source_engine=self.SOURCE_ID,
                    ))
            
            # Detect patterns
            pattern = self._detect_pattern(values)
            if pattern:
                facts.append(Fact(
                    key=f"{field}_trend_pattern",
                    value=pattern,
                    period=latest_year,
                    source_engine=self.SOURCE_ID,
                ))
            
            # Detect consecutive trends
            if self._has_consecutive_trend(values, "up", 3):
                facts.append(Fact(
                    key=f"{field}_increasing_3y",
                    value=True,
                    period=latest_year,
                    source_engine=self.SOURCE_ID,
                ))
            
            if self._has_consecutive_trend(values, "down", 3):
                facts.append(Fact(
                    key=f"{field}_declining_3y",
                    value=True,
                    period=latest_year,
                    source_engine=self.SOURCE_ID,
                ))
        
        # Compute comparison metrics
        comparison_facts = self._compute_comparison_metrics(historical_data, latest_year)
        facts.extend(comparison_facts)
        
        logger.info(f"Computed {len(facts)} trend facts from {n_years} years of data")
        return facts
    
    def _compute_cagr(self, values: List[Optional[float]]) -> Optional[float]:
        """
        Compute Compound Annual Growth Rate.
        
        Returns percentage (e.g., 0.15 for 15% growth).
        """
        # Filter valid values
        valid_pairs = [(i, v) for i, v in enumerate(values) if v is not None and v != 0]
        
        if len(valid_pairs) < 2:
            return None
        
        start_idx, start_val = valid_pairs[0]
        end_idx, end_val = valid_pairs[-1]
        years = end_idx - start_idx
        
        if years <= 0 or start_val == 0:
            return None
        
        # Handle same-sign values
        if start_val * end_val > 0:
            cagr = (abs(end_val) / abs(start_val)) ** (1 / years) - 1
            return cagr
        
        # Mixed signs - CAGR undefined
        return None
    
    def _compute_yoy_series(self, values: List[Optional[float]]) -> List[Optional[float]]:
        """Compute year-over-year growth rates as a series."""
        yoy_rates = []
        
        for i in range(1, len(values)):
            prev_val = values[i - 1]
            curr_val = values[i]
            
            if prev_val is None or prev_val == 0 or curr_val is None:
                yoy_rates.append(None)
            else:
                yoy = (curr_val - prev_val) / abs(prev_val)
                yoy_rates.append(yoy)
        
        return yoy_rates
    
    def _detect_pattern(self, values: List[Optional[float]]) -> Optional[str]:
        """
        Detect overall pattern in the time series.
        
        Returns one of: "steady_growth", "steady_decline", "volatile", 
                       "accelerating", "decelerating", "stable", "recovery"
        """
        valid_values = [v for v in values if v is not None]
        
        if len(valid_values) < 3:
            return None
        
        # Compute YoY changes
        changes = []
        for i in range(1, len(valid_values)):
            if valid_values[i - 1] != 0:
                change = (valid_values[i] - valid_values[i - 1]) / abs(valid_values[i - 1])
                changes.append(change)
        
        if not changes:
            return None
        
        # Analyze pattern
        positive_count = sum(1 for c in changes if c > 0.02)
        negative_count = sum(1 for c in changes if c < -0.02)
        total = len(changes)
        
        # Check for steady trends
        if positive_count >= total * 0.8:
            # Check if accelerating
            if len(changes) >= 2 and changes[-1] > changes[0]:
                return "accelerating"
            return "steady_growth"
        
        if negative_count >= total * 0.8:
            # Check if decelerating (declining faster)
            if len(changes) >= 2 and changes[-1] < changes[0]:
                return "decelerating"
            return "steady_decline"
        
        # Check for volatility
        if positive_count > 0 and negative_count > 0:
            # Check for recovery (negative then positive)
            if changes[0] < 0 and changes[-1] > 0:
                return "recovery"
            # Check for reversal (positive then negative)
            if changes[0] > 0 and changes[-1] < 0:
                return "reversal"
            return "volatile"
        
        return "stable"
    
    def _has_consecutive_trend(
        self,
        values: List[Optional[float]],
        direction: str,
        span: int,
    ) -> bool:
        """Check for consecutive trend (up/down) across span years."""
        if len(values) < span:
            return False
        
        cmp = (lambda a, b: a > b) if direction == "up" else (lambda a, b: a < b)
        streak = 0
        
        for i in range(1, len(values)):
            prev = values[i - 1]
            curr = values[i]
            
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
    
    def _compute_comparison_metrics(
        self,
        historical_data: List[Dict[str, Any]],
        latest_year: Optional[int],
    ) -> List[Fact]:
        """
        Compute comparison metrics (e.g., debt CAGR vs revenue CAGR).
        """
        facts: List[Fact] = []
        
        # Define standard comparisons
        comparisons = [
            ("debt_vs_revenue", "total_debt", "revenue"),
            ("debt_vs_ebitda", "total_debt", "ebitda"),
            ("lt_debt_vs_revenue", "long_term_debt", "revenue"),
            ("receivables_vs_revenue", "trade_receivables", "revenue"),
            ("inventory_vs_revenue", "inventories", "revenue"),
            ("intangibles_vs_revenue", "intangible_assets", "revenue"),
        ]
        
        for comp_name, field1, field2 in comparisons:
            values1 = [d.get(field1) for d in historical_data]
            values2 = [d.get(field2) for d in historical_data]
            
            cagr1 = self._compute_cagr(values1)
            cagr2 = self._compute_cagr(values2)
            
            if cagr1 is not None and cagr2 is not None:
                diff = (cagr1 - cagr2) * 100  # Convert to percentage points
                facts.append(Fact(
                    key=f"{comp_name}_cagr_diff",
                    value=round(diff, 2),
                    unit="percentage_points",
                    period=latest_year,
                    source_engine=self.SOURCE_ID,
                    metadata={
                        f"{field1}_cagr": round(cagr1 * 100, 2),
                        f"{field2}_cagr": round(cagr2 * 100, 2),
                    }
                ))
        
        return facts
