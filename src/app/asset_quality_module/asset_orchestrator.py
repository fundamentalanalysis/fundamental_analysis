from collections import Counter
from typing import Tuple, List, Dict

from .asset_config import load_asset_config, IndustryAssetBenchmarks
from .asset_llm import generate_asset_llm_narrative
from .asset_metrics import compute_per_year_metrics
from .asset_models import AssetQualityInput, AssetQualityOutput, RuleResult
from .asset_rules import apply_rules
from .asset_trend import compute_trend_metrics

class AssetIntangibleQualityModule:
    def __init__(self, config: IndustryAssetBenchmarks = None):
        self.config = config or load_asset_config()

    def run(self, input_data: AssetQualityInput) -> AssetQualityOutput:
        # 1. Compute Metrics
        per_year_metrics = compute_per_year_metrics(input_data.financials_5y)
        
        # 2. Compute Trends
        trend_metrics = compute_trend_metrics(per_year_metrics)
        
        # 3. Apply Rules
        rule_results = apply_rules(
            metrics=per_year_metrics,
            trends=trend_metrics,
            benchmarks=input_data.industry_asset_quality_benchmarks or self.config
        )
        
        # 4. Compute Base Score
        base_score = self._compute_score(rule_results)
        
        # 5. Summarize Flags
        red_flags, positives = self._summarize(rule_results)
        
        # 6. Generate Deterministic Narrative
        deterministic_notes = self._build_narrative_notes(per_year_metrics, trend_metrics, red_flags)
        
        # 7. LLM Reasoning
        narrative, adjusted_score = generate_asset_llm_narrative(
            company_id=input_data.company_id,
            metrics=per_year_metrics,
            trends=trend_metrics,
            rule_results=rule_results,
            deterministic_notes=deterministic_notes,
            base_score=base_score,
        )
        
        # 8. Construct Output
        return AssetQualityOutput(
            module="AssetIntangibleQuality",
            sub_score_adjusted=adjusted_score,
            analysis_narrative=narrative,
            red_flags=red_flags,
            positive_points=positives,
            rules=rule_results
        )

    def _compute_score(self, rule_results: List[RuleResult]) -> int:
        # Start at 100
        score = 100
        # Penalties: RED=10, YELLOW=5, CRITICAL=20 (if implemented, but spec says RED/YELLOW mostly)
        # Spec says:
        # A1: <0.7 RED, 0.7-1.0 YELLOW
        # B1: >75% RED, 60-75% YELLOW
        # C1: >5% RED
        # C2: >30% YELLOW
        # D1: >40% RED, 25-40% YELLOW
        # etc.
        # User provided general scoring logic in Step 95:
        # GREEN=0, YELLOW=5, RED=10, CRITICAL=20
        
        for r in rule_results:
            if r.flag == "RED":
                score -= 10
            elif r.flag == "YELLOW":
                score -= 5
            elif r.flag == "CRITICAL":
                score -= 20
                
        return max(0, min(100, score))

    def _summarize(self, rule_results: List[RuleResult]) -> Tuple[List[Dict], List[str]]:
        red_flags = []
        positives = []
        for r in rule_results:
            if r.flag in ("RED", "CRITICAL"):
                severity = "CRITICAL" if r.flag == "CRITICAL" else "HIGH"
                # Some REDs might be CRITICAL based on rule ID if specified, but for now map RED->HIGH
                # Spec Step 140 Section 6 shows "CRITICAL" severity in red_flags.
                # Let's map based on flag.
                red_flags.append({
                    "severity": severity,
                    "title": r.rule_name,
                    "detail": r.reason
                })
            elif r.flag == "GREEN":
                positives.append(f"{r.rule_name}: {r.reason}")
        return red_flags, positives

    def _build_narrative_notes(self, metrics: Dict[int, dict], trends: Dict[str, any], red_flags: List[Dict]) -> List[str]:
        notes = []
        latest_year = max(metrics.keys())
        latest = metrics[latest_year]
        
        if trends.get("asset_turnover_declining"):
            notes.append("Asset turnover has been declining for three years, indicating weakening asset utilization.")
        
        age = latest.get("asset_age_proxy")
        if age and age > 0.7:
            notes.append(f"Asset age proxy exceeds {age*100:.0f}%, suggesting an aging asset base.")
            
        gw_cagr = trends.get("goodwill_cagr")
        rev_cagr = trends.get("revenue_cagr")
        if gw_cagr and rev_cagr and gw_cagr > rev_cagr:
            notes.append("Goodwill has increased faster than revenue, suggesting acquisitions may not be value-accretive.")
            
        if red_flags:
            notes.append(f"Key concerns: {', '.join(f['title'] for f in red_flags[:2])}.")
            
        return notes or ["Asset quality assessment based on latest financials."]
