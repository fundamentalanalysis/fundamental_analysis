# # rule_engine.py

# def eval_rule(rule_id, name, value, threshold, flag, reason):
#     return {
#         "rule_id": rule_id,
#         "rule_name": name,
#         "value": value,
#         "threshold": threshold,
#         "flag": flag,
#         "reason": reason
#     }


# def wc_rule_engine(metrics, trends, rules):
#     flags = []

#     # ────────────────────────────
#     # A. Receivables Collection
#     # ────────────────────────────
#     dso = metrics["latest"]["dso"]

#     if dso > rules.dso_high:
#         flags.append(eval_rule("A1", "DSO High", dso, f">{rules.dso_high}", "RED",
#                                "Very slow collections"))
#     elif dso >= rules.dso_moderate:
#         flags.append(eval_rule("A1", "DSO Moderate", dso,
#                                f"{rules.dso_moderate}-{rules.dso_high}", "YELLOW",
#                                "Moderate delay in collections"))

#     # Receivable growth vs Revenue growth
#     last_trend = trends[-1] if trends else None
#     if last_trend and last_trend["receivables_yoy"] and last_trend["revenue_yoy"]:
#         if last_trend["receivables_yoy"] > rules.receivable_growth_threshold and \
#                 last_trend["revenue_yoy"] < 0.10:
#             flags.append(eval_rule("A2", "Receivables rising faster than revenue",
#                                    last_trend["receivables_yoy"], ">20%", "YELLOW",
#                                    "Credit risk build-up"))

#     # ────────────────────────────
#     # B. Inventory Efficiency
#     # ────────────────────────────
#     dio = metrics["latest"]["dio"]
#     if dio > rules.dio_high:
#         flags.append(eval_rule("B1", "DIO High", dio, f">{rules.dio_high}", "RED",
#                                "Slow moving inventory"))
#     elif dio >= rules.dio_moderate:
#         flags.append(eval_rule("B1", "DIO Moderate", dio,
#                                f"{rules.dio_moderate}-{rules.dio_high}", "YELLOW",
#                                "Some inventory build-up"))

#     # Inventory vs revenue growth
#     if last_trend and last_trend["inventory_yoy"] and last_trend["revenue_yoy"]:
#         if last_trend["inventory_yoy"] > rules.inventory_growth_threshold and \
#                 last_trend["revenue_yoy"] < 0.05:
#             flags.append(eval_rule("B2", "Inventory rising without revenue growth",
#                                    last_trend["inventory_yoy"], ">20%", "YELLOW",
#                                    "Possible demand slowdown or over-stocking"))

#     # ────────────────────────────
#     # C. Supplier Payment (DPO)
#     # ────────────────────────────
#     dpo = metrics["latest"]["dpo"]
#     if dpo > rules.dpo_high:
#         flags.append(eval_rule("C1", "DPO Very High", dpo, f">{rules.dpo_high}",
#                                "YELLOW", "Company relying excessively on supplier credit"))
#     elif dpo < rules.dpo_low:
#         flags.append(eval_rule("C1", "DPO Very Low", dpo, f"<{rules.dpo_low}",
#                                "YELLOW", "Paying suppliers too soon"))

#     # ────────────────────────────
#     # D. CCC
#     # ────────────────────────────
#     ccc = metrics["latest"]["ccc"]
#     if ccc > rules.critical_ccc:
#         flags.append(eval_rule("D1", "CCC Critical", ccc, f">{rules.critical_ccc}", "RED",
#                                "Severe working capital stress"))
#     elif ccc >= rules.moderate_ccc:
#         flags.append(eval_rule("D1", "CCC High", ccc,
#                                f"{rules.moderate_ccc}-{rules.critical_ccc}", "YELLOW",
#                                "High cash lock-up"))

#     return flags


# ============================================================
# WORKING CAPITAL RULE ENGINE (FULL VERSION: A1–E2)
# ============================================================

def eval_rule(rule_id, name, value, threshold, flag, reason):
    return {
        "rule_id": rule_id,
        "rule_name": name,
        "value": value,
        "threshold": threshold,
        "flag": flag,
        "reason": reason
    }


