# =============================================================
# src/app/engines/data_quality_engine.py
# Data Quality Engine - Missingness, Anomalies, Confidence
# Layer A - Deterministic Truth Surface
# =============================================================
"""
Assesses data quality and applies confidence penalties.

The Data Quality Engine:
- Detects missing fields
- Identifies anomalies and outliers
- Computes confidence penalties
- Produces DataQualityReport for the Blackboard
"""

from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
import math
import logging

from src.app.blackboard.models import DataQualityReport, Fact

logger = logging.getLogger(__name__)


class DataQualityEngine:
    """
    Data quality assessment engine.
    
    Validates input data, detects anomalies, and computes confidence scores.
    """
    
    SOURCE_ID = "data_quality_engine"
    
    # Required fields for each module (minimum viable data)
    REQUIRED_FIELDS = {
        "borrowings": [
            "short_term_debt", "long_term_debt", "total_equity",
            "ebitda", "interest", "revenue",
        ],
        "liquidity": [
            "current_assets", "current_liabilities", "cash_equivalents",
        ],
        "quality_of_earnings": [
            "cash_from_operating_activity", "net_profit", "revenue",
        ],
        "equity_funding_mix": [
            "equity_capital", "reserves", "net_profit",
        ],
        "working_capital": [
            "trade_receivables", "inventories", "trade_payables", "revenue",
        ],
    }
    
    # Expected ranges for key metrics (for anomaly detection)
    EXPECTED_RANGES = {
        "de_ratio": (0, 10),
        "current_ratio": (0, 20),
        "interest_coverage": (-10, 100),
        "roe": (-2, 2),
        "revenue": (0, float('inf')),
        "net_profit": (float('-inf'), float('inf')),
    }
    
    def __init__(self):
        """Initialize the data quality engine."""
        pass
    
    def assess_quality(
        self,
        data: Dict[str, Any],
        modules: Optional[List[str]] = None,
    ) -> DataQualityReport:
        """
        Assess data quality and produce a report.
        
        Args:
            data: Financial data to assess
            modules: Optional list of modules to check requirements for
            
        Returns:
            DataQualityReport with quality score and issues
        """
        missing_fields = self._find_missing_fields(data, modules)
        anomalies = self._detect_anomalies(data)
        outliers = self._detect_outliers(data)
        
        # Compute overall quality score
        quality_score = self._compute_quality_score(
            data, missing_fields, anomalies, outliers
        )
        
        # Compute per-field confidence penalties
        confidence_penalties = self._compute_confidence_penalties(
            missing_fields, anomalies, outliers
        )
        
        # Generate warnings and recommendations
        warnings, recommendations = self._generate_warnings(
            missing_fields, anomalies, outliers
        )
        
        report = DataQualityReport(
            quality_score=quality_score,
            missing_fields=missing_fields,
            missing_rate=len(missing_fields) / max(len(data), 1),
            anomalies=anomalies,
            outliers=outliers,
            confidence_penalties=confidence_penalties,
            warnings=warnings,
            recommendations=recommendations,
        )
        
        logger.info(
            f"Data quality assessed: score={quality_score:.2f}, "
            f"missing={len(missing_fields)}, anomalies={len(anomalies)}"
        )
        
        return report
    
    def _find_missing_fields(
        self,
        data: Dict[str, Any],
        modules: Optional[List[str]] = None,
    ) -> List[str]:
        """Find required fields that are missing or None."""
        missing = []
        
        if modules is None:
            modules = list(self.REQUIRED_FIELDS.keys())
        
        checked_fields: Set[str] = set()
        
        for module in modules:
            required = self.REQUIRED_FIELDS.get(module, [])
            for field in required:
                if field in checked_fields:
                    continue
                checked_fields.add(field)
                
                value = data.get(field)
                if value is None:
                    missing.append(field)
        
        return missing
    
    def _detect_anomalies(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect anomalous values that are technically valid but unusual."""
        anomalies = []
        
        # Check for negative values where they shouldn't be
        non_negative_fields = [
            "revenue", "total_assets", "total_equity", "inventories",
            "trade_receivables", "cash_equivalents", "gross_block",
        ]
        
        for field in non_negative_fields:
            value = data.get(field)
            if value is not None and value < 0:
                anomalies.append({
                    "field": field,
                    "value": value,
                    "issue": "unexpected_negative",
                    "severity": "medium",
                    "message": f"{field} is negative ({value}), which is unusual",
                })
        
        # Check for unusual relationships
        # Revenue should be > EBITDA > Net Profit (usually)
        revenue = data.get("revenue", 0) or 0
        ebitda = data.get("ebitda") or data.get("operating_profit", 0) or 0
        net_profit = data.get("net_profit", 0) or 0
        
        if revenue > 0 and net_profit > revenue:
            anomalies.append({
                "field": "net_profit",
                "value": net_profit,
                "issue": "profit_exceeds_revenue",
                "severity": "high",
                "message": f"Net profit ({net_profit}) exceeds revenue ({revenue})",
            })
        
        # Check for zero revenue with non-zero operations
        if revenue == 0 and (ebitda != 0 or net_profit != 0):
            anomalies.append({
                "field": "revenue",
                "value": 0,
                "issue": "zero_revenue_with_operations",
                "severity": "high",
                "message": "Revenue is zero but operating metrics are non-zero",
            })
        
        return anomalies
    
    def _detect_outliers(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect values that are extreme outliers."""
        outliers = []
        
        for field, (min_val, max_val) in self.EXPECTED_RANGES.items():
            value = data.get(field)
            if value is None:
                continue
            
            if value < min_val or value > max_val:
                outliers.append({
                    "field": field,
                    "value": value,
                    "expected_range": (min_val, max_val),
                    "severity": "medium" if abs(value) < 100 else "high",
                    "message": f"{field}={value} is outside expected range [{min_val}, {max_val}]",
                })
        
        return outliers
    
    def _compute_quality_score(
        self,
        data: Dict[str, Any],
        missing_fields: List[str],
        anomalies: List[Dict[str, Any]],
        outliers: List[Dict[str, Any]],
    ) -> float:
        """
        Compute overall data quality score (0.0 to 1.0).
        """
        score = 1.0
        
        # Penalize for missing fields
        total_expected = 20  # Approximate number of important fields
        missing_penalty = len(missing_fields) / total_expected * 0.4
        score -= missing_penalty
        
        # Penalize for anomalies
        for anomaly in anomalies:
            if anomaly.get("severity") == "high":
                score -= 0.15
            else:
                score -= 0.05
        
        # Penalize for outliers
        for outlier in outliers:
            if outlier.get("severity") == "high":
                score -= 0.10
            else:
                score -= 0.03
        
        return max(0.0, min(1.0, score))
    
    def _compute_confidence_penalties(
        self,
        missing_fields: List[str],
        anomalies: List[Dict[str, Any]],
        outliers: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        Compute per-module confidence penalties.
        """
        penalties: Dict[str, float] = {}
        
        # Map fields to modules
        field_to_module = {}
        for module, fields in self.REQUIRED_FIELDS.items():
            for field in fields:
                if field not in field_to_module:
                    field_to_module[field] = []
                field_to_module[field].append(module)
        
        # Apply penalties from missing fields
        for field in missing_fields:
            for module in field_to_module.get(field, []):
                penalties[module] = penalties.get(module, 0) + 0.1
        
        # Apply penalties from anomalies
        for anomaly in anomalies:
            field = anomaly.get("field", "")
            for module in field_to_module.get(field, []):
                penalty = 0.2 if anomaly.get("severity") == "high" else 0.1
                penalties[module] = penalties.get(module, 0) + penalty
        
        # Cap penalties at 0.5 per module
        return {k: min(v, 0.5) for k, v in penalties.items()}
    
    def _generate_warnings(
        self,
        missing_fields: List[str],
        anomalies: List[Dict[str, Any]],
        outliers: List[Dict[str, Any]],
    ) -> Tuple[List[str], List[str]]:
        """Generate human-readable warnings and recommendations."""
        warnings = []
        recommendations = []
        
        if missing_fields:
            if len(missing_fields) > 5:
                warnings.append(
                    f"Significant data gaps: {len(missing_fields)} required fields are missing"
                )
                recommendations.append(
                    "Review data source and ensure all financial statement items are extracted"
                )
            else:
                warnings.append(f"Missing fields: {', '.join(missing_fields[:5])}")
        
        high_severity_issues = [
            a for a in anomalies + outliers if a.get("severity") == "high"
        ]
        
        for issue in high_severity_issues[:3]:
            warnings.append(issue.get("message", "Unknown issue detected"))
        
        if len(high_severity_issues) > 3:
            warnings.append(
                f"... and {len(high_severity_issues) - 3} more high-severity issues"
            )
            recommendations.append(
                "Manual review recommended due to multiple data quality issues"
            )
        
        return warnings, recommendations
