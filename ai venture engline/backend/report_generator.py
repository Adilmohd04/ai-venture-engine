"""Report Generator — creates shareable public reports from investment memos."""

import re
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from models import InvestmentMemo
from deal_breaker_detector import DealBreaker


class KeyStrength(BaseModel):
    """A single key strength."""
    rank: int = Field(ge=1, le=3)
    dimension: str
    description: str


class PublicReport(BaseModel):
    """Public report data structure."""
    analysis_id: str
    startup_name: str
    investor_readiness_overall: float = Field(ge=0, le=10)
    deal_breakers: list[DealBreaker]
    key_strengths: list[KeyStrength]
    created_at: str


class ReportGenerator:
    """Generates shareable public reports."""

    # Dimension display names
    DIMENSION_LABELS = {
        "market_potential": "Market Opportunity",
        "team_strength": "Team Strength",
        "product_differentiation": "Product Differentiation",
        "moat": "Defensibility",
        "traction": "Traction",
    }

    def generate_report(
        self, 
        memo: InvestmentMemo, 
        deal_breakers: list[DealBreaker]
    ) -> PublicReport:
        """Generate public report from memo and deal breakers.
        
        Args:
            memo: Complete investment memo
            deal_breakers: Top 3 deal breakers from DealBreakerDetector
            
        Returns:
            PublicReport with limited public data
        """
        # Extract startup name
        startup_name = self._extract_startup_name(memo)
        
        # Derive key strengths
        key_strengths = self._derive_key_strengths(memo)
        
        # Get investor readiness score
        investor_readiness = memo.investor_readiness.overall if memo.investor_readiness else memo.final_score
        
        return PublicReport(
            analysis_id=memo.analysis_id,
            startup_name=startup_name,
            investor_readiness_overall=round(investor_readiness, 1),
            deal_breakers=deal_breakers,
            key_strengths=key_strengths,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _extract_startup_name(self, memo: InvestmentMemo) -> str:
        """Extract startup name from memo."""
        # Try structured extraction first
        if memo.structured_extraction and memo.structured_extraction.startup_name:
            return memo.structured_extraction.startup_name
        
        # Try to extract from overview
        if memo.startup_overview:
            # Pattern: "X is building Y"
            match = re.match(r'^([^,]+?)\s+is\s+building', memo.startup_overview)
            if match:
                return match.group(1).strip()
            
            # Pattern: first capitalized word
            words = memo.startup_overview.split()
            for word in words:
                if word and word[0].isupper() and len(word) > 2:
                    return word
        
        return "Startup"

    def _derive_key_strengths(self, memo: InvestmentMemo) -> list[KeyStrength]:
        """Derive key strengths from high dimension scores and bull case.
        
        Returns:
            List of exactly 3 KeyStrength objects
        """
        strengths = []
        
        # Extract from high dimension scores (>7)
        score_breakdown = memo.score_breakdown.model_dump()
        for dimension, score in score_breakdown.items():
            if score > 7:
                description = self._format_strength_from_dimension(dimension, score, memo)
                strengths.append({
                    "dimension": dimension,
                    "score": score,
                    "description": description,
                })
        
        # Extract from bull case
        bull_strengths = self._extract_strengths_from_bull_case(memo.bull_case)
        for strength_desc in bull_strengths:
            strengths.append({
                "dimension": "competitive_advantage",
                "score": 8.0,  # Default high score for bull case strengths
                "description": strength_desc,
            })
        
        # Sort by score and take top 3
        strengths.sort(key=lambda x: x["score"], reverse=True)
        top_3 = strengths[:3]
        
        # If fewer than 3, include medium-high scores (6-7)
        if len(top_3) < 3:
            for dimension, score in score_breakdown.items():
                if 6 <= score <= 7 and dimension not in [s["dimension"] for s in top_3]:
                    description = self._format_strength_from_dimension(dimension, score, memo)
                    top_3.append({
                        "dimension": dimension,
                        "score": score,
                        "description": description,
                    })
                    if len(top_3) >= 3:
                        break
        
        # Ensure exactly 3 strengths
        while len(top_3) < 3:
            top_3.append({
                "dimension": "general_strength",
                "score": 6.0,
                "description": "Solid fundamentals with room for growth",
            })
        
        # Format as KeyStrength objects
        return [
            KeyStrength(
                rank=i + 1,
                dimension=s["dimension"],
                description=s["description"]
            )
            for i, s in enumerate(top_3[:3])
        ]

    def _format_strength_from_dimension(
        self, 
        dimension: str, 
        score: float, 
        memo: InvestmentMemo
    ) -> str:
        """Format a strength description from a high dimension score."""
        label = self.DIMENSION_LABELS.get(dimension, dimension.replace("_", " ").title())
        
        # Try to extract specific evidence from judge reasoning
        reasoning = memo.judge_reasoning
        
        # Look for dimension-specific evidence
        if dimension == "traction" and memo.structured_extraction:
            ext = memo.structured_extraction
            if ext.growth:
                return f"Strong {label}: {ext.growth} growth rate"
            if ext.arr:
                return f"Strong {label}: {ext.arr} ARR achieved"
            if ext.customers:
                return f"Strong {label}: {ext.customers} customers acquired"
        
        if dimension == "market_potential" and memo.market_size:
            tam = memo.market_size.tam
            if tam:
                return f"Large {label}: {tam} TAM"
        
        if dimension == "team_strength" and memo.structured_extraction:
            if memo.structured_extraction.founding_team:
                team = memo.structured_extraction.founding_team
                # Truncate if too long
                if len(team) > 80:
                    team = team[:77] + "..."
                return f"Experienced {label}: {team}"
        
        # Extract from judge reasoning
        sentences = reasoning.split(".")
        for sent in sentences:
            if dimension.replace("_", " ") in sent.lower() or label.lower() in sent.lower():
                sent = sent.strip()
                if len(sent) > 100:
                    sent = sent[:97] + "..."
                return f"{label}: {sent}"
        
        # Default strength description
        return f"Strong {label} ({score:.1f}/10)"

    def _extract_strengths_from_bull_case(self, bull_case: str) -> list[str]:
        """Extract specific strengths from bull case arguments.
        
        Returns:
            List of strength descriptions
        """
        if not bull_case:
            return []
        
        strengths = []
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', bull_case)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 20:
                continue
            
            # Look for strength indicators
            strength_indicators = [
                "strong", "advantage", "unique", "differentiat", "lead",
                "proven", "experienced", "traction", "growth", "opportunity"
            ]
            
            if any(indicator in sentence.lower() for indicator in strength_indicators):
                # Clean up and truncate
                if len(sentence) > 100:
                    sentence = sentence[:97] + "..."
                strengths.append(sentence)
                
                if len(strengths) >= 2:
                    break
        
        return strengths
