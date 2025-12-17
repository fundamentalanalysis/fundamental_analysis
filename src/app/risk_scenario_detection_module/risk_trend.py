# risk_trend.py
from typing import List, Dict, Any


class RiskTrendAnalyzer:

    # ======================================================
    # SAFE BASIC TREND
    # ======================================================
    @staticmethod
    def compute_trend(arr: List[float]) -> Dict[str, Any]:
        if not arr:
            return {"latest": None, "yoy": "flat"}

        latest = arr[-1]

        if len(arr) < 2 or arr[-2] in (None, 0) or latest is None:
            return {"latest": latest, "yoy": "flat"}

        prev = arr[-2]
        pct = (latest - prev) / abs(prev)

        if pct > 0.15:
            direction = "up"
        elif pct < -0.15:
            direction = "down"
        else:
            direction = "flat"

        return {"latest": latest, "yoy": direction, "pct": round(pct, 3)}

    @staticmethod
    def _values(arr: List[float]) -> Dict[str, float]:
        if not arr:
            return {}
        return {
            f"Y-{i}" if i else "Y": v
            for i, v in enumerate(reversed(arr[-5:]))
        }

    # ======================================================
    # 3.1 ZOMBIE COMPANY (SAFE)
    # ======================================================
    @staticmethod
    def zombie_company_rule(ebit, interest, ocf, net_debt) -> bool:
        if min(len(ebit), len(interest), len(ocf)) < 3 or len(net_debt) < 2:
            return False

        ebit_breach = sum(
            1 for e, i in zip(ebit[-3:], interest[-3:])
            if e is not None and i is not None and e < i
        )

        cfo_breach = sum(
            1 for c, i in zip(ocf[-3:], interest[-3:])
            if c is not None and i is not None and c < i
        )

        debt_up = net_debt[-1] > net_debt[-2]

        return ebit_breach >= 2 and cfo_breach >= 2 and debt_up

    @staticmethod
    def zombie_signals(ebit, interest, ocf, net_debt, net_income=None):
        return {
            "ebit_trend": RiskTrendAnalyzer.compute_trend(ebit),
            "interest_trend": RiskTrendAnalyzer.compute_trend(interest),
            "ocf_trend": RiskTrendAnalyzer.compute_trend(ocf),
            "net_debt_trend": RiskTrendAnalyzer.compute_trend(net_debt),
            "zombie_company_flag": RiskTrendAnalyzer.zombie_company_rule(
                ebit, interest, ocf, net_debt
            )
        }

    # ======================================================
    # 3.2 WINDOW DRESSING (SAFE)
    # ======================================================
    @staticmethod
    def window_dressing_rule(cash, net_income, oneoff, receivables) -> bool:
        if len(cash) < 2 or len(net_income) < 2:
            return False

        cash_spike = (
            cash[-2] not in (None, 0)
            and (cash[-1] - cash[-2]) / abs(cash[-2]) > 0.25
        )

        oneoff_ratio = (
            oneoff[-1] / abs(net_income[-1])
            if oneoff and net_income[-1] not in (None, 0)
            else 0
        )

        recv_drop = len(receivables) >= 2 and receivables[-1] < receivables[-2]
        profit_jump = net_income[-1] > net_income[-2]

        return cash_spike or oneoff_ratio > 0.25 or (recv_drop and profit_jump)

    @staticmethod
    def window_dressing(cash, net_income, oneoff, receivables):
        return {
            "cash_trend": RiskTrendAnalyzer.compute_trend(cash),
            "net_income_trend": RiskTrendAnalyzer.compute_trend(net_income),
            "oneoff_income_trend": RiskTrendAnalyzer.compute_trend(oneoff),
            "receivables_trend": RiskTrendAnalyzer.compute_trend(receivables),
            "window_dressing_flag": RiskTrendAnalyzer.window_dressing_rule(
                cash, net_income, oneoff, receivables
            )
        }

    # ======================================================
    # 3.3 ASSET STRIPPING (SAFE)
    # ======================================================
    @staticmethod
    def asset_stripping_rule(fixed_assets, net_debt, dividends) -> bool:
        if len(fixed_assets) < 3 or len(net_debt) < 2:
            return False

        return (
            fixed_assets[-1] < fixed_assets[-2] < fixed_assets[-3]
            and net_debt[-1] > net_debt[-2]
            and dividends and dividends[-1]
        )

    @staticmethod
    def asset_stripping(fixed_assets, net_debt, dividends):
        return {
            "fixed_assets_trend": RiskTrendAnalyzer.compute_trend(fixed_assets),
            "net_debt_trend": RiskTrendAnalyzer.compute_trend(net_debt),
            "dividend_trend": RiskTrendAnalyzer.compute_trend(dividends),
            "asset_stripping_flag": RiskTrendAnalyzer.asset_stripping_rule(
                fixed_assets, net_debt, dividends
            )
        }

    # ======================================================
    # 3.4 LOAN EVERGREENING (SAFE)
    # ======================================================
    @staticmethod
    def loan_evergreening_rule(rollover, net_debt, int_cap, interest, principal) -> bool:
        if not rollover or not net_debt or not interest:
            return False

        rollover_ratio = rollover[-1] / net_debt[-1] if net_debt[-1] else 0
        cap_ratio = int_cap[-1] / interest[-1] if int_cap and interest[-1] else 0
        repay_low = not principal or principal[-1] in (None, 0)

        return rollover_ratio > 0.5 and cap_ratio > 0.2 and repay_low

    @staticmethod
    def loan_evergreening(rollover, net_debt, int_cap, interest, principal):
        return {
            "rollover_trend": RiskTrendAnalyzer.compute_trend(rollover),
            "interest_cap_trend": RiskTrendAnalyzer.compute_trend(int_cap),
            "interest_trend": RiskTrendAnalyzer.compute_trend(interest),
            "principal_repayment_trend": RiskTrendAnalyzer.compute_trend(principal),
            "loan_evergreening_flag": RiskTrendAnalyzer.loan_evergreening_rule(
                rollover, net_debt, int_cap, interest, principal
            )
        }

    # ======================================================
    # 3.5 CIRCULAR TRADING (SAFE)
    # ======================================================
    @staticmethod
    def circular_trading_rule(rpt_sales, rpt_recv, total_sales, ocf, recv_g, sales_g) -> bool:
        if len(rpt_sales) < 2 or len(rpt_recv) < 2:
            return False

        fake_rev = (
            len(total_sales) >= 2
            and len(ocf) >= 2
            and total_sales[-1] > total_sales[-2]
            and ocf[-1] <= 0
        )

        aggressive = recv_g > sales_g

        return rpt_sales[-1] > rpt_sales[-2] and rpt_recv[-1] > rpt_recv[-2] and (fake_rev or aggressive)

    @staticmethod
    def circular_trading(rpt_sales, rpt_recv, total_sales, ocf, recv_g, sales_g):
        return {
            "rpt_sales_trend": RiskTrendAnalyzer.compute_trend(rpt_sales),
            "rpt_receivables_trend": RiskTrendAnalyzer.compute_trend(rpt_recv),
            "revenue_trend": RiskTrendAnalyzer.compute_trend(total_sales),
            "ocf_trend": RiskTrendAnalyzer.compute_trend(ocf),
            "circular_trading_flag": RiskTrendAnalyzer.circular_trading_rule(
                rpt_sales, rpt_recv, total_sales, ocf, recv_g, sales_g
            )
        }

    # ======================================================
    # FINAL SAFE OUTPUT
    # ======================================================
    @staticmethod
    def build_trends_output(financial_data: Dict[str, List[float]]) -> Dict[str, Any]:
        return {
            "zombie_company_metrics": {
                "values": RiskTrendAnalyzer._values(financial_data.get("ebit", [])),
                **RiskTrendAnalyzer.zombie_signals(
                    financial_data.get("ebit", []),
                    financial_data.get("interest", []),
                    financial_data.get("ocf", []),
                    financial_data.get("net_debt", [])
                )
            },
            "window_dressing_metrics": {
                "values": RiskTrendAnalyzer._values(financial_data.get("cash", [])),
                **RiskTrendAnalyzer.window_dressing(
                    financial_data.get("cash", []),
                    financial_data.get("net_income", []),
                    financial_data.get("oneoff", []),
                    financial_data.get("receivables", [])
                )
            },
            "asset_stripping_metrics": {
                "values": RiskTrendAnalyzer._values(financial_data.get("fixed_assets", [])),
                **RiskTrendAnalyzer.asset_stripping(
                    financial_data.get("fixed_assets", []),
                    financial_data.get("net_debt", []),
                    financial_data.get("dividends", [])
                )
            },
            "loan_evergreening_metrics": {
                "values": RiskTrendAnalyzer._values(financial_data.get("loan_rollover", [])),
                **RiskTrendAnalyzer.loan_evergreening(
                    financial_data.get("loan_rollover", []),
                    financial_data.get("net_debt", []),
                    financial_data.get("interest_cap", []),
                    financial_data.get("interest", []),
                    financial_data.get("principal_repayment", [])
                )
            },
            "circular_trading_metrics": {
                "values": RiskTrendAnalyzer._values(financial_data.get("rpt_sales", [])),
                **RiskTrendAnalyzer.circular_trading(
                    financial_data.get("rpt_sales", []),
                    financial_data.get("rpt_receivables", []),
                    financial_data.get("total_sales", []),
                    financial_data.get("ocf", []),
                    financial_data.get("recv_growth_yoy", 0),
                    financial_data.get("sales_growth_yoy", 0)
                )
            }
        }
