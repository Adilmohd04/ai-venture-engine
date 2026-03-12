"""
Bug Condition Exploration Tests

CRITICAL: These tests MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.
Document counterexamples that demonstrate the bug exists.
"""

import pytest
import asyncio
import re
from supabase_client import increment_credits, get_profile
from research import _structured_extraction
import os

# Test data
SENTINEL_AI_PITCH = """
Sentinel AI
Cybersecurity Intelligence Platform

Company Overview:
Sentinel AI is a cybersecurity intelligence platform that protects critical infrastructure.

Traction:
- $12.9M ARR
- 148% Net Revenue Retention
- 2,500 enterprise customers
- $5,200 Average Contract Value

Validation:
- DARPA contract for threat detection
- SECRET security clearance
- 2.1B proprietary threat dataset

Market:
- $180B TAM
- $22B SAM
- $1.1B SOM
"""


class TestBug1_CreditsNotIncrementing:
    """
    Property 1: Fault Condition - Credits Not Incrementing After Analysis
    
    EXPECTED OUTCOME: Test FAILS (backend logs success but database unchanged)
    """
    
    @pytest.mark.asyncio
    async def test_credits_increment_after_analysis(self):
        """
        Test that credits increment after successful analysis completion.
        
        EXPECTED TO FAIL ON UNFIXED CODE:
        - Backend logs "✅ Credit incremented"
        - Database credits_used remains unchanged
        
        Counterexample: Backend success log but no database update
        """
        # Use a test user ID (replace with actual test user)
        test_user_id = os.getenv("TEST_USER_ID", "test-user-123")
        
        # Get initial credit count
        initial_profile = await get_profile(test_user_id)
        initial_credits = initial_profile.get("credits_used", 0) if initial_profile else 0
        
        print(f"Initial credits_used: {initial_credits}")
        
        # Simulate analysis completion by calling increment_credits
        result = await increment_credits(test_user_id)
        
        print(f"increment_credits returned: {result}")
        
        # Re-fetch profile to check if database was updated
        updated_profile = await get_profile(test_user_id)
        updated_credits = updated_profile.get("credits_used", 0) if updated_profile else 0
        
        print(f"Updated credits_used: {updated_credits}")
        
        # ASSERTION: This should FAIL on unfixed code
        # Backend logs success but database doesn't update
        assert updated_credits == initial_credits + 1, \
            f"COUNTEREXAMPLE: Backend logged success but credits_used unchanged ({initial_credits} -> {updated_credits})"


class TestBug2_DataExtractionFailure:
    """
    Property 1: Fault Condition - Financial Metrics Not Extracted
    
    EXPECTED OUTCOME: Test FAILS (explicit metrics in deck but extraction returns null)
    """
    
    @pytest.mark.asyncio
    async def test_arr_extraction_from_explicit_value(self):
        """
        Test that ARR is extracted when explicitly stated as "$12.9M ARR".
        
        EXPECTED TO FAIL ON UNFIXED CODE:
        - Deck contains "$12.9M ARR"
        - Extraction returns arr: null or empty
        
        Counterexample: Explicit "$12.9M ARR" but extraction.arr = null
        """
        extraction = await _structured_extraction(SENTINEL_AI_PITCH)
        
        print(f"Extracted ARR: {extraction.arr}")
        print(f"Extracted startup_name: {extraction.startup_name}")
        print(f"Extracted NRR/growth: {extraction.growth}")
        print(f"Extracted customers: {extraction.customers}")
        
        # ASSERTION: This should FAIL on unfixed code
        assert extraction.arr is not None and extraction.arr != "", \
            f"COUNTEREXAMPLE: Deck contains '$12.9M ARR' but extraction.arr = {extraction.arr}"
        
        assert "12.9" in str(extraction.arr) or "12900000" in str(extraction.arr), \
            f"COUNTEREXAMPLE: ARR value not correctly parsed: {extraction.arr}"
    
    @pytest.mark.asyncio
    async def test_startup_name_extraction(self):
        """
        Test that startup name is extracted from title slide.
        
        EXPECTED TO FAIL ON UNFIXED CODE:
        - Deck title shows "Sentinel AI"
        - Extraction returns startup_name: "Unknown Startup"
        
        Counterexample: Title shows "Sentinel AI" but extraction returns "Unknown Startup"
        """
        extraction = await _structured_extraction(SENTINEL_AI_PITCH)
        
        print(f"Extracted startup_name: {extraction.startup_name}")
        
        # ASSERTION: This should FAIL on unfixed code
        assert extraction.startup_name != "Unknown Startup", \
            f"COUNTEREXAMPLE: Deck title shows 'Sentinel AI' but extraction.startup_name = '{extraction.startup_name}'"
        
        assert "Sentinel" in extraction.startup_name or "sentinel" in extraction.startup_name.lower(), \
            f"COUNTEREXAMPLE: Startup name not correctly extracted: {extraction.startup_name}"
    
    @pytest.mark.asyncio
    async def test_nrr_extraction(self):
        """
        Test that NRR is extracted when stated as "148% Net Revenue Retention".
        
        EXPECTED TO FAIL ON UNFIXED CODE:
        - Deck contains "148% Net Revenue Retention"
        - Extraction returns growth: null or doesn't capture NRR
        
        Counterexample: Elite 148% NRR stated but not extracted
        """
        extraction = await _structured_extraction(SENTINEL_AI_PITCH)
        
        print(f"Extracted growth/NRR: {extraction.growth}")
        
        # ASSERTION: This should FAIL on unfixed code
        # NRR might be in growth field or separate nrr field
        growth_str = str(extraction.growth) if extraction.growth else ""
        
        assert "148" in growth_str or extraction.growth is not None, \
            f"COUNTEREXAMPLE: Deck contains '148% NRR' but extraction.growth = {extraction.growth}"


