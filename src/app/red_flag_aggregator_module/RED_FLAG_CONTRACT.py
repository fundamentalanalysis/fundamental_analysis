"""
Red Flag Contract: Binding Specification for All Upstream Modules

THIS DOCUMENT IS BINDING.

Every module that emits red flags MUST conform to this contract.

Failure to conform will cause aggregator validation errors.
This is intentional and correct.
"""

# =============================================================================
# CANONICAL RISK CATEGORIES
# =============================================================================

CANONICAL_RISK_CATEGORIES = {
    "liquidity": "Liquidity Stress",
    "leverage": "Leverage & Debt Risk",
    "earnings_quality": "Earnings Quality Risk",
    "working_capital": "Working Capital Stress",
    "governance_fraud": "Corporate Governance / Fraud Indicators",
    "asset_utilization": "Growth / Asset Utilization Risk",
}

"""
Every red flag MUST have risk_category set to exactly one of these values.
No abbreviations. No inference. No exceptions.

If a module detects risk that doesn't fit these 6 categories, the module is
wrong, not the aggregator.
"""

# =============================================================================
# REQUIRED FIELDS FOR EVERY RED FLAG
# =============================================================================

RED_FLAG_REQUIRED_FIELDS = {
    "module": {
        "type": "string",
        "description": "Name of the source module (e.g., 'liquidity', 'borrowings', 'quality_of_earnings')",
        "example": "borrowings",
    },
    "severity": {
        "type": "enum",
        "values": ["GREEN", "YELLOW", "RED", "CRITICAL"],
        "description": "Severity level. GREEN flags are ignored by aggregator. Must match the condition detected.",
        "example": "CRITICAL",
    },
    "title": {
        "type": "string",
        "description": "Short, analyst-readable title. Max 100 chars.",
        "example": "Debt-to-Equity Ratio (D/E) > 3",
    },
    "detail": {
        "type": "string",
        "description": "1-2 sentence explanation of why this flag was raised.",
        "example": "Excessive reliance on debt relative to equity capital.",
    },
    "risk_category": {
        "type": "string (enum)",
        "values": list(CANONICAL_RISK_CATEGORIES.keys()),
        "description": "Canonical risk category. No inference. No guessing.",
        "example": "leverage",
        "MANDATORY": True,
    },
}

# =============================================================================
# OPTIONAL BUT RECOMMENDED FIELDS
# =============================================================================

RED_FLAG_OPTIONAL_FIELDS = {
    "metric": {
        "type": "string",
        "description": "Name of the metric that triggered the flag (e.g., 'de_ratio', 'cash_ratio')",
        "example": "de_ratio",
    },
    "value": {
        "type": "float or int",
        "description": "The actual value of the metric.",
        "example": 5.5,
    },
    "threshold": {
        "type": "string",
        "description": "Human-readable threshold that triggered the flag.",
        "example": ">5.0 for CRITICAL",
    },
    "period": {
        "type": "string",
        "description": "Time period for which this flag applies (e.g., 'FY2024', 'Q4 2024', 'TTM')",
        "example": "FY2024",
    },
}

# =============================================================================
# SEVERITY DOCTRINE (Binding)
# =============================================================================

SEVERITY_DOCTRINE = """
GREEN (0 penalty)
  => No material risk. Use sparingly.

YELLOW (5 penalty)
  => Early stress signal. Trend-based risk.
  => Survivable with management action.
  => Examples: Current ratio dips slightly, DSO rises 5-10%, minor receivables growth

RED (10 penalty)
  => Material financial risk. Impacts solvency or valuation.
  => Requires management response.
  => Examples: D/E > 3, cash ratio < 0.3, QoE < 0.8, CCC > 180 days

CRITICAL (20 penalty)
  => Structural failure. Fraud. Insolvency threat.
  => No amount of other "good" can offset this.
  => Examples:
       - Related-party fraud
       - Evergreening (debt rollover)
       - Asset stripping
       - Negative equity
       - Debt/EBITDA > 7
       - Cash ratio < 0.15

Use CRITICAL sparingly and defensibly.
If you emit CRITICAL lightly, the aggregator becomes hysterical.
If you emit CRITICAL conservatively, fraud slips through.
Get this calibration right.
"""

