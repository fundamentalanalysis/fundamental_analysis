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