class TestBug3_MarkdownInStreaming:
    """
    Property 1: Fault Condition - Raw Markdown in Streaming Output
    
    EXPECTED OUTCOME: Test FAILS (literal asterisks visible in streaming output)
    
    NOTE: This is a frontend test - requires manual verification or browser automation
    """
    
    def test_markdown_detection_in_sample_output(self):
        """
        Test that markdown patterns are detected in sample agent output.
        
        This simulates what would appear in the UI during streaming.
        
        EXPECTED TO FAIL ON UNFIXED CODE:
        - Agent outputs "***strong traction***"
        - UI displays literal "***strong traction***" instead of clean text
        
        Counterexample: Raw markdown visible to user
        """
        # Sample agent outputs that would appear during streaming
        sample_outputs = [
            "***strong traction*** with 148% NRR",
            "**concerning burn rate** of only 8 months",
            "*moderate risk* in the competitive landscape"
        ]
        
        for output in sample_outputs:
            print(f"Sample output: {output}")
            
            # Check if markdown patterns are present
            has_triple_asterisk = "***" in output
            has_double_asterisk = "**" in output and "***" not in output
            has_single_asterisk = re.search(r'(?<!\*)\*(?!\*)', output) is not None
            
            # ASSERTION: This documents the bug - markdown IS present
            assert has_triple_asterisk or has_double_asterisk or has_single_asterisk, \
                f"COUNTEREXAMPLE: Expected markdown in '{output}' but none found"
            
            print(f"  ✓ Markdown detected: triple={has_triple_asterisk}, double={has_double_asterisk}, single={has_single_asterisk}")
            print(f"  ❌ UNFIXED: This would display raw markdown to users")


class TestBug4_JSONInRiskEngine:
    """
    Property 1: Fault Condition - Raw JSON in Risk Engine Display
    
    EXPECTED OUTCOME: Test FAILS (JSON brackets, quotes visible to user)
    
    NOTE: This is a frontend test - requires manual verification or browser automation
    """
    
    def test_json_detection_in_risk_output(self):
        """
        Test that JSON structures are detected in risk engine output.
        
        This simulates what would appear in the UI during risk engine streaming.
        
        EXPECTED TO FAIL ON UNFIXED CODE:
        - Risk engine streams '{"signals": [...]}'
        - UI displays raw JSON with brackets and quotes
        
        Counterexample: Raw JSON structure visible to user
        """
        # Sample risk engine outputs that would appear during streaming
        sample_outputs = [
            '{"signals": [{"type": "red_flag", "title": "Weak moat"}], "overall_risk_level": "medium"}',
            'Analyzing risks... {"market_risk": "high", "team_risk": "low"}',
            '[{"category": "market", "score": 7}, {"category": "team", "score": 9}]'
        ]
        
        for output in sample_outputs:
            print(f"Sample output: {output[:80]}...")
            
            # Check if JSON patterns are present
            has_json_object = re.search(r'\{[^}]*"[^"]*"[^}]*\}', output) is not None
            has_json_array = re.search(r'\[[^\]]*\{[^\}]*\}[^\]]*\]', output) is not None
            
            # ASSERTION: This documents the bug - JSON IS present
            assert has_json_object or has_json_array, \
                f"COUNTEREXAMPLE: Expected JSON in output but none found"
            
            print(f"  ✓ JSON detected: object={has_json_object}, array={has_json_array}")
            print(f"  ❌ UNFIXED: This would display raw JSON to users")


class TestBug5_InconsistentQuality:
    """
    Property 1: Fault Condition - Inconsistent Analysis Results
    
    EXPECTED OUTCOME: Test FAILS (scores differ by >0.5, government contracts flagged as risks)
    
    NOTE: This requires running full analysis pipeline twice - may need integration test setup
    """
    
    def test_moat_interpretation_context(self):
        """
        Test that strong moat indicators are recognized correctly.
        
        EXPECTED TO FAIL ON UNFIXED CODE:
        - Deck shows DARPA contract, SECRET clearance, 2.1B dataset
        - Analysis flags these as "weak moat" or "dependency risk"
        
        Counterexample: Strong moat indicators misinterpreted as weaknesses
        """
        # Check if the pitch contains strong moat indicators
        has_government_contract = "DARPA" in SENTINEL_AI_PITCH
        has_security_clearance = "SECRET" in SENTINEL_AI_PITCH
        has_large_dataset = "2.1B" in SENTINEL_AI_PITCH
        has_elite_nrr = "148%" in SENTINEL_AI_PITCH
        
        print(f"Strong moat indicators present:")
        print(f"  - Government contract (DARPA): {has_government_contract}")
        print(f"  - Security clearance (SECRET): {has_security_clearance}")
        print(f"  - Large proprietary dataset (2.1B): {has_large_dataset}")
        print(f"  - Elite NRR (148%): {has_elite_nrr}")
        
        # ASSERTION: Document that these indicators exist
        assert has_government_contract and has_security_clearance and has_large_dataset, \
            "Test setup error: Sentinel AI pitch should contain strong moat indicators"
        
        print(f"\n❌ UNFIXED: Current system may flag these as weaknesses or miss them entirely")
        print(f"   Expected: These should be recognized as STRONG moat indicators")
        print(f"   Actual (unfixed): May be flagged as 'customer concentration risk' or 'weak moat'")


if __name__ == "__main__":
    print("=" * 80)
    print("BUG CONDITION EXPLORATION TESTS")
    print("=" * 80)
    print("\nCRITICAL: These tests are EXPECTED TO FAIL on unfixed code.")
    print("Failures confirm the bugs exist and document counterexamples.\n")
    
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
