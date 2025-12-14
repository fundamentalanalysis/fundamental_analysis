# risk_trend.py (SAFE VERSION)
from typing import List, Optional


def _safe_is_number(x) -> bool:
    return x is not None


def safe_lt(a: Optional[float], b: Optional[float]) -> bool:
    """Return True if a < b and both numbers are present, else False."""
    if a is None or b is None:
        return False
    return a < b


def safe_gt(a: Optional[float], b: Optional[float]) -> bool:
    """Return True if a > b and both numbers are present, else False."""
    if a is None or b is None:
        return False
    return a > b


def safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """Return numerator/denominator or None on invalid input (None/0)."""
    if numerator is None or denominator in (None, 0):
        return None
    try:
        return numerator / denominator
    except Exception:
        return None


class RiskTrendAnalyzer:
    @staticmethod
    def yoy(series: List[Optional[float]]) -> List[Optional[float]]:
        """
        Year-over-year growth as fraction (not percent).
        Returns list of length len(series)-1 where each element is (curr - prev)/abs(prev)
        or None if prev or curr invalid.
        """
        out: List[Optional[float]] = []
        for i in range(1, len(series)):
            prev = series[i - 1]
            curr = series[i]
            # require both prev and curr to be valid numbers and prev != 0
            if prev in (None, 0) or curr is None:
                out.append(None)
            else:
                try:
                    out.append((curr - prev) / abs(prev))
                except Exception:
                    out.append(None)
        return out

    @staticmethod
    def cagr(start: Optional[float], end: Optional[float], periods: int) -> float:
        if start in (None, 0) or end is None or periods <= 0:
            return 0.0
        try:
            return (end / start) ** (1.0 / periods) - 1.0
        except Exception:
            return 0.0

    @staticmethod
    def consecutive_true(seq: List[bool]) -> int:
        cur = 0
        best = 0
        for v in seq:
            if v:
                cur += 1
            else:
                cur = 0
            if cur > best:
                best = cur
        return best

    # scenario helpers
    def zombie_signals(self, ebit: List[Optional[float]], interest: List[Optional[float]], ocf: List[Optional[float]]):
        # each element True if both numbers present and ebit < interest
        ebit_lt_int = [(_safe_is_number(a) and _safe_is_number(b) and a < b) for a, b in zip(ebit, interest)]
        ocf_lt_int = [(_safe_is_number(a) and _safe_is_number(b) and a < b) for a, b in zip(ocf, interest)]
        return {
            "ebit_interest_consec": self.consecutive_true(ebit_lt_int),
            "ocf_interest_consec": self.consecutive_true(ocf_lt_int)
        }

    def window_signals(self, cash: List[Optional[float]], net_income: List[Optional[float]],
                       revenue: List[Optional[float]], one_off: List[Optional[float]]):
        # oneoff_ratio: elementwise abs(one_off) / abs(net_income) when both present and net_income != 0
        oneoff_ratio = []
        for n, o in zip(net_income, one_off):
            if n in (None, 0) or o is None:
                oneoff_ratio.append(None)
            else:
                try:
                    oneoff_ratio.append(abs(o) / abs(n))
                except Exception:
                    oneoff_ratio.append(None)

        return {
            "cash_yoy": self.yoy(cash),
            "net_income_yoy": self.yoy(net_income),
            "revenue_yoy": self.yoy(revenue),
            "oneoff_ratio": oneoff_ratio
        }

    def asset_signals(self, fixed_assets: List[Optional[float]], net_debt: List[Optional[float]],
                      dividend: List[Optional[float]], net_income: List[Optional[float]]):
        # fixed asset YoY and count declines
        fa_yoy = self.yoy(fixed_assets)
        declines = sum(1 for v in fa_yoy if v is not None and v < 0)

        # dividend payout ratio: abs(dividend) / abs(net_income) when both present and net_income != 0
        payout = []
        for d, n in zip(dividend, net_income):
            if n in (None, 0) or d is None:
                payout.append(None)
            else:
                try:
                    payout.append(abs(d) / abs(n))
                except Exception:
                    payout.append(None)

        # assets_shrinking: compare first and last fixed_assets only if both present
        assets_shrinking = False
        if fixed_assets and len(fixed_assets) >= 2:
            fa_first = fixed_assets[0]
            fa_last = fixed_assets[-1]
            if fa_first is not None and fa_last is not None:
                assets_shrinking = fa_last < fa_first

        # debt_rising: compare first and last net_debt only if both present
        debt_rising = False
        if net_debt and len(net_debt) >= 2:
            nd_first = net_debt[0]
            nd_last = net_debt[-1]
            if nd_first is not None and nd_last is not None:
                debt_rising = nd_last > nd_first

        return {
            "fixed_asset_decline_years": declines,
            "dividend_payout_ratio": payout,
            "assets_shrinking": assets_shrinking,
            "debt_rising": debt_rising
        }

    def evergreening_signals(self, rollover: List[Optional[float]], net_debt: List[Optional[float]],
                             int_cap: List[Optional[float]], interest: List[Optional[float]],
                             principal_repayment: List[Optional[float]]):
        rollover_ratio = []
        for r, nd in zip(rollover, net_debt):
            if r is None or nd in (None, 0):
                rollover_ratio.append(None)
            else:
                try:
                    rollover_ratio.append(r / nd)
                except Exception:
                    rollover_ratio.append(None)

        int_cap_ratio = []
        for ic, it in zip(int_cap, interest):
            if ic is None or it in (None, 0):
                int_cap_ratio.append(None)
            else:
                try:
                    int_cap_ratio.append(ic / it)
                except Exception:
                    int_cap_ratio.append(None)

        principal_ratio = []
        for pr, nd in zip(principal_repayment, net_debt):
            if pr is None or nd in (None, 0):
                principal_ratio.append(None)
            else:
                try:
                    principal_ratio.append(abs(pr) / nd)
                except Exception:
                    principal_ratio.append(None)

        return {
            "rollover_ratio": rollover_ratio,
            "interest_cap_ratio": int_cap_ratio,
            "principal_repayment_ratio": principal_ratio
        }

    def circular_signals(self, rpt_sales: List[Optional[float]], total_sales: List[Optional[float]],
                         rpt_recv: List[Optional[float]], total_recv: List[Optional[float]],
                         revenue: List[Optional[float]], ocf: List[Optional[float]],
                         assets: List[Optional[float]]):
        rpt_sales_ratio = []
        for r, t in zip(rpt_sales, total_sales):
            if r is None or t in (None, 0):
                rpt_sales_ratio.append(None)
            else:
                try:
                    rpt_sales_ratio.append(r / t)
                except Exception:
                    rpt_sales_ratio.append(None)

        rpt_assets_ratio = []
        for r, a in zip(rpt_sales, assets):
            if r is None or a in (None, 0):
                rpt_assets_ratio.append(None)
            else:
                try:
                    rpt_assets_ratio.append(r / a)
                except Exception:
                    rpt_assets_ratio.append(None)

        rpt_recv_ratio = []
        for r, t in zip(rpt_recv, total_recv):
            if r is None or t in (None, 0):
                rpt_recv_ratio.append(None)
            else:
                try:
                    rpt_recv_ratio.append(r / t)
                except Exception:
                    rpt_recv_ratio.append(None)

        return {
            "rpt_sales_ratio": rpt_sales_ratio,
            "rpt_assets_ratio": rpt_assets_ratio,
            "rpt_recv_ratio": rpt_recv_ratio,
            "recv_yoy": self.yoy(total_recv),
            "rev_yoy": self.yoy(revenue),
            "ocf_yoy": self.yoy(ocf)
        }
