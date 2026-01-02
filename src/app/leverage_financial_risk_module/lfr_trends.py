

# # src/app/leverage_financial_risk_module/lfr_trends.py

# def _build_values(per_year, key):
#     """
#     Build Y, Y-1, Y-2, Y-3, Y-4 series safely
#     using canonical metric keys from per_year
#     """
#     years = sorted(per_year.keys(), reverse=True)
#     labels = ["Y", "Y-1", "Y-2", "Y-3", "Y-4"]

#     values = {}

#     for i, label in enumerate(labels):
#         if i < len(years):
#             year = years[i]
#             values[label] = round(per_year[year].get(key, 0.0), 4)
#         else:
#             values[label] = 0.0

#     return values


# def _generate_trend_insight(values: dict, metric_name: str) -> str:
#     """
#     Deterministic insight based on first vs last value
#     """
#     series = list(values.values())

#     latest = series[0]
#     oldest = series[-1]

#     if latest < oldest:
#         return f"{metric_name} has improved over the past five years."
#     elif latest > oldest:
#         return f"{metric_name} has increased over the past five years."
#     else:
#         return f"{metric_name} has remained broadly stable over the period."


# def compute_leverage_trends(per_year):
#     """
#     Build leverage trends using ONLY core leverage metrics
#     (NO rating-agency / advanced metrics)
#     """

#     # -----------------------------
#     # CORE METRICS
#     # -----------------------------
#     de_ratio = _build_values(per_year, "de_ratio")
#     debt_ebitda = _build_values(per_year, "debt_ebitda")
#     interest_cov = _build_values(per_year, "interest_coverage")
#     st_ratio = _build_values(per_year, "st_debt_ratio")

#     return {
#         # =================================================
#         # BASIC LEVERAGE METRICS
#         # =================================================
#         "basic leverage metrics": {

#             "debt_to_equity": {
#                 "total_debt": {
#                     "values": _build_values(per_year, "total_debt")
#                 },
#                 "equity": {
#                     "values": _build_values(per_year, "equity")
#                 },
#                 "debt to equity": {
#                     "values": de_ratio
#                 },
#                 "insight": _generate_trend_insight(
#                     de_ratio,
#                     "Debt-to-Equity"
#                 ),
#             },

#             "debt_to_ebitda": {
#                 "total_debt": {
#                     "values": _build_values(per_year, "total_debt")
#                 },
#                 "ebitda": {
#                     "values": _build_values(per_year, "ebitda")
#                 },
#                 "debt to ebitda": {
#                     "values": debt_ebitda
#                 },
#                 "insight": _generate_trend_insight(
#                     debt_ebitda,
#                     "Debt-to-EBITDA"
#                 ),
#             },

#             "interest_coverage": {
#                 "ebit": {
#                     "values": _build_values(per_year, "ebit")
#                 },
#                 "interest_cost": {
#                     "values": _build_values(per_year, "interest")
#                 },
#                 "interest coverage ratio": {
#                     "values": interest_cov
#                 },
#                 "insight": _generate_trend_insight(
#                     interest_cov,
#                     "Interest Coverage"
#                 ),
#             },
#         },

#         # =================================================
#         # SHORT-TERM DEBT DEPENDENCE
#         # =================================================
#         "short-term debt dependence": {
#             "short_term_debt": {
#                 "values": _build_values(per_year, "short_term_debt")
#             },
#             "total_debt": {
#                 "values": _build_values(per_year, "total_debt")
#             },
#             "st debt share": {
#                 "values": st_ratio
#             },
#             "insight": _generate_trend_insight(
#                 st_ratio,
#                 "Short-Term Debt Dependence"
#             ),
#         },
#     }


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
        return f"{metric_name} has improved over the past five years."
    elif latest > oldest:
        return f"{metric_name} has increased over the past five years."
    else:
        return f"{metric_name} has remained broadly stable over the period."


def compute_leverage_trends(per_year):
    """
    Build leverage trends using ONLY core leverage metrics
    Names strictly follow snake_case canonical schema
    """

    # -----------------------------
    # CORE METRICS
    # -----------------------------
    debt_to_equity = _build_values(per_year, "de_ratio")
    debt_to_ebitda = _build_values(per_year, "debt_ebitda")
    interest_coverage_ratio = _build_values(per_year, "interest_coverage")
    st_debt_share = _build_values(per_year, "st_debt_ratio")

    return {
        # =================================================
        # BASIC LEVERAGE METRICS
        # =================================================
        "basic leverage metrics": {

            "debt_to_equity": {
                "total_debt": {
                    "values": _build_values(per_year, "total_debt")
                },
                "equity": {
                    "values": _build_values(per_year, "equity")
                },
                "debt_to_equity": {
                    "values": debt_to_equity
                },
                "insight": _generate_trend_insight(
                    debt_to_equity,
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
                "debt_to_ebitda": {
                    "values": debt_to_ebitda
                },
                "insight": _generate_trend_insight(
                    debt_to_ebitda,
                    "Debt-to-EBITDA"
                ),
            },

            "interest_coverage_ratio": {
                "ebit": {
                    "values": _build_values(per_year, "ebit")
                },
                "interest_cost": {
                    "values": _build_values(per_year, "interest")
                },
                "interest_coverage_ratio": {
                    "values": interest_coverage_ratio
                },
                "insight": _generate_trend_insight(
                    interest_coverage_ratio,
                    "Interest Coverage"
                ),
            },
        },

        # =================================================
        # SHORT-TERM DEBT DEPENDENCE
        # =================================================
        "short-term debt dependence": {
            "short_term_debt": {
                "values": _build_values(per_year, "short_term_debt")
            },
            "total_debt": {
                "values": _build_values(per_year, "total_debt")
            },
            "st_debt_share": {
                "values": st_debt_share
            },
            "insight": _generate_trend_insight(
                st_debt_share,
                "Short-Term Debt Dependence"
            ),
        },
    }
