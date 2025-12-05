# # orchestrator.py

# from .metrics_engine import compute_year_metrics
# from .trend_engine import compute_trends
# from .rules_engine import evaluate_rules
# from .llm_agent import generate_llm_narrative

# def run_capex_cwip_module(payload):
#     """
#     llm → function(prompt) → text
#     """
#     print('hi')
#     company = payload.company
#     financial_data = payload.financial_data.dict()
#     print(financial_data)
#     financials = sorted(financial_data['financial_years'], key=lambda x: x["year"], reverse=True)
#     print(financials)

#     # ------------------------------------------------
#     # 1️⃣ Compute metrics for each year
#     # ------------------------------------------------
#     yearly_results = []
#     for i, year_data in enumerate(financials):
#         prev = financials[i - 1] if i > 0 else None
#         metrics = compute_year_metrics(year_data, prev)
#         yearly_results.append({
#             "year": year_data["year"],
#             "metrics": metrics
#         })

#     # ------------------------------------------------
#     # 2️⃣ Compute multi-year CAGRs & Trend Signals
#     # ------------------------------------------------
#     cagr_data = compute_trends(financials)

#     # ------------------------------------------------
#     # 3️⃣ Apply Rules for Each Year
#     # ------------------------------------------------
#     all_year_flags = []
#     for item in yearly_results:
#         flags = evaluate_rules(item["metrics"], cagr_data)
#         for f in flags:
#             all_year_flags.append({
#                 "year": item["year"],
#                 **f
#             })

#     # ------------------------------------------------
#     # 3️⃣a Filter rules for latest year only
#     # ------------------------------------------------
#     latest_year = max([item["year"] for item in yearly_results])
#     all_year_flags = [f for f in all_year_flags if f["year"] == latest_year]

#     # ------------------------------------------------
#     # 4️⃣ Classify flags into red/yellow/green
#     # ------------------------------------------------
#     red_flags = []
#     yellow_flags = []
#     green_flags = []

#     for f in all_year_flags:
#         if f["flag"] == "RED":
#             red_flags.append(f)
#         elif f["flag"] == "YELLOW":
#             yellow_flags.append(f)
#         else:
#             green_flags.append(f)

#     # ------------------------------------------------
#     # 5️⃣ Normalize Output Flags (as per schema)
#     # ------------------------------------------------
#     formatted_red_flags = [{
#         "severity": "CRITICAL" if rf["flag"] == "RED" else "HIGH",
#         "title": rf["rule_name"],
#         "detail": rf["reason"]
#     } for rf in red_flags]

#     # Positive points → from green rule messages
#     positive_points = [
#         f["reason"]
#         for f in green_flags
#     ]

#     # ------------------------------------------------
#     # 6️⃣ Compute Sub-score
#     # ------------------------------------------------
#     red_score = len(red_flags) * 15
#     yellow_score = len(yellow_flags) * 5
#     sub_score = max(0, 100 - red_score - yellow_score)

#     # ------------------------------------------------
#     # 7️⃣ Build LLM Narrative
#     # ------------------------------------------------
#     metrics_table_text = "\n".join([str(x) for x in yearly_results])
#     narrative = generate_llm_narrative(company, metrics_table_text, all_year_flags) 
#     narrative_list =[line.strip() for line in narrative.split("\n") if line.strip()]

#     # ------------------------------------------------
#     # 8️⃣ Final Output Schema
#     # ------------------------------------------------
#     result = {
#         "module": "CapexCWIP",
#         "sub_score_adjusted": sub_score,
#         "analysis_narrative": narrative_list,
#         "red_flags": formatted_red_flags,
#         "positive_points": positive_points,
#         "rules": all_year_flags,
#         "yearly_metrics": yearly_results,
#     }

#     return result

# orchestrator.py

# from collections import Counter
# from typing import Dict, List

# from .metrics_engine import compute_year_metrics
# from .trend_engine import compute_trends
# from .rules_engine import apply_rules    # now returns RuleResult objects
# from .llm_agent import generate_llm_narrative


# class CapexCwipModule:
#     """Capex–CWIP analysis orchestrator, aligned with BorrowingsModule architecture."""

#     def run(self, payload) -> Dict:
#         company = payload.company
#         financial_data = payload.financial_data.dict()

#         # ------------------------------------------------
#         # 1️⃣ Structure financial years as {year: row}
#         # ------------------------------------------------
#         # Input is list of dicts → convert to year-indexed dict
#         financials_list = sorted(
#             financial_data["financial_years"], key=lambda x: x["year"]
#         )
#         yearly: Dict[int, dict] = {item["year"]: item for item in financials_list}

#         # ------------------------------------------------
#         # 2️⃣ Compute per-year metrics
#         # ------------------------------------------------
#         per_year_metrics: Dict[int, dict] = {}
#         years_sorted = sorted(yearly.keys())

#         for i, yr in enumerate(years_sorted):
#             prev_year = years_sorted[i - 1] if i > 0 else None
#             prev_data = yearly.get(prev_year)
#             metrics = compute_year_metrics(yearly[yr], prev_data)
#             per_year_metrics[yr] = metrics

