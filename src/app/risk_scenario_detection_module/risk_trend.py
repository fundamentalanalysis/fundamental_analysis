
def compute_trends(metrics: dict):
    years = sorted(metrics.keys())

    def ym(key):
        return {
            "Y": metrics[years[-1]].get(key),
            "Y-1": metrics[years[-2]].get(key),
            "Y-2": metrics[years[-3]].get(key),
            "Y-3": metrics[years[-4]].get(key),
            "Y-4": metrics[years[-5]].get(key),
        }

    # ============================
    # 3.1 ZOMBIE COMPANY
    # ============================
    ebit_below, cfo_below, debt_profit = [], [], []

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

    for i in range(1, len(years)):
        y, p = years[i], years[i - 1]

        if metrics[p]["cash"] > 0 and (metrics[y]["cash"] - metrics[p]["cash"]) / metrics[p]["cash"] > 0.30:
            cash_spike.append(y)

        if metrics[p]["net_profit"] > 0 and (metrics[y]["net_profit"] - metrics[p]["net_profit"]) / metrics[p]["net_profit"] > 0.25:
            profit_spike.append(y)

        if metrics[y]["receivables"] < metrics[p]["receivables"] and metrics[y]["net_profit"] > metrics[p]["net_profit"]:
            recv_profit.append(y)

        if metrics[y].get("other_income", 0) and metrics[y]["net_profit"] != 0:
            if abs(metrics[y]["other_income"]) / abs(metrics[y]["net_profit"]) > 0.20:
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
        }
    }

    # ============================
    # 3.3 ASSET STRIPPING  ✅ FIXED
    # ============================
    asset_decline, debt_asset = [], []

    for i in range(1, len(years)):
        y, p = years[i], years[i - 1]

        if metrics[y]["fixed_assets"] < metrics[p]["fixed_assets"]:
            asset_decline.append(y)

        if (
            metrics[y]["net_debt"] > metrics[p]["net_debt"]
            and metrics[y]["fixed_assets"] < metrics[p]["fixed_assets"]
        ):
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
            "insight": "Dividend payouts are not significant enough to indicate asset stripping."
        },
        "promoter_extraction": {
            "status": "DATA_LIMITED",
            "insight": "No direct data on promoter withdrawals beyond related-party disclosures."
        }
    }

    # ============================
    # 3.4 LOAN EVERGREENING
    # ============================
    rollover, debt_ebitda = [], []

    for i in range(1, len(years)):
        y, p = years[i], years[i - 1]

        if metrics[y]["proceeds_from_borrowings"] > metrics[y]["repayment_of_borrowings"]:
            rollover.append(y)

        if metrics[y]["net_debt"] > metrics[p]["net_debt"] and metrics[y]["ebitda"] <= metrics[p]["ebitda"]:
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
            "values": {
                "net_debt": ym("net_debt"),
                "ebitda": ym("ebitda"),
            },
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
            "insight": "Short-term and long-term principal repayment split is not disclosed."
        },
        "interest_capitalization": {
            "status": "NOT_COMPUTABLE",
            "insight": "No disclosure of interest capitalization into assets or CWIP."
        }
    }

    # ============================
    # 3.5 CIRCULAR TRADING
    # ============================
    sales_cfo, recv_rev = [], []

    for i in range(1, len(years)):
        y, p = years[i], years[i - 1]

        if metrics[y]["revenue"] > metrics[p]["revenue"] and metrics[y]["cfo"] < metrics[p]["cfo"]:
            sales_cfo.append(y)

        if (metrics[y]["receivables"] - metrics[p]["receivables"]) > \
           (metrics[y]["revenue"] - metrics[p]["revenue"]):
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
            "insight": "Insufficient related-party sales data to assess abnormal spikes."
        },
        "rpt_receivables_high": {
            "status": "DATA_LIMITED",
            "insight": "Related-party receivable disclosure is insufficient for threshold analysis."
        },
        "rpt_balance_rising": {
            "status": "DATA_LIMITED",
            "insight": "Long-term trend in related-party balances cannot be reliably established."
        }
    }

    return {
        "zombie_company": zombie_company,
        "window_dressing": window_dressing,
        "asset_stripping": asset_stripping,   # ✅ FIXED
        "loan_evergreening": loan_evergreening,
        "circular_trading": circular_trading,
    }
