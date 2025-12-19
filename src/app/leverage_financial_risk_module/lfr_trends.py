
# src/app/leverage_financial_risk_module/lfr_trends.py

def _build_values(per_year, key):
    """
    Build Y, Y-1, Y-2, Y-3, Y-4 series safely
    using canonical metric keys from per_year
    """
    years = sorted(per_year.keys(), reverse=True)
    labels = ["Y", "Y-1", "Y-2", "Y-3", "Y-4"]

    values = {}

    for i, label in enumerate(labels):
        if i < len(years):
            year = years[i]
            values[label] = round(per_year[year].get(key, 0.0), 4)
        else:
            values[label] = 0.0

    return values


def _generate_trend_insight(values: dict, metric_name: str) -> str:
    """
    Deterministic insight based on first vs last value
    """
    series = list(values.values())

    latest = series[0]
    oldest = series[-1]

    if latest < oldest:
        return f"{metric_name} has improved over the past five years, indicating strengthening financial profile."
    elif latest > oldest:
        return f"{metric_name} has increased over the past five years, indicating rising leverage or risk."
    else:
        return f"{metric_name} has remained broadly stable over the period."


def compute_leverage_trends(per_year):
    """
    Build leverage trends using CANONICAL metric keys
    and attach deterministic insights
    """

    # -----------------------------
    # BASIC METRICS
    # -----------------------------
    de_ratio = _build_values(per_year, "de_ratio")
    debt_ebitda = _build_values(per_year, "debt_ebitda")
    interest_cov = _build_values(per_year, "interest_coverage")

    # -----------------------------
    # ADVANCED METRICS
    # -----------------------------
    net_debt = _build_values(per_year, "net_debt")
    net_debt_ebitda = _build_values(per_year, "net_debt_ebitda")
    ffo_cov = _build_values(per_year, "ffo_coverage")
    st_ratio = _build_values(per_year, "st_debt_ratio")

    return {
        "basic leverage metrics": {
            "debt_to_equity": {
                "total_debt": {
                    "values": _build_values(per_year, "total_debt")
                },
                "equity": {
                    "values": _build_values(per_year, "equity")
                },
                "debt to equity": {
                    "values": de_ratio
                },
                "insight": _generate_trend_insight(
                    de_ratio,
                    "Debt-to-Equity"
                ),
            },

            "debt_to_ebitda": {
                "total_debt": {
                    "values": _build_values(per_year, "total_debt")
                },
                "ebitda": {
                    "values": _build_values(per_year, "ebitda")
                },
                "debt to ebitda": {
                    "values": debt_ebitda
                },
                "insight": _generate_trend_insight(
                    debt_ebitda,
                    "Debt-to-EBITDA"
                ),
            },

            "interest_coverage": {
                "ebit": {
                    "values": _build_values(per_year, "ebit")
                },
                "interest_cost": {
                    "values": _build_values(per_year, "interest_cost")
                },
                "interest coverage ratio": {
                    "values": interest_cov
                },
                "insight": _generate_trend_insight(
                    interest_cov,
                    "Interest Coverage"
                ),
            },
        },

        "advanced fitch / s&p style metrics": {
            "net_debt": {
                "total_debt": {
                    "values": _build_values(per_year, "total_debt")
                },
                "cash": {
                    "values": _build_values(per_year, "cash")
                },
                "net debt": {
                    "values": net_debt
                },
                "insight": _generate_trend_insight(
                    net_debt,
                    "Net Debt"
                ),
            },

            "net_debt_to_ebitda": {
                "net_debt": {
                    "values": _build_values(per_year, "net_debt")
                },
                "ebitda": {
                    "values": _build_values(per_year, "ebitda")
                },
                "net debt to ebitda": {
                    "values": net_debt_ebitda
                },
                "insight": _generate_trend_insight(
                    net_debt_ebitda,
                    "Net Debt-to-EBITDA"
                ),
            },

            "ffo_coverage": {
                "ebitda": {
                    "values": _build_values(per_year, "ebitda")
                },
                "interest_cost": {
                    "values": _build_values(per_year, "interest_cost")
                },
                "taxes": {
                    "values": _build_values(per_year, "taxes")
                },
                "ffo": {
                    "values": _build_values(per_year, "ffo")
                },
                "ffo coverage": {
                    "values": ffo_cov
                },
                "insight": _generate_trend_insight(
                    ffo_cov,
                    "FFO Coverage"
                ),
            },

            "debt_service_burden": {
                "short_term_debt": {
                    "values": _build_values(per_year, "short_term_debt")
                },
                "total_debt": {
                    "values": _build_values(per_year, "total_debt")
                },
                "debt service burden": {
                    "values": st_ratio
                },
                "insight": _generate_trend_insight(
                    st_ratio,
                    "Debt Service Burden"
                ),
            },
        },

        "short-term debt dependence": {
            "short_term_debt": {
                "values": _build_values(per_year, "short_term_debt")
            },
            "total_debt": {
                "values": _build_values(per_year, "total_debt")
            },
            "st debt share": {
                "values": st_ratio
            },
            "insight": _generate_trend_insight(
                st_ratio,
                "Short-Term Debt Dependence"
            ),
        },
    }
