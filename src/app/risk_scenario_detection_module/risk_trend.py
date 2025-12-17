# def compute_trends(metrics: dict):
#     years = sorted(metrics.keys())

#     def values(key):
#         return {f"Y-{len(years)-1-i}" if i < len(years)-1 else "Y": metrics[y][key]
#                 for i, y in enumerate(years)}

#     # -----------------------------
#     # Zombie Company Metrics
#     # -----------------------------
#     ebit_vs_interest = {}
#     cfo_vs_interest = {}

#     ebit_below = 0
#     cfo_below = 0

#     for y in years:
#         ebit = metrics[y]["ebit"]
#         interest = metrics[y]["interest"]
#         cfo = metrics[y]["cfo"]

#         e_ratio = ebit / interest if interest else None
#         c_ratio = cfo / interest if interest else None

#         ebit_vs_interest[y] = e_ratio
#         cfo_vs_interest[y] = c_ratio

#         if e_ratio is not None and e_ratio < 1:
#             ebit_below += 1
#         if c_ratio is not None and c_ratio < 1:
#             cfo_below += 1

#     # Net debt trend
#     net_debt_values = [metrics[y]["net_debt"] for y in years]
#     net_debt_rising = all(net_debt_values[i] >= net_debt_values[i-1]
#                           for i in range(1, len(net_debt_values)))

#     profit_values = [metrics[y]["net_profit"] for y in years]
#     profit_falling = profit_values[-1] < profit_values[-2]

#     # -----------------------------
#     # Window Dressing
#     # -----------------------------
#     cash_spike = None
#     profit_spike = None

#     if metrics[years[-2]]["cash"]:
#         cash_spike = (
#             metrics[years[-1]]["cash"] - metrics[years[-2]]["cash"]
#         ) / metrics[years[-2]]["cash"]

#     if metrics[years[-2]]["net_profit"]:
#         profit_spike = (
#             metrics[years[-1]]["net_profit"] - metrics[years[-2]]["net_profit"]
#         ) / metrics[years[-2]]["net_profit"]

#     one_off_ratio = (
#         abs(metrics[years[-1]]["other_income"]) / metrics[years[-1]]["net_profit"]
#         if metrics[years[-1]]["net_profit"] else None
#     )

#     # -----------------------------
#     # Asset Stripping (WITH OVERLAP YEARS)
#     # -----------------------------
#     debt_rising_years = []
#     assets_falling_years = []
#     overlap_years = []

#     for i in range(1, len(years)):
#         prev, curr = years[i-1], years[i]

#         if metrics[curr]["net_debt"] > metrics[prev]["net_debt"]:
#             debt_rising_years.append(curr)

#         if metrics[curr]["fixed_assets"] < metrics[prev]["fixed_assets"]:
#             assets_falling_years.append(curr)

#         if (
#             metrics[curr]["net_debt"] > metrics[prev]["net_debt"]
#             and metrics[curr]["fixed_assets"] < metrics[prev]["fixed_assets"]
#         ):
#             overlap_years.append(curr)

#     # -----------------------------
#     # Loan Evergreening
#     # -----------------------------
#     total_proceeds = metrics[years[-1]]["proceeds"]
#     total_repayment = metrics[years[-1]]["repayment"]
#     total_debt = metrics[years[-1]]["borrowings"]

#     rollover_ratio = (
#         total_proceeds / total_debt if total_debt else None
#     )

#     principal_ratio = (
#         total_repayment / total_debt if total_debt else None
#     )

#     # -----------------------------
#     # Circular Trading
#     # -----------------------------
#     sales_up_cash_down = (
#         metrics[years[-1]]["revenue"] > metrics[years[-2]]["revenue"]
#         and metrics[years[-1]]["cfo"] < metrics[years[-2]]["cfo"]
#     )

#     return {
#         "zombie_company": {
#             "ebit_vs_interest": {
#                 "values": ebit_vs_interest,
#                 "years_below_1": ebit_below,
#             },
#             "cfo_vs_interest": {
#                 "values": cfo_vs_interest,
#                 "years_below_1": cfo_below,
#             },
#             "net_debt": {
#                 "values": values("net_debt"),
#                 "rising": net_debt_rising,
#             },
#             "profit": {
#                 "values": values("net_profit"),
#                 "falling": profit_falling,
#             },
#         },

