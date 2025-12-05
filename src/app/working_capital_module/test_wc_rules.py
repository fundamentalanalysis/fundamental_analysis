
import sys
import os

# Add the current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from wc_rules import wc_rule_engine

def test_wc_rules():
    # Mock Metrics
    metrics = {
        "latest": {
            "dso": 80,          # Should trigger RED (>75)
            "dio": 100,         # Should trigger YELLOW (90-120)
            "dpo": 40,          # Should trigger GREEN (30-90)
            "ccc": 140,         # Should trigger YELLOW (120-180)
            "nwc_ratio": 0.20,  # Should trigger YELLOW (0.15-0.25)
            "nwc_cagr": 0.15,   # 15%
            "revenue_cagr": 0.04 # 4% -> NWC > Rev + 10% (0.15 > 0.14) -> RED
        }
    }

    # Mock Trends (Output from wc_trend.py)
    trends = {
        "trade_receivables": {
            "yoy_growth_pct": { "Y_vs_Y-1": 25.0 } # > 20%
        },
        "inventory": {
            "yoy_growth_pct": { "Y_vs_Y-1": 10.0 }
        },
        "trade_payables": {
            "yoy_growth_pct": { "Y_vs_Y-1": -15.0 } # < -10%
        },
        "revenue": {
            "yoy_growth_pct": { "Y_vs_Y-1": 8.0 } # < 10% (for Receivables rule)
        }
    }
    # Receivables Rule A2: Rcv > 20 (25) AND Rev < 10 (8) -> YELLOW
    # Payables Rule C2: Pay < -10 (-15) AND Rev > 5 (8) -> YELLOW

    results = wc_rule_engine(metrics, trends, rules=None)
    
    print(f"Generated {len(results)} flags:")
    for res in results:
        # res is a RuleResult object, use to_dict()
        print(res.to_dict())

if __name__ == "__main__":
    test_wc_rules()
