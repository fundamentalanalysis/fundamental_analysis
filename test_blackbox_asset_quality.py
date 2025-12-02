"""
Test script for Asset & Intangible Quality Module with BLACKBOX data
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

def test_blackbox_asset_quality():
    # Data provided by user
    raw_data = {
      "company": "BLACKBOX",
      "financial_data": {
        "financial_years": [
          {
            "year": 2025,
            "net_block": 769,
            "accumulated_depreciation": 420,
            "gross_block": 1188,
            "impairment_loss": None,
            "cwip": 0,
            "intangibles": 388,
            "goodwill": 0,
            "revenue": 5967,
            "intangible_amortization": None,
            "r_and_d_expenses": None
          },
          {
            "year": 2024,
            "net_block": 808,
            "accumulated_depreciation": 341,
            "gross_block": 1149,
            "impairment_loss": None,
            "cwip": 0,
            "intangibles": 385,
            "goodwill": 0,
            "revenue": 6282,
            "intangible_amortization": None,
            "r_and_d_expenses": None
          },
          {
            "year": 2023,
            "net_block": 794,
            "accumulated_depreciation": 401,
            "gross_block": 1195,
            "impairment_loss": None,
            "cwip": 2,
            "intangibles": 366,
            "goodwill": 0,
            "revenue": 6288,
            "intangible_amortization": None,
            "r_and_d_expenses": None
          },
          {
            "year": 2022,
            "net_block": 732,
            "accumulated_depreciation": 368,
            "gross_block": 1100,
            "impairment_loss": None,
            "cwip": 0,
            "intangibles": 347,
            "goodwill": 0,
            "revenue": 5370,
            "intangible_amortization": None,
            "r_and_d_expenses": None
          },
          {
            "year": 2021,
            "net_block": 622,
            "accumulated_depreciation": 281,
            "gross_block": 903,
            "impairment_loss": None,
            "cwip": 0,
            "intangibles": 314,
            "goodwill": 0,
            "revenue": 4674,
            "intangible_amortization": None,
            "r_and_d_expenses": None
          }
        ]
      }
    }

    financials = [
        AssetFinancialYearInput(**fy)
        for fy in raw_data["financial_data"]["financial_years"]
    ]

    module_input = AssetQualityInput(
        company_id=raw_data["company"],
        industry_code="GENERAL",
        financials_5y=financials,
        industry_asset_quality_benchmarks=IndustryAssetBenchmarks()
    )

    engine = AssetIntangibleQualityModule()
    result = engine.run(module_input)

    print("="*60)
    print(f"ASSET QUALITY ANALYSIS FOR {raw_data['company']}")
    print("="*60)
    print(json.dumps(result.dict(), indent=2, default=str))

if __name__ == "__main__":
    test_blackbox_asset_quality()
