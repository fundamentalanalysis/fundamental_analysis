def compute_trends(metrics: dict):
    years = sorted(metrics.keys())

    def year_map(key):
        return {
            "Y": metrics[years[-1]][key],
            "Y-1": metrics[years[-2]][key],
            "Y-2": metrics[years[-3]][key],
            "Y-3": metrics[years[-4]][key],
            "Y-4": metrics[years[-5]][key],
        }

    # ==================================================
    # 3.1 ZOMBIE COMPANY
    # ==================================================
    ebit_below, cfo_below, debt_profit_overlap = [], [], []

    for i in range(1, len(years)):
        y, p = years[i], years[i - 1]

        if metrics[y]["ebit"] < metrics[y]["interest"]:
            ebit_below.append(y)

        if metrics[y]["cfo"] < metrics[y]["interest"]:
            cfo_below.append(y)

        if (
            metrics[y]["net_debt"] > metrics[p]["net_debt"]
            and metrics[y]["net_profit"] < metrics[p]["net_profit"]
        ):
            debt_profit_overlap.append(y)

    zombie_company = {
        "ebit_vs_interest": {
            "values": {"ebit": year_map("ebit"), "interest": year_map("interest")},
            "comparison": {
                "years_below": ebit_below,
                "count": len(ebit_below),
                "rule_triggered": len(ebit_below) >= 2,
                "interpretation": (
                    "Earnings insufficient to cover interest for multiple years."
                    if len(ebit_below) >= 2
                    else "EBIT consistently covered interest expense."
                ),
            },
        },
        "cfo_vs_interest": {
            "values": {"cfo": year_map("cfo"), "interest": year_map("interest")},
            "comparison": {
                "years_below": cfo_below,
                "count": len(cfo_below),
                "rule_triggered": len(cfo_below) >= 2,
                "interpretation": (
                    "Operating cash flows failed to cover interest, indicating refinancing dependence."
                    if len(cfo_below) >= 2
                    else "Cash flows generally sufficient for interest servicing."
                ),
            },
        },
        "debt_vs_profit": {
            "values": {"net_debt": year_map("net_debt"), "net_profit": year_map("net_profit")},
            "comparison": {
                "years_overlap": debt_profit_overlap,
                "count": len(debt_profit_overlap),
                "rule_triggered": len(debt_profit_overlap) >= 2,
                "interpretation": (
                    "Rising debt despite weakening profitability indicates a debt spiral."
                    if len(debt_profit_overlap) >= 2
                    else "Debt trends broadly aligned with profitability."
                ),
            },
        },
    }

    # ==================================================
    # 3.2 WINDOW DRESSING
    # ==================================================
    cash_spike, profit_spike, recv_profit_mismatch, ebit_volatility = [], [], [], []

    # ---- YoY based checks ----
    for i in range(1, len(years)):
        y, p = years[i], years[i - 1]

        if metrics[p]["cash"] > 0 and (metrics[y]["cash"] - metrics[p]["cash"]) / metrics[p]["cash"] > 0.25:
            cash_spike.append(y)

        if metrics[p]["net_profit"] > 0 and (metrics[y]["net_profit"] - metrics[p]["net_profit"]) / metrics[p]["net_profit"] > 0.25:
            profit_spike.append(y)

        if metrics[y]["receivables"] < metrics[p]["receivables"] and metrics[y]["net_profit"] > metrics[p]["net_profit"]:
            recv_profit_mismatch.append(y)

        if metrics[p]["ebit"] != 0 and abs(metrics[y]["ebit"] - metrics[p]["ebit"]) / abs(metrics[p]["ebit"]) > 0.30:
            ebit_volatility.append(y)

    # ---- ✅ CORRECT one-off income logic (ALL YEARS) ----
    one_off_income = []
    for y in years:
        if metrics[y]["net_profit"] != 0:
            ratio = abs(metrics[y]["other_income"]) / abs(metrics[y]["net_profit"])
            if ratio >= 0.20:
                one_off_income.append(y)

    window_dressing = {
        "cash_spike": {
            "values": {"cash": year_map("cash")},
            "comparison": {
                "years_flagged": cash_spike,
                "count": len(cash_spike),
                "rule_triggered": len(cash_spike) >= 1,
                "interpretation": (
                    "Sudden year-end cash spikes suggest balance sheet beautification."
                    if cash_spike else "No abnormal year-end cash spikes detected."
                ),
            },
        },
        "profit_spike": {
            "values": {"net_profit": year_map("net_profit")},
            "comparison": {
                "years_flagged": profit_spike,
                "count": len(profit_spike),
                "rule_triggered": len(profit_spike) >= 1,
                "interpretation": (
                    "Sharp profit jumps suggest cosmetic profit adjustments."
                    if profit_spike else "Profit growth appears organic."
                ),
            },
        },
        "one_off_income": {
            "values": {
                "other_income": year_map("other_income"),
                "net_profit": year_map("net_profit"),
            },
            "comparison": {
                "years_flagged": one_off_income,
                "count": len(one_off_income),
                "rule_triggered": len(one_off_income) >= 1,
                "interpretation": (
                    "Exceptional income materially influenced reported profits."
                    if one_off_income else "Profits are not driven by exceptional income."
                ),
            },
        },
        "receivables_vs_profit": {
            "values": {"receivables": year_map("receivables"), "net_profit": year_map("net_profit")},
            "comparison": {
                "years_flagged": recv_profit_mismatch,
                "count": len(recv_profit_mismatch),
                "rule_triggered": len(recv_profit_mismatch) >= 1,
                "interpretation": (
                    "Receivable decline alongside profit growth suggests cosmetic revenue recognition."
                    if recv_profit_mismatch else "Receivables align with profit trends."
                ),
            },
        },
        "ebit_volatility": {
            "values": {"ebit": year_map("ebit")},
            "comparison": {
                "years_flagged": ebit_volatility,
                "count": len(ebit_volatility),
                "rule_triggered": len(ebit_volatility) >= 1,
                "interpretation": (
                    "High EBIT volatility suggests earnings smoothing."
                    if ebit_volatility else "EBIT trends are stable."
                ),
            },
        },
    }

    # ==================================================
    # 3.3 ASSET STRIPPING (DIVIDENDS REMOVED)
    # ==================================================
    asset_decline, debt_asset_overlap, promoter_withdrawals = [], [], []

    for i in range(1, len(years)):
        y, p = years[i], years[i - 1]

        if metrics[y]["fixed_assets"] < metrics[p]["fixed_assets"]:
            asset_decline.append(y)

        if metrics[y]["net_debt"] > metrics[p]["net_debt"] and metrics[y]["fixed_assets"] < metrics[p]["fixed_assets"]:
            debt_asset_overlap.append(y)

        if metrics[y]["rpt_receivables"] > metrics[p]["rpt_receivables"]:
            promoter_withdrawals.append(y)

    asset_stripping = {
        "fixed_asset_decline": {
            "values": {"fixed_assets": year_map("fixed_assets")},
            "comparison": {
                "years_flagged": asset_decline,
                "count": len(asset_decline),
                "rule_triggered": len(asset_decline) >= 2,
                "interpretation": (
                    "Sustained decline in fixed assets suggests asset base hollowing."
                    if len(asset_decline) >= 2 else "No sustained erosion of fixed assets."
                ),
            },
        },
        "debt_vs_assets": {
            "values": {"net_debt": year_map("net_debt"), "fixed_assets": year_map("fixed_assets")},
            "comparison": {
                "years_flagged": debt_asset_overlap,
                "count": len(debt_asset_overlap),
                "rule_triggered": len(debt_asset_overlap) >= 2,
                "interpretation": (
                    "Debt increased while asset base shrank, indicating asset stripping risk."
                    if len(debt_asset_overlap) >= 2 else "Debt movements appear asset-backed."
                ),
            },
        },
        "promoter_extraction": {
            "values": {"rpt_receivables": year_map("rpt_receivables")},
            "comparison": {
                "years_flagged": promoter_withdrawals,
                "count": len(promoter_withdrawals),
                "rule_triggered": len(promoter_withdrawals) >= 1,
                "interpretation": (
                    "Rising related-party receivables suggest promoter extraction."
                    if promoter_withdrawals else "No abnormal promoter withdrawals detected."
                ),
            },
        },
    }

    # ==================================================
    # 3.4 LOAN EVERGREENING
    # ==================================================
    rollover, low_repay, interest_cap, debt_ebitda = [], [], [], []

    for i in range(1, len(years)):
        y, p = years[i], years[i - 1]

        if metrics[y]["borrowings"] > 0 and metrics[y]["proceeds"] / metrics[y]["borrowings"] > 0.50:
            rollover.append(y)

        if metrics[y]["borrowings"] > 0 and abs(metrics[y]["repayment"]) / metrics[y]["borrowings"] < 0.10:
            low_repay.append(y)

        if metrics[y]["interest"] > 0 and metrics[y]["interest_capitalized"] / metrics[y]["interest"] > 0.20:
            interest_cap.append(y)

        if metrics[y]["net_debt"] > metrics[p]["net_debt"] and metrics[y]["ebitda"] <= metrics[p]["ebitda"]:
            debt_ebitda.append(y)

    loan_evergreening = {
        "loan_rollover": {
            "values": {"proceeds": year_map("proceeds"), "borrowings": year_map("borrowings")},
            "comparison": {
                "years_flagged": rollover,
                "count": len(rollover),
                "rule_triggered": len(rollover) >= 1,
                "interpretation": (
                    "Large share of borrowings rolled over."
                    if rollover else "Borrowing profile does not indicate excessive rollovers."
                ),
            },
        },
        "principal_repayment": {
            "values": {"repayment": year_map("repayment"), "borrowings": year_map("borrowings")},
            "comparison": {
                "years_flagged": low_repay,
                "count": len(low_repay),
                "rule_triggered": len(low_repay) >= 1,
                "interpretation": (
                    "Minimal principal repayment suggests loan evergreening."
                    if low_repay else "Principal repayments appear adequate."
                ),
            },
        },
        "interest_capitalized": {
            "values": {"interest_capitalized": year_map("interest_capitalized"), "interest": year_map("interest")},
            "comparison": {
                "years_flagged": interest_cap,
                "count": len(interest_cap),
                "rule_triggered": len(interest_cap) >= 1,
                "interpretation": (
                    "Capitalization of interest indicates cash stress."
                    if interest_cap else "Interest capitalization remains limited."
                ),
            },
        },
        "debt_vs_ebitda": {
            "values": {"net_debt": year_map("net_debt"), "ebitda": year_map("ebitda")},
            "comparison": {
                "years_flagged": debt_ebitda,
                "count": len(debt_ebitda),
                "rule_triggered": len(debt_ebitda) >= 2,
                "interpretation": (
                    "Debt increased while EBITDA stagnated or declined."
                    if len(debt_ebitda) >= 2 else "Debt growth supported by EBITDA."
                ),
            },
        },
    }

    # ==================================================
    # 3.5 CIRCULAR TRADING / RPT FRAUD
    # ==================================================
    sales_cfo_mismatch, recv_vs_rev, rpt_surge = [], [], []

    for i in range(1, len(years)):
        y, p = years[i], years[i - 1]

        if metrics[y]["revenue"] > metrics[p]["revenue"] and metrics[y]["cfo"] < metrics[p]["cfo"]:
            sales_cfo_mismatch.append(y)

        if metrics[p]["receivables"] > 0 and metrics[p]["revenue"] > 0:
            if (
                (metrics[y]["receivables"] - metrics[p]["receivables"]) / metrics[p]["receivables"]
                >
                (metrics[y]["revenue"] - metrics[p]["revenue"]) / metrics[p]["revenue"]
            ):
                recv_vs_rev.append(y)

        if metrics[p]["rpt_receivables"] > 0 and (
            (metrics[y]["rpt_receivables"] - metrics[p]["rpt_receivables"])
            / metrics[p]["rpt_receivables"]
        ) > 0.40:
            rpt_surge.append(y)

    circular_trading = {
        "sales_vs_cfo": {
            "values": {"revenue": year_map("revenue"), "cfo": year_map("cfo")},
            "comparison": {
                "years_flagged": sales_cfo_mismatch,
                "count": len(sales_cfo_mismatch),
                "rule_triggered": len(sales_cfo_mismatch) >= 1,
                "interpretation": (
                    "Revenue growth not supported by operating cash flows."
                    if sales_cfo_mismatch else "Revenue growth aligns with cash flow generation."
                ),
            },
        },
        "receivables_vs_revenue": {
            "values": {"receivables": year_map("receivables"), "revenue": year_map("revenue")},
            "comparison": {
                "years_flagged": recv_vs_rev,
                "count": len(recv_vs_rev),
                "rule_triggered": len(recv_vs_rev) >= 1,
                "interpretation": (
                    "Receivables grew faster than revenue, indicating aggressive revenue recognition."
                    if recv_vs_rev else "Receivable growth aligns with revenue trends."
                ),
            },
        },
        "rpt_balance_surge": {
            "values": {"rpt_receivables": year_map("rpt_receivables")},
            "comparison": {
                "years_flagged": rpt_surge,
                "count": len(rpt_surge),
                "rule_triggered": len(rpt_surge) >= 1,
                "interpretation": (
                    "Rapid increase in related-party balances suggests round-tripping."
                    if rpt_surge else "No abnormal surge in related-party balances detected."
                ),
            },
        },
    }

    return {
        "zombie_company": zombie_company,
        "window_dressing": window_dressing,
        "asset_stripping": asset_stripping,
        "loan_evergreening": loan_evergreening,
        "circular_trading": circular_trading,
    }
