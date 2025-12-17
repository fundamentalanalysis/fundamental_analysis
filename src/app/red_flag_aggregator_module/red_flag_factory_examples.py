"""
Red Flag Factory Examples and Helpers

This module demonstrates how upstream modules should use the red flag
definitions to generate properly-severity'd flags. It serves as both
documentation and a helper for module authors.
"""

from typing import Dict, Any, List, Optional
from .red_flag_definitions import generate_red_flag, determine_severity


# =============================================================================
# EXAMPLE: How Liquidity Module Should Generate Flags
# =============================================================================

def example_liquidity_module_flags(
    company_id: str,
    cash_ratio: float,
    dir_days: float,
    ocf_cl_ratio: float,
    period: str = "FY2024",
) -> List[Dict[str, Any]]:
    """
    Example: Liquidity module generates red flags for detected metrics.

    This is NOT production code; it shows the pattern upstream modules should follow.
    """
    flags = []

    # Flag 1: Cash ratio
    flag1 = generate_red_flag(
        module="liquidity",
        category="liquidity",
        metric_key="cash_ratio",
        value=cash_ratio,
        period=period,
    )
    flags.append(flag1)

    # Flag 2: Days immediate runway
    flag2 = generate_red_flag(
        module="liquidity",
        category="liquidity",
        metric_key="dir",
        value=dir_days,
        period=period,
    )
    flags.append(flag2)

    # Flag 3: OCF/CL
    flag3 = generate_red_flag(
        module="liquidity",
        category="liquidity",
        metric_key="ocf_cl_ratio",
        value=ocf_cl_ratio,
        period=period,
    )
    flags.append(flag3)

    return flags


# =============================================================================
# EXAMPLE: How Borrowings Module Should Generate Flags
# =============================================================================

def example_borrowings_module_flags(
    company_id: str,
    de_ratio: float,
    debt_ebitda: float,
    net_debt_ebitda: float,
    period: str = "FY2024",
) -> List[Dict[str, Any]]:
    """
    Example: Borrowings module generates red flags for leverage metrics.
    """
    flags = []

    flag1 = generate_red_flag(
        module="borrowings",
        category="leverage",
        metric_key="de_ratio",
        value=de_ratio,
        period=period,
    )
    flags.append(flag1)

    flag2 = generate_red_flag(
        module="borrowings",
        category="leverage",
        metric_key="debt_ebitda",
        value=debt_ebitda,
        period=period,
    )
    flags.append(flag2)

    flag3 = generate_red_flag(
        module="borrowings",
        category="leverage",
        metric_key="net_debt_ebitda",
        value=net_debt_ebitda,
        period=period,
    )
    flags.append(flag3)

    return flags


# =============================================================================
# EXAMPLE: How QoE Module Should Generate Flags
# =============================================================================

def example_qoe_module_flags(
    company_id: str,
    qoe: float,
    accrual_ratio: float,
    dso_yoy_change: float,
    period: str = "FY2024",
) -> List[Dict[str, Any]]:
    """
    Example: Quality of Earnings module generates red flags.
    """
    flags = []

    flag1 = generate_red_flag(
        module="quality_of_earnings",
        category="earnings_quality",
        metric_key="qoe",
        value=qoe,
        period=period,
    )
    flags.append(flag1)

    flag2 = generate_red_flag(
        module="quality_of_earnings",
        category="earnings_quality",
        metric_key="accrual_ratio",
        value=accrual_ratio,
        period=period,
    )
    flags.append(flag2)

    flag3 = generate_red_flag(
        module="quality_of_earnings",
        category="earnings_quality",
        metric_key="dso_yoy_change",
        value=dso_yoy_change,
        period=period,
    )
    flags.append(flag3)

    return flags


# =============================================================================
# EXAMPLE: How Working Capital Module Should Generate Flags
# =============================================================================

def example_wc_module_flags(
    company_id: str,
    ccc: float,
    inventory_revenue_divergence: float,
    receivables_revenue_divergence: float,
    period: str = "FY2024",
) -> List[Dict[str, Any]]:
    """
    Example: Working Capital module generates red flags.
    """
    flags = []

    flag1 = generate_red_flag(
        module="working_capital",
        category="working_capital",
        metric_key="ccc",
        value=ccc,
        period=period,
    )
    flags.append(flag1)

    flag2 = generate_red_flag(
        module="working_capital",
        category="working_capital",
        metric_key="inventory_revenue_divergence",
        value=inventory_revenue_divergence,
        period=period,
    )
    flags.append(flag2)

    flag3 = generate_red_flag(
        module="working_capital",
        category="working_capital",
        metric_key="receivables_revenue_divergence",
        value=receivables_revenue_divergence,
        period=period,
    )
    flags.append(flag3)

    return flags


# =============================================================================
# EXAMPLE: Governance / Fraud Module (Qualitative Flags)
# =============================================================================

def generate_governance_flag(
    module: str,
    metric_key: str,
    severity: str,
    title: str,
    detail: str,
    period: Optional[str] = None,
) -> Dict[str, Any]:
    """
    For qualitative flags (circular trading, RPT, etc.), module authors
    must manually specify severity because thresholds are not numeric.

    Example:
        flag = generate_governance_flag(
            module="governance",
            metric_key="circular_trading",
            severity="CRITICAL",
            title="Circular Trading Detected",
            detail="Repetitive trades with same counterparty lacking economic substance",
            period="FY2024"
        )
    """
    return {
        "module": module,
        "severity": severity,
        "title": title,
        "detail": detail,
        "metric": metric_key,
        "value": None,
        "threshold": None,
        "period": period,
        "risk_category": "governance_fraud",
    }


# =============================================================================
# UNIT TEST / VALIDATION EXAMPLES
# =============================================================================

def test_liquidity_flag_generation():
    """Demonstrates flag generation for various liquidity conditions."""
    print("\n=== LIQUIDITY FLAGS ===\n")

    # Case 1: Healthy company
    flags = example_liquidity_module_flags(
        "TST001",
        cash_ratio=0.6,
        dir_days=120,
        ocf_cl_ratio=1.2,
    )
    for f in flags:
        print(f"  {f['metric']}: {f['severity']} (value={f['value']})")

    # Case 2: Stressed company
    flags = example_liquidity_module_flags(
        "TST002",
        cash_ratio=0.12,
        dir_days=20,
        ocf_cl_ratio=0.2,
    )
    print("\n  Stressed company:")
    for f in flags:
        print(f"  {f['metric']}: {f['severity']} (value={f['value']})")


def test_leverage_flag_generation():
    """Demonstrates flag generation for leverage conditions."""
    print("\n=== LEVERAGE FLAGS ===\n")

    # Case 1: Normal leverage
    flags = example_borrowings_module_flags(
        "TST001",
        de_ratio=1.5,
        debt_ebitda=2.5,
        net_debt_ebitda=2.0,
    )
    print("  Healthy leverage:")
    for f in flags:
        print(f"  {f['metric']}: {f['severity']} (value={f['value']})")

    # Case 2: Overleveraged
    flags = example_borrowings_module_flags(
        "TST003",
        de_ratio=5.5,
        debt_ebitda=8.0,
        net_debt_ebitda=7.5,
    )
    print("\n  Overleveraged:")
    for f in flags:
        print(f"  {f['metric']}: {f['severity']} (value={f['value']})")


if __name__ == "__main__":
    test_liquidity_flag_generation()
    test_leverage_flag_generation()
    print("\nNote: These examples show how upstream modules should emit red flags")
    print("using the factory pattern to ensure correct severity assignment.\n")
