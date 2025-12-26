# =============================================================
# src/app/mesh/analyst_agents.py
# Domain-Specific Analyst Agents
# Layer C - Agentic Mesh
# =============================================================
"""
Analyst agents for each domain:
- DebtAnalystAgent: Borrowings, leverage, debt structure
- LiquidityAnalystAgent: Short-term liquidity, cash position
- AssetQualityAnalystAgent: Asset turnover, intangibles, CWIP
- QoEAnalystAgent: Quality of earnings, cash conversion
- WorkingCapitalAnalystAgent: DSO, DIO, DPO, CCC
- EquityAnalystAgent: ROE, retained earnings, funding mix
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import time
import logging

from .base_agent import BaseMeshAgent, AgentOutput
from src.app.blackboard.models import Hypothesis, Fact
from src.app.blackboard.store import Blackboard

logger = logging.getLogger(__name__)


class DebtAnalystAgent(BaseMeshAgent):
    """
    Analyzes borrowings, leverage, debt structure, and refinancing risk.
    
    Maps to the 'borrowings' module in agents_config.yaml.
    """
    
    agent_id = "debt_analyst"
    agent_name = "Debt Analyst"
    description = "Senior credit analyst specializing in debt and leverage analysis"
    hypothesis_budget = 6
    
    # Key facts to analyze
    KEY_FACTS = [
        "de_ratio", "debt_ebitda", "interest_coverage",
        "total_debt", "short_term_debt", "long_term_debt",
        "maturity_lt_1y_pct", "floating_share", "wacd",
        "total_debt_cagr", "debt_vs_ebitda_cagr_diff",
    ]
    
    def execute(self, blackboard: Blackboard) -> AgentOutput:
        """Execute debt analysis and generate hypotheses."""
        start_time = time.time()
        hypotheses = []
        facts_used = []
        
        try:
            # Get relevant facts
            facts = self.get_relevant_facts(blackboard, module="borrowings")
            facts_dict = {f.key: f.value for f in facts}
            facts_used = [f.fact_id for f in facts]
            
            # Analyze leverage
            de_ratio = facts_dict.get("de_ratio")
            if de_ratio is not None:
                if de_ratio > 1.0:
                    hyp = self.generate_hypothesis(
                        claim=f"Company has high leverage with D/E ratio of {de_ratio:.2f}x, "
                              f"indicating significant financial risk and vulnerability to interest rate shocks.",
                        confidence=0.85,
                        linked_facts=[f.fact_id for f in facts if f.key == "de_ratio"],
                        reasoning="D/E > 1.0 indicates debt exceeds equity",
                    )
                    if hyp:
                        hypotheses.append(hyp)
                elif de_ratio < 0.5:
                    hyp = self.generate_hypothesis(
                        claim=f"Company maintains conservative leverage with D/E of {de_ratio:.2f}x, "
                              f"providing financial flexibility for growth or weathering downturns.",
                        confidence=0.80,
                        linked_facts=[f.fact_id for f in facts if f.key == "de_ratio"],
                    )
                    if hyp:
                        hypotheses.append(hyp)
            
            # Analyze interest coverage
            icr = facts_dict.get("interest_coverage")
            if icr is not None:
                if icr < 1.5:
                    hyp = self.generate_hypothesis(
                        claim=f"Critical interest coverage of {icr:.2f}x - earnings barely cover "
                              f"interest payments. High default risk if earnings decline.",
                        confidence=0.90,
                        linked_facts=[f.fact_id for f in facts if f.key == "interest_coverage"],
                    )
                    if hyp:
                        hypotheses.append(hyp)
                elif icr > 5.0:
                    hyp = self.generate_hypothesis(
                        claim=f"Strong interest coverage of {icr:.2f}x provides substantial cushion "
                              f"for debt servicing even under stress scenarios.",
                        confidence=0.75,
                        linked_facts=[f.fact_id for f in facts if f.key == "interest_coverage"],
                    )
                    if hyp:
                        hypotheses.append(hyp)
            
            # Analyze refinancing risk
            st_debt_pct = facts_dict.get("maturity_lt_1y_pct")
            if st_debt_pct is not None and st_debt_pct > 0.50:
                hyp = self.generate_hypothesis(
                    claim=f"Significant refinancing risk: {st_debt_pct:.0%} of debt matures within 1 year. "
                          f"Company needs to refinance or repay substantial amounts soon.",
                    confidence=0.85,
                    linked_facts=[f.fact_id for f in facts if f.key == "maturity_lt_1y_pct"],
                )
                if hyp:
                    hypotheses.append(hyp)
            
            # Analyze debt growth vs earnings
            debt_vs_ebitda = facts_dict.get("debt_vs_ebitda_cagr_diff")
            if debt_vs_ebitda is not None and debt_vs_ebitda > 5:
                hyp = self.generate_hypothesis(
                    claim=f"Debt growing faster than earnings capacity: {debt_vs_ebitda:.1f}pp differential. "
                          f"Unsustainable trajectory that may lead to credit stress.",
                    confidence=0.80,
                    linked_facts=[f.fact_id for f in facts if "cagr" in f.key.lower()],
                )
                if hyp:
                    hypotheses.append(hyp)
            
            execution_time = (time.time() - start_time) * 1000
            self.log_execution(True, len(hypotheses), execution_time)
            
            return AgentOutput(
                agent_id=self.agent_id,
                hypotheses=hypotheses[:self.hypothesis_budget],
                facts_used=facts_used,
                execution_time_ms=execution_time,
                success=True,
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.log_execution(False, 0, execution_time, str(e))
            return AgentOutput(
                agent_id=self.agent_id,
                hypotheses=[],
                facts_used=facts_used,
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e),
            )


class LiquidityAnalystAgent(BaseMeshAgent):
    """
    Analyzes short-term liquidity, cash position, and working capital adequacy.
    
    Maps to the 'liquidity' module.
    """
    
    agent_id = "liquidity_analyst"
    agent_name = "Liquidity Analyst"
    description = "Analyst focused on short-term solvency and cash adequacy"
    hypothesis_budget = 5
    
    KEY_FACTS = [
        "current_ratio", "quick_ratio", "cash_ratio",
        "defensive_interval_ratio_days", "ocf_to_current_liabilities",
        "cash_and_equivalents", "current_liabilities",
    ]
    
    def execute(self, blackboard: Blackboard) -> AgentOutput:
        """Execute liquidity analysis."""
        start_time = time.time()
        hypotheses = []
        facts_used = []
        
        try:
            facts = self.get_relevant_facts(blackboard, module="liquidity")
            facts_dict = {f.key: f.value for f in facts}
            facts_used = [f.fact_id for f in facts]
            
            # Analyze current ratio
            current_ratio = facts_dict.get("current_ratio")
            if current_ratio is not None:
                if current_ratio < 1.0:
                    hyp = self.generate_hypothesis(
                        claim=f"Liquidity stress: Current ratio of {current_ratio:.2f}x means "
                              f"current liabilities exceed current assets. Near-term solvency risk.",
                        confidence=0.90,
                        linked_facts=[f.fact_id for f in facts if f.key == "current_ratio"],
                    )
                    if hyp:
                        hypotheses.append(hyp)
                elif current_ratio > 2.0:
                    hyp = self.generate_hypothesis(
                        claim=f"Strong liquidity position with current ratio of {current_ratio:.2f}x. "
                              f"Ample cushion to meet short-term obligations.",
                        confidence=0.75,
                        linked_facts=[f.fact_id for f in facts if f.key == "current_ratio"],
                    )
                    if hyp:
                        hypotheses.append(hyp)
            
            # Analyze defensive interval
            dir_days = facts_dict.get("defensive_interval_ratio_days")
            if dir_days is not None:
                if dir_days < 30:
                    hyp = self.generate_hypothesis(
                        claim=f"Low liquidity runway: Only {dir_days:.0f} days of defensive interval. "
                              f"Company would struggle to survive without new cash inflows.",
                        confidence=0.85,
                        linked_facts=[f.fact_id for f in facts if "defensive" in f.key],
                    )
                    if hyp:
                        hypotheses.append(hyp)
                elif dir_days > 180:
                    hyp = self.generate_hypothesis(
                        claim=f"Strong liquidity buffer: {dir_days:.0f} days of operating expenses "
                              f"covered by liquid assets.",
                        confidence=0.70,
                        linked_facts=[f.fact_id for f in facts if "defensive" in f.key],
                    )
                    if hyp:
                        hypotheses.append(hyp)
            
            # Analyze OCF coverage
            ocf_coverage = facts_dict.get("ocf_to_current_liabilities")
            if ocf_coverage is not None and ocf_coverage < 0.3:
                hyp = self.generate_hypothesis(
                    claim=f"Weak operating cash flow coverage ({ocf_coverage:.2f}x) of current liabilities. "
                          f"May need external financing for day-to-day operations.",
                    confidence=0.80,
                    linked_facts=[f.fact_id for f in facts if "ocf" in f.key],
                )
                if hyp:
                    hypotheses.append(hyp)
            
            execution_time = (time.time() - start_time) * 1000
            self.log_execution(True, len(hypotheses), execution_time)
            
            return AgentOutput(
                agent_id=self.agent_id,
                hypotheses=hypotheses[:self.hypothesis_budget],
                facts_used=facts_used,
                execution_time_ms=execution_time,
                success=True,
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return AgentOutput(
                agent_id=self.agent_id,
                hypotheses=[],
                facts_used=facts_used,
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e),
            )


class AssetQualityAnalystAgent(BaseMeshAgent):
    """
    Analyzes asset quality, turnover, intangibles, and CWIP.
    
    Maps to 'asset_intangible_quality' and 'capex_cwip' modules.
    """
    
    agent_id = "asset_quality_analyst"
    agent_name = "Asset Quality Analyst"
    description = "Analyst focused on asset quality and intangible-heavy balance sheets"
    hypothesis_budget = 5
    
    def execute(self, blackboard: Blackboard) -> AgentOutput:
        """Execute asset quality analysis."""
        start_time = time.time()
        hypotheses = []
        facts_used = []
        
        try:
            # Get facts from relevant modules
            aiq_facts = self.get_relevant_facts(blackboard, module="asset_intangible_quality")
            capex_facts = self.get_relevant_facts(blackboard, module="capex_cwip")
            facts = aiq_facts + capex_facts
            facts_dict = {f.key: f.value for f in facts}
            facts_used = [f.fact_id for f in facts]
            
            # Analyze asset turnover
            asset_turnover = facts_dict.get("asset_turnover")
            if asset_turnover is not None:
                if asset_turnover < 0.5:
                    hyp = self.generate_hypothesis(
                        claim=f"Low asset turnover of {asset_turnover:.2f}x suggests inefficient "
                              f"use of fixed assets or significant idle capacity.",
                        confidence=0.75,
                        linked_facts=[f.fact_id for f in facts if f.key == "asset_turnover"],
                    )
                    if hyp:
                        hypotheses.append(hyp)
            
            # Analyze intangibles
            intangible_pct = facts_dict.get("intangible_pct_total_assets")
            if intangible_pct is not None and intangible_pct > 0.30:
                hyp = self.generate_hypothesis(
                    claim=f"High intangibles concentration ({intangible_pct:.0%} of assets). "
                          f"Impairment risk if business performance deteriorates.",
                    confidence=0.70,
                    linked_facts=[f.fact_id for f in facts if "intangible" in f.key],
                )
                if hyp:
                    hypotheses.append(hyp)
            
            # Analyze CWIP
            cwip_pct = facts_dict.get("cwip_pct")
            cwip_increasing = facts_dict.get("cwip_increasing_3y")
            if cwip_increasing:
                hyp = self.generate_hypothesis(
                    claim="CWIP has been increasing for 3 consecutive years. "
                          "Verify project timelines and expected ROI for ongoing investments.",
                    confidence=0.75,
                    linked_facts=[f.fact_id for f in facts if "cwip" in f.key],
                )
                if hyp:
                    hypotheses.append(hyp)
            
            # Analyze asset age
            asset_age = facts_dict.get("asset_age_proxy")
            if asset_age is not None and asset_age > 0.70:
                hyp = self.generate_hypothesis(
                    claim=f"Aging asset base (accumulated depreciation at {asset_age:.0%} of gross block). "
                          f"May require significant capex for replacement/upgrades.",
                    confidence=0.70,
                    linked_facts=[f.fact_id for f in facts if "age" in f.key],
                )
                if hyp:
                    hypotheses.append(hyp)
            
            execution_time = (time.time() - start_time) * 1000
            self.log_execution(True, len(hypotheses), execution_time)
            
            return AgentOutput(
                agent_id=self.agent_id,
                hypotheses=hypotheses[:self.hypothesis_budget],
                facts_used=facts_used,
                execution_time_ms=execution_time,
                success=True,
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return AgentOutput(
                agent_id=self.agent_id,
                hypotheses=[],
                facts_used=facts_used,
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e),
            )


class QoEAnalystAgent(BaseMeshAgent):
    """
    Analyzes quality of earnings, cash conversion, and earnings sustainability.
    
    Maps to 'quality_of_earnings' module.
    """
    
    agent_id = "qoe_analyst"
    agent_name = "Quality of Earnings Analyst"
    description = "Forensic accounting analyst evaluating earnings quality"
    hypothesis_budget = 5
    
    def execute(self, blackboard: Blackboard) -> AgentOutput:
        """Execute quality of earnings analysis."""
        start_time = time.time()
        hypotheses = []
        facts_used = []
        
        try:
            facts = self.get_relevant_facts(blackboard, module="quality_of_earnings")
            facts_dict = {f.key: f.value for f in facts}
            facts_used = [f.fact_id for f in facts]
            
            # Analyze QoE ratio
            qoe = facts_dict.get("qoe")
            if qoe is not None:
                if qoe < 0.5:
                    hyp = self.generate_hypothesis(
                        claim=f"Poor earnings quality: CFO/Net Income ratio of {qoe:.2f}x. "
                              f"Earnings are not translating to cash, suggesting accrual-heavy accounting.",
                        confidence=0.85,
                        linked_facts=[f.fact_id for f in facts if f.key == "qoe"],
                    )
                    if hyp:
                        hypotheses.append(hyp)
                elif qoe > 1.2:
                    hyp = self.generate_hypothesis(
                        claim=f"Strong cash conversion with QoE ratio of {qoe:.2f}x. "
                              f"Earnings are well-supported by actual cash generation.",
                        confidence=0.75,
                        linked_facts=[f.fact_id for f in facts if f.key == "qoe"],
                    )
                    if hyp:
                        hypotheses.append(hyp)
            
            # Analyze DSO
            dso = facts_dict.get("dso")
            if dso is not None and dso > 90:
                hyp = self.generate_hypothesis(
                    claim=f"Extended receivables cycle: DSO of {dso:.0f} days is concerning. "
                          f"May indicate collection issues or aggressive revenue recognition.",
                    confidence=0.80,
                    linked_facts=[f.fact_id for f in facts if f.key == "dso"],
                )
                if hyp:
                    hypotheses.append(hyp)
            
            # Analyze other income dependence
            other_income_ratio = facts_dict.get("other_income_ratio")
            if other_income_ratio is not None and other_income_ratio > 0.20:
                hyp = self.generate_hypothesis(
                    claim=f"High other income dependence ({other_income_ratio:.0%} of profits). "
                          f"Core operating earnings may be weaker than headline numbers suggest.",
                    confidence=0.75,
                    linked_facts=[f.fact_id for f in facts if "other_income" in f.key],
                )
                if hyp:
                    hypotheses.append(hyp)
            
            # Analyze accruals
            accruals = facts_dict.get("accruals_ratio")
            if accruals is not None and accruals > 0.10:
                hyp = self.generate_hypothesis(
                    claim=f"High accruals ratio of {accruals:.1%} may indicate earnings management. "
                          f"Recommend scrutiny of revenue recognition and expense deferrals.",
                    confidence=0.70,
                    linked_facts=[f.fact_id for f in facts if "accruals" in f.key],
                )
                if hyp:
                    hypotheses.append(hyp)
            
            execution_time = (time.time() - start_time) * 1000
            self.log_execution(True, len(hypotheses), execution_time)
            
            return AgentOutput(
                agent_id=self.agent_id,
                hypotheses=hypotheses[:self.hypothesis_budget],
                facts_used=facts_used,
                execution_time_ms=execution_time,
                success=True,
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return AgentOutput(
                agent_id=self.agent_id,
                hypotheses=[],
                facts_used=facts_used,
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e),
            )


class WorkingCapitalAnalystAgent(BaseMeshAgent):
    """
    Analyzes working capital efficiency: DSO, DIO, DPO, and cash conversion cycle.
    
    Maps to 'working_capital' module.
    """
    
    agent_id = "working_capital_analyst"
    agent_name = "Working Capital Analyst"
    description = "Analyst focused on working capital efficiency and cash cycle"
    hypothesis_budget = 4
    
    def execute(self, blackboard: Blackboard) -> AgentOutput:
        """Execute working capital analysis."""
        start_time = time.time()
        hypotheses = []
        facts_used = []
        
        try:
            facts = self.get_relevant_facts(blackboard, module="working_capital")
            facts_dict = {f.key: f.value for f in facts}
            facts_used = [f.fact_id for f in facts]
            
            # Analyze cash conversion cycle
            ccc = facts_dict.get("ccc")
            if ccc is not None:
                if ccc > 90:
                    hyp = self.generate_hypothesis(
                        claim=f"Long cash conversion cycle of {ccc:.0f} days ties up significant capital. "
                              f"Working capital efficiency improvement opportunities exist.",
                        confidence=0.75,
                        linked_facts=[f.fact_id for f in facts if f.key == "ccc"],
                    )
                    if hyp:
                        hypotheses.append(hyp)
                elif ccc < 0:
                    hyp = self.generate_hypothesis(
                        claim=f"Negative cash conversion cycle ({ccc:.0f} days) - company gets paid "
                              f"before paying suppliers. Strong working capital position.",
                        confidence=0.80,
                        linked_facts=[f.fact_id for f in facts if f.key == "ccc"],
                    )
                    if hyp:
                        hypotheses.append(hyp)
            
            # Analyze inventory days
            dio = facts_dict.get("dio")
            if dio is not None and dio > 120:
                hyp = self.generate_hypothesis(
                    claim=f"High inventory days ({dio:.0f}) may indicate demand weakness or "
                          f"inventory obsolescence risk.",
                    confidence=0.70,
                    linked_facts=[f.fact_id for f in facts if f.key == "dio"],
                )
                if hyp:
                    hypotheses.append(hyp)
            
            # Analyze net working capital
            nwc = facts_dict.get("net_working_capital")
            if nwc is not None and nwc < 0:
                hyp = self.generate_hypothesis(
                    claim="Negative net working capital indicates current liabilities exceed "
                          "current assets. May signal liquidity pressure.",
                    confidence=0.75,
                    linked_facts=[f.fact_id for f in facts if "working_capital" in f.key],
                )
                if hyp:
                    hypotheses.append(hyp)
            
            execution_time = (time.time() - start_time) * 1000
            self.log_execution(True, len(hypotheses), execution_time)
            
            return AgentOutput(
                agent_id=self.agent_id,
                hypotheses=hypotheses[:self.hypothesis_budget],
                facts_used=facts_used,
                execution_time_ms=execution_time,
                success=True,
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return AgentOutput(
                agent_id=self.agent_id,
                hypotheses=[],
                facts_used=facts_used,
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e),
            )


class EquityAnalystAgent(BaseMeshAgent):
    """
    Analyzes equity quality, ROE, retained earnings, and funding mix.
    
    Maps to 'equity_funding_mix' module.
    """
    
    agent_id = "equity_analyst"
    agent_name = "Equity Analyst"
    description = "Senior equity analyst evaluating shareholder value creation"
    hypothesis_budget = 5
    
    def execute(self, blackboard: Blackboard) -> AgentOutput:
        """Execute equity and funding mix analysis."""
        start_time = time.time()
        hypotheses = []
        facts_used = []
        
        try:
            facts = self.get_relevant_facts(blackboard, module="equity_funding_mix")
            facts_dict = {f.key: f.value for f in facts}
            facts_used = [f.fact_id for f in facts]
            
            # Analyze ROE
            roe = facts_dict.get("roe")
            if roe is not None:
                if roe < 0.10:
                    hyp = self.generate_hypothesis(
                        claim=f"Subpar ROE of {roe:.1%} - returns may be below cost of equity. "
                              f"Value creation at risk if sustained.",
                        confidence=0.80,
                        linked_facts=[f.fact_id for f in facts if f.key == "roe"],
                    )
                    if hyp:
                        hypotheses.append(hyp)
                elif roe > 0.20:
                    hyp = self.generate_hypothesis(
                        claim=f"Strong ROE of {roe:.1%} indicates effective use of shareholder capital "
                              f"to generate returns. Premium valuation may be justified.",
                        confidence=0.75,
                        linked_facts=[f.fact_id for f in facts if f.key == "roe"],
                    )
                    if hyp:
                        hypotheses.append(hyp)
            
            # Analyze dividend sustainability
            payout = facts_dict.get("dividend_payout_ratio")
            if payout is not None:
                if payout > 1.0:
                    hyp = self.generate_hypothesis(
                        claim=f"Unsustainable dividend: Payout ratio of {payout:.0%} exceeds earnings. "
                              f"Company is dipping into reserves or borrowing for dividends.",
                        confidence=0.90,
                        linked_facts=[f.fact_id for f in facts if "payout" in f.key],
                    )
                    if hyp:
                        hypotheses.append(hyp)
            
            # Analyze dilution
            dilution = facts_dict.get("equity_dilution_pct")
            if dilution is not None and dilution > 0.10:
                hyp = self.generate_hypothesis(
                    claim=f"Significant equity dilution of {dilution:.0%}. "
                          f"Existing shareholders' ownership has been materially reduced.",
                    confidence=0.80,
                    linked_facts=[f.fact_id for f in facts if "dilution" in f.key],
                )
                if hyp:
                    hypotheses.append(hyp)
            
            # Analyze retained earnings trend
            retained_declining = facts_dict.get("retained_declining")
            if retained_declining:
                hyp = self.generate_hypothesis(
                    claim="Retained earnings declining for 3+ years - company consuming more than "
                          "it generates. Self-funding capacity is eroding.",
                    confidence=0.80,
                    linked_facts=[f.fact_id for f in facts if "retained" in f.key],
                )
                if hyp:
                    hypotheses.append(hyp)
            
            execution_time = (time.time() - start_time) * 1000
            self.log_execution(True, len(hypotheses), execution_time)
            
            return AgentOutput(
                agent_id=self.agent_id,
                hypotheses=hypotheses[:self.hypothesis_budget],
                facts_used=facts_used,
                execution_time_ms=execution_time,
                success=True,
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return AgentOutput(
                agent_id=self.agent_id,
                hypotheses=[],
                facts_used=facts_used,
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e),
            )