#         # ------------------------------------------------
#         # 3️⃣ Compute Trends (CAGR + YoY + Multi-year trends)
#         # ------------------------------------------------
#         trend_metrics = compute_trends(yearly)

#         # ------------------------------------------------
#         # 4️⃣ Apply rules
#         # ------------------------------------------------
#         rule_results = []
#         for yr, metrics in per_year_metrics.items():
#             # Pass full metrics for this year + trend data
#             results = apply_rules(metrics, trend_metrics)
#             rule_results.extend(results)

#         # ------------------------------------------------
#         # 5️⃣ Filter rules for latest year only (same as reference)
#         # ------------------------------------------------
#         latest_year = max(per_year_metrics.keys())
#         rule_results = [r for r in rule_results if r.year == latest_year]

#         # ------------------------------------------------
#         # 6️⃣ Compute Score (same formula as Borrowings)
#         # ------------------------------------------------
#         base_score = self._compute_score(rule_results)

#         # ------------------------------------------------
#         # 7️⃣ Summaries: Red flags + Positive points
#         # ------------------------------------------------
#         red_flags, positives = self._summarize(rule_results)

#         # ------------------------------------------------
#         # 8️⃣ Build additional narrative notes
#         # ------------------------------------------------
#         key_metrics = self._extract_key_metrics(per_year_metrics, trend_metrics)
#         deterministic_notes = self._build_deterministic_notes(
#             key_metrics, trend_metrics, red_flags
#         )

#         # ------------------------------------------------
#         # 9️⃣ Generate LLM narrative
#         # ------------------------------------------------
#         narrative = generate_llm_narrative(
#             company_id=company,
#             key_metrics=key_metrics,
#             rule_results=rule_results,
#             deterministic_notes=deterministic_notes,
#             base_score=base_score,
#             trend_data=trend_metrics,
#         )

#         # ------------------------------------------------
#         # 🔟 Final Output (aligned with BorrowingsOutput)
#         # ------------------------------------------------
#         return {
#             "module": "CapexCWIP",
#             "company": company,
#             "key_metrics": key_metrics,
#             "trends": trend_metrics,
#             "analysis_narrative": narrative,
#             "red_flags": red_flags,
#             "positive_points": positives,
#             "rules": rule_results,
#         }

#     # ======================================================
#     # Helper Methods (mirroring BorrowingsModule structure)
#     # ======================================================

#     @staticmethod
#     def _compute_score(rule_results) -> int:
#         counts = Counter(r.flag for r in rule_results)
#         score = 100
#         score -= 10 * counts.get("RED", 0)
#         score -= 5 * counts.get("YELLOW", 0)
#         return max(0, min(100, score))

#     @staticmethod
#     def _summarize(rule_results):
#         red_flags = []
#         positives = []

#         for r in rule_results:
#             if r.flag == "RED":
#                 severity = "CRITICAL"  # you may map rule_ids if needed
#                 red_flags.append({
#                     "severity": severity,
#                     "title": r.rule_name,
#                     "detail": r.reason,
#                 })
#             elif r.flag == "GREEN":
#                 positives.append(f"{r.rule_name}: {r.reason}")

#         return red_flags, positives

#     @staticmethod
#     def _extract_key_metrics(per_year_metrics, trend_metrics):
#         latest_year = max(per_year_metrics.keys())
#         m = per_year_metrics[latest_year]

#         return {
#             "year": latest_year,
#             "capex_intensity": m.get("capex_intensity"),
#             "cwip_pct": m.get("cwip_pct"),
#             "asset_turnover": m.get("asset_turnover"),
#             "debt_funded_capex": m.get("debt_funded_capex"),
#             "fcf_coverage": m.get("fcf_coverage"),

#             "capex_cagr": trend_metrics.get("capex_cagr"),
#             "cwip_cagr": trend_metrics.get("cwip_cagr"),
#             "nfa_cagr": trend_metrics.get("nfa_cagr"),
#             "revenue_cagr": trend_metrics.get("revenue_cagr"),
#         }

#     @staticmethod
#     def _build_deterministic_notes(key_metrics, trends, red_flags):
#         notes = []

#         ci = key_metrics.get("capex_intensity")
#         if ci is not None:
#             notes.append(f"Capex intensity at {ci:.2f}.")

#         cw = key_metrics.get("cwip_pct")
#         if cw is not None:
#             notes.append(f"CWIP at {cw*100:.1f}% of fixed assets.")

#         if key_metrics.get("asset_turnover") is not None:
#             notes.append(f"Asset turnover = {key_metrics['asset_turnover']:.2f}x.")

#         if key_metrics.get("debt_funded_capex") is not None:
#             notes.append(
#                 f"Debt-funded capex ratio = {key_metrics['debt_funded_capex']:.2f}."
#             )

#         if red_flags:
#             notes.append(
#                 "Key concerns: " + ", ".join(r["title"] for r in red_flags[:2])
#             )

#         return notes



# orchestrator.py — FINAL FIXED VERSION

# orchestrator.py — FINAL FIXED VERSION

