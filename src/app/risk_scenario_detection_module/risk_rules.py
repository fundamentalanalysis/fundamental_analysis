from typing import List, Dict
from .risk_models import YearFinancials, RuleResult
from .risk_trend import RiskTrendAnalyzer
from .risk_config import DEFAULT_THRESHOLDS


# ---------------- SAFE HELPERS ---------------- #

def safe_lt(a, b):
    try:
        if a is None or b is None:
            return False
        return float(a) < float(b)
    except (ValueError, TypeError):
        return False

def safe_gt(a, b):
    try:
        if a is None or b is None:
            return False
        return float(a) > float(b)
    except (ValueError, TypeError):
        return False

def safe_ratio(a, b):
    if a is None or b in (None, 0):
        return None
    return a / b

def safe_yoy(curr, prev):
    if curr is None or prev in (None, 0):
        return None
    return (curr - prev) / abs(prev)


def _make_rule(rule_id, rule_name, year, flag, value, threshold, reason):
    return RuleResult(
        rule_id=rule_id,
        rule_name=rule_name,
        year=year,
        flag=flag,
        value=value,
        threshold=threshold,
        reason=reason
    )
def yoy_growth(arr):
    if len(arr) < 2 or arr[-2] == 0:
        return 0
    return (arr[-1] - arr[-2]) / arr[-2]

# ------------------------------------------------ #
#               RISK RULE ENGINE (SAFE)
# ------------------------------------------------ #

