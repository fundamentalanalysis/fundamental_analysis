# trend_engine.py

def yoy(current, previous):
    if previous == 0 or previous is None:
        return None
    return (current - previous) / previous


def compute_yoy_trends(financials):
    trends = []

    for i in range(1, len(financials)):
        curr = financials[i]
        prev = financials[i - 1]

        trends.append({
            "year": curr.year,
            "receivables_yoy": yoy(curr.trade_receivables, prev.trade_receivables),
            "payables_yoy": yoy(curr.trade_payables, prev.trade_payables),
            "inventory_yoy": yoy(curr.inventory, prev.inventory),
            "revenue_yoy": yoy(curr.revenue, prev.revenue),
        })

    return trends


def compute_cagr(start, end, years):
    if start <= 0 or years <= 0:
        return None
    return ((end / start) ** (1 / years)) - 1
