# src/app/borrowing_module/debt_trend.py

def compute_cagr(start, end, years):
    if not start or not end or start <= 0 or years <= 0:
        return None
    # CAGR formula: (End/Start)^(1/n) - 1
    # We return the percentage value (e.g., 7.5 for 7.5%)
    return ((end / start) ** (1 / years) - 1) * 100


def compute_yoy(current, previous):
    if not previous or previous == 0:
        return 0.0
    return (current - previous) / previous * 100


def compute_trend_metrics(financials, yearly):
    # yearly is Dict[int, dict] from compute_per_year_metrics
    years = sorted(yearly.keys())
    if len(years) < 2:
        return {}

    first_year = years[0]
    last_year = years[-1]
    num_years = len(years) - 1

    # --- 1. CAGRs (Total Debt, LT Debt, EBITDA, Finance Cost) ---

    # Total Debt
    debt_start = yearly[first_year]["total_debt"]
    debt_end = yearly[last_year]["total_debt"]
    debt_cagr = compute_cagr(debt_start, debt_end, num_years)



    # Long Term Debt
    lt_debt_start = yearly[first_year]["long_term_debt"]
    lt_debt_end = yearly[last_year]["long_term_debt"]
    lt_debt_cagr = compute_cagr(lt_debt_start, lt_debt_end, num_years)

    # EBITDA
    ebitda_start = yearly[first_year]["ebitda"]
    ebitda_end = yearly[last_year]["ebitda"]
    ebitda_cagr = compute_cagr(ebitda_start, ebitda_end, num_years)

    # Finance Cost
    fc_start = yearly[first_year]["finance_cost"]
    fc_end = yearly[last_year]["finance_cost"]
    finance_cost_cagr = compute_cagr(fc_start, fc_end, num_years)

    # --- 2. YoY Growth Lists (for ST Debt Surge Rule) ---
    st_debt_yoy_growth = []

    for i in range(1, len(years)):
        prev_y = years[i - 1]
        curr_y = years[i]

        st_prev = yearly[prev_y]["short_term_debt"]
        st_curr = yearly[curr_y]["short_term_debt"]

        growth = compute_yoy(st_curr, st_prev)
        st_debt_yoy_growth.append(growth)
    # --- 3. Revenue CAGR ---
    # Note: Revenue is not in the current input model, so we return None.
    # If needed, add 'revenue' to YearFinancialInput and calculate here.
    # revenue_cagr = None
    revenue_start = yearly[first_year]["revenue"]
    revenue_end = yearly[last_year]["revenue"]
    revenue_cagr = compute_cagr(revenue_start, revenue_end, num_years)

    return {
        "debt_cagr": debt_cagr,
        "ebitda_cagr": ebitda_cagr,
        "lt_debt_cagr": lt_debt_cagr,
        "finance_cost_cagr": finance_cost_cagr,
        "st_debt_yoy_growth": st_debt_yoy_growth,
        "revenue_cagr": revenue_cagr,
        # Helper for comparison
        "debt_growth_vs_ebitda": (
            (debt_cagr - ebitda_cagr)
            if (debt_cagr is not None and ebitda_cagr is not None)
            else None
        ),
    }
