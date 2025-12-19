# src/app/leverage_financial_risk_module/lfr_metrics.py

def _parse_tax_rate(tax_str):
    """
    Convert '19%' → 0.19
    """
    if not tax_str:
        return 0.0
    if isinstance(tax_str, str) and "%" in tax_str:
        return float(tax_str.replace("%", "").strip()) / 100
    return 0.0


def compute_per_year_metrics(financials):
    """
    Compute leverage metrics per year using correct tax & FFO logic
    """

    per_year = {}

    for fy in financials:
        year = fy.year

        # -----------------------------
        # Base Inputs
        # -----------------------------
        total_debt = fy.borrowings
        short_term_debt = fy.short_term_debt
        cash = fy.cash_equivalents

        equity = fy.equity
        ebit = fy.operating_profit
        depreciation = fy.depreciation
        ebitda = ebit + depreciation
        interest_cost = fy.interest

        profit_before_tax = getattr(fy, "profit_before_tax", 0.0)
        tax_rate = _parse_tax_rate(getattr(fy, "tax", None))

        # -----------------------------
        # Correct Tax Calculation ✅
        # -----------------------------
        tax_amount = round(profit_before_tax * tax_rate, 2)

        # -----------------------------
        # Derived Metrics
        # -----------------------------
        net_debt = total_debt - cash

        # FFO (Fitch / S&P definition)
        ffo = ebitda - interest_cost - tax_amount

        de_ratio = total_debt / equity if equity else 0.0
        debt_ebitda = total_debt / ebitda if ebitda else 0.0
        net_debt_ebitda = net_debt / ebitda if ebitda else 0.0
        interest_coverage = ebit / interest_cost if interest_cost else 0.0
        st_debt_ratio = short_term_debt / total_debt if total_debt else 0.0
        ffo_coverage = ffo / interest_cost if interest_cost else 0.0

        # -----------------------------
        # Store Canonical Metrics ✅
        # (KEY NAMES MATTER)
        # -----------------------------
        per_year[year] = {
            "year": year,

            # Absolute values
            "total_debt": round(total_debt, 2),
            "short_term_debt": round(short_term_debt, 2),
            "cash": round(cash, 2),
            "equity": round(equity, 2),
            "ebit": round(ebit, 2),
            "ebitda": round(ebitda, 2),
            "interest_cost": round(interest_cost, 2),   # ✅ FIXED
            "taxes": tax_amount,                          # ✅ FIXED
            "net_debt": round(net_debt, 2),
            "ffo": round(ffo, 2),

            # Ratios
            "de_ratio": round(de_ratio, 6),
            "debt_ebitda": round(debt_ebitda, 6),
            "net_debt_ebitda": round(net_debt_ebitda, 6),
            "interest_coverage": round(interest_coverage, 6),
            "st_debt_ratio": round(st_debt_ratio, 6),
            "ffo_coverage": round(ffo_coverage, 6),
        }

    return per_year
