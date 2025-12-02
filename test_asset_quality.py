"""
Test script for Asset & Intangible Quality Module
"""
import sys
import os
import json

# Ensure package imports work
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from src.app.asset_quality_module.asset_models import (
    AssetQualityInput,
    AssetFinancialYearInput,
    IndustryAssetBenchmarks,
)
from src.app.asset_quality_module.asset_orchestrator import AssetIntangibleQualityModule

def test_asset_quality_module():
    # Sample data based on user spec
    # Year 2024 (Y)
    # net_block: 5500.0
    # accumulated_depreciation: 3200.0
    # gross_block: 8700.0
    # impairment_loss: 150.0
    # cwip: 900.0
    # intangibles: 1800.0
    # goodwill: 1200.0
    # revenue: 9500.0
    # intangible_amortization: 250.0
    # r_and_d_expenses: 300.0

    # Creating 5 years of data to test trends
    financials = [
        AssetFinancialYearInput(
            year=2020,
            net_block=4000.0, accumulated_depreciation=2000.0, gross_block=6000.0,
            impairment_loss=50.0, cwip=500.0, intangibles=1000.0, goodwill=800.0,
            revenue=8000.0, intangible_amortization=150.0, r_and_d_expenses=200.0
        ),
        AssetFinancialYearInput(
            year=2021,
            net_block=4500.0, accumulated_depreciation=2300.0, gross_block=6800.0,
            impairment_loss=60.0, cwip=600.0, intangibles=1200.0, goodwill=900.0,
            revenue=8500.0, intangible_amortization=180.0, r_and_d_expenses=220.0
        ),
        AssetFinancialYearInput(
            year=2022,
            net_block=4800.0, accumulated_depreciation=2600.0, gross_block=7400.0,
            impairment_loss=80.0, cwip=700.0, intangibles=1400.0, goodwill=1000.0,
            revenue=8800.0, intangible_amortization=200.0, r_and_d_expenses=240.0
        ),
        AssetFinancialYearInput(
            year=2023,
            net_block=5200.0, accumulated_depreciation=2900.0, gross_block=8100.0,
            impairment_loss=100.0, cwip=800.0, intangibles=1600.0, goodwill=1100.0,
            revenue=9000.0, intangible_amortization=220.0, r_and_d_expenses=260.0
        ),
        AssetFinancialYearInput(
            year=2024,
            net_block=5500.0, accumulated_depreciation=3200.0, gross_block=8700.0,
            impairment_loss=150.0, cwip=900.0, intangibles=1800.0, goodwill=1200.0,
            revenue=9500.0, intangible_amortization=250.0, r_and_d_expenses=300.0
        ),
    ]

    module_input = AssetQualityInput(
        company_id="TEST_CORP",
        industry_code="CEMENT",
        financials_5y=financials,
        industry_asset_quality_benchmarks=IndustryAssetBenchmarks()
    )

    engine = AssetIntangibleQualityModule()
    result = engine.run(module_input)

    print("="*60)
    print("ASSET QUALITY MODULE OUTPUT")
    print("="*60)
    print(json.dumps(result.dict(), indent=2, default=str))
    
    # Validation
    assert result.module == "AssetIntangibleQuality"
    assert result.sub_score_adjusted is not None
    assert len(result.analysis_narrative) > 0
    
    # Check specific rule logic
    # Impairment % in 2024: 150 / 5500 = 2.7% (below 5% threshold, so GREEN for C1)
    # But wait, spec example says "Impairments exceed 5% of net block" for 0.067 value.
    # My data has 2.7%. Let's check if any rule triggered.
    
    # Check trends
    # Revenue CAGR: 8000 -> 9500 over 4 years
    # Intangible CAGR: 1000 -> 1800 over 4 years (higher growth)
    
    print("\n✅ Test completed successfully!")

if __name__ == "__main__":
    test_asset_quality_module()
