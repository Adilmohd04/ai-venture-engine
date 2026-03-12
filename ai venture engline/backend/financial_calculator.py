"""Financial Calculator — handles all numeric calculations to avoid LLM math errors.

CRITICAL: LLMs are terrible at math. All financial metrics MUST be calculated
in code, not by the model. This module provides safe, tested calculation functions.
"""

from typing import Optional


def calculate_clv_cac_ratio(
    arpu: Optional[float],
    lifetime_months: Optional[float],
    cac: Optional[float]
) -> Optional[float]:
    """Calculate CLV/CAC ratio safely.
    
    Args:
        arpu: Average Revenue Per User (monthly)
        lifetime_months: Customer lifetime in months
        cac: Customer Acquisition Cost
        
    Returns:
        CLV/CAC ratio, or None if inputs are invalid
    """
    if not all([arpu, lifetime_months, cac]) or cac == 0:
        return None
    
    clv = arpu * lifetime_months
    ratio = clv / cac
    return round(ratio, 2)


def calculate_payback_period(
    cac: Optional[float],
    arpu: Optional[float]
) -> Optional[float]:
    """Calculate CAC payback period in months.
    
    Args:
        cac: Customer Acquisition Cost
        arpu: Average Revenue Per User (monthly)
        
    Returns:
        Payback period in months, or None if inputs are invalid
    """
    if not all([cac, arpu]) or arpu == 0:
        return None
    
    months = cac / arpu
    return round(months, 1)


def calculate_runway_months(
    cash_balance: Optional[float],
    monthly_burn: Optional[float]
) -> Optional[float]:
    """Calculate runway in months.
    
    Args:
        cash_balance: Current cash balance
        monthly_burn: Monthly burn rate (positive number)
        
    Returns:
        Runway in months, or None if inputs are invalid
    """
    if not all([cash_balance, monthly_burn]) or monthly_burn == 0:
        return None
    
    months = cash_balance / monthly_burn
    return round(months, 1)


def calculate_revenue_multiple(
    valuation: Optional[float],
    arr: Optional[float]
) -> Optional[float]:
    """Calculate valuation / ARR multiple.
    
    Args:
        valuation: Company valuation
        arr: Annual Recurring Revenue
        
    Returns:
        Revenue multiple, or None if inputs are invalid
    """
    if not all([valuation, arr]) or arr == 0:
        return None
    
    multiple = valuation / arr
    return round(multiple, 1)


def parse_currency_string(value: str) -> Optional[float]:
    """Parse currency string to float.
    
    Examples:
        "$10M" -> 10000000
        "5.5B" -> 5500000000
        "$1,234,567" -> 1234567
        "100K" -> 100000
        
    Args:
        value: Currency string
        
    Returns:
        Numeric value, or None if parsing fails
    """
    if not value or not isinstance(value, str):
        return None
    
    # Remove currency symbols and whitespace
    clean = value.replace("$", "").replace(",", "").strip()
    
    # Handle suffixes
    multipliers = {
        "B": 1e9,
        "M": 1e6,
        "K": 1e3,
        "b": 1e9,
        "m": 1e6,
        "k": 1e3,
    }
    
    for suffix, multiplier in multipliers.items():
        if clean.endswith(suffix):
            try:
                num = float(clean[:-1])
                return num * multiplier
            except ValueError:
                return None
    
    # Try direct conversion
    try:
        return float(clean)
    except ValueError:
        return None


def format_currency(value: Optional[float], decimals: int = 1) -> str:
    """Format numeric value as currency string.
    
    Args:
        value: Numeric value
        decimals: Number of decimal places
        
    Returns:
        Formatted string (e.g., "$10.5M")
    """
    if value is None:
        return "N/A"
    
    if value >= 1e9:
        return f"${value / 1e9:.{decimals}f}B"
    if value >= 1e6:
        return f"${value / 1e6:.{decimals}f}M"
    if value >= 1e3:
        return f"${value / 1e3:.{decimals}f}K"
    
    return f"${value:,.{decimals}f}"


def calculate_growth_rate(
    current: Optional[float],
    previous: Optional[float]
) -> Optional[float]:
    """Calculate growth rate as percentage.
    
    Args:
        current: Current period value
        previous: Previous period value
        
    Returns:
        Growth rate as percentage, or None if inputs are invalid
    """
    if not all([current, previous]) or previous == 0:
        return None
    
    rate = ((current - previous) / previous) * 100
    return round(rate, 1)


