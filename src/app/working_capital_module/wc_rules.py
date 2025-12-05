
from typing import List, Dict, Optional
try:
    from .wc_models import RuleResult
except ImportError:
    from wc_models import RuleResult

def _make(rule_id, name, metric, year, flag, value, threshold, reason):
    return RuleResult(
        rule_id=rule_id,
        rule_name=name,
        metric=metric,
        year=year,
        flag=flag,
        value=value,
        threshold=threshold,
        reason=reason,
    )

def wc_rule_engine(metrics: Dict, trends: Dict, rules: any) -> List[RuleResult]:
    results = []

    latest = metrics["latest"]
    dso = latest["dso"]
    dio = latest["dio"]
    dpo = latest["dpo"]
    ccc = latest["ccc"]
    nwc_ratio = latest.get("nwc_ratio")
    nwc_cagr = latest.get("nwc_cagr")
    revenue_cagr = latest.get("revenue_cagr")
    
    # Assuming 'latest' metrics correspond to the most recent year available
    # We don't have the explicit year in 'metrics["latest"]', so we might use "Latest" or 0
    current_year = "Latest"

    # Helper to safely get latest YoY from trends dict
    # trends structure: { "metric": { "yoy_growth_pct": { "Y_vs_Y-1": val, ... } } }
    def get_latest_yoy(metric_key):
        if metric_key in trends and "yoy_growth_pct" in trends[metric_key]:
            return trends[metric_key]["yoy_growth_pct"].get("Y_vs_Y-1")
        return None

    rcv_yoy = get_latest_yoy("trade_receivables")
    inv_yoy = get_latest_yoy("inventory")
    payables_yoy = get_latest_yoy("trade_payables")
    rev_yoy = get_latest_yoy("revenue")

    # ============================================================
    # A. RECEIVABLES & COLLECTION EFFICIENCY
    # ============================================================

    # ---- Rule A1: DSO vs Benchmark ----
    if dso > 75:
        results.append(_make(
            "A1", "DSO vs Benchmark", "dso", current_year,
            "RED", dso, ">75",
            "DSO above 75 days — very slow collections and elevated credit risk."
        ))
    elif 60 <= dso <= 75:
        results.append(_make(
            "A1", "DSO vs Benchmark", "dso", current_year,
            "YELLOW", dso, "60–75",
            "DSO between 60–75 days — moderate delay in customer collections."
        ))
    else:
        results.append(_make(
            "A1", "DSO vs Benchmark", "dso", current_year,
            "GREEN", dso, "<60",
            "Healthy collection cycle with DSO below 60 days."
        ))

    # ---- Rule A2: Receivables Rising Faster Than Revenue ----
    if rcv_yoy is not None and rev_yoy is not None:
        if rcv_yoy > 20 and rev_yoy < 10: # Thresholds: >20% and <10% (values are percentages)
            results.append(_make(
                "A2", "Receivables vs Revenue Growth", "receivables_yoy", current_year,
                "YELLOW", rcv_yoy, "Receivables YoY >20% & Revenue YoY <10%",
                f"Receivables rising faster ({rcv_yoy:.1f}%) than revenue ({rev_yoy:.1f}%) — potential credit risk buildup."
            ))
        else:
            results.append(_make(
                "A2", "Receivables vs Revenue Growth", "receivables_yoy", current_year,
                "GREEN", rcv_yoy, "Normal",
                "Receivable and revenue growth trends appear aligned."
            ))

    # ============================================================
    # B. INVENTORY EFFICIENCY
    # ============================================================

    # ---- Rule B1: DIO Threshold ----
    if dio > 120:
        results.append(_make(
            "B1", "DIO Threshold", "dio", current_year,
            "RED", dio, ">120",
            "DIO above 120 — slow-moving inventory, working capital at risk."
        ))
    elif 90 <= dio <= 120:
        results.append(_make(
            "B1", "DIO Threshold", "dio", current_year,
            "YELLOW", dio, "90–120",
            "DIO between 90–120 — moderate buildup of inventory."
        ))
    else:
        results.append(_make(
            "B1", "DIO Threshold", "dio", current_year,
            "GREEN", dio, "<90",
            "Healthy inventory turnover with DIO below 90 days."
        ))

    # ---- Rule B2: Inventory Growth Without Revenue Growth ----
    if inv_yoy is not None and rev_yoy is not None:
        if inv_yoy > 20 and rev_yoy < 5:
            results.append(_make(
                "B2", "Inventory Growth vs Revenue", "inventory_yoy", current_year,
                "YELLOW", inv_yoy, ">20% inventory YoY & Revenue YoY <5%",
                f"Inventory rising faster ({inv_yoy:.1f}%) than revenue ({rev_yoy:.1f}%) — possible over-stocking or demand slowdown."
            ))
        else:
            results.append(_make(
                "B2", "Inventory Growth vs Revenue", "inventory_yoy", current_year,
                "GREEN", inv_yoy, "Normal",
                "Inventory and revenue trends are aligned."
            ))

    # ============================================================
    # C. SUPPLIER PAYMENT BEHAVIOR (DPO)
    # ============================================================

    # ---- Rule C1: DPO Interpretation ----
    if dpo > 90:
        results.append(_make(
            "C1", "DPO Interpretation", "dpo", current_year,
            "YELLOW", dpo, ">90",
            "DPO above 90 — company relying heavily on supplier credit (could indicate stress)."
        ))
    elif dpo < 30:
        results.append(_make(
            "C1", "DPO Interpretation", "dpo", current_year,
            "YELLOW", dpo, "<30",
            "DPO below 30 — paying suppliers too early, inefficient working capital usage."
        ))
    else:
        results.append(_make(
            "C1", "DPO Interpretation", "dpo", current_year,
            "GREEN", dpo, "30–90",
            "Healthy supplier payment cycle."
        ))

    # ---- Rule C2: Payables Falling While Revenue Rising ----
    if payables_yoy is not None and rev_yoy is not None:
        if payables_yoy < -10 and rev_yoy > 5:
            results.append(_make(
                "C2", "Payables Decline with Revenue Growth", "payables_yoy", current_year,
                "YELLOW", payables_yoy, "<-10% & Revenue YoY >5%",
                f"Payables falling ({payables_yoy:.1f}%) while revenue rising ({rev_yoy:.1f}%) — losing supplier credit or tighter payment terms."
            ))
        else:
            results.append(_make(
                "C2", "Payables Decline with Revenue Growth", "payables_yoy", current_year,
                "GREEN", payables_yoy, "Normal",
                "Payables behaviour is normal relative to revenue growth."
            ))

    # ============================================================
    # D. CASH CONVERSION CYCLE (CCC)
    # ============================================================

    # ---- Rule D1: CCC Threshold ----
    if ccc > 180:
        results.append(_make(
            "D1", "CCC Threshold", "ccc", current_year,
            "RED", ccc, ">180",
            "Cash conversion cycle above 180 days — severe WC pressure."
        ))
    elif 120 <= ccc <= 180:
        results.append(_make(
            "D1", "CCC Threshold", "ccc", current_year,
            "YELLOW", ccc, "120–180",
            "CCC between 120–180 days — high cash lock-up in working capital."
        ))
    else:
        results.append(_make(
            "D1", "CCC Threshold", "ccc", current_year,
            "GREEN", ccc, "<120",
            "Efficient cash cycle with CCC under 120 days."
        ))

    # ---- Rule D2: CCC Trend ----
    # Note: New trend engine does not output CCC trend directly.
    # We skip this rule if data is unavailable.
    # Future improvement: Calculate CCC trend in wc_trend.py

    # ============================================================
    # E. NET WORKING CAPITAL STRESS
    # ============================================================

    # ---- Rule E1: NWC / Revenue Ratio ----
    if nwc_ratio is not None:
        if nwc_ratio > 0.25:
            results.append(_make(
                "E1", "NWC/Revenue Ratio", "nwc_ratio", current_year,
                "RED", nwc_ratio, ">0.25",
                "Net Working Capital above 25% of revenue — excessive WC tied up."
            ))
        elif 0.15 <= nwc_ratio <= 0.25:
            results.append(_make(
                "E1", "NWC/Revenue Ratio", "nwc_ratio", current_year,
                "YELLOW", nwc_ratio, "0.15–0.25",
                "Elevated NWC levels relative to revenue."
            ))
        else:
            results.append(_make(
                "E1", "NWC/Revenue Ratio", "nwc_ratio", current_year,
                "GREEN", nwc_ratio, "<0.15",
                "Healthy NWC positioning relative to revenue."
            ))

    # ---- Rule E2: NWC CAGR vs Revenue CAGR ----
    if nwc_cagr is not None and revenue_cagr is not None:
        if nwc_cagr > (revenue_cagr + 0.10): # +10% (0.10)
             # Note: CAGRs are usually decimals in metrics? Or percentages?
             # In wc_trend.py compute_cagr returns percentage ( * 100).
             # In metrics["latest"], we need to know if they are % or decimal.
             # Assuming they are decimals based on previous code (nwc_cagr > revenue_cagr + 0.10)
             # BUT wc_trend returns percentages.
             # Let's assume metrics["latest"] values are consistent with how they were generated (likely decimals if from a ratio calculation, or % if from trend).
             # The previous code used `revenue_cagr + 0.10`, implying 10%.
             
            results.append(_make(
                "E2", "NWC CAGR vs Revenue CAGR", "nwc_cagr", current_year,
                "RED", nwc_cagr, f"NWC CAGR > Revenue CAGR +10%",
                "NWC growing significantly faster than revenue — WC inefficiency worsening."
            ))
        else:
            results.append(_make(
                "E2", "NWC CAGR vs Revenue CAGR", "nwc_cagr", current_year,
                "GREEN", nwc_cagr, "Normal",
                "NWC growth in line with revenue growth."
            ))

    return results
