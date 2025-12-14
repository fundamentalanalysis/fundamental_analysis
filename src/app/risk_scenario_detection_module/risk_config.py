# risk_config.py
from typing import Dict

DEFAULT_THRESHOLDS: Dict[str, float] = {
    "interest_overtake_years": 2,
    "fake_cash_spike_threshold": 0.30,
    "oneoff_profit_jump_threshold": 0.20,
    "profit_spike_no_revenue_threshold": 0.25,
    "fixed_asset_decline_years": 2,
    "dividend_high_ratio": 0.50,
    "loan_rollover_critical_ratio": 0.50,
    "interest_capitalized_ratio": 0.20,
    "minimal_principal_repayment_ratio": 0.10,
    "rpt_revenue_threshold": 0.15,
    "rpt_assets_threshold": 0.10,
    "rpt_recv_spike_threshold": 0.25,
}


# "related_party_sales": 37.21 , 
# "related_party_receivables": 18.65

# for 2024:
# related_party_sales : 21.09 , related_party_receivables : 11.46

# for 2023:
# related_party_sales : 21.97 , related_party_receivables : 15.87

# for 2022:
# related_party_sales : 29.23 , related_party_receivables : 13.14

# for 2021:
# related_party_sales : 20.45 , related_party_receivables : 7.70

manual_vals = {
    "related_party_sales": [37.21, 21.09, 21.97, 29.23, 20.45],
    "related_party_receivables": [18.65, 11.46, 15.87, 13.14, 7.70]
}