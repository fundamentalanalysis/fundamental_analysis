
def compute_per_year_metrics(financial_years):
    """
    Normalize all financial inputs into a per-year metrics dictionary.
    """

    metrics = {}

    for fy in financial_years:
        year = fy.year

        borrowings = fy.borrowings or 0
        cash = fy.cash_equivalents or 0

        metrics[year] = {
            # Profitability
            "revenue": fy.revenue or 0,
            "ebit": fy.operating_profit or 0,
            "interest": fy.interest or 0,
            "net_profit": fy.net_profit or 0,
            "other_income": fy.other_income or 0,
            "depreciation": fy.depreciation or 0,
            "ebitda": (fy.operating_profit or 0) + (fy.depreciation or 0),

            # Cash flow
            "cfo": fy.cash_from_operating_activity or 0,
            "dividends_paid": fy.dividends_paid or 0,

            # Balance sheet
            "fixed_assets": fy.fixed_assets or 0,
            "total_assets": fy.total_assets or 0,
            "receivables": fy.trade_receivables or 0,
            "cash": cash,
            "net_debt": borrowings - cash,

            # Evergreening
            "proceeds_from_borrowings": fy.proceeds_from_borrowings or 0,
            "repayment_of_borrowings": abs(fy.repayment_of_borrowings or 0),
            "interest_paid": abs(fy.interest_paid_fin or 0),
            "interest_capitalized": fy.interest_capitalized or 0,
            "short_term_debt": fy.short_term_debt or 0,

            # Related party
            "rpt_sales": fy.related_party_sales or 0,
            "rpt_receivables": fy.related_party_receivables or 0,
        }

    return metrics