def wc_rule_engine(metrics, trends, rules):
    flags = []

    latest = metrics["latest"]
    dso = latest["dso"]
    dio = latest["dio"]
    dpo = latest["dpo"]
    ccc = latest["ccc"]
    nwc_ratio = latest.get("nwc_ratio")
    nwc_cagr = latest.get("nwc_cagr")
    revenue_cagr = latest.get("revenue_cagr")

    last_trend = trends[-1] if trends else None

    # ============================================================
    # A. RECEIVABLES & COLLECTION EFFICIENCY
    # ============================================================

    # ---- Rule A1: DSO vs Benchmark ----
    if dso > 75:
        flags.append(eval_rule(
            "A1", "DSO vs Benchmark",
            dso, ">75",
            "RED",
            "DSO above 75 days — very slow collections and elevated credit risk."
        ))
    elif 60 <= dso <= 75:
        flags.append(eval_rule(
            "A1", "DSO vs Benchmark",
            dso, "60–75",
            "YELLOW",
            "DSO between 60–75 days — moderate delay in customer collections."
        ))
    else:
        flags.append(eval_rule(
            "A1", "DSO vs Benchmark",
            dso, "<60",
            "GREEN",
            "Healthy collection cycle with DSO below 60 days."
        ))

    # ---- Rule A2: Receivables Rising Faster Than Revenue ----
    if last_trend:
        rcv_yoy = last_trend.get("receivables_yoy")
        rev_yoy = last_trend.get("revenue_yoy")

        if rcv_yoy is not None and rev_yoy is not None:
            if rcv_yoy > 0.20 and rev_yoy < 0.10:
                flags.append(eval_rule(
                    "A2", "Receivables vs Revenue Growth",
                    rcv_yoy, "Receivables YoY >20% & Revenue YoY <10%",
                    "YELLOW",
                    "Receivables are rising faster than revenue — potential credit risk buildup."
                ))
            else:
                flags.append(eval_rule(
                    "A2", "Receivables vs Revenue Growth",
                    rcv_yoy, "Normal",
                    "GREEN",
                    "Receivable and revenue growth trends appear aligned."
                ))

    # ============================================================
    # B. INVENTORY EFFICIENCY
    # ============================================================

    # ---- Rule B1: DIO Threshold ----
    if dio > 120:
        flags.append(eval_rule(
            "B1", "DIO Threshold",
            dio, ">120",
            "RED",
            "DIO above 120 — slow-moving inventory, working capital at risk."
        ))
    elif 90 <= dio <= 120:
        flags.append(eval_rule(
            "B1", "DIO Threshold",
            dio, "90–120",
            "YELLOW",
            "DIO between 90–120 — moderate buildup of inventory."
        ))
    else:
        flags.append(eval_rule(
            "B1", "DIO Threshold",
            dio, "<90",
            "GREEN",
            "Healthy inventory turnover with DIO below 90 days."
        ))

    # ---- Rule B2: Inventory Growth Without Revenue Growth ----
    if last_trend:
        inv_yoy = last_trend.get("inventory_yoy")
        rev_yoy = last_trend.get("revenue_yoy")

        if inv_yoy is not None and rev_yoy is not None:
            if inv_yoy > 0.20 and rev_yoy < 0.05:
                flags.append(eval_rule(
                    "B2", "Inventory Growth vs Revenue",
                    inv_yoy, ">20% inventory YoY & Revenue YoY <5%",
                    "YELLOW",
                    "Inventory rising faster than revenue — possible over-stocking or demand slowdown."
                ))
            else:
                flags.append(eval_rule(
                    "B2", "Inventory Growth vs Revenue",
                    inv_yoy, "Normal",
                    "GREEN",
                    "Inventory and revenue trends are aligned."
                ))

    # ============================================================
    # C. SUPPLIER PAYMENT BEHAVIOR (DPO)
    # ============================================================

    # ---- Rule C1: DPO Interpretation ----
    if dpo > 90:
        flags.append(eval_rule(
            "C1", "DPO Interpretation",
            dpo, ">90",
            "YELLOW",
            "DPO above 90 — company relying heavily on supplier credit (could indicate stress)."
        ))
    elif dpo < 30:
        flags.append(eval_rule(
            "C1", "DPO Interpretation",
            dpo, "<30",
            "YELLOW",
            "DPO below 30 — paying suppliers too early, inefficient working capital usage."
        ))
    else:
        flags.append(eval_rule(
            "C1", "DPO Interpretation",
            dpo, "30–90",
            "GREEN",
            "Healthy supplier payment cycle."
        ))

    # ---- Rule C2: Payables Falling While Revenue Rising ----
    if last_trend:
        payables_yoy = last_trend.get("payables_yoy")
        rev_yoy = last_trend.get("revenue_yoy")

        if payables_yoy is not None and rev_yoy is not None:
            if payables_yoy < -0.10 and rev_yoy > 0.05:
                flags.append(eval_rule(
                    "C2", "Payables Decline with Revenue Growth",
                    payables_yoy, "<-10% & Revenue YoY >5%",
                    "YELLOW",
                    "Payables falling while revenue rising — losing supplier credit or tighter payment terms."
                ))
            else:
                flags.append(eval_rule(
                    "C2", "Payables Decline with Revenue Growth",
                    payables_yoy, "Normal",
                    "GREEN",
                    "Payables behaviour is normal relative to revenue growth."
                ))

    # ============================================================
    # D. CASH CONVERSION CYCLE (CCC)
    # ============================================================

    # ---- Rule D1: CCC Threshold ----
    if ccc > 180:
        flags.append(eval_rule(
            "D1", "CCC Threshold",
            ccc, ">180",
            "RED",
            "Cash conversion cycle above 180 days — severe WC pressure."
        ))
    elif 120 <= ccc <= 180:
        flags.append(eval_rule(
            "D1", "CCC Threshold",
            ccc, "120–180",
            "YELLOW",
            "CCC between 120–180 days — high cash lock-up in working capital."
        ))
    else:
        flags.append(eval_rule(
            "D1", "CCC Threshold",
            ccc, "<120",
            "GREEN",
            "Efficient cash cycle with CCC under 120 days."
        ))

    # ---- Rule D2: CCC Trend ----
    if trends and len(trends) >= 3:
        # Check if CCC increased for 3+ consecutive years
        ccc_values = [t.get("ccc") for t in trends[-3:]]
        if None not in ccc_values and ccc_values[0] < ccc_values[1] < ccc_values[2]:
            flags.append(eval_rule(
                "D2", "CCC Trend",
                ccc_values, "Increasing 3+ years",
                "YELLOW",
                "CCC increasing for 3 consecutive years — deterioration in WC efficiency."
            ))
        else:
            flags.append(eval_rule(
                "D2", "CCC Trend",
                ccc_values, "Stable/Improving",
                "GREEN",
                "CCC trend is stable or improving."
            ))

    # ============================================================
    # E. NET WORKING CAPITAL STRESS
    # ============================================================

    # ---- Rule E1: NWC / Revenue Ratio ----
    if nwc_ratio is not None:
        if nwc_ratio > 0.25:
            flags.append(eval_rule(
                "E1", "NWC/Revenue Ratio",
                nwc_ratio, ">0.25",
                "RED",
                "Net Working Capital above 25% of revenue — excessive WC tied up."
            ))
        elif 0.15 <= nwc_ratio <= 0.25:
            flags.append(eval_rule(
                "E1", "NWC/Revenue Ratio",
                nwc_ratio, "0.15–0.25",
                "YELLOW",
                "Elevated NWC levels relative to revenue."
            ))
        else:
            flags.append(eval_rule(
                "E1", "NWC/Revenue Ratio",
                nwc_ratio, "<0.15",
                "GREEN",
                "Healthy NWC positioning relative to revenue."
            ))

    # ---- Rule E2: NWC CAGR vs Revenue CAGR ----
    if nwc_cagr is not None and revenue_cagr is not None:
        if nwc_cagr > (revenue_cagr + 0.10):
            flags.append(eval_rule(
                "E2", "NWC CAGR vs Revenue CAGR",
                nwc_cagr, f"NWC CAGR > Revenue CAGR +10%",
                "RED",
                "NWC growing significantly faster than revenue — WC inefficiency worsening."
            ))
        else:
            flags.append(eval_rule(
                "E2", "NWC CAGR vs Revenue CAGR",
                nwc_cagr, "Normal",
                "GREEN",
                "NWC growth in line with revenue growth."
            ))

    return flags

