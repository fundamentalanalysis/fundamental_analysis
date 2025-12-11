# ==============================================================
# debt_metrics.py
# Core per-year metric calculations for Borrowings Module
# ==============================================================

from typing import Dict
from .debt_models import YearFinancialInput


def safe_div(a, b):
    return a / b if (b not in (0, None) and a is not None) else None


def compute_per_year_metrics(financials_5y) -> Dict[int, dict]:
    """
    Input:  List[YearFinancialInput]
    Output: Dict of metrics per year
    """

    metrics = {}
    
    # Sort to ensure we can identify the latest year
    sorted_fin = sorted(financials_5y, key=lambda x: x.year)
    if not sorted_fin:
        return {}
        
    latest_year = sorted_fin[-1].year

    for f in sorted_fin:
        total_debt = (f.short_term_debt or 0) + (f.long_term_debt or 0)
        
        # Proxy for total assets (Equity + Debt) since full BS is not provided
        # Needed for Rule A3b (CWIP / Total Assets)
        total_assets = (f.total_equity or 0) + total_debt

        m = {
            "year": f.year,
            "total_debt": total_debt,
            "short_term_debt": f.short_term_debt,
            "long_term_debt": f.long_term_debt,
            "finance_cost": f.finance_cost,
            "revenue": f.revenue,
            "ebitda": f.ebitda,
            "cwip": f.cwip,
            "total_assets": total_assets,
            
            # 3.1 Core Derived Metrics
            "st_debt_share": safe_div(f.short_term_debt, total_debt),
            "de_ratio": safe_div(total_debt, f.total_equity),
            "debt_ebitda": safe_div(total_debt, f.ebitda),
            "interest_coverage": safe_div(f.ebit, f.finance_cost),
        }

        # Add "Latest Year" specific metrics from 'midd'
        # These are only valid/provided for the most recent snapshot
        if f.year == latest_year:
            # Handle Floating Rate: Input might be ratio (0.60) or amount
            float_input = f.floating_rate_debt or 0
            if float_input <= 1 and float_input > 0:
                # It's likely a ratio already (e.g. 0.60)
                m["floating_share"] = float_input
            else:
                # It's an amount, calculate share
                m["floating_share"] = safe_div(float_input, total_debt)

            m["wacd"] = f.weighted_avg_interest_rate
            
            # Maturity Profile
            m["maturity_lt_1y_pct"] = safe_div(f.total_debt_maturing_lt_1y, total_debt)
            print(f.total_debt_maturing_lt_1y)
            m["maturity_1_3y_pct"] = safe_div(f.total_debt_maturing_lt_1y, total_debt)
            m["maturity_gt_3y_pct"] = safe_div(f.total_debt_maturing_lt_1y, total_debt)
        else:
            # Historical years don't have this granular data in the current input model
            m["floating_share"] = None
            m["wacd"] = None
            m["maturity_lt_1y_pct"] = None
            m["maturity_1_3y_pct"] = None
            m["maturity_gt_3y_pct"] = None
    
        metrics[f.year] = m

    return metrics
def compute_yoy_percentage(metrics_by_year: Dict[int, dict]) -> Dict[str, dict]:
    """
    Converts absolute per-year metrics into YoY % growth for every metric.
    Output will have years in descending order: latest → oldest
    """
    yoy_output = {}

    # Sort years ascending to calculate YoY properly
    years = sorted(metrics_by_year.keys())

    # All metric keys except 'year'
    metric_keys = [k for k in metrics_by_year[years[0]].keys() if k != "year"]

    for metric in metric_keys:
        temp_dict = {}
        for i, year in enumerate(years):
            label = f"Mar {year}"
            if i == 0:
                temp_dict[label] = None  # First year has no previous year
            else:
                prev_year = years[i - 1]
                curr_val = metrics_by_year[year][metric]
                prev_val = metrics_by_year[prev_year][metric]

                if curr_val is None or prev_val in (None, 0):
                    temp_dict[label] = None
                else:
                    pct_change = ((curr_val - prev_val) / prev_val) * 100
                    temp_dict[label] = f"{round(pct_change)}%"

        # Reverse temp_dict to get descending years
        yoy_output[metric] = dict(sorted(temp_dict.items(), reverse=True))

    return yoy_output