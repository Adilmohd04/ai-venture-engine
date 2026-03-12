"""Unit tests for the Research Agent."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models import Competitor, MarketSize, ResearchResult, SearchResult, StartupInfo
from research import ResearchAgent, _parse_json_from_llm


class TestParseJsonFromLlm:
    """Tests for JSON extraction from LLM output."""

    def test_plain_json(self):
        result = _parse_json_from_llm('{"name": "Acme"}')
        assert result == {"name": "Acme"}

    def test_json_with_markdown_fences(self):
        text = '```json\n{"name": "Acme"}\n```'
        result = _parse_json_from_llm(text)
        assert result == {"name": "Acme"}

    def test_json_array(self):
        result = _parse_json_from_llm('[{"a": 1}]')
        assert result == [{"a": 1}]


class TestSearchWeb:
    """Tests for the search_web method."""

    @pytest.mark.asyncio
    async def test_returns_search_results(self):
        agent = ResearchAgent()
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text.return_value = [
            {"title": "Result 1", "body": "Snippet 1", "href": "https://example.com/1"},
            {"title": "Result 2", "body": "Snippet 2", "href": "https://example.com/2"},
        ]

        with patch("research.DDGS", return_value=mock_ddgs):
            results = await agent.search_web("test query")

        assert len(results) == 2
        assert results[0].title == "Result 1"
        assert results[0].snippet == "Snippet 1"
        assert results[0].url == "https://example.com/1"

    @pytest.mark.asyncio
    async def test_returns_empty_on_failure(self):
        agent = ResearchAgent()
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text.side_effect = Exception("Network error")

        with patch("research.DDGS", return_value=mock_ddgs):
            results = await agent.search_web("test query")

        assert results == []


class TestExtractStartupInfo:
    """Tests for startup info extraction with LLM fallback."""

    @pytest.mark.asyncio
    async def test_extracts_info_from_llm(self):
        agent = ResearchAgent()
        llm_response = json.dumps({
            "name": "TechCo",
            "product": "AI Platform",
            "industry": "SaaS",
            "stage": "Series A",
            "founding_team": "John Doe",
            "traction": "$1M ARR",
            "ask": "$5M",
        })
        with patch("research._call_llm", new_callable=AsyncMock, return_value=llm_response):
            info = await agent._extract_startup_info("Some pitch text about TechCo")

        assert info.name == "TechCo"
        assert info.product == "AI Platform"
        assert info.industry == "SaaS"
        assert info.stage == "Series A"

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self):
        agent = ResearchAgent()
        with patch("research._call_llm", new_callable=AsyncMock, side_effect=Exception("API error")):
            info = await agent._extract_startup_info("Some pitch text")

        assert info.name == "Unknown Startup"
        assert info.product == "Unknown Product"
        assert info.industry == "Unknown Industry"


class TestResearchStartup:
    """Tests for the full research pipeline."""

    @pytest.mark.asyncio
    async def test_returns_complete_research_result(self):
        agent = ResearchAgent()

        startup_info = StartupInfo(name="TestCo", product="Widget", industry="Tech")
        market_size = MarketSize(tam="$10B", sam="$2B", som="$500M", sources=["src1"])
        competitors = [Competitor(name="Rival", description="A rival company")]

        with (
            patch.object(agent, "_extract_startup_info", new_callable=AsyncMock, return_value=startup_info),
            patch.object(agent, "_search_market_data", new_callable=AsyncMock, return_value=[]),
            patch.object(agent, "_estimate_market_size", new_callable=AsyncMock, return_value=market_size),
            patch.object(agent, "discover_competitors", new_callable=AsyncMock, return_value=competitors),
            patch.object(agent, "_extract_traction", new_callable=AsyncMock, return_value=["$1M ARR"]),
        ):
            result = await agent.research_startup("pitch text")

        assert isinstance(result, ResearchResult)
        assert result.startup_info.name == "TestCo"
        assert result.market_size.tam == "$10B"
        assert len(result.competitors) == 1
        assert result.traction_signals == ["$1M ARR"]
        assert result.raw_research is not None

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_search_failure(self):
        """When web search fails, the agent should still return a valid ResearchResult."""
        agent = ResearchAgent()

        startup_info = StartupInfo(name="TestCo", product="Widget", industry="Tech")
        market_size = MarketSize(tam="Unknown", sam="Unknown", som="Unknown")

        with (
            patch.object(agent, "_extract_startup_info", new_callable=AsyncMock, return_value=startup_info),
            patch.object(agent, "_search_market_data", new_callable=AsyncMock, return_value=[]),
            patch.object(agent, "_estimate_market_size", new_callable=AsyncMock, return_value=market_size),
            patch.object(agent, "discover_competitors", new_callable=AsyncMock, return_value=[]),
            patch.object(agent, "_extract_traction", new_callable=AsyncMock, return_value=[]),
        ):
            result = await agent.research_startup("pitch text")

        assert isinstance(result, ResearchResult)
        assert result.startup_info.name == "TestCo"
        assert result.competitors == []
        assert result.market_size.tam == "Unknown"


class TestDiscoverCompetitors:
    """Tests for competitor discovery."""

    @pytest.mark.asyncio
    async def test_uses_search_results_when_available(self):
        agent = ResearchAgent()
        startup_info = StartupInfo(name="TestCo", product="Widget", industry="Tech")

        search_results = [
            SearchResult(title="Rival Co", snippet="A competitor", url="https://rival.com"),
        ]
        competitors = [Competitor(name="Rival Co", description="A competitor")]

        with (
            patch.object(agent, "search_web", new_callable=AsyncMock, return_value=search_results),
            patch.object(agent, "_extract_competitors", new_callable=AsyncMock, return_value=competitors),
        ):
            result = await agent.discover_competitors(startup_info)

        assert len(result) == 1
        assert result[0].name == "Rival Co"

    @pytest.mark.asyncio
    async def test_falls_back_to_pitch_when_search_empty(self):
        agent = ResearchAgent()
        startup_info = StartupInfo(name="TestCo", product="Widget", industry="Tech")

        fallback_competitors = [Competitor(name="Inferred Rival", description="Inferred")]

        with (
            patch.object(agent, "search_web", new_callable=AsyncMock, return_value=[]),
            patch.object(agent, "_competitors_from_pitch", new_callable=AsyncMock, return_value=fallback_competitors),
        ):
            result = await agent.discover_competitors(startup_info)

        assert len(result) == 1
        assert result[0].name == "Inferred Rival"
