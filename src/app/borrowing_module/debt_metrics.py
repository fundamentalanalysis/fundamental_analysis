from typing import Dict, List

from .debt_models import YearFinancialInput


def safe_div(a, b):
    return a / b if (b not in (0, None) and a is not None) else None


def compute_per_year_metrics(financials_5y: List[YearFinancialInput]) -> Dict[int, dict]:
    metrics = {}
    sorted_fin = sorted(financials_5y, key=lambda x: x.year)

    for f in sorted_fin:
        total_debt = (f.short_term_debt or 0.0) + (f.long_term_debt or 0.0)
        total_assets = (f.total_equity or 0.0) + total_debt

        floating_share = None
        if f.floating_rate_debt is not None:
            if 0 < f.floating_rate_debt <= 1:
                floating_share = f.floating_rate_debt
            else:
                floating_share = safe_div(f.floating_rate_debt, total_debt)

        fixed_share = None
        if f.fixed_rate_debt is not None:
            if 0 < f.fixed_rate_debt <= 1:
                fixed_share = f.fixed_rate_debt
            else:
                fixed_share = safe_div(f.fixed_rate_debt, total_debt)
        elif floating_share is not None:
            fixed_share = max(0.0, 1 - floating_share)

        finance_cost_yield = safe_div(f.finance_cost, total_debt)
        wacd = f.weighted_avg_interest_rate if f.weighted_avg_interest_rate is not None else finance_cost_yield

        metrics[f.year] = {
            "year": f.year,
            "short_term_debt": f.short_term_debt,
            "long_term_debt": f.long_term_debt,
            "total_debt": total_debt,
            "total_equity": f.total_equity,
            "ebitda": f.ebitda,
            "ebit": f.ebit,
            "finance_cost": f.finance_cost,
            "capex": f.capex,
            "cwip": f.cwip,
            "revenue": f.revenue,
            "operating_cash_flow": f.operating_cash_flow,
            "total_assets": total_assets,
            "st_debt_share": safe_div(f.short_term_debt, total_debt),
            "de_ratio": safe_div(total_debt, f.total_equity),
            "debt_ebitda": safe_div(total_debt, f.ebitda),
            "interest_coverage": safe_div(f.ebit, f.finance_cost),
            "floating_share": floating_share,
            "fixed_share": fixed_share,
            "maturity_lt_1y_pct": safe_div(f.total_debt_maturing_lt_1y, total_debt),
            "maturity_1_3y_pct": safe_div(f.total_debt_maturing_1_3y, total_debt),
            "maturity_gt_3y_pct": safe_div(f.total_debt_maturing_gt_3y, total_debt),
            "wacd": wacd,
            "finance_cost_yield": finance_cost_yield,
            "ocf_to_debt": safe_div(f.operating_cash_flow, total_debt),
        }

    return metrics


def compute_yoy_percentages(metrics_by_year: Dict[int, dict]) -> Dict[str, Dict[str, str]]:
    yoy_output: Dict[str, Dict[str, str]] = {}
    years = sorted(metrics_by_year.keys())
    if not years:
        return yoy_output

    metric_keys = [k for k in metrics_by_year[years[0]].keys() if k != "year"]

    for key in metric_keys:
        yoy_output[key] = {}
        for idx, year in enumerate(years):
            label = f"Mar {year}"
            if idx == 0:
                yoy_output[key][label] = None
                continue

            prev_year = years[idx - 1]
            curr_val = metrics_by_year[year].get(key)
            prev_val = metrics_by_year[prev_year].get(key)

            if curr_val is None or prev_val in (None, 0):
                yoy_output[key][label] = None
            else:
                pct_change = ((curr_val - prev_val) / prev_val) * 100
                yoy_output[key][label] = f"{pct_change:.1f}%"

    return {k: dict(sorted(v.items(), reverse=True)) for k, v in yoy_output.items()}
# ==============================================================
# debt_metrics.py
# Core per-year metric calculations for Borrowings Module
# ==============================================================

from typing import Dict, List
from .debt_models import YearFinancialInput


def safe_div(a, b):
    return a / b if (b not in (0, None) and a is not None) else None


def compute_per_year_metrics(financials_5y: List[YearFinancialInput]) -> Dict[int, dict]:
    """
    Input:  List[YearFinancialInput]
    Output: Dict of metrics per year
    """

    metrics = {}
    
    # Sort to ensure we can identify the latest year
    sorted_fin = sorted(financials_5y, key=lambda x: x.year)
    if not sorted_fin:
        return {}
        
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
            "operating_cash_flow": f.operating_cash_flow,
            "total_assets": total_assets,
            
            # 3.1 Core Derived Metrics
            "st_debt_share": safe_div(f.short_term_debt, total_debt),
            "de_ratio": safe_div(total_debt, f.total_equity),
            "debt_ebitda": safe_div(total_debt, f.ebitda),
            "interest_coverage": safe_div(f.ebit, f.finance_cost),
        }

        # Floating vs fixed share (accept ratio or absolute)
        float_input = f.floating_rate_debt
        if float_input is not None:
            if 0 < float_input <= 1:
                m["floating_share"] = float_input
            else:
                m["floating_share"] = safe_div(float_input, total_debt)
        else:
            m["floating_share"] = None

        fixed_input = f.fixed_rate_debt
        if fixed_input is not None:
            if 0 < fixed_input <= 1:
                m["fixed_share"] = fixed_input
            else:
                m["fixed_share"] = safe_div(fixed_input, total_debt)
        elif m["floating_share"] is not None:
            m["fixed_share"] = max(0.0, 1 - m["floating_share"])
        else:
            m["fixed_share"] = None

        # Maturity Profile – assume granular data available per year
        m["maturity_lt_1y_pct"] = safe_div(f.total_debt_maturing_lt_1y, total_debt)
        m["maturity_1_3y_pct"] = safe_div(f.total_debt_maturing_1_3y, total_debt)
        m["maturity_gt_3y_pct"] = safe_div(f.total_debt_maturing_gt_3y, total_debt)

        # Cost of debt metrics
        wacd = f.weighted_avg_interest_rate
        if wacd is None:
            wacd = safe_div(f.finance_cost, total_debt)
        m["wacd"] = wacd
        m["finance_cost_yield"] = safe_div(f.finance_cost, total_debt)

        # Cash flow coverage
        m["ocf_to_debt"] = safe_div(f.operating_cash_flow, total_debt)
    
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
