
import sys
import os

# Add the current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from wc_models import YearFinancialInput
    from wc_metrics import compute_per_year_metrics
except ImportError:
    # Fallback if running from root
    from src.app.working_capital_module.wc_models import YearFinancialInput
    from src.app.working_capital_module.wc_metrics import compute_per_year_metrics

def test_wc_metrics():
    financials = [
        YearFinancialInput(
            year=2023,
            trade_receivables=100,
            trade_payables=50,
            inventory=80,
            revenue=1000,
            cogs=600
        )
    ]
    
    metrics = compute_per_year_metrics(financials)
    m2023 = metrics[2023]
    
    print("Metrics for 2023:")
    print(m2023)
    
    # Verification
    # DSO = 100/1000 * 365 = 36.5
    # DIO = 80/600 * 365 = 48.66
    # DPO = 50/600 * 365 = 30.41
    # CCC = 36.5 + 48.66 - 30.41 = 54.75
    # NWC = 100 + 80 - 50 = 130
    # NWC Ratio = 130/1000 = 0.13
    
    assert abs(m2023["dso"] - 36.5) < 0.1, f"DSO mismatch: {m2023['dso']}"
    assert abs(m2023["dio"] - 48.66) < 0.1, f"DIO mismatch: {m2023['dio']}"
    assert abs(m2023["dpo"] - 30.41) < 0.1, f"DPO mismatch: {m2023['dpo']}"
    assert abs(m2023["ccc"] - 54.75) < 0.1, f"CCC mismatch: {m2023['ccc']}"
    assert m2023["nwc"] == 130, f"NWC mismatch: {m2023['nwc']}"
    assert m2023["nwc_ratio"] == 0.13, f"NWC Ratio mismatch: {m2023['nwc_ratio']}"
    
    print("All assertions passed!")

if __name__ == "__main__":
    test_wc_metrics()
