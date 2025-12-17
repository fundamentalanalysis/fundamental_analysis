# def compute_per_year_metrics(financials):
#     metrics = {}

#     for f in financials:
#         net_debt = f.borrowings + f.lease_liabilities - f.cash_equivalents

#         metrics[f.year] = {
#             "year": f.year,
#             "revenue": f.revenue,
#             "ebit": f.operating_profit,
#             "interest": f.interest,
#             "net_profit": f.net_profit,
#             "other_income": f.other_income,

#             "cash": f.cash_equivalents,
#             "cfo": f.cash_from_operating_activity,

#             "fixed_assets": f.fixed_assets,
#             "receivables": f.trade_receivables,

#             "borrowings": f.borrowings,
#             "net_debt": net_debt,

#             "dividends": f.dividends_paid,
#             "proceeds": f.proceeds_from_borrowings,
#             "repayment": abs(f.repayment_of_borrowings),
#         }

#     return metrics


# risk_metrics.py


def compute_per_year_metrics(financials):
    metrics = {}

    for f in financials:
        net_debt = f.borrowings + f.lease_liabilities - f.cash_equivalents
        ebitda = f.operating_profit + f.depreciation

        metrics[f.year] = {
            "year": f.year,

            # Profitability
            "revenue": f.revenue,
            "ebit": f.operating_profit,
            "ebitda": ebitda,
            "interest": f.interest,
            "net_profit": f.net_profit,
            "other_income": f.other_income,

            # Cash
            "cash": f.cash_equivalents,
            "cfo": f.cash_from_operating_activity,

            # Assets
            "fixed_assets": f.fixed_assets,
            "receivables": f.trade_receivables,

            # Debt
            "borrowings": f.borrowings,
            "short_term_debt": f.short_term_debt,
            "net_debt": net_debt,

            # Financing
            "proceeds": f.proceeds_from_borrowings,
            "repayment": abs(f.repayment_of_borrowings),
            "interest_capitalized": f.interest_capitalized,

            # RPT
            "rpt_sales": f.related_party_sales,
            "rpt_receivables": f.related_party_receivables,
        }

    return metrics

