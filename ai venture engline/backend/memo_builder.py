"""Memo Builder — compiles all agent outputs into a structured VC investment memo."""

import json
import re
from datetime import datetime, timezone

from models import (
    Competitor,
    InvestmentMemo,
    InvestorReadiness,
    JudgeVerdict,
    MarketSize,
    ResearchResult,
    RiskAnalysis,
    ScoreBreakdown,
    score_to_verdict,
)


def parse_judge_verdict(judge_text: str) -> JudgeVerdict:
    """Parse the Judge agent's raw output into a structured JudgeVerdict.

    The judge is prompted to include a JSON block at the end of its output.
    This function extracts that JSON and falls back to defaults if parsing fails.
    """
    # Try to find JSON in a code block
    json_match = re.search(r"```json\s*([\s\S]*?)```", judge_text)
    if json_match:
        raw_json = json_match.group(1).strip()
    else:
        # Try to find a bare JSON object
        json_match = re.search(r"\{[\s\S]*\"final_score\"[\s\S]*\}", judge_text)
        raw_json = json_match.group(0) if json_match else ""

    try:
        data = json.loads(raw_json)
        scores_data = data.get("scores", {})
        scores = ScoreBreakdown(
            market_potential=_clamp(scores_data.get("market_potential", 5)),
            team_strength=_clamp(scores_data.get("team_strength", 5)),
            product_differentiation=_clamp(scores_data.get("product_differentiation", 5)),
            moat=_clamp(scores_data.get("moat", 5)),
            traction=_clamp(scores_data.get("traction", 5)),
        )
        final_score = _clamp(data.get("final_score", 5))
        verdict = score_to_verdict(final_score)
        reasoning = data.get("reasoning", judge_text[:500])
    except (json.JSONDecodeError, KeyError, TypeError):
        scores = ScoreBreakdown(
            market_potential=5, team_strength=5,
            product_differentiation=5, moat=5, traction=5,
        )
        final_score = 5.0
        verdict = score_to_verdict(final_score)
        reasoning = judge_text[:500] if judge_text else "Unable to parse judge verdict."

    return JudgeVerdict(
        scores=scores,
        final_score=final_score,
        verdict=verdict,
        reasoning=reasoning,
    )


def _clamp(value: float, lo: float = 0, hi: float = 10) -> float:
    """Clamp a numeric value to [lo, hi]."""
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return 5.0


