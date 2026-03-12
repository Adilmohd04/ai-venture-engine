"""Risk Engine — detects and categorizes risk signals from pitch and agent analyses.

This module provides a standalone RiskEngine class that wraps the RiskEngineAgent
from agents.py, adding overall risk level computation and severity aggregation.
"""

from models import DebateResult, ResearchResult, RiskAnalysis, RiskSignal


SEVERITY_WEIGHTS = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def compute_overall_risk_level(signals: list[RiskSignal]) -> str:
    """Compute overall risk level from individual signal severities.

    Returns one of: low, medium, high, critical.
    """
    if not signals:
        return "low"
    avg = sum(SEVERITY_WEIGHTS.get(s.severity, 2) for s in signals) / len(signals)
    if avg >= 3.5:
        return "critical"
    if avg >= 2.5:
        return "high"
    if avg >= 1.5:
        return "medium"
    return "low"


class RiskEngine:
    """High-level risk analysis that delegates LLM work to RiskEngineAgent."""

    def __init__(self, model: str, api_key: str):
        from agents import RiskEngineAgent
        self._agent = RiskEngineAgent(model, api_key)

    async def analyze_risks(
        self,
        pitch_text: str,
        research: ResearchResult,
        debate: DebateResult,
    ) -> RiskAnalysis:
        """Detect risk signals and return a complete RiskAnalysis."""
        analysis, _ = await self._agent.analyze_risks(pitch_text, research, debate)
        # Recompute overall risk level from parsed signals
        analysis.overall_risk_level = compute_overall_risk_level(analysis.signals)
        return analysis
