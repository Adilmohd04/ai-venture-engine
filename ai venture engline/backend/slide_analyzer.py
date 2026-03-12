"""Slide-Level Deck Analyzer — provides specific feedback for each slide."""

import re
from typing import Optional

from pydantic import BaseModel

from models import InvestmentMemo


class SlideFeedback(BaseModel):
    """Feedback for a single slide."""
    slide_number: int
    slide_title: str
    slide_type: str  # Problem, Solution, Market, Team, Traction, etc.
    content_summary: str
    problem: Optional[str] = None  # What's wrong with this slide
    investor_reaction: str  # How investors perceive this
    fix_suggestion: str  # Specific actionable fix
    severity: str  # critical, high, medium, low


class SlideAnalyzer:
    """Analyzes individual slides and provides specific feedback."""
    
    # Slide type classification keywords
    SLIDE_TYPES = {
        "problem": ["problem", "pain point", "challenge", "issue", "gap"],
        "solution": ["solution", "product", "platform", "technology", "how it works"],
        "market": ["market", "tam", "sam", "som", "opportunity", "addressable"],
        "business_model": ["business model", "revenue", "pricing", "monetization", "unit economics"],
        "traction": ["traction", "growth", "metrics", "customers", "revenue", "arr", "mrr"],
        "team": ["team", "founders", "leadership", "experience", "background"],
        "competition": ["competition", "competitive", "landscape", "alternatives", "vs"],
        "go_to_market": ["go to market", "gtm", "sales", "marketing", "distribution", "channels"],
        "financials": ["financials", "projections", "forecast", "runway", "burn"],
        "ask": ["ask", "raising", "funding", "investment", "round"],
    }
    
    def analyze_slides(
        self, 
        slides_dict: dict[int, str],
        memo: InvestmentMemo
    ) -> list[SlideFeedback]:
        """Analyze each slide and generate specific feedback.
        
        Args:
            slides_dict: Dict mapping page numbers to slide text
            memo: Complete investment memo with analysis
            
        Returns:
            List of SlideFeedback objects, one per slide
        """
        feedbacks = []
        
        for page_num, slide_text in slides_dict.items():
            if not slide_text.strip():
                continue
            
            # Extract slide title (first line or first sentence)
            title = self._extract_title(slide_text)
            
            # Classify slide type
            slide_type = self._classify_slide(slide_text, title)
            
            # Generate content summary
            summary = self._summarize_content(slide_text)
            
            # Generate feedback based on slide type and memo analysis
            problem, reaction, fix, severity = self._generate_feedback(
                slide_type, slide_text, title, memo
            )
            
            feedbacks.append(SlideFeedback(
                slide_number=page_num,
                slide_title=title,
                slide_type=slide_type,
                content_summary=summary,
                problem=problem,
                investor_reaction=reaction,
                fix_suggestion=fix,
                severity=severity
            ))
        
        return feedbacks
    
    def _extract_title(self, slide_text: str) -> str:
        """Extract slide title from text."""
        lines = [line.strip() for line in slide_text.split('\n') if line.strip()]
        if not lines:
            return "Untitled Slide"
        
        # First line is usually the title
        title = lines[0]
        
        # Truncate if too long
        if len(title) > 60:
            title = title[:57] + "..."
        
        return title
    
    def _classify_slide(self, slide_text: str, title: str) -> str:
        """Classify slide type based on content."""
        text_lower = (title + " " + slide_text).lower()
        
        # Score each type
        scores = {}
        for slide_type, keywords in self.SLIDE_TYPES.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                scores[slide_type] = score
        
        if not scores:
            return "other"
        
        # Return type with highest score
        return max(scores, key=scores.get)
    
    def _summarize_content(self, slide_text: str) -> str:
        """Create brief summary of slide content."""
        # Take first 150 characters
        summary = slide_text.strip()[:150]
        if len(slide_text) > 150:
            summary += "..."
        return summary
    
    def _generate_feedback(
        self,
        slide_type: str,
        slide_text: str,
        title: str,
        memo: InvestmentMemo
    ) -> tuple[Optional[str], str, str, str]:
        """Generate problem, reaction, fix, and severity for a slide.
        
        Returns:
            (problem, investor_reaction, fix_suggestion, severity)
        """
        # Default feedback
        problem = None
        reaction = "Slide appears adequate"
        fix = "Consider adding more specific data and evidence"
        severity = "low"
        
        # Type-specific feedback
        if slide_type == "market":
            problem, reaction, fix, severity = self._analyze_market_slide(
                slide_text, title, memo
            )
        elif slide_type == "traction":
            problem, reaction, fix, severity = self._analyze_traction_slide(
                slide_text, title, memo
            )
        elif slide_type == "problem":
            problem, reaction, fix, severity = self._analyze_problem_slide(
                slide_text, title, memo
            )
        elif slide_type == "business_model":
            problem, reaction, fix, severity = self._analyze_business_model_slide(
                slide_text, title, memo
            )
        elif slide_type == "team":
            problem, reaction, fix, severity = self._analyze_team_slide(
                slide_text, title, memo
            )
        elif slide_type == "competition":
            problem, reaction, fix, severity = self._analyze_competition_slide(
                slide_text, title, memo
            )
        
        return problem, reaction, fix, severity
    
    def _analyze_market_slide(
        self, slide_text: str, title: str, memo: InvestmentMemo
    ) -> tuple[Optional[str], str, str, str]:
        """Analyze market/TAM slide."""
        text_lower = slide_text.lower()
        
        # Check for sources
        has_source = any(
            term in text_lower 
            for term in ["source:", "gartner", "mckinsey", "idc", "forrester", "statista"]
        )
        
        # Check for TAM/SAM/SOM breakdown
        has_breakdown = "sam" in text_lower or "som" in text_lower
        
        if not has_source:
            return (
                "TAM claim lacks credible source",
                "Investors will question the market size validity",
                f"Add source citation (e.g., 'Source: Gartner 2024'). Research shows TAM is {memo.market_size.tam}",
                "high"
            )
        
        if not has_breakdown:
            return (
                "Missing SAM/SOM breakdown",
                "Investors want to see serviceable and obtainable market, not just TAM",
                f"Add SAM ({memo.market_size.sam}) and SOM ({memo.market_size.som}) with clear definitions",
                "medium"
            )
        
        return (
            None,
            "Market sizing appears credible with sources",
            "Consider adding growth rate projections (CAGR)",
            "low"
        )
    
    def _analyze_traction_slide(
        self, slide_text: str, title: str, memo: InvestmentMemo
    ) -> tuple[Optional[str], str, str, str]:
        """Analyze traction/metrics slide."""
        text_lower = slide_text.lower()
        
        # Check for growth metrics
        has_growth = any(
            term in text_lower 
            for term in ["growth", "mom", "yoy", "%", "increase"]
        )
        
        # Check for specific numbers
        has_numbers = bool(re.search(r'\d+', slide_text))
        
        if not has_numbers:
            return (
                "No specific metrics shown",
                "Investors need concrete numbers, not vague claims",
                "Add specific metrics: ARR, MRR, customer count, or growth rate with actual numbers",
                "critical"
            )
        
        if not has_growth:
            return (
                "Missing growth rate",
                "Static numbers don't show momentum",
                "Add MoM or YoY growth percentage to show trajectory",
                "high"
            )
        
        # Check if growth aligns with memo
        if memo.structured_extraction and memo.structured_extraction.growth:
            return (
                None,
                f"Strong traction: {memo.structured_extraction.growth}",
                "Consider adding cohort retention or unit economics",
                "low"
            )
        
        return (
            None,
            "Traction metrics present",
            "Add comparison to industry benchmarks",
            "low"
        )
    
    def _analyze_problem_slide(
        self, slide_text: str, title: str, memo: InvestmentMemo
    ) -> tuple[Optional[str], str, str, str]:
        """Analyze problem slide."""
        text_lower = slide_text.lower()
        
        # Check for quantification
        has_numbers = bool(re.search(r'\$\d+|\d+%|\d+[BMK]', slide_text))
        
        # Check for urgency indicators
        has_urgency = any(
            term in text_lower 
            for term in ["cost", "waste", "loss", "inefficient", "broken", "painful"]
        )
        
        if not has_numbers:
            return (
                "Problem not quantified",
                "Investors want to see the economic impact",
                "Add dollar amount of problem (e.g., '$50B wasted annually on X')",
                "high"
            )
        
        if not has_urgency:
            return (
                "Problem lacks urgency",
                "Investors question if this is a 'nice-to-have' vs 'must-have'",
                "Emphasize pain points: costs, time wasted, or risks of not solving",
                "medium"
            )
        
        return (
            None,
            "Problem is well-articulated",
            "Consider adding customer quotes or case studies",
            "low"
        )
    
    def _analyze_business_model_slide(
        self, slide_text: str, title: str, memo: InvestmentMemo
    ) -> tuple[Optional[str], str, str, str]:
        """Analyze business model slide."""
        text_lower = slide_text.lower()
        
        # Check for pricing
        has_pricing = any(
            term in text_lower 
            for term in ["$", "price", "pricing", "subscription", "fee"]
        )
        
        # Check for unit economics
        has_unit_econ = any(
            term in text_lower 
            for term in ["cac", "ltv", "margin", "payback"]
        )
        
        if not has_pricing:
            return (
                "No pricing information",
                "Investors need to understand revenue model",
                "Add pricing tiers or average contract value (ACV)",
                "high"
            )
        
        if not has_unit_econ:
            return (
                "Missing unit economics",
                "Investors want to see CAC, LTV, and payback period",
                "Add: CAC = $X, LTV = $Y, LTV/CAC ratio = Z, Payback = N months",
                "high"
            )
        
        return (
            None,
            "Business model is clear",
            "Consider showing revenue projections by segment",
            "low"
        )
    
    def _analyze_team_slide(
        self, slide_text: str, title: str, memo: InvestmentMemo
    ) -> tuple[Optional[str], str, str, str]:
        """Analyze team slide."""
        text_lower = slide_text.lower()
        
        # Check for relevant experience
        has_experience = any(
            term in text_lower 
            for term in ["ex-", "former", "years", "led", "built", "scaled"]
        )
        
        # Check for domain expertise
        has_domain = memo.startup_info.industry.lower() in text_lower if memo.startup_info.industry else False
        
        if not has_experience:
            return (
                "Team credentials not highlighted",
                "Investors invest in people - show track record",
                "Add: 'Ex-Google PM', '10 years in fintech', 'Built $50M ARR company'",
                "high"
            )
        
        if not has_domain:
            return (
                "Domain expertise unclear",
                "Investors want to see industry-specific experience",
                f"Highlight team's experience in {memo.startup_info.industry}",
                "medium"
            )
        
        return (
            None,
            "Team credentials are strong",
            "Consider adding advisor logos or notable investors",
            "low"
        )
    
    def _analyze_competition_slide(
        self, slide_text: str, title: str, memo: InvestmentMemo
    ) -> tuple[Optional[str], str, str, str]:
        """Analyze competition slide."""
        # Check if competitors from memo are mentioned
        mentioned_competitors = []
        for comp in memo.competitor_landscape[:3]:
            if comp.name.lower() in slide_text.lower():
                mentioned_competitors.append(comp.name)
        
        if len(mentioned_competitors) < 2:
            comp_names = ", ".join([c.name for c in memo.competitor_landscape[:3]])
            return (
                "Missing key competitors",
                "Investors will notice if you ignore major players",
                f"Add these competitors to your analysis: {comp_names}",
                "high"
            )
        
        # Check for differentiation
        has_differentiation = any(
            term in slide_text.lower() 
            for term in ["unique", "only", "first", "differentiat", "advantage"]
        )
        
        if not has_differentiation:
            return (
                "Differentiation not clear",
                "Investors need to understand your unique value",
                "Add: 'Only solution that X' or 'First to market with Y'",
                "medium"
            )
        
        return (
            None,
            "Competitive positioning is clear",
            "Consider adding competitive matrix or feature comparison",
            "low"
        )