class RiskRulesEngine:
    def __init__(self, thresholds: Dict[str, float] = None):
        self.th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.trend = RiskTrendAnalyzer()
        

    def evaluate(self, financials: List[YearFinancials]) -> List[RuleResult]:
        results = []
        if not financials:
            return results

        financials = sorted(financials, key=lambda x: x.year)
        years = [f.year for f in financials]

        # Extract arrays safely
        ebit = []
        for f in financials:
            if f.ebit is not None:
                ebit.append(f.ebit)
            else:
                if f.operating_profit is not None and f.depreciation is not None:
                    ebit.append(f.operating_profit - f.depreciation)
                else:
                    ebit.append(None)

        interest = [f.interest for f in financials]

        ocf = [
            getattr(f, "operating_cash_flow", None)
            or getattr(f, "cash_from_operating_activity", None)
            for f in financials
        ]

        net_debt = [f.borrowings for f in financials]
        fixed_assets = [f.fixed_assets for f in financials]
        dividends = [getattr(f, "dividends_paid", None) for f in financials]

        net_income = [
            f.net_profit if f.net_profit is not None else f.profit_from_operations
            for f in financials
        ]

        cash = [f.cash_equivalents for f in financials]
        one_off = [f.other_income for f in financials]
        revenue = [f.revenue for f in financials]

        rpt_sales = [getattr(f, "related_party_sales", None) for f in financials]
        rpt_recv = [getattr(f, "related_party_receivables", None) for f in financials]

        total_recv = [
            getattr(f, "total_receivables", None) or f.trade_receivables
            for f in financials
        ]

        loan_rollover = [
            getattr(f, "loan_rollover_amount", None)
            or ((f.proceeds_from_borrowings or 0) - (f.repayment_of_borrowings or 0))
            for f in financials
        ]

        interest_cap = [
            getattr(f, "interest_capitalized", None)
            or ((f.interest_paid_fin or 0) - (f.interest or 0))
            for f in financials
        ]

        principal_repayment = [f.repayment_of_borrowings for f in financials]
        assets = [f.total_assets for f in financials]

        # Calculate risk patterns
        zomb = self.trend.zombie_signals(ebit, interest, ocf, net_debt, net_income)
        window = self.trend.window_dressing(cash, net_income, revenue, one_off)
        asset = self.trend.asset_stripping(fixed_assets, net_debt, dividends)
        everg = self.trend.loan_evergreening(
            loan_rollover, net_debt, interest_cap, interest, principal_repayment
        )

        recv_growth = yoy_growth(total_recv)
        sales_growth = yoy_growth(revenue)
        circ = self.trend.circular_trading(
            rpt_sales, rpt_recv, revenue, ocf, recv_growth, sales_growth
        )

        latest_year = years[-1]

        # ----------------------------------------------------------- #
        #                           RULES
        # ----------------------------------------------------------- #
        print("Zombie analysis:", zomb)
        # Z1: EBIT < Interest consecutive years
        if zomb["ebit_trend"]["latest"] >= self.th["interest_overtake_years"]:
            results.append(_make_rule(
                "Z1", "Zombie Company Detection", latest_year, "CRITICAL",
                zomb["ebit_trend"]["latest"] ,
                f">={self.th['interest_overtake_years']} years",
                "EBIT < Interest for multiple years."
            ))
       
        # Z2: OCF < Interest consecutive years
        if zomb["ocf_trend"]["latest"] >= self.th["interest_overtake_years"]:
            results.append(_make_rule(
                "Z2", "Zombie Company Detection", latest_year, "HIGH",
                zomb["ocf_trend"]["latest"],
                f">={self.th['interest_overtake_years']} years",
                "OCF < Interest for multiple years."
            ))

        # Z3: net debt ↑ AND profit ↓
        if safe_lt(net_income[-1], net_income[0]) and safe_gt(net_debt[-1], net_debt[0]):
            results.append(_make_rule(
                "Z3", "Zombie Company Detection", latest_year, "HIGH",
                net_debt[-1] - net_debt[0],
                "net_debt up & profit down",
                "Net debt rising while profits falling."
            ))
        print("Window dressing analysis:", window)
        # W1: Cash spike
        for i, (year, val) in enumerate(window["cash_trend"].items()):
            if val is not None and safe_gt(val, self.th["fake_cash_spike_threshold"]):
                results.append(_make_rule(
                    "W1", "Window Dressing - Cash Spike", year, "YELLOW",
                    val, f">{ self.th['fake_cash_spike_threshold'] }",
                    "Large YoY cash spike."
                ))

        # W2: One-off income spike
        for i, (year, ratio) in enumerate(window["oneoff_income_trend"].items()):
            if ratio is not None and safe_gt(ratio, self.th["oneoff_profit_jump_threshold"]):
                results.append(_make_rule(
                    "W2", "One-off Income", year, "YELLOW",
                    ratio, f"> {self.th['oneoff_profit_jump_threshold']}",
                    "One-off income large vs PAT."
                ))

        # W3: Profit spike without revenue
        # ni_yoy = window["net_income_trend"]
        # rev_yoy = circ["revenue_trend"]
        ni_yoy = net_income
        rev_yoy = revenue
        print("NI YoY:", ni_yoy)
        print("Rev YoY:", rev_yoy)
        for i in range(min(len(ni_yoy), len(rev_yoy)) - 1):
            print(f"Year {financials[i+1].year}")

            ni = ni_yoy[i]
            rv = rev_yoy[i]
            print("NI YoY value:", ni)
            if ni is not None and safe_gt(ni, self.th["profit_spike_no_revenue_threshold"]) and (rv is None or safe_lt(rv, 0.05)):
                results.append(_make_rule(
                    "W3", "Profit Spike Without Revenue Growth", financials[i+1].year,
                    "YELLOW", ni,
                    f"profit>{self.th['profit_spike_no_revenue_threshold']} & rev<5%",
                    "Profit spike not backed by revenue."
                ))
        print("Asset stripping analysis:", asset)   
        # A1: Fixed assets declining

        if asset["fixed_assets_trend"]['pct'] >= self.th["fixed_asset_decline_years"]:

            results.append(_make_rule(
                "A1", "Fixed Assets Decline", latest_year, "RED",
                asset["fixed_assets_trend"],
                f">={self.th['fixed_asset_decline_years']['pct']} years",
                "Fixed assets declining."
            ))

        # A2: Dividends despite falling assets
        for i in range(1, len(financials)):
            if safe_gt(dividends[i], 0) and safe_lt(fixed_assets[i], fixed_assets[i - 1]):
                results.append(_make_rule(
                    "A2", "Dividends Despite Falling Assets", financials[i].year,
                    "YELLOW", dividends[i],
                    "dividend>0 & fixed assets down",
                    "Promoter extraction risk."
                ))
                break

        # A3: debt rising & assets shrinking
        if asset["fixed_assets_trend"]['yoy'] == "down" and asset["net_debt_trend"]['yoy'] == "up":
            results.append(_make_rule(
                "A3", "Debt Up & Assets Down", latest_year, "CRITICAL",
                None, "debt up & assets down",
                "Debt rising while assets shrink."
            ))

        # E1: Loan rollover > threshold
        for i, r in enumerate(everg["rollover_trend"]):
            if r is not None and safe_gt(r, self.th["loan_rollover_critical_ratio"]):
                results.append(_make_rule(
                    "E1", "Loan Rollover >50%", financials[i].year, "RED",
                    r, f">{self.th['loan_rollover_critical_ratio']}",
                    "High rollover suggests evergreening."
                ))

        # E2: Interest capitalized high
        for i, r in enumerate(everg["interest_cap_trend"]):
            if r is not None and safe_gt(r, self.th["interest_capitalized_ratio"]):
                results.append(_make_rule(
                    "E2", "Interest Capitalized", financials[i].year, "YELLOW",
                    r, f">{self.th['interest_capitalized_ratio']}",
                    "Capitalized interest indicates stress."
                ))

        # E3: Minimal principal repayment
        for i, r in enumerate(everg["principal_repayment_trend"]):
            if r is not None and safe_lt(r, self.th["minimal_principal_repayment_ratio"]):
                results.append(_make_rule(
                    "E3", "Minimal Principal Repayment", financials[i].year,
                    "YELLOW", r,
                    f"<{self.th['minimal_principal_repayment_ratio']}",
                    "Very low principal repayment."
                ))

        # C1: High RPT sales
        for i, rsr in enumerate(circ["rpt_sales_trend"]):
            if rsr is not None and safe_gt(rsr, self.th["rpt_revenue_threshold"]):
                results.append(_make_rule(
                    "C1", "High RPT Sales", financials[i].year, "RED",
                    rsr, f">{self.th['rpt_revenue_threshold']}",
                    "Related-party sales unusually high."
                ))

        # C2a: High RPT receivables
        for i, r in enumerate(circ["rpt_receivables_trend"]):
            if r is not None and safe_gt(r, self.th["rpt_recv_spike_threshold"]):
                results.append(_make_rule(
                    "C2", "RPT Receivables High", financials[i].year, "YELLOW",
                    r, f">{self.th['rpt_recv_spike_threshold']}",
                    "High related-party receivables."
                ))

        # C2b: receivables YoY spike > revenue YoY spike
        total_recv_arr = [f.trade_receivables for f in financials]
        revenue_arr = [f.revenue for f in financials]
        total_recv_yoy = yoy_growth(total_recv_arr)
        revenue_yoy = yoy_growth(revenue_arr)

        for i in range(min(len(total_recv_arr), len(revenue_arr)) - 1):
            ry = total_recv_arr[i]
            rv = total_recv_arr[i]

            if ry is None or rv is None:
                continue

            if safe_gt(ry, rv) and safe_gt(ry, self.th["rpt_recv_spike_threshold"]):
                results.append(_make_rule(
                    "C2b", "Receivables Spike YoY", financials[i+1].year,
                    "YELLOW", ry, f">{self.th['rpt_recv_spike_threshold']}",
                    "Receivables growing faster than revenue."
                ))

        # C3: revenue ↑ but OCF ↓
        for i in range(min(len(revenue),len(ocf) - 1)):
            rev = revenue[i]
            ocf_ = revenue[i]

            if safe_gt(rev, 0) and safe_lt(ocf_, 0):
                results.append(_make_rule(
                    "C3", "Revenue Up, OCF Down", financials[i+1].year,
                    "RED", rev, "rev up & ocf down",
                    "Revenue growth without cash flow."
                ))

        # # ----------------------------------------------------------- #
        # #               FORCE ALL RULES (DEMO MODE)
        # # ----------------------------------------------------------- #
        # if self.force_all:
        #     existing = {r.rule_id for r in results}

        #     ALL_RULES = {
        #         "Z1": ("Zombie Company Detection", "CRITICAL"),
        #         "Z2": ("Zombie - OCF Coverage", "HIGH"),
        #         "Z3": ("Debt Rising, Profit Falling", "HIGH"),
        #         "W1": ("Window Dressing - Cash Spike", "YELLOW"),
        #         "W2": ("One-off Income", "YELLOW"),
        #         "W3": ("Profit Spike Without Revenue", "YELLOW"),
        #         "A1": ("Fixed Assets Decline", "RED"),
        #         "A2": ("Dividends Despite Asset Decline", "YELLOW"),
        #         "A3": ("Debt Up & Assets Down", "CRITICAL"),
        #         "E1": ("Loan Evergreening Risk", "RED"),
        #         "E2": ("Interest Capitalized", "YELLOW"),
        #         "E3": ("Minimal Principal Repayment", "YELLOW"),
        #         "C1": ("High RPT Sales", "RED"),
        #         "C2": ("High RPT Receivables", "YELLOW"),
        #         "C2b": ("Receivables Growing Faster Than Sales", "YELLOW"),
        #         "C3": ("Revenue Up While OCF Down", "RED"),
        #     }

        #     for rule_id, (name, severity) in ALL_RULES.items():
        #         if rule_id not in existing:
        #             results.append(RuleResult(
        #                 rule_id=rule_id,
        #                 rule_name=name,
        #                 year=latest_year,
        #                 flag=severity,
        #                 value=None,
        #                 threshold="FORCED",
        #                 reason="Rule forcibly included for demo/testing."
        #             ))

        # # ----------------------------------------------------------- #
        # #                 ORDER RULES CONSISTENTLY
        # # ----------------------------------------------------------- #

        # RULE_ORDER = {
        #     "Z1": 1, "Z2": 2, "Z3": 3,
        #     "W1": 4, "W2": 5, "W3": 6,
        #     "A1": 7, "A2": 8, "A3": 9,
        #     "E1": 10, "E2": 11, "E3": 12,
        #     "C1": 13, "C2": 14, "C2b": 15, "C3": 16
        # }

        # results.sort(
        #     key=lambda r: RULE_ORDER.get(r.rule_id, 999)
        # )


        return results