class MemoBuilder:
    """Compiles all agent outputs into a final InvestmentMemo."""

    @staticmethod
    def _compute_investor_readiness(
        research: ResearchResult,
        judge_verdict: JudgeVerdict,
        risks: RiskAnalysis,
    ) -> InvestorReadiness:
        """Derive an Investor Readiness Score from existing pipeline data."""
        ext = research.structured_extraction

        # Deck Quality: how complete is the pitch deck info?
        deck_fields = [
            ext.tam, ext.sam, ext.som, ext.arr, ext.mrr,
            ext.customers, ext.growth, ext.funding_ask, ext.founding_team,
        ] if ext else []
        filled = sum(1 for f in deck_fields if f)
        deck_quality = min(10, (filled / max(len(deck_fields), 1)) * 10 + 1)
        # Penalize for missing info
        missing_penalty = min(3, len(research.missing_info) * 0.5)
        deck_quality = max(0, deck_quality - missing_penalty)

        # Market Opportunity: from judge scores
        market_opportunity = judge_verdict.scores.market_potential

        # Team Credibility: from judge scores
        team_credibility = judge_verdict.scores.team_strength

        # Business Model Clarity: blend of traction + moat, penalized by unclear_biz risk
        biz_clarity = (judge_verdict.scores.traction + judge_verdict.scores.moat) / 2
        for sig in risks.signals:
            if sig.category == "unclear_business_model" and sig.severity in ("high", "critical"):
                biz_clarity = max(0, biz_clarity - 2)
                break

        # Defensibility: moat + product differentiation, penalized by weak_moat/ai_commoditization
        defensibility = (judge_verdict.scores.moat + judge_verdict.scores.product_differentiation) / 2
        for sig in risks.signals:
            if sig.category in ("weak_moat", "ai_commoditization") and sig.severity in ("high", "critical"):
                defensibility = max(0, defensibility - 1.5)

        overall = round((deck_quality + market_opportunity + team_credibility + biz_clarity + defensibility) / 5, 1)

        return InvestorReadiness(
            deck_quality=round(deck_quality, 1),
            market_opportunity=round(market_opportunity, 1),
            team_credibility=round(team_credibility, 1),
            business_model_clarity=round(biz_clarity, 1),
            defensibility=round(defensibility, 1),
            overall=overall,
        )

    @staticmethod
    def _compute_top_concerns(
        risks: RiskAnalysis,
        judge_verdict: JudgeVerdict,
    ) -> list[str]:
        """Extract top 3 investor concerns from risk signals, ranked by severity."""
        severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        category_labels = {
            "market_saturation": "Heavy market competition",
            "weak_moat": "Weak defensibility",
            "founder_domain_mismatch": "Team lacks domain expertise",
            "unclear_business_model": "Unclear path to profitability",
            "regulatory_risk": "Regulatory exposure",
            "scaling_challenges": "Scaling difficulty",
            "platform_dependency": "Platform dependency risk",
            "ai_commoditization": "AI commoditization risk",
            "low_willingness_to_pay": "Low willingness to pay",
            "concentration_risk": "Revenue concentration risk",
        }
        sorted_signals = sorted(
            risks.signals,
            key=lambda s: severity_rank.get(s.severity, 0),
            reverse=True,
        )
        concerns: list[str] = []
        seen_cats: set[str] = set()
        for sig in sorted_signals:
            if sig.category in seen_cats:
                continue
            seen_cats.add(sig.category)
            label = category_labels.get(sig.category, sig.category.replace("_", " ").title())
            # Use the signal's own description for specificity
            short_desc = sig.description
            if len(short_desc) > 80:
                short_desc = short_desc[:77] + "..."
            concerns.append(f"{label}: {short_desc}")
            if len(concerns) >= 3:
                break
        return concerns

    @staticmethod
    def _format_currency(val: str) -> str:
        """Format raw numbers like 10000000 into $10M."""
        if not val:
            return val
        if any(c in val for c in "$BMKbmk"):
            return val
        try:
            num = float(val.replace(",", ""))
        except (ValueError, TypeError):
            return val
        if num >= 1e9:
            f = num / 1e9
            return f"${f:.0f}B" if f == int(f) else f"${f:.1f}B"
        if num >= 1e6:
            f = num / 1e6
            return f"${f:.0f}M" if f == int(f) else f"${f:.1f}M"
        if num >= 1e3:
            return f"${num / 1e3:.0f}K"
        return f"${num:,.0f}"

    def build_memo(
        self,
        analysis_id: str,
        research: ResearchResult,
        bull_case: str,
        bear_case: str,
        bull_rebuttal: str,
        bear_rebuttal: str,
        risks: RiskAnalysis,
        judge_verdict: JudgeVerdict,
    ) -> InvestmentMemo:
        """Assemble the complete investment memo from all pipeline outputs."""
        overview = (
            f"{research.startup_info.name} is building {research.startup_info.product} "
            f"in the {research.startup_info.industry} industry."
        )
        if research.startup_info.stage:
            overview += f" Stage: {research.startup_info.stage}."
        if research.startup_info.ask:
            ask_formatted = self._format_currency(research.startup_info.ask)
            overview += f" Seeking: {ask_formatted}."

        readiness = self._compute_investor_readiness(research, judge_verdict, risks)
        top_concerns = self._compute_top_concerns(risks, judge_verdict)

        return InvestmentMemo(
            analysis_id=analysis_id,
            investor_readiness=readiness,
            top_investor_concerns=top_concerns,
            startup_overview=overview,
            structured_extraction=research.structured_extraction,
            claim_verifications=research.claim_verifications,
            market_size=research.market_size,
            competitor_landscape=research.competitors,
            ecosystem_map=research.ecosystem_map,
            market_benchmark=research.market_benchmark,
            bull_case=bull_case,
            bear_case=bear_case,
            bull_rebuttal=bull_rebuttal,
            bear_rebuttal=bear_rebuttal,
            risk_signals=risks,
            score_breakdown=judge_verdict.scores,
            final_score=judge_verdict.final_score,
            verdict=judge_verdict.verdict,
            judge_reasoning=judge_verdict.reasoning,
            missing_info=research.missing_info,
            confidence_scores=research.confidence_scores,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
