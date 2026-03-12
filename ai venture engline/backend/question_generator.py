"""Question Generator — generates tough investor questions from investment memos."""

import re
from typing import Optional

from models import InvestmentMemo, Competitor


class QuestionGenerator:
    """Generates investor questions from investment memo."""

    # Question templates by category
    TEMPLATES = {
        "competitive_threat": [
            "Why can't {competitor} add this feature in 6 months?",
            "How will you compete against {competitor} with {funding}?",
            "{competitor} has {advantage}. What's your counter-strategy?",
        ],
        "business_model": [
            "What's your CAC and LTV, and when do you reach payback?",
            "How do you plan to monetize this without {concern}?",
            "Your unit economics show {metric}. How will you improve this?",
        ],
        "market_risk": [
            "How will you differentiate in a market with {count} competitors?",
            "What happens if {platform} changes their pricing or API?",
            "The market is {condition}. Why now?",
        ],
        "team_capability": [
            "Your team lacks {domain} experience. How will you overcome this?",
            "Who on your team has built {capability} before?",
        ],
        "platform_dependency": [
            "What happens if {platform} changes their API or pricing?",
            "How dependent are you on {platform} for core functionality?",
        ],
    }

    def generate_questions(self, memo: InvestmentMemo) -> list[str]:
        """Generate 5-8 startup-specific investor questions.
        
        Args:
            memo: Complete investment memo with risks, competitors, and debate
            
        Returns:
            List of 5-8 questions, each ≤150 characters
        """
        questions = []
        
        # 1. Competitive threat questions
        comp_questions = self._generate_competitive_questions(memo)
        questions.extend(comp_questions)
        
        # 2. Business model questions
        biz_questions = self._generate_business_model_questions(memo)
        questions.extend(biz_questions)
        
        # 3. Market risk questions
        market_questions = self._generate_market_risk_questions(memo)
        questions.extend(market_questions)
        
        # 4. Team capability questions
        team_questions = self._generate_team_questions(memo)
        questions.extend(team_questions)
        
        # 5. Platform dependency questions
        platform_questions = self._generate_platform_questions(memo)
        questions.extend(platform_questions)
        
        # 6. Extract from bear case
        bear_questions = self._extract_questions_from_bear_case(memo.bear_case)
        questions.extend(bear_questions)
        
        # Ensure 5-8 questions
        questions = questions[:8]
        
        # If fewer than 5, add fallback questions
        if len(questions) < 5:
            fallback = self._generate_fallback_questions(memo)
            questions.extend(fallback)
        
        # Final trim to 8 max
        return questions[:8]

    def _generate_competitive_questions(self, memo: InvestmentMemo) -> list[str]:
        """Generate questions about competitive threats."""
        questions = []
        
        if not memo.competitor_landscape:
            return questions
        
        # Find strongest competitor (highest funding or first mentioned)
        strongest = self._get_strongest_competitor(memo.competitor_landscape)
        
        if strongest:
            # Extract competitor advantage
            advantage = "significant market share"
            if strongest.funding:
                advantage = f"{strongest.funding} in funding"
            elif strongest.differentiator:
                advantage = strongest.differentiator
            
            question = f"Why can't {strongest.name} add this feature in 6 months?"
            if len(question) <= 150:
                questions.append(question)
            
            # Second competitive question
            if len(memo.competitor_landscape) >= 3:
                question = f"How will you differentiate against {strongest.name} and {len(memo.competitor_landscape)-1} other competitors?"
                if len(question) <= 150:
                    questions.append(question)
        
        return questions

    def _generate_business_model_questions(self, memo: InvestmentMemo) -> list[str]:
        """Generate questions about business model and unit economics."""
        questions = []
        
        # Check for missing unit economics
        missing_info = [m.lower() for m in memo.missing_info]
        has_unit_econ_gap = any(
            term in " ".join(missing_info) 
            for term in ["unit economics", "cac", "ltv", "payback", "revenue model"]
        )
        
        # Check for unclear business model risk
        has_unclear_biz = any(
            risk.category == "unclear_business_model" 
            for risk in memo.risk_signals.signals
        )
        
        if has_unit_econ_gap or has_unclear_biz:
            questions.append("What's your CAC and LTV, and when do you reach payback?")
        
        # Extract from judge reasoning
        if "monetiz" in memo.judge_reasoning.lower():
            questions.append("How do you plan to monetize without cannibalizing your free tier?")
        
        return questions

    def _generate_market_risk_questions(self, memo: InvestmentMemo) -> list[str]:
        """Generate questions about market risks."""
        questions = []
        
        # Check for market saturation risk
        market_risks = [
            risk for risk in memo.risk_signals.signals 
            if risk.category == "market_saturation"
        ]
        
        if market_risks:
            risk = market_risks[0]
            # Extract competitor count if mentioned
            count_match = re.search(r'(\d+)\+?\s+competitors?', risk.description, re.IGNORECASE)
            if count_match:
                count = count_match.group(1)
                question = f"How will you differentiate in a market with {count}+ competitors?"
            else:
                question = f"The market is saturated. What's your unique angle?"
            
            if len(question) <= 150:
                questions.append(question)
        
        return questions

    def _generate_team_questions(self, memo: InvestmentMemo) -> list[str]:
        """Generate questions about team capability."""
        questions = []
        
        # Check for founder domain mismatch risk
        team_risks = [
            risk for risk in memo.risk_signals.signals 
            if risk.category == "founder_domain_mismatch"
        ]
        
        if team_risks:
            risk = team_risks[0]
            # Try to extract domain from description
            domain = self._extract_domain_from_risk(risk.description)
            if domain:
                question = f"Your team lacks {domain} experience. How will you overcome this?"
            else:
                question = "What domain expertise does your team bring to this problem?"
            
            if len(question) <= 150:
                questions.append(question)
        
        return questions

    def _generate_platform_questions(self, memo: InvestmentMemo) -> list[str]:
        """Generate questions about platform dependency."""
        questions = []
        
        # Check for platform dependency risk
        platform_risks = [
            risk for risk in memo.risk_signals.signals 
            if risk.category == "platform_dependency"
        ]
        
        if platform_risks:
            risk = platform_risks[0]
            platform = self._extract_platform_name(risk.description)
            if platform:
                question = f"What happens if {platform} changes their API or pricing?"
            else:
                question = "How dependent are you on third-party platforms for core functionality?"
            
            if len(question) <= 150:
                questions.append(question)
        
        return questions

    def _extract_questions_from_bear_case(self, bear_case: str) -> list[str]:
        """Convert bear case concerns into questions."""
        if not bear_case:
            return []
        
        questions = []
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', bear_case)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 15:
                continue
            
            # Convert statements to questions
            question = self._convert_concern_to_question(sentence)
            if question and len(question) <= 150:
                questions.append(question)
                
                if len(questions) >= 3:
                    break
        
        return questions

    def _convert_concern_to_question(self, concern: str) -> Optional[str]:
        """Convert a concern statement into a question."""
        concern = concern.strip()
        
        # Already a question
        if concern.endswith("?"):
            return concern
        
        # Pattern: "X is a concern" → "How will you address X?"
        if "concern" in concern.lower() or "risk" in concern.lower():
            # Extract the subject
            match = re.search(r'(.*?)\s+(?:is|are|poses?)\s+(?:a|an)?\s*(?:concern|risk)', concern, re.IGNORECASE)
            if match:
                subject = match.group(1).strip()
                return f"How will you address {subject}?"
        
        # Pattern: "Competitors have X" → "Why can't competitors Y?"
        if "competitor" in concern.lower():
            return f"What prevents competitors from replicating your approach?"
        
        # Pattern: "Market is X" → "How will you succeed in X market?"
        if "market" in concern.lower():
            return f"How will you succeed in this market?"
        
        # Default: "Why" question
        return f"Why {concern.lower()}?"

    def _generate_fallback_questions(self, memo: InvestmentMemo) -> list[str]:
        """Generate fallback questions when not enough specific questions exist."""
        fallback = [
            "What's your customer acquisition strategy?",
            "How will you defend against well-funded competitors?",
            "What are your key assumptions and how have you validated them?",
            "What's your path to profitability?",
            "Why is now the right time for this solution?",
        ]
        
        return fallback[:5]

    def _get_strongest_competitor(self, competitors: list[Competitor]) -> Optional[Competitor]:
        """Identify the strongest competitor based on funding or position."""
        if not competitors:
            return None
        
        # Prioritize by funding amount
        funded = [c for c in competitors if c.funding]
        if funded:
            # Sort by funding (extract numbers)
            def extract_funding_value(funding_str: str) -> float:
                if not funding_str:
                    return 0
                match = re.search(r'(\d+(?:\.\d+)?)\s*([BMK])', funding_str, re.IGNORECASE)
                if match:
                    value = float(match.group(1))
                    unit = match.group(2).upper()
                    multipliers = {"B": 1e9, "M": 1e6, "K": 1e3}
                    return value * multipliers.get(unit, 1)
                return 0
            
            funded.sort(key=lambda c: extract_funding_value(c.funding or ""), reverse=True)
            return funded[0]
        
        # Otherwise return first competitor
        return competitors[0]

    def _extract_domain_from_risk(self, description: str) -> Optional[str]:
        """Extract domain expertise from risk description."""
        # Look for patterns like "lacks X experience" or "no X background"
        patterns = [
            r'lacks?\s+([a-z\s]+)\s+experience',
            r'no\s+([a-z\s]+)\s+(?:experience|background)',
            r'missing\s+([a-z\s]+)\s+expertise',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                domain = match.group(1).strip()
                return domain
        
        return None

    def _extract_platform_name(self, description: str) -> Optional[str]:
        """Extract platform name from risk description."""
        # Look for proper nouns (capitalized words)
        words = description.split()
        for i, word in enumerate(words):
            if word and word[0].isupper() and len(word) > 2:
                # Check if it's a known platform indicator
                if any(term in description.lower() for term in ["api", "platform", "service", "provider"]):
                    return word
        
        return None
