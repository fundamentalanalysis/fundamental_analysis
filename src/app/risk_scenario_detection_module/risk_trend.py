# risk_trend.py
from typing import List, Dict, Any


class RiskTrendAnalyzer:

    # --------------------------------------------
    # SAFE HELPER: returns latest + YoY direction
    # --------------------------------------------
    @staticmethod
    def compute_trend(arr: List[Any], label: str):
        if not arr or arr[-1] is None:
            return {"latest": None, "yoy": "flat", "note": f"{label}: insufficient data"}

        latest = arr[-1]

        if len(arr) < 2 or arr[-2] is None:
            return {"latest": latest, "yoy": "flat", "note": f"{label}: no YoY comparison"}

        prev = arr[-2]
        if prev == 0:
            return {"latest": latest, "yoy": "flat", "note": f"{label}: previous value = 0"}

        change = (latest - prev) / prev

        if change > 0.15:
            direction = "up"
        elif change < -0.15:
            direction = "down"
        else:
            direction = "flat"

        return {"latest": latest, "yoy": direction, "pct": round(change, 3)}

    # -----------------------------------------------------------
    # 1. ZOMBIE COMPANY DIAGNOSTICS
    # Condition: EBIT < Interest + OCF negative + Net Debt rising
    # -----------------------------------------------------------
    @staticmethod
    def zombie_signals(ebit, interest, ocf, net_debt, net_income):
        ebit_t = RiskTrendAnalyzer.compute_trend(ebit, "EBIT")
        int_t = RiskTrendAnalyzer.compute_trend(interest, "Interest")
        ocf_t = RiskTrendAnalyzer.compute_trend(ocf, "OCF")
        debt_t = RiskTrendAnalyzer.compute_trend(net_debt, "Net Debt")
        income_t = RiskTrendAnalyzer.compute_trend(net_income, "Net Income")

        zombie_risk = (
            (ebit_t["latest"] is not None and int_t["latest"] is not None and ebit_t["latest"] < int_t["latest"])
            and ocf_t["latest"] is not None and ocf_t["latest"] < 0
            and debt_t["yoy"] == "up"
        )

        return {
            "ebit_trend": ebit_t,
            "interest_trend": int_t,
            "ocf_trend": ocf_t,
            "net_debt_trend": debt_t,
            "net_income_trend": income_t,
            "zombie_company_flag": zombie_risk
        }

    # -------------------------------------------------------
    # 2. WINDOW DRESSING
    # Sudden jump in cash, income, or one-off income
    # -------------------------------------------------------
    @staticmethod
    def window_dressing(cash, net_income, oneoff, receivables):
        cash_t = RiskTrendAnalyzer.compute_trend(cash, "Cash")
        inc_t = RiskTrendAnalyzer.compute_trend(net_income, "Net Income")
        one_t = RiskTrendAnalyzer.compute_trend(oneoff, "One-off Income")
        recv_t = RiskTrendAnalyzer.compute_trend(receivables, "Receivables")

        suspicious = (
            cash_t["yoy"] == "up"
            and inc_t["yoy"] == "up"
            and one_t["latest"] not in (None, 0)
            and recv_t["yoy"] == "up"
        )

        return {
            "cash_trend": cash_t,
            "net_income_trend": inc_t,
            "oneoff_income_trend": one_t,
            "receivables_trend": recv_t,
            "window_dressing_flag": suspicious
        }

    # -------------------------------------------------------
    # 3. ASSET STRIPPING
    # Falling fixed assets + rising debt + high dividends
    # -------------------------------------------------------
    @staticmethod
    def asset_stripping(fixed_assets, net_debt, dividends):
        fa_t = RiskTrendAnalyzer.compute_trend(fixed_assets, "Fixed Assets")
        debt_t = RiskTrendAnalyzer.compute_trend(net_debt, "Net Debt")
        div_t = RiskTrendAnalyzer.compute_trend(dividends, "Dividend Paid")

        stripping = (
            fa_t["yoy"] == "down" and
            debt_t["yoy"] == "up" and
            div_t["latest"] not in (None, 0)
        )

        return {
            "fixed_assets_trend": fa_t,
            "net_debt_trend": debt_t,
            "dividend_trend": div_t,
            "asset_stripping_flag": stripping
        }

    # -------------------------------------------------------
    # 4. LOAN EVERGREENING
    # Rollovers ↑ + interest capitalized ↑ + no principal paid
    # -------------------------------------------------------
    @staticmethod
    def loan_evergreening(rollover, net_debt, int_cap, interest, principal_repayment):
        roll_t = RiskTrendAnalyzer.compute_trend(rollover, "Loan Rollover")
        debt_t = RiskTrendAnalyzer.compute_trend(net_debt, "Net Debt")
        cap_t = RiskTrendAnalyzer.compute_trend(int_cap, "Interest Capitalized")
        int_t = RiskTrendAnalyzer.compute_trend(interest, "Interest")
        repay_t = RiskTrendAnalyzer.compute_trend(principal_repayment, "Principal Repayment")

        evergreen = (
            roll_t["yoy"] == "up" and
            cap_t["yoy"] == "up" and
            (repay_t["latest"] is None or repay_t["latest"] == 0)
        )

        return {
            "rollover_trend": roll_t,
            "net_debt_trend": debt_t,
            "interest_cap_trend": cap_t,
            "interest_trend": int_t,
            "principal_repayment_trend": repay_t,
            "loan_evergreening_flag": evergreen
        }

    # -------------------------------------------------------
    # 5. CIRCULAR TRADING WITH RPT (MOST FRAUD PRONE)
    # RPT Sales ↑ faster than revenue
    # RPT receivables ↑ faster than total receivables
    # OCF weak or negative
    # -------------------------------------------------------
    @staticmethod
    def circular_trading(rpt_sales, rpt_recv, total_sales, ocf, recv_growth, sales_growth):

        rpt_sales_t = RiskTrendAnalyzer.compute_trend(rpt_sales, "RPT Sales")
        rpt_recv_t = RiskTrendAnalyzer.compute_trend(rpt_recv, "RPT Receivables")
        sales_t = RiskTrendAnalyzer.compute_trend(total_sales, "Total Revenue")
        ocf_t = RiskTrendAnalyzer.compute_trend(ocf, "Operating Cash Flow")

        fraud_flag = (
            rpt_sales_t["yoy"] == "up"
            and rpt_recv_t["yoy"] == "up"
            and ocf_t["latest"] is not None
            and ocf_t["latest"] <= 0
            and recv_growth > 0
            and sales_growth < 0.20      # RPT growing faster than normal revenue
        )

        return {
            "rpt_sales_trend": rpt_sales_t,
            "rpt_receivables_trend": rpt_recv_t,
            "revenue_trend": sales_t,
            "ocf_trend": ocf_t,
            "total_receivable_growth_yoy": recv_growth,
            "total_sales_growth_yoy": sales_growth,
            "circular_trading_flag": fraud_flag
        }