def extract_financial_metrics(structured_extraction: dict) -> dict:
    """Extract and calculate all financial metrics from structured extraction.
    
    Args:
        structured_extraction: Structured data from pitch deck
        
    Returns:
        Dict with calculated metrics
    """
    metrics = {}
    
    # Parse ARR/MRR
    arr_str = structured_extraction.get("arr")
    mrr_str = structured_extraction.get("mrr")
    
    if arr_str:
        metrics["arr"] = parse_currency_string(arr_str)
    elif mrr_str:
        mrr = parse_currency_string(mrr_str)
        if mrr:
            metrics["arr"] = mrr * 12
    
    # Parse customer count
    customers_str = structured_extraction.get("customers")
    if customers_str:
        try:
            # Extract first number from string
            import re
            match = re.search(r'[\d,]+', customers_str)
            if match:
                metrics["customers"] = int(match.group().replace(",", ""))
        except (ValueError, AttributeError):
            pass
    
    # Calculate ARPU if we have ARR and customers
    if "arr" in metrics and "customers" in metrics and metrics["customers"] > 0:
        metrics["arpu_monthly"] = round(metrics["arr"] / metrics["customers"] / 12, 2)
    
    return metrics


# ---------------------------------------------------------------------------
# Financial Reasoning Engine — pre-AI logic layer
# ---------------------------------------------------------------------------
# These functions compute hard financial signals BEFORE the AI agents run.
# The results are injected into the agent context so the LLM doesn't have to
# do math (which it's bad at).