# =============================================================
# orchestrator.py  (CLEAN + CORRECTED + INDENT SAFE)
# =============================================================

from .metrics_engine import compute_year_metrics
from .trend_engine import compute_trends
from .rules_engine import apply_rules
from .llm_agent import generate_llm_narrative
from .models import RuleResult


class CapexCwipModule:

    def run(self, payload):

        company = payload.company
        finyrs = payload.financial_data.financial_years

        # Convert Pydantic models → normal dicts and sort by year ASC
        financials = sorted(
            [fy.dict() for fy in finyrs],
            key=lambda x: x["year"]
        )

        # --------------------------------------------------
        # 1) Compute per-year metrics
        # --------------------------------------------------
        per_year_metrics = {}
        prev = None

        for yr in financials:
            metrics = compute_year_metrics(yr, prev)
            per_year_metrics[yr["year"]] = metrics
            prev = yr

        # --------------------------------------------------
        # 2) Multi-year trend metrics
        # --------------------------------------------------
        trend_input = {fy["year"]: fy for fy in financials}
        trend_metrics = compute_trends(trend_input)

        # --------------------------------------------------
        # 3) Apply rules PER YEAR (correct)
        # --------------------------------------------------
        rule_results: list[RuleResult] = []

        for year, metrics in per_year_metrics.items():

            results = apply_rules(
                metrics=metrics,
                trends=trend_metrics
            )

            # ensure year is assigned
            for r in results:
                r.year = year

            rule_results.extend(results)

        # --------------------------------------------------
        # 4) Filter to latest year only (Borrowings style)
        # --------------------------------------------------
        latest_year = max(per_year_metrics.keys())
        rule_results = [r for r in rule_results if r.year == latest_year]

        # --------------------------------------------------
        # 5) Compute score
        # --------------------------------------------------
        red_count = sum(1 for r in rule_results if r.flag == "RED")
        yellow_count = sum(1 for r in rule_results if r.flag == "YELLOW")

        base_score = max(0, 100 - red_count * 15 - yellow_count * 5)

        # --------------------------------------------------
        # 6) Key metrics (latest year only)
        # --------------------------------------------------
        latest = per_year_metrics[latest_year]

        key_metrics = {
            "year": latest_year,
            "capex_intensity": latest["capex_intensity"],
            "cwip_pct": latest["cwip_pct"],
            "asset_turnover": latest["asset_turnover"],
            "debt_funded_capex": latest["debt_funded_capex"],
            "fcf_coverage": latest["fcf_coverage"],

            "capex_cagr": trend_metrics["capex_cagr"],
            "cwip_cagr": trend_metrics["cwip_cagr"],
            "nfa_cagr": trend_metrics["nfa_cagr"],
            "revenue_cagr": trend_metrics["revenue_cagr"],
        }

        # --------------------------------------------------
        # 7) Trend summary
        # --------------------------------------------------
        trend_summary = {
            "cwip": {
                "values": trend_metrics["cwip_series"],
                "yoy_growth_pct": trend_metrics["cwip_yoy"],
                "insight": None
            },
            "capex": {
                "values": trend_metrics["capex_series"],
                "yoy_growth_pct": trend_metrics["capex_yoy"],
                "insight": None
            },
            "nfa": {
                "values": trend_metrics["nfa_series"],
                "yoy_growth_pct": trend_metrics["nfa_yoy"],
                "insight": None
            },
        }

        # --------------------------------------------------
        # 8) Deterministic notes → LLM
        # --------------------------------------------------
        deterministic_notes = [
            f"Capex intensity {latest['capex_intensity']:.2f}.",
            f"CWIP ratio {latest['cwip_pct']:.2f}.",
            f"Asset turnover {latest['asset_turnover']:.2f}.",
            f"Debt-funded capex {latest['debt_funded_capex']:.2f}.",
        ]

        # --------------------------------------------------
        # 9) LLM narrative
        # --------------------------------------------------
        narrative, adjusted_score, trend_insights = generate_llm_narrative(
            company_id=company,
            key_metrics=key_metrics,
            rule_results=rule_results,
            deterministic_notes=deterministic_notes,
            base_score=base_score,
            trend_data=trend_summary,
        )

        # Insert LLM-generated insights
        for metric, text in trend_insights.items():
            if metric in trend_summary:
                trend_summary[metric]["insight"] = text

        # --------------------------------------------------
        # 10) Summaries
        # --------------------------------------------------
        red_flags = []
        positives = []

        for r in rule_results:
            if r.flag == "RED":
                red_flags.append({
                    "severity": "CRITICAL",
                    "title": r.rule_name,
                    "detail": r.reason
                })
            elif r.flag == "GREEN":
                positives.append(f"{r.rule_name}: {r.reason}")

        # --------------------------------------------------
        # FINAL OUTPUT
        # --------------------------------------------------
        return {
            "module": "CapexCWIP",
            "company": company,
            "key_metrics": key_metrics,
            "trends": trend_summary,
            "analysis_narrative": narrative,
            "red_flags": red_flags,
            "positive_points": positives,
            "rules": [r.dict() for r in rule_results],
        }