#         "window_dressing": {
#             "cash_spike_yoy": cash_spike,
#             "profit_spike_yoy": profit_spike,
#             "one_off_income_ratio": one_off_ratio,
#         },

#         "asset_stripping": {
#             "fixed_assets": {
#                 "values": values("fixed_assets"),
#                 "decline_years": len(assets_falling_years),
#             },
#             "debt_vs_assets": {
#                 "net_debt": values("net_debt"),
#                 "fixed_assets": values("fixed_assets"),
#                 "comparison": {
#                     "debt_rising_years": debt_rising_years,
#                     "assets_falling_years": assets_falling_years,
#                     "overlap_years": overlap_years,
#                     "overlap_count": len(overlap_years),
#                     "rule_triggered": len(overlap_years) >= 2,
#                     "interpretation": (
#                         "Debt increased while assets declined across multiple years."
#                         if len(overlap_years) >= 2
#                         else
#                         "Debt increased, but asset decline was not persistent enough."
#                     ),
#                 },
#             },
#         },

#         "loan_evergreening": {
#             "loan_rollover_ratio": rollover_ratio,
#             "principal_repayment_ratio": principal_ratio,
#         },

#         "circular_trading": {
#             "receivables": values("receivables"),
#             "revenue": values("revenue"),
#             "sales_up_cash_down": sales_up_cash_down,
#         },
#     }

# risk_trend.py

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

    # =========================
    # 3.1 ZOMBIE COMPANY
    # =========================
    ebit_below = []
    cfo_below = []
    debt_profit_overlap = []

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
            "values": {
                "ebit": year_map("ebit"),
                "interest": year_map("interest"),
            },
            "comparison": {
                "years_below": ebit_below,
                "count": len(ebit_below),
                "rule_triggered": len(ebit_below) >= 2,
                "interpretation": (
                    "EBIT failed to cover interest for multiple years."
                    if len(ebit_below) >= 2
                    else "EBIT consistently exceeded interest expense."
                ),
            },
        },

        "cfo_vs_interest": {
            "values": {
                "cfo": year_map("cfo"),
                "interest": year_map("interest"),
            },
            "comparison": {
                "years_below": cfo_below,
                "count": len(cfo_below),
                "rule_triggered": len(cfo_below) >= 2,
                "interpretation": (
                    "Operating cash flows failed to cover interest in multiple years."
                    if len(cfo_below) >= 2
                    else "Cash flows generally covered interest."
                ),
            },
        },

        "debt_vs_profit": {
            "values": {
                "net_debt": year_map("net_debt"),
                "net_profit": year_map("net_profit"),
            },
            "comparison": {
                "overlap_years": debt_profit_overlap,
                "overlap_count": len(debt_profit_overlap),
                "rule_triggered": len(debt_profit_overlap) >= 2,
                "interpretation": (
                    "Debt increased while profits weakened across multiple years."
                    if len(debt_profit_overlap) >= 2
                    else "No sustained debt spiral."
                ),
            },
        },
    }

    # =========================
    # 3.4 LOAN EVERGREENING
    # =========================
    debt_ebitda_overlap = []

    for i in range(1, len(years)):
        y, p = years[i], years[i - 1]
        if (
            metrics[y]["net_debt"] > metrics[p]["net_debt"]
            and metrics[y]["ebitda"] <= metrics[p]["ebitda"]
        ):
            debt_ebitda_overlap.append(y)

    loan_evergreening = {
        "debt_vs_ebitda": {
            "values": {
                "net_debt": year_map("net_debt"),
                "ebitda": year_map("ebitda"),  # ✅ NOW FIXED
            },
            "comparison": {
                "overlap_years": debt_ebitda_overlap,
                "overlap_count": len(debt_ebitda_overlap),
                "rule_triggered": len(debt_ebitda_overlap) >= 2,
                "interpretation": (
                    "Debt rising while EBITDA stagnated or declined."
                    if len(debt_ebitda_overlap) >= 2
                    else "Debt growth supported by EBITDA."
                ),
            },
        }
    }

    return {
        "zombie_company": zombie_company,
        "loan_evergreening": loan_evergreening,
    }
