from typing import Dict, List, Optional

try:
    from .aiqm_models import YearAssetIntangibleInput
except ImportError:
    from aiqm_models import YearAssetIntangibleInput


# ------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------

def safe_div(a, b):
    """Safely divide two numbers, returning None if division invalid."""
    return a / b if (b not in (0, None) and a is not None) else None


def extract_year_int(year_value):
    """Extract integer year."""
    if isinstance(year_value, int):
        return year_value
    parts = str(year_value).split()
    return int(parts[-1])


# ------------------------------------------------------------
# Core Metric Calculations
# ------------------------------------------------------------

def calc_asset_turnover(revenue, net_block):
    return safe_div(revenue, net_block)


def calc_asset_age_proxy(acc_dep, gross_block):
    return safe_div(acc_dep, gross_block)


def derive_intangible_amortization(intangibles, gross_block, depreciation):
    """
    If intangible amortization is not given, derive:
    Amortization = Depreciation × (Intangibles / (Gross Block + Intangibles))
    """
    if depreciation in (None, 0) or intangibles is None:
        return None

    total_assets_base = gross_block + intangibles
    if total_assets_base in (0, None):
        return None

    weight = intangibles / total_assets_base
    return depreciation * weight


def calc_intangible_growth(current, prev):
    return safe_div((current - prev), prev) if prev not in (None, 0) else None


def calc_intangible_pct_total(intangibles, total_assets):
    return safe_div(intangibles, total_assets)


# ------------------------------------------------------------
# R&D Derivation
# ------------------------------------------------------------

def derive_r_and_d_expense(intangibles_current, intangibles_prev, r_and_d_given):
    """
    If R&D is provided → use directly.
    Otherwise → derive using:
    R&D ≈ New Intangible Additions = current_intangibles - previous_intangibles
    """
    if r_and_d_given not in (None, 0):
        return r_and_d_given

    if intangibles_prev is None:
        return None  # Cannot derive for first year

    return intangibles_current - intangibles_prev


# ------------------------------------------------------------
# Main Metrics Computation (Per Year)
# ------------------------------------------------------------

def compute_per_year_metrics(financials_5y: List[YearAssetIntangibleInput]) -> Dict[int, dict]:
    """
    Compute all Asset & Intangible module metrics for each year.
    """
    metrics = {}

    # Sort years
    sorted_fin = sorted(financials_5y, key=lambda x: extract_year_int(x.year))
    print(f"DEBUG: Sorted financial years: {[f.year for f in sorted_fin]}")

    previous_intangibles = None  # For intangible additions / R&D derivation

    for f in sorted_fin:

        # --------------------------
        # Compute Derived Values
        # --------------------------
        year_int = extract_year_int(f.year)
        gross_block = f.gross_block
        acc_dep = f.accumulated_depreciation

        # Net block (already derived in model if missing)
        net_block = f.net_block

        # ------------------------------
        # Tangible Metrics
        # ------------------------------
        asset_turnover = calc_asset_turnover(f.revenue, net_block)
        age_proxy = calc_asset_age_proxy(acc_dep, gross_block)

        # ------------------------------
        # Intangible Metrics
        # ------------------------------
        intangible_pct_total = calc_intangible_pct_total(f.intangible_assets, f.total_assets)

        intangible_growth = calc_intangible_growth(
            f.intangible_assets,
            previous_intangibles
        ) if previous_intangibles is not None else None

        # ------------------------------
        # Amortization (real or derived)
        # ------------------------------
        amortization = (
            f.intangible_amortization
            if f.intangible_amortization not in (None, 0)
            else derive_intangible_amortization(
                f.intangible_assets,
                gross_block,
                f.depreciation
            )
        )

        amortization_ratio = safe_div(amortization, f.intangible_assets)

        # ------------------------------
        # R&D Expense (real or derived)
        # ------------------------------
        r_and_d_expense = derive_r_and_d_expense(
            f.intangible_assets,
            previous_intangibles,
            f.r_and_d_expense
        )
        r_and_d_ratio = safe_div(r_and_d_expense, (f.intangible_assets - previous_intangibles)) \
            if previous_intangibles is not None else None

        # ------------------------------
        # Update previous intangible value
        # ------------------------------
        previous_intangibles = f.intangible_assets

        # ------------------------------
        # Store Metrics for Year
        # ------------------------------
        metrics[year_int] = {
            "year": year_int,
            "year_label": f.year,
            # Tangible metrics
            "gross_block": gross_block,
            "accumulated_depreciation": acc_dep,
            "net_block": net_block,
            "asset_turnover": asset_turnover,
            "asset_age_proxy": age_proxy,

            # Intangible metrics
            "intangibles": f.intangible_assets,
            "intangible_pct_total_assets": intangible_pct_total,
            "intangible_growth_yoy": intangible_growth,

            # Amortization
            "intangible_amortization": amortization,
            "amortization_ratio": amortization_ratio,

            # R&D derived metrics
            "r_and_d_expense": r_and_d_expense,
            "r_and_d_intangible_ratio": r_and_d_ratio,

            # Context fields
            "total_assets": f.total_assets,
            "revenue": f.revenue,
            "cwip": f.cwip,
        }

    print(f"DEBUG: Computed per year AIQM metrics: {metrics}")
    return metrics
