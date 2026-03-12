"""Deal Breaker Detector — identifies top 3 instant rejection signals from investment memos."""

import re
from typing import Optional

from pydantic import BaseModel, Field

from models import InvestmentMemo, RiskSignal


class DealBreaker(BaseModel):
    """A single deal breaker signal."""
    rank: int = Field(ge=1, le=3)
    category: str
    description: str


class DealBreakerDetector:
    """Detects top 3 instant rejection signals from investment memo."""

    # Severity weights for priority scoring
    SEVERITY_WEIGHTS = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
    }

    # Category weights for priority scoring
    CATEGORY_WEIGHTS = {
        "weak_moat": 5,
        "market_saturation": 4,
        "unclear_business_model": 4,
        "platform_dependency": 3,
        "ai_commoditization": 3,
        "regulatory_risk": 2,
        "scaling_challenges": 2,
        "founder_domain_mismatch": 2,
        "low_willingness_to_pay": 2,
        "concentration_risk": 2,
    }

    # Category display names
    CATEGORY_LABELS = {
        "weak_moat": "Weak Moat",
        "market_saturation": "Market Saturation",
        "unclear_business_model": "Unclear Business Model",
        "platform_dependency": "Platform Dependency",
        "ai_commoditization": "AI Commoditization",
        "regulatory_risk": "Regulatory Risk",
        "scaling_challenges": "Scaling Challenges",
        "founder_domain_mismatch": "Team Domain Mismatch",
        "low_willingness_to_pay": "Low Willingness to Pay",
        "concentration_risk": "Concentration Risk",
    }

    def detect_deal_breakers(self, memo: InvestmentMemo) -> list[DealBreaker]:
        """Analyze memo and return top 3 deal breakers ranked by priority.
        
        Args:
            memo: Complete investment memo with risks, scores, and debate
            
        Returns:
            List of exactly 3 DealBreaker objects ranked by priority
        """
        candidates = []

        # Extract from risk signals
        for risk in memo.risk_signals.signals:
            priority = self._calculate_priority(risk)
            description = self._format_deal_breaker_from_risk(risk)
            candidates.append({
                "priority": priority,
                "category": risk.category,
                "description": description,
            })

        # Extract from low dimension scores (< 4)
        score_breakdown = memo.score_breakdown.model_dump()
        for dimension, score in score_breakdown.items():
            if score < 4:
                priority = (3 * 10) + (4 * 5) + (2 * 3)  # high severity, high category weight
                description = self._format_deal_breaker_from_low_score(dimension, score, memo)
                candidates.append({
                    "priority": priority,
                    "category": dimension,
                    "description": description,
                })

        # Extract from bear case arguments
        bear_concerns = self._extract_concerns_from_bear_case(memo.bear_case)
        for concern in bear_concerns:
            priority = (2 * 10) + (3 * 5) + (1 * 3)  # medium severity
            candidates.append({
                "priority": priority,
                "category": "competitive_threat",
                "description": concern,
            })

        # Sort by priority and take top 3
        candidates.sort(key=lambda x: x["priority"], reverse=True)
        top_3 = candidates[:3]

        # If fewer than 3, pad with medium-severity concerns
        while len(top_3) < 3 and len(candidates) > len(top_3):
            top_3.append(candidates[len(top_3)])

        # Ensure we always have exactly 3
        while len(top_3) < 3:
            top_3.append({
                "priority": 0,
                "category": "general_concern",
                "description": "Further due diligence required on business fundamentals",
            })

        # Format as DealBreaker objects
        return [
            DealBreaker(
                rank=i + 1,
                category=c["category"],
                description=c["description"]
            )
            for i, c in enumerate(top_3)
        ]

    def _calculate_priority(self, risk: RiskSignal) -> float:
        """Calculate priority score for a risk signal.
        
        Priority = (severity_weight * 10) + (category_weight * 5) + (evidence_quality * 3)
        """
        severity_weight = self.SEVERITY_WEIGHTS.get(risk.severity, 1)
        category_weight = self.CATEGORY_WEIGHTS.get(risk.category, 2)
        evidence_quality = self._assess_evidence_quality(risk.evidence)
        
        return (severity_weight * 10) + (category_weight * 5) + (evidence_quality * 3)

    def _assess_evidence_quality(self, evidence: str) -> int:
        """Assess evidence quality based on specificity.
        
        Returns:
            3 if specific metrics or competitor names present, otherwise 1
        """
        if not evidence:
            return 1
        
        # Check for specific indicators: numbers, percentages, dollar amounts, competitor names
        has_numbers = bool(re.search(r'\d+', evidence))
        has_currency = bool(re.search(r'\$|USD|revenue|funding', evidence, re.IGNORECASE))
        has_percentage = bool(re.search(r'\d+%', evidence))
        has_proper_nouns = bool(re.search(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', evidence))
        
        # High quality if at least 2 indicators present
        indicators = sum([has_numbers, has_currency, has_percentage, has_proper_nouns])
        return 3 if indicators >= 2 else 1

    def _format_deal_breaker_from_risk(self, risk: RiskSignal) -> str:
        """Format a deal breaker description from a risk signal."""
        category_label = self.CATEGORY_LABELS.get(risk.category, risk.category.replace("_", " ").title())
        
        # Use the risk description directly, truncate if too long
        description = risk.description
        if len(description) > 150:
            description = description[:147] + "..."
        
        return f"{category_label}: {description}"

    def _format_deal_breaker_from_low_score(
        self, 
        dimension: str, 
        score: float, 
        memo: InvestmentMemo
    ) -> str:
        """Format a deal breaker description from a low dimension score."""
        dimension_labels = {
            "market_potential": "Market Potential",
            "team_strength": "Team Strength",
            "product_differentiation": "Product Differentiation",
            "moat": "Defensibility",
            "traction": "Traction",
        }
        
        label = dimension_labels.get(dimension, dimension.replace("_", " ").title())
        
        # Try to extract specific reason from judge reasoning
        reasoning = memo.judge_reasoning.lower()
        if dimension == "moat" and "moat" in reasoning:
            # Extract sentence containing "moat"
            sentences = reasoning.split(".")
            for sent in sentences:
                if "moat" in sent:
                    return f"Weak {label}: {sent.strip().capitalize()}"
        
        return f"Low {label} Score ({score:.1f}/10): Insufficient evidence of strong {label.lower()}"

    def _extract_concerns_from_bear_case(self, bear_case: str) -> list[str]:
        """Extract specific concerns from bear case arguments.
        
        Returns:
            List of concern strings extracted from bear case
        """
        if not bear_case:
            return []
        
        concerns = []
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', bear_case)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 20:
                continue
            
            # Look for concern indicators
            concern_indicators = [
                "risk", "concern", "challenge", "problem", "issue",
                "competitor", "threat", "difficult", "unclear", "weak"
            ]
            
            if any(indicator in sentence.lower() for indicator in concern_indicators):
                # Clean up and truncate
                if len(sentence) > 120:
                    sentence = sentence[:117] + "..."
                concerns.append(sentence)
                
                if len(concerns) >= 3:
                    break
        
        return concerns
