from typing import Dict, Any, Optional


# ============================================================
# Helpers
# ============================================================

def safe_div(a, b) -> Optional[float]:
    if a is None or b in (None, 0):
        return None
    return round(a / b, 4)


def parse_tax_percent(tax) -> float:
    if tax is None:
        return 0.0
    if isinstance(tax, str):
        return float(tax.replace("%", "").strip())
    return float(tax)


# ============================================================
# PUBLIC API — METRICS ENGINE
# ============================================================

def compute_per_year_metrics(input_data: Dict[str, Any]) -> Dict[int, dict]:
    """
    Deterministic leverage + FFO metrics per year.
    IMPORT-SAFE. SPAWN-SAFE.
    """

    financial_years = input_data["financial_data"]["financial_years"]
    metrics: Dict[int, dict] = {}

    for f in sorted(financial_years, key=lambda x: x["year"]):
        year = f["year"]

        # -----------------------------
        # DEBT
        # -----------------------------
        short_term_debt = float(f.get("short_term_debt", 0))
        long_term_debt = float(f.get("long_term_debt", 0))
        lease_liabilities = float(f.get("lease_liabilities", 0))
        other_borrowings = float(f.get("other_borrowings", 0))
        cash = float(f.get("cash_equivalents", 0))

        total_debt = (
            short_term_debt
            + long_term_debt
            + lease_liabilities
            + other_borrowings
        )

        # -----------------------------
        # EQUITY (schema-safe)
        # -----------------------------
        equity_capital = f.get("equity_capital") or f.get("total_equity")
        reserves = f.get("reserves")

        if equity_capital is None or reserves is None:
            raise ValueError(f"[LFR_METRICS] Equity missing for year {year}")

        equity_capital = float(equity_capital)
        reserves = float(reserves)
        equity = equity_capital + reserves

        # -----------------------------
        # PROFITABILITY
        # -----------------------------
        ebit = float(f["operating_profit"])
        depreciation = float(f["depreciation"])
        interest_cost = float(f["interest"])

        ebitda = ebit + depreciation

        # -----------------------------
        # PROFIT BEFORE TAX (STRICT)
        # -----------------------------
        if f.get("profit_before_tax") is not None:
            profit_before_tax = float(f["profit_before_tax"])
        else:
            profit_before_tax = ebit - interest_cost

        # -----------------------------
        # TAX (CORRECT)
        # -----------------------------
        tax_percent = parse_tax_percent(f.get("tax"))
        tax_amount = profit_before_tax * tax_percent / 100

        # -----------------------------
        # NET DEBT & FFO
        # -----------------------------
        net_debt = total_debt - cash
        ffo = ebitda - interest_cost - tax_amount

        # -----------------------------
        # OUTPUT
        # -----------------------------
        metrics[year] = {
            "year": year,

            "total_debt": round(total_debt, 2),
            "short_term_debt": short_term_debt,
            "long_term_debt": long_term_debt,
            "lease_liabilities": lease_liabilities,
            "other_borrowings": other_borrowings,
            "cash": cash,

            "equity_capital": equity_capital,
            "reserves": reserves,
            "equity": round(equity, 2),

            "ebit": ebit,
            "ebitda": round(ebitda, 2),
            "interest_cost": interest_cost,
            "profit_before_tax": round(profit_before_tax, 2),

            "tax_percent": tax_percent,
            "tax_amount": round(tax_amount, 2),

            "net_debt": round(net_debt, 2),
            "ffo": round(ffo, 2),

            "de_ratio": safe_div(total_debt, equity),
            "debt_ebitda": safe_div(total_debt, ebitda),
            "net_debt_ebitda": safe_div(net_debt, ebitda),
            "ffo_coverage": safe_div(ffo, interest_cost),
            "st_debt_ratio": safe_div(short_term_debt, total_debt),
        }

    return metrics