def compute_financial_signals(structured_extraction: dict) -> dict:
    """Compute all financial signals from structured extraction data.
    
    This is the core financial reasoning engine. It runs deterministic
    calculations that the AI agents would otherwise get wrong.
    
    Returns a dict of signals with verdicts that get injected into agent context.
    """
    import re
    signals = {}
    metrics = extract_financial_metrics(structured_extraction)
    
    # --- Parse additional metrics from key_metrics citations ---
    key_metrics = structured_extraction.get("key_metrics", [])
    growth_str = structured_extraction.get("growth", "")
    
    # Extract NRR
    nrr = None
    for m in key_metrics:
        text = m.get("text", "") if isinstance(m, dict) else str(m)
        nrr_match = re.search(r'(\d+(?:\.\d+)?)\s*%?\s*(?:NRR|Net\s+Revenue\s+Retention)', text, re.IGNORECASE)
        if nrr_match:
            nrr = float(nrr_match.group(1))
            break
    if not nrr and growth_str:
        nrr_match = re.search(r'(\d+(?:\.\d+)?)\s*%?\s*NRR', growth_str, re.IGNORECASE)
        if nrr_match:
            nrr = float(nrr_match.group(1))
    
    # Extract CAC
    cac = None
    for m in key_metrics:
        text = m.get("text", "") if isinstance(m, dict) else str(m)
        cac_match = re.search(r'CAC[:\s]*\$?([\d,.]+)\s*([KkMm])?', text, re.IGNORECASE)
        if cac_match:
            cac = parse_currency_string(f"${cac_match.group(1)}{cac_match.group(2) or ''}")
            break
    
    # Extract ACV
    acv = None
    for m in key_metrics:
        text = m.get("text", "") if isinstance(m, dict) else str(m)
        acv_match = re.search(r'ACV[:\s]*\$?([\d,.]+)\s*([KkMm])?', text, re.IGNORECASE)
        if acv_match:
            acv = parse_currency_string(f"${acv_match.group(1)}{acv_match.group(2) or ''}")
            break
    # Fallback: compute ACV from ARR / customers
    if not acv and metrics.get("arr") and metrics.get("customers") and metrics["customers"] > 0:
        acv = metrics["arr"] / metrics["customers"]
    
    # Extract LTV:CAC ratio
    ltv_cac = None
    for m in key_metrics:
        text = m.get("text", "") if isinstance(m, dict) else str(m)
        ltv_match = re.search(r'(\d+(?:\.\d+)?)\s*[x×]\s*LTV[:/]CAC', text, re.IGNORECASE)
        if ltv_match:
            ltv_cac = float(ltv_match.group(1))
            break
    
    # --- CAC vs ACV Analysis ---
    if cac and acv and acv > 0:
        ratio = round(cac / acv, 2)
        if ratio < 0.2:
            verdict = "EXCELLENT"
            risk = "none"
        elif ratio < 0.5:
            verdict = "GOOD"
            risk = "low"
        elif ratio < 1.0:
            verdict = "ACCEPTABLE"
            risk = "medium"
        else:
            verdict = "PROBLEMATIC"
            risk = "high"
        signals["cac_acv"] = {
            "cac": format_currency(cac),
            "acv": format_currency(acv),
            "ratio": ratio,
            "verdict": verdict,
            "risk_level": risk,
            "summary": f"CAC/ACV ratio = {ratio} ({verdict}). "
                       f"CAC {format_currency(cac)} vs ACV {format_currency(acv)}."
        }
    elif cac and not acv:
        signals["cac_acv"] = {
            "cac": format_currency(cac),
            "acv": "Not disclosed",
            "ratio": None,
            "verdict": "UNKNOWN",
            "risk_level": "unknown",
            "summary": f"CAC is {format_currency(cac)} but ACV is not disclosed. Cannot evaluate unit economics."
        }
    
    # --- NRR Analysis ---
    if nrr:
        if nrr > 140:
            verdict = "EXCEPTIONAL"
            signal = "strong_expansion"
        elif nrr > 120:
            verdict = "ELITE"
            signal = "strong_expansion"
        elif nrr > 100:
            verdict = "HEALTHY"
            signal = "stable"
        else:
            verdict = "CONCERNING"
            signal = "contraction"
        signals["nrr"] = {
            "value": nrr,
            "verdict": verdict,
            "expansion_signal": signal,
            "summary": f"NRR = {nrr}% ({verdict}). "
                       + ("Top 1% of SaaS — exceptional expansion revenue." if nrr > 140
                          else "Top 5% of SaaS — elite retention." if nrr > 120
                          else "Healthy retention, customers staying." if nrr > 100
                          else "Net contraction — customers churning or downgrading.")
        }
    
    # --- LTV:CAC Analysis ---
    if ltv_cac:
        if ltv_cac > 30:
            verdict = "EXCEPTIONAL"
        elif ltv_cac > 10:
            verdict = "STRONG"
        elif ltv_cac > 3:
            verdict = "VIABLE"
        else:
            verdict = "WEAK"
        signals["ltv_cac"] = {
            "ratio": ltv_cac,
            "verdict": verdict,
            "summary": f"LTV:CAC = {ltv_cac}x ({verdict})."
        }
    
    # --- Payback Period ---
    if cac and metrics.get("arpu_monthly") and metrics["arpu_monthly"] > 0:
        payback = round(cac / metrics["arpu_monthly"], 1)
        if payback < 12:
            verdict = "EXCELLENT"
        elif payback < 18:
            verdict = "GOOD"
        elif payback < 24:
            verdict = "ACCEPTABLE"
        else:
            verdict = "SLOW"
        signals["payback_period"] = {
            "months": payback,
            "verdict": verdict,
            "summary": f"CAC payback = {payback} months ({verdict})."
        }
    
    # --- Revenue Multiple (if valuation disclosed) ---
    arr = metrics.get("arr")
    funding_ask = structured_extraction.get("funding_ask")
    if arr and funding_ask:
        ask_val = parse_currency_string(funding_ask)
        if ask_val:
            # Rough implied valuation = 5x the raise (typical Series A)
            implied_val = ask_val * 5
            multiple = round(implied_val / arr, 1)
            signals["revenue_multiple"] = {
                "implied_valuation": format_currency(implied_val),
                "arr": format_currency(arr),
                "multiple": multiple,
                "summary": f"Implied ~{multiple}x ARR multiple."
                           + (" Aggressive." if multiple > 50 else " Reasonable." if multiple < 30 else " High but defensible if growth is strong.")
            }
    
    return signals


def format_financial_context(signals: dict) -> str:
    """Format financial signals into a text block for injection into agent prompts.
    
    This text is prepended to the agent context so the AI doesn't have to
    compute these numbers itself.
    """
    if not signals:
        return ""
    
    lines = ["## Pre-Computed Financial Analysis (TRUST THESE NUMBERS — do not recalculate)"]
    
    for key, data in signals.items():
        summary = data.get("summary", "")
        if summary:
            lines.append(f"- {summary}")
    
    lines.append("")
    lines.append("IMPORTANT: The above calculations are mathematically verified. "
                 "Use them directly in your analysis. Do NOT override with your own math.")
    
    return "\n".join(lines)