# =============================================================================
# STEP-BY-STEP: How to Emit a Properly-Formed Red Flag
# =============================================================================

PATTERN_EXAMPLE = """
Step 1: Detect a condition in your module
  - Your module calculates Debt-to-Equity = 5.5
  - This is > 5.0, which is CRITICAL per your spec

Step 2: Determine risk_category
  - This is a leverage metric
  - risk_category = "leverage"

Step 3: Determine severity
  - >= 5.0 => CRITICAL
  - severity = "CRITICAL"

Step 4: Construct the flag dict
  {
    "module": "borrowings",
    "severity": "CRITICAL",
    "title": "Debt-to-Equity Ratio (D/E) > 3",
    "detail": "Excessive reliance on debt relative to equity capital.",
    "risk_category": "leverage",
    "metric": "de_ratio",
    "value": 5.5,
    "threshold": ">5.0 for CRITICAL",
    "period": "FY2024",
  }

Step 5: Validate (pseudocode)
  - All required fields present? YES
  - severity in {GREEN, YELLOW, RED, CRITICAL}? YES
  - risk_category in {liquidity, leverage, earnings_quality, ...}? YES
  - Emit the flag

Step 6: Return to aggregator
  - Aggregator receives flag
  - No inference needed
  - Flag immediately categorized
  - Score updated
"""

# =============================================================================
# ANTI-PATTERNS: WHAT NOT TO DO
# =============================================================================

ANTI_PATTERNS = """
ANTI-PATTERN 1: Omit risk_category
  BAD:
    {
      "module": "quality_of_earnings",
      "severity": "RED",
      "title": "QoE Low",
      "detail": "Profits not in cash",
      # Missing risk_category!
    }
  
  RESULT: Aggregator fails with clear error
  FIX: Add "risk_category": "earnings_quality"


ANTI-PATTERN 2: Use ambiguous module name, skip explicit field
  BAD:
    {
      "module": "equity_funding_mix",  # Module renamed?
      "severity": "RED",
      "title": "Equity Dilution",
      "detail": "...",
      # Relying on module name to infer category?
    }
  
  RESULT: Aggregator fails (no mapping for this module)
  FIX: Always provide risk_category explicitly


ANTI-PATTERN 3: Use abbreviated or non-canonical category
  BAD:
    {
      "module": "liquidity",
      "severity": "RED",
      "title": "...",
      "detail": "...",
      "risk_category": "liq",  # Abbreviated!
    }
  
  RESULT: Validation error
  FIX: Use canonical value: "liquidity"


ANTI-PATTERN 4: Overuse CRITICAL
  BAD:
    Every high metric = CRITICAL
    (Aggregator becomes useless noise)
  
  RESULT: Score capping ignores all non-CRITICAL risks
  FIX: Reserve CRITICAL for structural failures


ANTI-PATTERN 5: Invent new severity level
  BAD:
    {
      "severity": "VERY_RED",  # Not a valid severity
    }
  
  RESULT: Validation error
  FIX: Severity must be exactly one of: GREEN, YELLOW, RED, CRITICAL
"""

# =============================================================================
# MODULE CHECKLIST: Before Emitting Red Flags
# =============================================================================

