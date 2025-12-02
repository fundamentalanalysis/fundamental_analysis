from typing import Dict, List
from .asset_models import AssetFinancialYearInput

def safe_div(a, b):
    return a / b if (b not in (0, None) and a is not None) else None

def compute_per_year_metrics(financials_5y: List[AssetFinancialYearInput]) -> Dict[int, dict]:
    metrics = {}
    sorted_fin = sorted(financials_5y, key=lambda x: x.year)

    for f in sorted_fin:
        # Core Derived Metrics
        # 3.1 Tangible Asset Productivity
        asset_turnover = safe_div(f.revenue, f.net_block)
        
        # Gross Block = Net Block + Accumulated Depreciation (provided in input, but can verify)
        # Using input gross_block as primary source
        gross_block = f.gross_block if f.gross_block else (f.net_block + f.accumulated_depreciation)
        
        asset_age_proxy = safe_div(f.accumulated_depreciation, gross_block)

        # 3.2 Impairment Metrics
        impairment_pct = safe_div(f.impairment_loss, f.net_block)

        # 3.3 Intangible & Goodwill Metrics
        # Total Assets isn't directly in input, but we can approximate or use what we have.
        # Wait, the spec says "Goodwill % of Total Assets".
        # The input contract doesn't have "Total Assets".
        # It has net_block, cwip, intangibles, goodwill.
        # Assuming Total Assets = Net Block + CWIP + Intangibles + Goodwill + (Current Assets? Not provided)
        # The user provided inputs: net_block, accumulated_depreciation, gross_block, impairment_loss, cwip, intangibles, goodwill, revenue, intangible_amortization, r_and_d_expenses.
        # Missing: Total Assets.
        # I will calculate "Operating Assets" or "Fixed Assets + Intangibles" as a proxy if needed,
        # OR I should check if I can ask the user or assume Total Assets is passed?
        # The input contract in the prompt DOES NOT have total_assets.
        # But the metric formula says "Goodwill / Total Assets".
        # I will use (Net Block + CWIP + Intangibles + Goodwill) as "Total Long Term Assets" for now, or maybe the user meant "Total Fixed Assets"?
        # Let's use the sum of provided asset components as the denominator for now, but note this limitation.
        # Actually, let's assume the user might add total_assets later or I should use what I have.
        # Let's define total_identifiable_assets = net_block + cwip + intangibles + goodwill
        total_identifiable_assets = (f.net_block or 0) + (f.cwip or 0) + (f.intangibles or 0) + (f.goodwill or 0)
        
        goodwill_pct = safe_div(f.goodwill, total_identifiable_assets)
        intangible_pct = safe_div(f.intangibles, total_identifiable_assets)
        
        intangible_amortization_ratio = safe_div(f.intangible_amortization, f.intangibles)
        
        # R&D to Intangibles Ratio: R&D / (New Intangible Additions)
        # New Intangible Additions requires previous year data, so per-year metric here might be tricky without context.
        # We'll calculate it in the trend/yoy section or here if we can.
        # For per-year, we just store the raw values needed.

        metrics[f.year] = {
            "year": f.year,
            "revenue": f.revenue,
            "net_block": f.net_block,
            "gross_block": gross_block,
            "accumulated_depreciation": f.accumulated_depreciation,
            "impairment_loss": f.impairment_loss,
            "cwip": f.cwip,
            "intangibles": f.intangibles,
            "goodwill": f.goodwill,
            "intangible_amortization": f.intangible_amortization,
            "r_and_d_expenses": f.r_and_d_expenses,
            "total_identifiable_assets": total_identifiable_assets,
            
            "asset_turnover": asset_turnover,
            "asset_age_proxy": asset_age_proxy,
            "impairment_pct": impairment_pct,
            "goodwill_pct": goodwill_pct,
            "intangible_pct": intangible_pct,
            "intangible_amortization_ratio": intangible_amortization_ratio,
        }

    return metrics
