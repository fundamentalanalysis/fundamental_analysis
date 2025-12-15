from typing import List, Optional, Dict


# ---------------------------------------------------
# SAFE HELPERS
# ---------------------------------------------------
def safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b in (None, 0):
        return None
    try:
        return a / b
    except Exception:
        return None


# ---------------------------------------------------
# RISK TREND ANALYZER
# ---------------------------------------------------
class RiskTrendAnalyzer:

    # -----------------------------
    # BASIC UTILITIES
    # -----------------------------
    @staticmethod
    def yoy(series: List[Optional[float]]) -> List[Optional[float]]:
        out = []
        for i in range(1, len(series)):
            prev, curr = series[i - 1], series[i]
            if prev in (None, 0) or curr is None:
                out.append(None)
            else:
                out.append((curr - prev) / abs(prev))
        return out

    @staticmethod
    def label_yoy(yoy: List[Optional[float]]) -> Dict[str, Optional[float]]:
        out = {}
        for i, v in enumerate(yoy):
            key = "Y_vs_Y-1" if i == 0 else f"Y-{i}_vs_Y-{i+1}"
            out[key] = v
        return out

    @staticmethod
    def label_values(values: List[Optional[float]]) -> Dict[str, Optional[float]]:
        out = {}
        for i, v in enumerate(values):
            key = "Y" if i == 0 else f"Y-{i}"
            out[key] = v
        return out

    @staticmethod
    def _max_consecutive_true(flags: List[bool]) -> int:
        streak = best = 0
        for f in flags:
            if f:
                streak += 1
                best = max(best, streak)
            else:
                streak = 0
        return best

    # =====================================================
    # 3.1 ZOMBIE COMPANY METRICS
    # =====================================================
    def zombie_signals(
        self,
        ebit: List[Optional[float]],
        interest: List[Optional[float]],
        ocf: List[Optional[float]],
    ) -> Dict:

        ebit_lt_interest = [
            e is not None and i is not None and e < i
            for e, i in zip(ebit, interest)
        ]
        ocf_lt_interest = [
            o is not None and i is not None and o < i
            for o, i in zip(ocf, interest)
        ]

        return {
            "EBIT_yoy": self.label_yoy(self.yoy(ebit)),
            "Interest_yoy": self.label_yoy(self.yoy(interest)),
            "OCF_yoy": self.label_yoy(self.yoy(ocf)),
            "EBIT_lt_Interest_consecutive_years": self._max_consecutive_true(ebit_lt_interest),
            "OCF_lt_Interest_consecutive_years": self._max_consecutive_true(ocf_lt_interest),
        }

    # =====================================================
    # 3.2 WINDOW DRESSING METRICS
    # =====================================================
    def window_signals(
        self,
        cash: List[Optional[float]],
        net_profit: List[Optional[float]],
        revenue: List[Optional[float]],
        one_off_income: List[Optional[float]],
        receivables: Optional[List[Optional[float]]] = None,
    ) -> Dict:

        oneoff_ratio = [
            safe_div(abs(o), abs(n)) if n not in (None, 0) else None
            for n, o in zip(net_profit, one_off_income)
        ]

        receivable_ratio = (
            [safe_div(r, rev) for r, rev in zip(receivables, revenue)]
            if receivables
            else []
        )

        return {
            "Cash_yoy": self.label_yoy(self.yoy(cash)),
            "NetProfit_yoy": self.label_yoy(self.yoy(net_profit)),
            "Revenue_yoy": self.label_yoy(self.yoy(revenue)),
            "OneOff_pct": self.label_values(oneoff_ratio),
            "Receivable_pct": self.label_values(receivable_ratio) if receivable_ratio else {},
        }

    # =====================================================
    # 3.3 ASSET STRIPPING METRICS
    # =====================================================
    def asset_signals(
        self,
        fixed_assets: List[Optional[float]],
        net_debt: List[Optional[float]],
        dividends: List[Optional[float]],
        net_profit: List[Optional[float]],
    ) -> Dict:

        return {
            "FixedAssets_yoy": self.label_yoy(self.yoy(fixed_assets)),
            "DividendPayout_pct": self.label_values(
                [safe_div(d, n) for d, n in zip(dividends, net_profit)]
            ),
            "AssetsShrinking": (
                fixed_assets[-1] < fixed_assets[0]
                if fixed_assets and fixed_assets[0] is not None and fixed_assets[-1] is not None
                else False
            ),
            "DebtRising": (
                net_debt[-1] > net_debt[0]
                if net_debt and net_debt[0] is not None and net_debt[-1] is not None
                else False
            ),
        }

    # =====================================================
    # 3.4 LOAN EVERGREENING METRICS (✅ FIXED)
    # =====================================================
    def evergreening_signals(
        self,
        rollover: List[Optional[float]],
        net_debt: List[Optional[float]],
        interest_capitalized: List[Optional[float]],
        interest: List[Optional[float]],
        principal_repayment: List[Optional[float]],
        ebitda: Optional[List[Optional[float]]] = None,   # ✅ OPTIONAL
    ) -> Dict:

        return {
            "LoanRollover_pct": self.label_values([safe_div(r, d) for r, d in zip(rollover, net_debt)]),
            "InterestCapitalized_pct": self.label_values([safe_div(ic, i) for ic, i in zip(interest_capitalized, interest)]),
            "PrincipalRepayment_pct": self.label_values([safe_div(p, d) for p, d in zip(principal_repayment, net_debt)]),
            "EBITDA_yoy": self.label_yoy(self.yoy(ebitda)) if ebitda else {},
            "Debt_yoy": self.label_yoy(self.yoy(net_debt)),
        }

    # =====================================================
    # 3.5 CIRCULAR TRADING / RPT FRAUD
    # =====================================================
    def circular_signals(
        self,
        rpt_sales: List[Optional[float]],
        total_sales: List[Optional[float]],
        rpt_receivables: List[Optional[float]],
        total_receivables: List[Optional[float]],
        revenue: List[Optional[float]],
        ocf: List[Optional[float]],
        assets: List[Optional[float]],
    ) -> Dict:

        return {
            "RPT_Sales_Revenue_pct": self.label_values([safe_div(r, t) for r, t in zip(rpt_sales, total_sales)]),
            "RPT_Sales_Assets_pct": self.label_values([safe_div(r, a) for r, a in zip(rpt_sales, assets)]),
            "RPT_Receivables_pct": self.label_values([safe_div(r, t) for r, t in zip(rpt_receivables, total_receivables)]),
            "Revenue_yoy": self.label_yoy(self.yoy(revenue)),
            "OCF_yoy": self.label_yoy(self.yoy(ocf)),
            "Receivables_yoy": self.label_yoy(self.yoy(total_receivables)),
        }
