# src/app/leverage_financial_risk_module/lfr_trends.py
def _build_values(per_year, key):
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
    return {
        # ---------------------------------
        # Leverage ratios
        # ---------------------------------
        "debt_to_equity": {
            "values": _build_values(per_year, "de_ratio"),
            "insight": _generate_trend_insight(
                _build_values(per_year, "de_ratio"),
                "Debt-to-Equity"
            ),
        },

        "debt_to_ebitda": {
            "values": _build_values(per_year, "debt_ebitda"),
            "insight": _generate_trend_insight(
                _build_values(per_year, "debt_ebitda"),
                "Debt-to-EBITDA"
            ),
        },

        "gross_debt_to_ebitda": {
            "values": _build_values(per_year, "debt_ebitda"),
            "insight": _generate_trend_insight(
                _build_values(per_year, "debt_ebitda"),
                "Gross Debt-to-EBITDA"
            ),
        },

        "net_debt": {
            "values": _build_values(per_year, "net_debt"),
            "insight": _generate_trend_insight(
                _build_values(per_year, "net_debt"),
                "Net Debt"
            ),
        },

        "net_debt_to_ebitda": {
            "values": _build_values(per_year, "net_debt_ebitda"),
            "insight": _generate_trend_insight(
                _build_values(per_year, "net_debt_ebitda"),
                "Net Debt-to-EBITDA"
            ),
        },

        # ---------------------------------
        # Coverage & servicing
        # ---------------------------------
        "interest_coverage_ratio": {
            "values": _build_values(per_year, "interest_coverage"),
            "insight": _generate_trend_insight(
                _build_values(per_year, "interest_coverage"),
                "Interest Coverage"
            ),
        },

        "debt_service_burden": {
            "values": _build_values(per_year, "debt_service_burden"),
            "insight": _generate_trend_insight(
                _build_values(per_year, "debt_service_burden"),
                "Debt Service Burden"
            ),
        },

        # ---------------------------------
        # Liquidity risk
        # ---------------------------------
        "st_debt_share": {
            "values": _build_values(per_year, "st_debt_ratio"),
            "insight": _generate_trend_insight(
                _build_values(per_year, "st_debt_ratio"),
                "Short-Term Debt Dependence"
            ),
        },
    }
