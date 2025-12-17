"""
Red Flag Definitions and Thresholds

This module documents the exhaustive set of red flag definitions and thresholds
that all upstream modules MUST conform to. It serves as the contract between
individual analysis modules and the aggregator.

When a module detects a risk condition, it MUST emit a red flag with the
correct severity from this specification.
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

# Import canonical RiskCategory enum from models
from .red_flag_aggregator_models import RiskCategory


# =============================================================================
# A. LIQUIDITY STRESS THEME
# =============================================================================

@dataclass
class LiquidityMetric:
    name: str
    metric_key: str
    definition: str
    calculation: str
    risk_category: str = "liquidity"


LIQUIDITY_METRICS: Dict[str, Dict[str, Any]] = {
    "cash_ratio_low": {
        "name": "Cash Ratio Low",
        "metric_key": "cash_ratio",
        "definition": "Indicates insufficient immediately available liquidity to meet current liabilities.",
        "calculation": "Cash Ratio = (Cash + Cash Equivalents) / Current Liabilities",
        "thresholds": {
            "GREEN": (0.5, float("inf")),
            "YELLOW": (0.3, 0.5),
            "RED": (0.15, 0.3),
            "CRITICAL": (0.0, 0.15),
        },
    },
    "days_immediate_runway": {
        "name": "Days of Immediate Runway (DIR) < 30",
        "metric_key": "dir",
        "definition": "Measures how long the company can operate using existing cash at the current burn rate.",
        "calculation": "DIR = Cash & Cash Equivalents / (Operating Expenses / 365)",
        "thresholds": {
            "GREEN": (90, float("inf")),
            "YELLOW": (30, 90),
            "RED": (15, 30),
            "CRITICAL": (0, 15),
        },
    },
    "ocf_to_current_liabilities": {
        "name": "Operating Cash Flow / Current Liabilities < 0.5",
        "metric_key": "ocf_cl_ratio",
        "definition": "Shows inability of core operations to cover short-term liabilities.",
        "calculation": "OCF / CL = Operating Cash Flow / Current Liabilities",
        "thresholds": {
            "GREEN": (1.0, float("inf")),
            "YELLOW": (0.5, 1.0),
            "RED": (0.25, 0.5),
            "CRITICAL": (0.0, 0.25),
        },
    },
}


# =============================================================================
# B. LEVERAGE & DEBT RISK THEME
# =============================================================================

LEVERAGE_METRICS: Dict[str, Dict[str, Any]] = {
    "debt_to_equity": {
        "name": "Debt-to-Equity Ratio (D/E) > 3",
        "metric_key": "de_ratio",
        "definition": "Indicates excessive reliance on debt relative to equity capital.",
        "calculation": "D/E = Total Debt / Shareholders' Equity",
        "thresholds": {
            "GREEN": (0, 2.0),
            "YELLOW": (2.0, 3.0),
            "RED": (3.0, 5.0),
            "CRITICAL": (5.0, float("inf")),
        },
        "special": "CRITICAL if equity is negative",
    },
    "debt_to_ebitda": {
        "name": "Debt / EBITDA > 5",
        "metric_key": "debt_ebitda",
        "definition": "Measures debt servicing capacity relative to operating earnings.",
        "calculation": "Debt / EBITDA = Total Debt / EBITDA",
        "thresholds": {
            "GREEN": (0, 3.0),
            "YELLOW": (3.0, 5.0),
            "RED": (5.0, 7.0),
            "CRITICAL": (7.0, float("inf")),
        },
        "special": "CRITICAL if EBITDA <= 0",
    },
    "net_debt_to_ebitda": {
        "name": "Net Debt / EBITDA > 5.5",
        "metric_key": "net_debt_ebitda",
        "definition": "Assesses leverage after adjusting for cash balances.",
        "calculation": "Net Debt = Total Debt – Cash & Equivalents; Net Debt / EBITDA",
        "thresholds": {
            "GREEN": (0, 4.0),
            "YELLOW": (4.0, 5.5),
            "RED": (5.5, 7.0),
            "CRITICAL": (7.0, float("inf")),
        },
    },
}


# =============================================================================
# C. EARNINGS QUALITY RISK THEME
# =============================================================================

EARNINGS_QUALITY_METRICS: Dict[str, Dict[str, Any]] = {
    "quality_of_earnings": {
        "name": "Quality of Earnings (QoE) < 0.8",
        "metric_key": "qoe",
        "definition": "Indicates profits not translating into cash.",
        "calculation": "QoE = Operating Cash Flow / Net Income",
        "thresholds": {
            "GREEN": (1.0, float("inf")),
            "YELLOW": (0.8, 1.0),
            "RED": (0.5, 0.8),
            "CRITICAL": (0.0, 0.5),
        },
    },
    "accrual_ratio": {
        "name": "Accruals > 20%",
        "metric_key": "accrual_ratio",
        "definition": "Measures reliance on non-cash accounting adjustments.",
        "calculation": "Accrual Ratio = (Net Income – Operating Cash Flow) / Total Assets",
        "thresholds": {
            "GREEN": (0, 0.10),
            "YELLOW": (0.10, 0.20),
            "RED": (0.20, 0.30),
            "CRITICAL": (0.30, float("inf")),
        },
    },
    "dso_rising": {
        "name": "Days Sales Outstanding (DSO) Rising",
        "metric_key": "dso_yoy_change",
        "definition": "Signals weakening cash collection or aggressive revenue recognition.",
        "calculation": "DSO = (Accounts Receivable / Revenue) × 365; check YoY change",
        "thresholds": {
            "GREEN": (-float("inf"), 0.05),  # Decline or up to 5% increase
            "YELLOW": (0.05, 0.10),  # 5-10% increase
            "RED": (0.10, 0.15),  # >10% increase
            "CRITICAL": (0.15, float("inf")),  # Sharp spike
        },
        "special": "Also consider revenue slowdown context",
    },
}


# =============================================================================
# D. WORKING CAPITAL STRESS THEME
# =============================================================================

WORKING_CAPITAL_METRICS: Dict[str, Dict[str, Any]] = {
    "cash_conversion_cycle": {
        "name": "Cash Conversion Cycle (CCC) > 180 Days",
        "metric_key": "ccc",
        "definition": "Measures time taken to convert operational investments back into cash.",
        "calculation": "CCC = DSO + DIO – DPO",
        "thresholds": {
            "GREEN": (0, 120),
            "YELLOW": (120, 180),
            "RED": (180, 240),
            "CRITICAL": (240, float("inf")),
        },
    },
    "inventory_growth_vs_revenue": {
        "name": "Inventory Rising Faster Than Revenue",
        "metric_key": "inventory_revenue_divergence",
        "definition": "Indicates overproduction, demand slowdown, or obsolescence risk.",
        "calculation": "Inventory Growth Rate – Revenue Growth Rate",
        "thresholds": {
            "GREEN": (-float("inf"), 0),  # Inventory <= Revenue growth
            "YELLOW": (0, 0.10),  # Inventory > Revenue by <= 10%
            "RED": (0.10, 0.30),  # Inventory > Revenue by > 10%
            "CRITICAL": (0.30, float("inf")),  # Multi-year divergence
        },
    },
    "receivables_growth_vs_revenue": {
        "name": "Receivables Rising Faster Than Revenue",
        "metric_key": "receivables_revenue_divergence",
        "definition": "Signals deteriorating credit quality or inflated sales.",
        "calculation": "Receivables Growth – Revenue Growth",
        "thresholds": {
            "GREEN": (-float("inf"), 0),
            "YELLOW": (0, 0.05),  # 0-5% gap
            "RED": (0.05, 0.15),  # >5% gap
            "CRITICAL": (0.15, float("inf")),  # Persistent gap
        },
        "special": "Also consider DSO spike context",
    },
}


# =============================================================================
# E. CORPORATE GOVERNANCE / FRAUD INDICATORS THEME
# =============================================================================

GOVERNANCE_METRICS: Dict[str, Dict[str, Any]] = {
    "circular_trading": {
        "name": "Circular Trading",
        "metric_key": "circular_trading",
        "definition": "Artificial transactions lacking economic substance.",
        "detection": "Repetitive trades with same counterparties; Revenue without net cash inflow",
        "severity_guidance": {
            "RED": "Isolated incidents",
            "CRITICAL": "Systemic or large-scale",
        },
    },
    "related_party_transactions": {
        "name": "Related-Party Transactions > 10% of Assets",
        "metric_key": "rpt_ratio",
        "definition": "Indicates tunneling and conflict-of-interest risk.",
        "calculation": "RPT Ratio = Related-Party Transactions / Total Assets",
        "thresholds": {
            "GREEN": (0, 0.05),
            "YELLOW": (0.05, 0.10),
            "RED": (0.10, 0.20),
            "CRITICAL": (0.20, float("inf")),
        },
    },
    "window_dressing": {
        "name": "Window Dressing",
        "metric_key": "window_dressing",
        "definition": "Temporary balance sheet manipulation near reporting dates.",
        "detection": "Quarter-end cash spikes; Short-term debt repayment reversals",
        "severity_guidance": {
            "YELLOW": "One-off occurrence",
            "RED": "Pattern detected",
            "CRITICAL": "Repeated across multiple quarters",
        },
    },
    "evergreening": {
        "name": "Evergreening",
        "metric_key": "evergreening",
        "definition": "New loans issued to repay old loans, masking credit stress.",
        "detection": "Debt rollover without cash generation; Stable NPAs despite weak cash flows",
        "severity_guidance": {
            "RED": "Isolated instances",
            "CRITICAL": "Systemic debt rollover pattern",
        },
    },
    "asset_stripping": {
        "name": "Asset Stripping",
        "metric_key": "asset_stripping",
        "definition": "Transfer of valuable assets without fair compensation.",
        "detection": "Asset sales to related parties; Declining asset base without debt reduction",
        "severity_guidance": {
            "CRITICAL": "Always critical if confirmed",
        },
    },
}


# =============================================================================
# F. GROWTH / ASSET UTILIZATION RISK THEME
# =============================================================================

ASSET_UTILIZATION_METRICS: Dict[str, Dict[str, Any]] = {
    "cwip_rising": {
        "name": "CWIP Rising for 3 Years",
        "metric_key": "cwip_trend",
        "definition": "Indicates stalled or mismanaged capital projects.",
        "calculation": "CWIP trend (YoY for 3 consecutive years)",
        "severity_guidance": {
            "RED": "Continuous rise for 3+ years",
            "CRITICAL": "CWIP > 30% of fixed assets",
        },
    },
    "fixed_asset_turnover_falling": {
        "name": "Fixed Asset Turnover Falling",
        "metric_key": "fat_trend",
        "definition": "Measures declining efficiency of asset use.",
        "calculation": "Fixed Asset Turnover = Revenue / Net Fixed Assets",
        "severity_guidance": {
            "YELLOW": "Mild decline (1-2 years)",
            "RED": "Sustained decline (3+ years)",
            "CRITICAL": "Decline + falling revenue simultaneously",
        },
    },
    "impairments_increasing": {
        "name": "Impairments Increasing",
        "metric_key": "impairment_trend",
        "definition": "Reflects historical capital misallocation.",
        "calculation": "Impairment Charges / Total Assets",
        "severity_guidance": {
            "YELLOW": "Sporadic impairments",
            "RED": "Rising YoY",
            "CRITICAL": "Large recurring impairments",
        },
    },
}


# =============================================================================
# AGGREGATED DEFINITION REGISTRY
# =============================================================================

ALL_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "liquidity": LIQUIDITY_METRICS,
    "leverage": LEVERAGE_METRICS,
    "earnings_quality": EARNINGS_QUALITY_METRICS,
    "working_capital": WORKING_CAPITAL_METRICS,
    "governance_fraud": GOVERNANCE_METRICS,
    "asset_utilization": ASSET_UTILIZATION_METRICS,
}

CATEGORY_NAMES: Dict[str, str] = {
    "liquidity": "Liquidity Stress",
    "leverage": "Leverage & Debt Risk",
    "earnings_quality": "Earnings Quality Risk",
    "working_capital": "Working Capital Stress",
    "governance_fraud": "Corporate Governance / Fraud Indicators",
    "asset_utilization": "Growth / Asset Utilization Risk",
}


# =============================================================================
# HELPER FUNCTIONS: Red Flag Generation from Metric Values
# =============================================================================

def determine_severity(
    metric_key: str, value: float, category: str
) -> str:
    """
    Determine severity from metric value against thresholds.

    Args:
        metric_key: e.g., "cash_ratio", "de_ratio"
        value: numeric value of the metric
        category: e.g., "liquidity", "leverage"

    Returns:
        Severity: "GREEN", "YELLOW", "RED", or "CRITICAL"

    Raises:
        ValueError if metric not found in definitions
    """
    if category not in ALL_DEFINITIONS:
        raise ValueError(f"Unknown category: {category}")

    metrics_in_category = ALL_DEFINITIONS[category]
    metric_def = None
    for key, defn in metrics_in_category.items():
        if defn.get("metric_key") == metric_key:
            metric_def = defn
            break

    if not metric_def:
        raise ValueError(
            f"Unknown metric '{metric_key}' in category '{category}'"
        )

    thresholds = metric_def.get("thresholds")
    if not thresholds:
        raise ValueError(
            f"No numeric thresholds for metric '{metric_key}' (qualitative flag)"
        )

    # Determine which severity bucket the value falls into
    for severity in ["CRITICAL", "RED", "YELLOW", "GREEN"]:
        if severity in thresholds:
            lower, upper = thresholds[severity]
            if lower <= value < upper:
                return severity

    # Fallback: if value exceeds all thresholds, it's CRITICAL
    return "CRITICAL"


def generate_red_flag(
    module: str,
    category: str,
    metric_key: str,
    value: float,
    title: Optional[str] = None,
    detail: Optional[str] = None,
    period: Optional[str] = None,
) -> Dict[str, any]:
    """
    Factory function: generate a properly-severity'd red flag from metric value.

    This ensures flags conform to the specification and have correct severity.

    Args:
        module: source module (e.g., "borrowings", "liquidity")
        category: risk category (e.g., "leverage", "liquidity")
        metric_key: metric identifier
        value: numeric value
        title: optional override for flag title (default: from definition)
        detail: optional override for detail (default: auto-generated)
        period: optional period (e.g., "FY2023", "Q4")

    Returns:
        dict: {"module", "severity", "title", "detail", "metric", "value", ...}

    Raises:
        ValueError if category or metric not found
    """
    if category not in ALL_DEFINITIONS:
        raise ValueError(f"Unknown category: {category}")

    metrics_in_category = ALL_DEFINITIONS[category]
    metric_def = None
    metric_key_found = None
    for key, defn in metrics_in_category.items():
        if defn.get("metric_key") == metric_key:
            metric_def = defn
            metric_key_found = key
            break

    if not metric_def:
        raise ValueError(
            f"Unknown metric '{metric_key}' in category '{category}'"
        )

    severity = determine_severity(metric_key, value, category)

    if title is None:
        title = metric_def.get("name", metric_key)

    if detail is None:
        detail = metric_def.get("definition", "")

    flag = {
        "module": module,
        "severity": severity,
        "title": title,
        "detail": detail,
        "metric": metric_key,
        "value": value,
        "threshold": None,
        "period": period,
        "risk_category": category,
    }

    # Add threshold info if available
    if "thresholds" in metric_def:
        thresholds = metric_def["thresholds"]
        if severity in thresholds:
            lower, upper = thresholds[severity]
            flag["threshold"] = f"[{lower}, {upper})"

    return flag


# =============================================================================
# VALIDATION AND DOCUMENTATION
# =============================================================================

def get_metric_definition(category: str, metric_key: str) -> Dict[str, Any]:
    """Retrieve full definition for a metric."""
    if category not in ALL_DEFINITIONS:
        raise ValueError(f"Unknown category: {category}")

    for key, defn in ALL_DEFINITIONS[category].items():
        if defn.get("metric_key") == metric_key:
            return defn

    raise ValueError(f"Unknown metric '{metric_key}' in category '{category}'")


def list_all_metrics() -> Dict[str, List[str]]:
    """Return all metric keys grouped by category."""
    return {
        cat: [m.get("metric_key") for m in metrics.values()]
        for cat, metrics in ALL_DEFINITIONS.items()
    }


def print_specification() -> str:
    """Generate a human-readable specification document."""
    lines = [
        "=" * 80,
        "RED FLAG DEFINITIONS AND THRESHOLDS",
        "=" * 80,
        "",
    ]

    for category in [
        "liquidity",
        "leverage",
        "earnings_quality",
        "working_capital",
        "governance_fraud",
        "asset_utilization",
    ]:
        category_name = CATEGORY_NAMES.get(category, category)
        lines.append(f"\n{category.upper()} - {category_name}")
        lines.append("-" * 80)

        metrics = ALL_DEFINITIONS[category]
        for metric_key, metric_def in metrics.items():
            lines.append(f"\n{metric_def.get('name', metric_key)}")
            lines.append(f"  Metric Key: {metric_def.get('metric_key')}")
            lines.append(
                f"  Definition: {metric_def.get('definition', 'N/A')}")
            lines.append(
                f"  Calculation: {metric_def.get('calculation', 'N/A')}"
            )

            if "thresholds" in metric_def:
                lines.append("  Thresholds:")
                for sev, (lower, upper) in metric_def["thresholds"].items():
                    upper_str = "∞" if upper == float("inf") else f"{upper}"
                    lines.append(
                        f"    {sev}: [{lower}, {upper_str})"
                    )

            if "severity_guidance" in metric_def:
                lines.append("  Severity Guidance:")
                for sev, guidance in metric_def[
                    "severity_guidance"
                ].items():
                    lines.append(f"    {sev}: {guidance}")

    lines.append("\n" + "=" * 80)
    return "\n".join(lines)