MODULE_AUTHOR_CHECKLIST = """
[ ] My module has identified a risk condition
[ ] I have mapped it to exactly ONE canonical risk_category
[ ] I have determined the correct severity (GREEN / YELLOW / RED / CRITICAL)
[ ] My flag dict includes all required fields:
    [ ] module
    [ ] severity
    [ ] title (short, analyst-readable)
    [ ] detail (1-2 sentences)
    [ ] risk_category (from canonical list, no abbreviations)
[ ] My flag dict includes optional but recommended fields:
    [ ] metric (what was measured?)
    [ ] value (what was the result?)
    [ ] threshold (what was the limit?)
    [ ] period (when does this apply?)
[ ] Severity is calibrated honestly:
    [ ] GREEN only if truly healthy (rare)
    [ ] YELLOW for early warnings (common)
    [ ] RED for material risks (common)
    [ ] CRITICAL only for structural failure (rare, defensible)
[ ] I have tested my flags with sample data
[ ] I have verified risk_category is not abbreviated or creative
[ ] I'm ready to emit to aggregator
"""

# =============================================================================
# EXAMPLE: Liquidity Module Red Flag Output
# =============================================================================

LIQUIDITY_MODULE_EXAMPLE = """
def emit_liquidity_flags(company_financials):
    flags = []
    
    # Calculate cash ratio
    cash_ratio = (cash + equivalents) / current_liabilities
    
    if cash_ratio >= 0.5:
        severity = "GREEN"
    elif cash_ratio >= 0.3:
        severity = "YELLOW"
    elif cash_ratio >= 0.15:
        severity = "RED"
    else:
        severity = "CRITICAL"
    
    # Only emit non-GREEN flags
    if severity != "GREEN":
        flag = {
            "module": "liquidity",
            "severity": severity,
            "title": "Cash Ratio Low",
            "detail": f"Cash & equivalents insufficient to cover current liabilities. Ratio = {cash_ratio:.2f}.",
            "risk_category": "liquidity",
            "metric": "cash_ratio",
            "value": cash_ratio,
            "threshold": f">={0.5 if severity=='GREEN' else ...}",
            "period": "FY2024",
        }
        flags.append(flag)
    
    return flags
"""

# =============================================================================
# EXAMPLE: Quality of Earnings Module Red Flag Output
# =============================================================================

QOE_MODULE_EXAMPLE = """
def emit_qoe_flags(company_financials):
    flags = []
    
    qoe = operating_cash_flow / net_income
    
    if qoe >= 1.0:
        severity = "GREEN"
    elif qoe >= 0.8:
        severity = "YELLOW"
    elif qoe >= 0.5:
        severity = "RED"
    else:
        severity = "CRITICAL"
    
    if severity != "GREEN":
        flag = {
            "module": "quality_of_earnings",
            "severity": severity,
            "title": "Quality of Earnings Low",
            "detail": f"Operating cash flow weak relative to net income. QoE = {qoe:.2f}.",
            "risk_category": "earnings_quality",  # EXPLICIT - not inferred
            "metric": "qoe",
            "value": qoe,
            "threshold": "<0.8 for RED, <0.5 for CRITICAL",
            "period": "FY2024",
        }
        flags.append(flag)
    
    return flags
"""

# =============================================================================
# ERROR MESSAGES YOU MAY SEE (And How to Fix Them)
# =============================================================================

ERROR_REFERENCE = """
1. "Missing required red-flag fields: ['risk_category']"
   FIX: Add "risk_category": "<canonical_value>" to your flag dict

2. "Unknown risk_category: X. Must be one of: liquidity, leverage, ..."
   FIX: Ensure risk_category is exactly one of the 6 canonical values

3. "Unknown severity: X"
   FIX: Ensure severity is exactly one of: GREEN, YELLOW, RED, CRITICAL

4. "Red flag must be an object/dict"
   FIX: Ensure flag is a dict/object, not a string or other type

5. "Invalid flag from module X: ..."
   FIX: Check the detailed error message and apply fixes above
"""

print(__doc__)
print(SEVERITY_DOCTRINE)
print(PATTERN_EXAMPLE)
print(MODULE_AUTHOR_CHECKLIST)
print(LIQUIDITY_MODULE_EXAMPLE)
print(QOE_MODULE_EXAMPLE)
print(ERROR_REFERENCE)
