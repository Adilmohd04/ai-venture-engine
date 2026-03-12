"""Research Agent — extracts startup info, searches market data, discovers competitors."""

import asyncio
import json
import logging
import math as _math
import os
import re
from typing import Any

import httpx
from ddgs import DDGS

from models import (
    BenchmarkCategory, BenchmarkMetric, Citation, ClaimVerification,
    Competitor, EcosystemCategory, EcosystemMap, MarketBenchmark,
    MarketSize, ResearchResult, SearchResult, StartupInfo, StructuredExtraction,
)

# Disable SSL verification — Windows Python 3.14 has broken cert chain
SSL_VERIFY = False

logger = logging.getLogger(__name__)

# ── Multi-provider LLM config (round-robin) ────────────────────────────
# 4 providers: each pipeline call is assigned a different provider to
# spread load and avoid rate limits on any single free tier.
# Cerebras promoted to #2 since HuggingFace free tier is exhausted (402).
PROVIDERS = [
    {
        "name": "groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "model_env": "GROQ_MODEL",
        "default_model": "llama-3.3-70b-versatile",
    },
    {
        "name": "cerebras",
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "key_env": "CEREBRAS_API_KEY",
        "model_env": "CEREBRAS_MODEL",
        "default_model": "llama3.1-8b",
    },
    {
        "name": "openrouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key_env": "OPENROUTER_API_KEY",
        "model_env": "OPENROUTER_MODEL",
        "default_model": "meta-llama/llama-3.3-70b-instruct:free",
    },
    {
        "name": "huggingface",
        "url": "https://router.huggingface.co/v1/chat/completions",
        "key_env": "HF_API_KEY",
        "model_env": "HF_MODEL",
        "default_model": "meta-llama/Llama-3.1-8B-Instruct:sambanova",
    },
]

# Round-robin counter — each _call_llm invocation picks the next provider
_provider_counter = 0
# Providers that returned 401/403/404 are blacklisted for the session
_blacklisted_providers: set[str] = set()

MAX_RETRIES_PER_PROVIDER = 3
PIPELINE_PAUSE = 2  # seconds between research pipeline LLM calls (reduced — less pressure per provider)


async def _call_llm(
    messages: list[dict[str, str]],
    temperature: float = 0.3,
    use_extraction_model: bool = False,
    provider_hint: int | None = None,
) -> str:
    """Call LLM with round-robin provider selection + failover.

    Each call picks the next provider in rotation. If that provider fails,
    it falls through to the remaining providers. This spreads load so no
    single free tier gets hammered.

    Args:
        provider_hint: Force a specific provider index (0-3). If None, uses
            the global round-robin counter.
    """
    global _provider_counter
    last_error: Exception | None = None

    # Pick starting provider via round-robin or explicit hint
    if provider_hint is not None:
        start_idx = provider_hint % len(PROVIDERS)
    else:
        start_idx = _provider_counter % len(PROVIDERS)
        _provider_counter += 1

    # Build rotation order: start at assigned provider, then try the rest
    provider_order = [PROVIDERS[(start_idx + i) % len(PROVIDERS)] for i in range(len(PROVIDERS))]

    for provider in provider_order:
        if provider["name"] in _blacklisted_providers:
            logger.info("Skipping %s — blacklisted this session", provider["name"])
            continue

        api_key = os.environ.get(provider["key_env"], "").strip()
        if not api_key:
            logger.info("Skipping %s — no API key set (%s)", provider["name"], provider["key_env"])
            continue

        model = os.environ.get(provider["model_env"], provider["default_model"])
        url = provider["url"]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
        }

        for attempt in range(MAX_RETRIES_PER_PROVIDER):
            try:
                async with httpx.AsyncClient(timeout=120, verify=SSL_VERIFY) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    logger.info("LLM call succeeded on %s (model=%s)", provider["name"], model)
                    return content
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code
                if status == 429:
                    wait = 2 * (attempt + 1)  # exponential-ish backoff: 2s, 4s
                    logger.warning(
                        "%s 429 rate-limited (attempt %d/%d) — waiting %ds",
                        provider["name"], attempt + 1, MAX_RETRIES_PER_PROVIDER, wait,
                    )
                    await asyncio.sleep(wait)
                    if attempt == MAX_RETRIES_PER_PROVIDER - 1:
                        break  # move to next provider
                elif status in (401, 402, 403, 404):
                    logger.warning(
                        "%s returned %d — blacklisting for this session", provider["name"], status,
                    )
                    _blacklisted_providers.add(provider["name"])
                    break  # don't retry auth/billing/not-found errors, move to next provider
                elif status >= 500:
                    wait = 2 ** attempt
                    logger.warning("%s server error %d, waiting %ds", provider["name"], status, wait)
                    await asyncio.sleep(wait)
                else:
                    raise
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                last_error = exc
                wait = 2 ** attempt
                logger.warning("%s network error, waiting %ds: %s", provider["name"], wait, exc)
                await asyncio.sleep(wait)

        logger.warning("Provider %s exhausted, trying next...", provider["name"])

    raise RuntimeError(
        f"All LLM providers failed. Last error: {last_error}"
    )


def _parse_json_from_llm(text: str) -> dict[str, Any]:
    """Extract and parse JSON from LLM output, handling markdown fences and common issues."""
    import re as _re
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Strip ```json ... ``` fences
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    # Try parsing as-is first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fix common LLM JSON issues: trailing commas before } or ]
    fixed = _re.sub(r",\s*([}\]])", r"\1", cleaned)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Try to extract the first JSON object or array from the text
    for pattern in [r"\{[\s\S]*\}", r"\[[\s\S]*\]"]:
        m = _re.search(pattern, cleaned)
        if m:
            candidate = m.group(0)
            candidate_fixed = _re.sub(r",\s*([}\]])", r"\1", candidate)
            try:
                return json.loads(candidate_fixed)
            except json.JSONDecodeError:
                continue

    # Last resort — raise with original text for debugging
    raise json.JSONDecodeError("Could not parse JSON from LLM output", cleaned, 0)


# ── Benchmark post-processing helpers ──────────────────────────────────

_MOM_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*[x×]\s*MoM"
    r"|(\d+(?:\.\d+)?)%\s*MoM",
    re.IGNORECASE,
)


def _fix_growth_value(value: str) -> str:
    """Fix MoM→YoY conversion using correct compound formula: (1+r)^12 - 1.

    Examples:
      '18% MoM' → '~644% YoY (18% MoM)'
      '4.1x MoM' → 'Hypergrowth (4.1x MoM)'
      '~4920% YoY (18% MoM)' → '~644% YoY (18% MoM)'  (fixes wrong LLM math)
    """
    if not value:
        return value

    # Check if LLM already did a wrong conversion like "~4920% YoY (18% MoM)"
    wrong_conv = re.match(
        r"~?(\d+(?:\.\d+)?)%\s*YoY\s*\((\d+(?:\.\d+)?)[%x×]?\s*MoM\)",
        value, re.IGNORECASE,
    )
    if wrong_conv:
        claimed_yoy = float(wrong_conv.group(1))
        mom_raw = wrong_conv.group(2)
        mom_val = float(mom_raw)
        if "x" in value.lower() or "×" in value:
            if mom_val > 3:
                return f"Hypergrowth ({mom_raw}x MoM)"
            monthly_rate = mom_val - 1
        else:
            monthly_rate = mom_val / 100
        correct_yoy = ((_math.pow(1 + monthly_rate, 12)) - 1) * 100
        if correct_yoy > 5000:
            return f"Hypergrowth ({mom_raw}% MoM)"
        return f"~{correct_yoy:.0f}% YoY ({mom_raw}% MoM)"

    m = _MOM_PATTERN.search(value)
    if m:
        multiplier_str = m.group(1)
        pct_str = m.group(2)
        if multiplier_str:
            mom_val = float(multiplier_str)
            if mom_val > 3:
                return f"Hypergrowth ({multiplier_str}x MoM)"
            monthly_rate = mom_val - 1
            correct_yoy = ((_math.pow(1 + monthly_rate, 12)) - 1) * 100
            if correct_yoy > 5000:
                return f"Hypergrowth ({multiplier_str}x MoM)"
            return f"~{correct_yoy:.0f}% YoY ({multiplier_str}x MoM)"
        elif pct_str:
            monthly_rate = float(pct_str) / 100
            correct_yoy = ((_math.pow(1 + monthly_rate, 12)) - 1) * 100
            if correct_yoy > 5000:
                return f"Hypergrowth ({pct_str}% MoM)"
            return f"~{correct_yoy:.0f}% YoY ({pct_str}% MoM)"

    return value


_IS_MULTIPLE = re.compile(r"^\~?\d+(\.\d+)?[x×]", re.IGNORECASE)
_IS_PERCENTAGE = re.compile(r"\d+(\.\d+)?%", re.IGNORECASE)
_IS_DOLLAR = re.compile(r"^\$|^\~?\$", re.IGNORECASE)
_IS_COUNT = re.compile(r"^\~?\d[\d,]*(\+)?$|^\~?\d+(\.\d+)?\s*(M|K|B)\b", re.IGNORECASE)


def _classify_value(value: str) -> str:
    """Classify a benchmark value into a type: multiple, percentage, dollar, count, or other."""
    v = value.strip()
    if v in ("N/A", "—", ""):
        return "na"
    if _IS_MULTIPLE.search(v):
        return "multiple"
    if _IS_DOLLAR.search(v):
        return "dollar"
    if _IS_PERCENTAGE.search(v):
        return "percentage"
    if _IS_COUNT.match(v):
        return "count"
    return "other"


def _validate_benchmark_categories(categories: list[BenchmarkCategory]) -> list[BenchmarkCategory]:
    """Post-process benchmark categories to enforce metric consistency.

    For each category, classify all entry values. If a category has mixed types
    (e.g. some entries are dollar amounts and some are multiples), drop the
    entries that don't match the majority type.
    """
    cleaned = []
    for cat in categories:
        for entry in cat.entries:
            entry.value = _fix_growth_value(entry.value)

        type_counts: dict[str, int] = {}
        entry_types: list[tuple[BenchmarkMetric, str]] = []
        for entry in cat.entries:
            vtype = _classify_value(entry.value)
            entry_types.append((entry, vtype))
            if vtype != "na":
                type_counts[vtype] = type_counts.get(vtype, 0) + 1

        if not type_counts:
            cleaned.append(cat)
            continue

        dominant_type = max(type_counts, key=type_counts.get)
        consistent_entries = [
            entry for entry, vtype in entry_types
            if vtype == dominant_type or vtype == "na"
        ]

        real_entries = [e for e in consistent_entries if _classify_value(e.value) != "na"]
        # Require at least 3 real entries for meaningful comparison (startup + 2 competitors minimum)
        if len(real_entries) >= 3:
            cat.entries = consistent_entries
            cleaned.append(cat)

    return cleaned


class ResearchAgent:
    """Performs web research about a startup, estimates market size, and discovers competitors."""

    def __init__(self, search_provider: str = "duckduckgo"):
        self.search_provider = search_provider

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def research_startup(self, pitch_text: str, on_progress=None) -> ResearchResult:
        """Evidence-grounded research pipeline — optimized for 3 LLM calls.

        LLM Call 1: Structured entity extraction (knowledge graph)
        LLM Call 2: Claim verification + deck competitor extraction (combined)
        LLM Call 3: Ecosystem map + market benchmarking (combined)
        No-LLM: Web search, traction regex, market size from deck, confidence scoring

        Args:
            on_progress: Optional async callback(message: str) for streaming status updates.
        """
        async def _progress(msg: str):
            if on_progress:
                await on_progress(msg)

        # ── LLM CALL 1 — Structured extraction ──────────────────────────
        await _progress("Extracting entities from pitch deck...")
        extraction = await self._structured_extraction(pitch_text)

        # Build StartupInfo from extraction (no LLM)
        startup_info = StartupInfo(
            name=extraction.startup_name or "Unknown Startup",
            product=extraction.product or "Unknown Product",
            industry=extraction.industry or "Unknown Industry",
            stage=extraction.stage,
            founding_team=extraction.founding_team,
            traction=extraction.customers or extraction.growth,
            ask=extraction.funding_ask,
        )

        # Build MarketSize from extraction (no LLM)
        market_size = MarketSize(
            tam=extraction.tam or "Unknown",
            sam=extraction.sam or "Unknown",
            som=extraction.som or "Unknown",
            sources=[c.source for c in extraction.key_metrics if "TAM" in c.text or "SAM" in c.text or "market" in c.text.lower()],
        )

        # Web search for market data if needed (no LLM, just DuckDuckGo)
        if market_size.tam == "Unknown" or market_size.sam == "Unknown":
            await _progress("Searching market data...")
            market_results = await self._search_market_data(startup_info)
        else:
            market_results = []

        # Traction signals via regex (no LLM)
        traction_signals = await self._extract_traction(pitch_text)

        # ── LLM CALL 2 — Claims + Deck Competitors (combined) ──────────
        await asyncio.sleep(PIPELINE_PAUSE)
        await _progress("Verifying claims and extracting competitors...")
        claims, deck_llm_competitors = await self._verify_claims_and_extract_competitors(
            extraction, pitch_text, startup_info,
        )

        # Build competitor list: deck-extracted names + LLM-extracted + web
        deck_competitors = [
            Competitor(name=c, description=f"Competitor in {extraction.industry}", category=extraction.industry)
            for c in extraction.competitors
        ]
        seen = {c.name.lower() for c in deck_competitors}
        competitors = list(deck_competitors)
        for c in deck_llm_competitors:
            if c.name.lower() not in seen:
                competitors.append(c)
                seen.add(c.name.lower())

        # Only do web competitor search if we have fewer than 3
        if len(competitors) < 3:
            await _progress("Searching for additional competitors...")
            web_competitors = await self.discover_competitors(startup_info)
            for c in web_competitors:
                if c.name.lower() not in seen:
                    competitors.append(c)
                    seen.add(c.name.lower())
        competitors = competitors[:7]

        # If market data was missing, estimate with LLM (reuse call 2 pause window)
        if market_size.tam == "Unknown" or market_size.sam == "Unknown":
            market_size = await self._estimate_market_size(
                startup_info, market_results, deck_market=market_size,
            )

        # ── LLM CALL 3 — Ecosystem Map + Benchmarking (combined) ───────
        await asyncio.sleep(PIPELINE_PAUSE)
        await _progress("Building ecosystem map and market benchmarks...")
        try:
            ecosystem_map, market_benchmark = await self._build_ecosystem_and_benchmarks(
                extraction, startup_info, competitors,
            )
        except Exception as e:
            # Make ecosystem/benchmarks non-blocking - analysis can complete without it
            logger.error(f"Ecosystem/benchmarks failed (non-blocking): {str(e)[:200]}")
            await _progress("⚠️ Ecosystem map unavailable - continuing analysis...")
            ecosystem_map = None
            market_benchmark = None

        # Confidence scoring (no LLM)
        confidence = self._compute_confidence(extraction, market_results, competitors)
        raw_research = self._format_raw_research(market_results, [])

        return ResearchResult(
            startup_info=startup_info,
            structured_extraction=extraction,
            claim_verifications=claims,
            market_size=market_size,
            competitors=competitors,
            ecosystem_map=ecosystem_map,
            market_benchmark=market_benchmark,
            traction_signals=traction_signals,
            missing_info=extraction.missing_info,
            confidence_scores=confidence,
            raw_research=raw_research,
        )

    async def search_web(self, query: str) -> list[SearchResult]:
        """Execute a web search via DuckDuckGo and return results."""
        try:
            with DDGS(verify=False) as ddgs:
                raw = list(ddgs.text(query, max_results=5))
            return [
                SearchResult(
                    title=r.get("title", ""),
                    snippet=r.get("body", ""),
                    url=r.get("href", ""),
                )
                for r in raw
            ]
        except Exception:
            logger.warning("Web search failed for query: %s", query, exc_info=True)
            return []

    async def discover_competitors(self, startup_info: StartupInfo) -> list[Competitor]:
        """Find competitors based on startup industry and product."""
        queries = [
            f"{startup_info.product} competitors",
            f"{startup_info.industry} startups similar to {startup_info.name}",
        ]
        all_results: list[SearchResult] = []
        for q in queries:
            results = await self.search_web(q)
            all_results.extend(results)

        if not all_results:
            return await self._competitors_from_pitch(startup_info)

        return await self._extract_competitors(startup_info, all_results)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _structured_extraction(self, pitch_text: str) -> StructuredExtraction:
        """Single-pass entity extraction from the pitch deck — builds the knowledge graph.

        Extracts ALL key entities with page citations in one LLM call.
        This is the foundation for the entire analysis pipeline.
        """
        prompt = (
            "You are analyzing a startup pitch deck. Extract ALL key entities and data points "
            "from the text below in a single pass.\n\n"
            "For EVERY data point you extract, note which page it came from "
            "(look for '--- PAGE N ---' markers in the text).\n\n"
            "Extract:\n"
            "1. startup_name — the company/startup name (usually on first page)\n"
            "2. product — what they build (one sentence)\n"
            "3. industry — sector/vertical\n"
            "4. stage — funding stage (pre-seed, seed, Series A, etc.)\n"
            "5. founding_team — key founders and their backgrounds\n"
            "6. tam — Total Addressable Market (exact number from deck, or null)\n"
            "7. sam — Serviceable Addressable Market (exact number, or null)\n"
            "8. som — Serviceable Obtainable Market (exact number, or null)\n"
            "9. arr — Annual Recurring Revenue (exact number, or null)\n"
            "10. mrr — Monthly Recurring Revenue (exact number, or null)\n"
            "11. customers — customer count or notable customers\n"
            "12. growth — growth metrics (MoM, YoY, user growth, NRR, etc.)\n"
            "13. funding_ask — how much they're raising\n"
            "14. competitors — list of competitor names mentioned in the deck\n"
            "15. key_metrics — array of {text, source, page} for every important number/claim\n"
            "16. missing_info — list of important items NOT found in the deck "
            "(e.g. 'No revenue data', 'No team bios', 'No competitive analysis')\n\n"
            "EXTRACTION EXAMPLES (learn these patterns):\n"
            "- '$12.9M ARR' → arr: '12.9M'\n"
            "- 'ARR: $12.9M' → arr: '12.9M'\n"
            "- '12.9M in annual recurring revenue' → arr: '12.9M'\n"
            "- 'Annual Recurring Revenue of 12.9 million dollars' → arr: '12.9M'\n"
            "- '148% Net Revenue Retention' → growth: '148% NRR'\n"
            "- 'NRR of 148%' → growth: '148% NRR'\n"
            "- '2,500 enterprise customers' → customers: '2,500'\n"
            "- 'Over 2500 customers' → customers: '2,500+'\n"
            "- Company name on title slide: 'Sentinel AI' → startup_name: 'Sentinel AI'\n"
            "- '$5M Series A' → funding_ask: '5M', stage: 'Series A'\n\n"
            "CRITICAL RULES:\n"
            "- Extract ONLY what is explicitly stated. Never invent data.\n"
            "- For key_metrics, include page numbers: 'Pitch Deck, Page 3'\n"
            "- For missing_info, flag anything a VC would expect but isn't in the deck.\n"
            "- The startup name is almost always present — scan carefully.\n"
            "- Look for financial metrics throughout the ENTIRE deck, not just the beginning.\n"
            "- Parse numbers in various formats: '$12.9M', '12.9M', '12.9 million', etc.\n\n"
            f"PITCH DECK TEXT:\n{pitch_text[:50000]}\n\n"
            "Return ONLY valid JSON matching the schema above."
        )
        try:
            # Force Groq provider (highest quality) for extraction
            raw = await _call_llm([
                {"role": "system", "content": (
                    "You are an expert pitch deck analyst performing structured entity extraction. "
                    "Extract every data point with its page citation. Be thorough but precise. "
                    "Return only valid JSON."
                )},
                {"role": "user", "content": prompt},
            ], use_extraction_model=True, provider_hint=0)
            data = _parse_json_from_llm(raw)

            # Regex fallback for critical fields if LLM extraction fails
            if not data.get("arr"):
                # Try to extract ARR with regex
                import re
                arr_patterns = [
                    r'\$?([\d.]+)M?\s*(?:in\s+)?ARR',
                    r'ARR[:\s]+\$?([\d.]+)M?',
                    r'Annual\s+Recurring\s+Revenue[:\s]+\$?([\d.]+)M?',
                ]
                for pattern in arr_patterns:
                    match = re.search(pattern, pitch_text, re.IGNORECASE)
                    if match:
                        data["arr"] = match.group(1) + "M"
                        break

            if not data.get("startup_name") or data.get("startup_name") == "Unknown Startup":
                # Try to extract company name from first 2000 chars (title slide)
                import re
                # Look for capitalized words at the start of lines (likely company names)
                name_match = re.search(r'(?:^|\n)([A-Z][A-Za-z0-9\s]{2,30})(?:\n|$)', pitch_text[:2000])
                if name_match:
                    potential_name = name_match.group(1).strip()
                    # Filter out common non-name words
                    if potential_name not in ["Pitch Deck", "Confidential", "Executive Summary", "Overview"]:
                        data["startup_name"] = potential_name

            if not data.get("growth"):
                # Try to extract NRR with regex
                import re
                nrr_patterns = [
                    r'([\d.]+)%\s*(?:Net\s+Revenue\s+Retention|NRR)',
                    r'(?:Net\s+Revenue\s+Retention|NRR)[:\s]+([\d.]+)%',
                ]
                for pattern in nrr_patterns:
                    match = re.search(pattern, pitch_text, re.IGNORECASE)
                    if match:
                        data["growth"] = match.group(1) + "% NRR"
                        break

            if not data.get("customers"):
                # Try to extract customer count with regex
                import re
                customer_patterns = [
                    r'([\d,]+)\s+(?:enterprise\s+)?customers',
                    r'(?:Over|More than)\s+([\d,]+)\s+customers',
                ]
                for pattern in customer_patterns:
                    match = re.search(pattern, pitch_text, re.IGNORECASE)
                    if match:
                        data["customers"] = match.group(1).replace(',', '')
                        break

            # Parse key_metrics into Citation objects
            key_metrics = []
            for m in data.get("key_metrics", []):
                if isinstance(m, dict):
                    # Extract page number and convert to int
                    page_val = m.get("page")
                    page_int = None
                    if page_val:
                        # Handle various formats: "Page 2", "2", "Pitch Deck, Page 2"
                        if isinstance(page_val, int):
                            page_int = page_val
                        elif isinstance(page_val, str):
                            # Extract number from string
                            import re
                            page_match = re.search(r'(\d+)', page_val)
                            if page_match:
                                page_int = int(page_match.group(1))
                    
                    key_metrics.append(Citation(
                        text=m.get("text", ""),
                        source=m.get("source", "Pitch Deck"),
                        page=page_int,
                    ))
                elif isinstance(m, str):
                    key_metrics.append(Citation(text=m, source="Pitch Deck"))

            # Coerce values to strings — LLMs sometimes return ints or lists
            def _str_or_none(val):
                if val is None:
                    return None
                if isinstance(val, list):
                    # e.g. founding_team as list of dicts
                    parts = []
                    for item in val:
                        if isinstance(item, dict):
                            parts.append(", ".join(f"{k}: {v}" for k, v in item.items()))
                        else:
                            parts.append(str(item))
                    return "; ".join(parts)
                return str(val)

            return StructuredExtraction(
                startup_name=data.get("startup_name") or self._guess_name_from_text(pitch_text) or "Unknown Startup",
                product=data.get("product") or self._guess_product_from_text(pitch_text) or "Unknown Product",
                industry=data.get("industry") or "Technology",
                stage=_str_or_none(data.get("stage")),
                founding_team=_str_or_none(data.get("founding_team")),
                tam=_str_or_none(data.get("tam")),
                sam=_str_or_none(data.get("sam")),
                som=_str_or_none(data.get("som")),
                arr=_str_or_none(data.get("arr")),
                mrr=_str_or_none(data.get("mrr")),
                customers=_str_or_none(data.get("customers")),
                growth=_str_or_none(data.get("growth")),
                funding_ask=_str_or_none(data.get("funding_ask")),
                competitors=data.get("competitors", []),
                key_metrics=key_metrics,
                missing_info=data.get("missing_info", []),
            )
        except Exception as e:
            logger.error(f"Structured extraction failed with error: {e}", exc_info=True)
            name = self._guess_name_from_text(pitch_text) or "Unknown Startup"
            product = self._guess_product_from_text(pitch_text) or "Unknown Product"
            return StructuredExtraction(
                startup_name=name,
                product=product,
                industry="Technology",
                missing_info=[f"Structured extraction error: {str(e)[:100]}"],
            )

    async def _verify_claims(
        self, extraction: StructuredExtraction, pitch_text: str
    ) -> list[ClaimVerification]:
        """Verify key claims from the extraction against the pitch text and common sense."""
        if not extraction.key_metrics:
            return []

        claims_text = "\n".join(
            f"- {c.text} (Source: {c.source})" for c in extraction.key_metrics[:15]
        )
        prompt = (
            "You are a due-diligence analyst verifying claims from a startup pitch deck.\n\n"
            f"Startup: {extraction.startup_name}\n"
            f"Product: {extraction.product}\n"
            f"Industry: {extraction.industry}\n\n"
            f"Claims to verify:\n{claims_text}\n\n"
            "CRITICAL DISTINCTION — there are TWO types of confidence:\n\n"
            "1) DECK-SOURCED CLAIMS (data that comes directly from the pitch deck):\n"
            "   - TAM/SAM/SOM numbers stated in the deck → 'high' confidence for deck-sourcing\n"
            "   - ARR/MRR/customer counts stated in the deck → 'high' confidence for deck-sourcing\n"
            "   - Team bios, product features, partnerships mentioned in deck → 'high'\n"
            "   - These are facts about what the DECK SAYS, not whether the numbers are accurate\n"
            "   - In reasoning, note: 'Sourced directly from pitch deck'\n\n"
            "2) EXTERNAL/MARKET CLAIMS (claims about the broader market or unverifiable assertions):\n"
            "   - Market growth projections not backed by named sources → 'medium' or 'low'\n"
            "   - Competitive advantage claims without evidence → 'medium'\n"
            "   - Revenue projections or future forecasts → 'low'\n"
            "   - Claims that contradict known market data → 'low'\n\n"
            "DO NOT mark deck-sourced data as 'low' just because you can't externally verify it. "
            "The deck IS the source for its own stated metrics.\n\n"
            "Return ONLY a valid JSON array of objects with keys: "
            "claim, source, confidence, reasoning"
        )
        try:
            raw = await _call_llm([
                {"role": "system", "content": (
                    "You are a precise due-diligence analyst. Your job is to verify claims "
                    "and correctly attribute their source. Claims directly stated in the pitch "
                    "deck should be marked 'high' confidence for sourcing (the deck is the source). "
                    "External market claims need independent verification. "
                    "Return only valid JSON."
                )},
                {"role": "user", "content": prompt},
            ], use_extraction_model=True)
            data = _parse_json_from_llm(raw)
            if not isinstance(data, list):
                data = data.get("verifications", data.get("claims", []))
            return [
                ClaimVerification(
                    claim=v.get("claim", ""),
                    source=v.get("source", "Pitch Deck"),
                    confidence=v.get("confidence", "unverified"),
                    reasoning=v.get("reasoning", ""),
                )
                for v in data[:15]
                if isinstance(v, dict) and v.get("claim")
            ]
        except Exception:
            logger.warning("Claim verification failed", exc_info=True)
            return []

    async def _verify_claims_and_extract_competitors(
        self,
        extraction: StructuredExtraction,
        pitch_text: str,
        startup_info: StartupInfo,
    ) -> tuple[list[ClaimVerification], list[Competitor]]:
        """COMBINED LLM call: verify claims AND extract competitors from deck in one shot."""
        claims_text = ""
        if extraction.key_metrics:
            claims_text = "\n".join(
                f"- {c.text} (Source: {c.source})" for c in extraction.key_metrics[:10]
            )

        prompt = (
            f"You are analyzing the pitch deck of '{extraction.startup_name}' "
            f"({extraction.product}) in the {extraction.industry} industry.\n\n"
            "Do TWO tasks in a single response:\n\n"
            "═══ TASK 1: CLAIM VERIFICATION ═══\n"
        )
        if claims_text:
            prompt += (
                f"Verify these claims:\n{claims_text}\n\n"
                "Rules:\n"
                "- Deck-sourced data (TAM, ARR, customers stated in deck) → 'high' confidence\n"
                "- External/market claims without evidence → 'medium' or 'low'\n"
                "- Never mark deck-sourced data as 'low'\n\n"
            )
        else:
            prompt += "No specific claims to verify. Return empty claims array.\n\n"

        prompt += (
            "═══ TASK 2: COMPETITOR EXTRACTION ═══\n"
            "Extract ONLY competitors explicitly mentioned in this pitch deck text.\n"
            "Look for sections like 'Competition', 'Competitive Landscape', 'vs', etc.\n"
            "If no competitors are mentioned, return empty array.\n\n"
            f"Pitch text (first 5000 chars):\n{pitch_text[:5000]}\n\n"
            "Return ONLY valid JSON with this exact structure:\n"
            '{"claims": [{"claim": "...", "source": "...", "confidence": "high|medium|low", '
            '"reasoning": "..."}], '
            '"competitors": [{"name": "...", "description": "...", "funding": null, '
            '"differentiator": "..."}]}'
        )
        try:
            raw = await _call_llm([
                {"role": "system", "content": (
                    "You are a VC due-diligence analyst. Perform both tasks precisely. "
                    "For claims, correctly attribute sources. For competitors, only extract "
                    "companies explicitly named in the deck. Return only valid JSON."
                )},
                {"role": "user", "content": prompt},
            ], use_extraction_model=True)
            data = _parse_json_from_llm(raw)

            # Parse claims
            claims_raw = data.get("claims", [])
            if not isinstance(claims_raw, list):
                claims_raw = []
            claims = [
                ClaimVerification(
                    claim=v.get("claim", ""),
                    source=v.get("source", "Pitch Deck"),
                    confidence=v.get("confidence", "unverified"),
                    reasoning=v.get("reasoning", ""),
                )
                for v in claims_raw[:15]
                if isinstance(v, dict) and v.get("claim")
            ]

            # Parse competitors
            comps_raw = data.get("competitors", [])
            if not isinstance(comps_raw, list):
                comps_raw = []
            competitors = [
                Competitor(
                    name=c.get("name") or "Unknown",
                    description=c.get("description") or "Competitor",
                    funding=c.get("funding"),
                    differentiator=c.get("differentiator"),
                )
                for c in comps_raw[:5]
                if isinstance(c, dict) and c.get("name")
            ]

            return claims, competitors
        except Exception:
            logger.warning("Combined claims+competitors call failed", exc_info=True)
            return [], []

    @staticmethod
    def _compute_confidence(
        extraction: StructuredExtraction,
        market_results: list[SearchResult],
        competitors: list[Competitor],
    ) -> dict[str, str]:
        """Compute confidence scores for each analysis dimension."""
        scores: dict[str, str] = {}

        # Startup identity
        if extraction.startup_name and extraction.startup_name != "Unknown Startup":
            scores["startup_identity"] = "high"
        else:
            scores["startup_identity"] = "low"

        # Market estimate
        if extraction.tam:
            scores["market_estimate"] = "high" if market_results else "medium"
        else:
            scores["market_estimate"] = "low" if not market_results else "medium"

        # Traction data
        has_traction = any([extraction.arr, extraction.mrr, extraction.customers, extraction.growth])
        scores["traction_data"] = "high" if has_traction else "low"

        # Competitive landscape
        if len(competitors) >= 3:
            scores["competitive_landscape"] = "high"
        elif len(competitors) >= 1:
            scores["competitive_landscape"] = "medium"
        else:
            scores["competitive_landscape"] = "low"

        # Team info
        scores["team_info"] = "high" if extraction.founding_team else "low"

        # Financial data
        has_financials = any([extraction.arr, extraction.mrr, extraction.funding_ask])
        scores["financial_data"] = "high" if has_financials else "low"

        return scores

    async def _extract_startup_info(self, pitch_text: str) -> StartupInfo:
        """Use LLM to extract structured startup info from pitch text.

        Uses a two-pass approach: first try with a very explicit prompt,
        then fall back to a simpler regex-based extraction if LLM fails.
        """
        # Send more text to the LLM — pitch decks often have the company name
        # on the first page and details spread across many pages
        text_for_llm = pitch_text[:8000]

        prompt = (
            "You are analyzing a startup pitch deck. Your ONLY job is to extract "
            "factual information that is EXPLICITLY written in the text below.\n\n"
            "STEP 1: Find the company/startup name. It is usually:\n"
            "  - On the first page or title slide\n"
            "  - In a header, logo text, or large text\n"
            "  - Before words like 'Inc', 'Ltd', 'AI', 'Health', 'Tech'\n"
            "  - Near phrases like 'About Us', 'Our Mission', 'Who We Are'\n\n"
            "STEP 2: Find what the company builds (product/service).\n"
            "STEP 3: Find the industry/sector.\n"
            "STEP 4: Find stage, team, traction numbers, and funding ask.\n\n"
            "CRITICAL RULES:\n"
            "- You MUST find the company name. Scan the ENTIRE text carefully.\n"
            "- NEVER return 'Unknown' for name if there is ANY company name in the text.\n"
            "- Extract EXACT text from the document, do not paraphrase.\n"
            "- For traction, include specific numbers (revenue, users, growth %).\n\n"
            f"PITCH DECK TEXT:\n{text_for_llm}\n\n"
            "Return ONLY valid JSON with keys: name, product, industry, stage, "
            "founding_team, traction, ask. Use null ONLY if truly not mentioned."
        )
        try:
            raw = await _call_llm([
                {"role": "system", "content": (
                    "You are an expert pitch deck analyst. You MUST extract the startup name, "
                    "product, and industry from the text. These are almost always present in "
                    "pitch decks. Scan carefully. Return only valid JSON."
                )},
                {"role": "user", "content": prompt},
            ], use_extraction_model=True)
            data = _parse_json_from_llm(raw)
            name = data.get("name") or self._guess_name_from_text(pitch_text)
            product = data.get("product") or self._guess_product_from_text(pitch_text)
            industry = data.get("industry") or "Technology"

            return StartupInfo(
                name=name or "Unnamed Startup",
                product=product or "Unspecified Product",
                industry=industry,
                stage=data.get("stage"),
                founding_team=data.get("founding_team"),
                traction=data.get("traction"),
                ask=data.get("ask"),
            )
        except Exception:
            logger.warning("LLM startup extraction failed, using text fallback", exc_info=True)
            # Fallback: try to extract basic info from the raw text
            name = self._guess_name_from_text(pitch_text)
            return StartupInfo(
                name=name or "Unnamed Startup",
                product=self._guess_product_from_text(pitch_text) or "Unspecified Product",
                industry="Technology",
            )


    @staticmethod
    def _guess_name_from_text(text: str) -> str | None:
        """Best-effort regex extraction of company name from first ~500 chars."""
        import re
        # The company name is usually one of the first prominent words
        # Look for capitalized multi-word names or names ending in common suffixes
        first_chunk = text[:500]
        # Try to find "CompanyName" patterns — capitalized words that aren't common English
        patterns = [
            r"(?:Welcome to|About|Introducing)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)",
            r"^([A-Z][A-Za-z]+(?:Med|AI|Health|Tech|Labs|io))\b",
            r"\b([A-Z][a-z]+(?:Med|AI|Health|Tech|Labs|io))\b",
        ]
        for pat in patterns:
            m = re.search(pat, first_chunk, re.MULTILINE)
            if m:
                return m.group(1).strip()
        return None

    @staticmethod
    def _guess_product_from_text(text: str) -> str | None:
        """Best-effort extraction of product description from text."""
        import re
        first_chunk = text[:1000].lower()
        # Look for common product description patterns
        patterns = [
            r"(?:we build|we develop|we provide|our product|our platform|our solution)[:\s]+([^.]+)",
            r"(?:is a|is an)\s+([^.]+(?:platform|solution|tool|system|engine|app))",
        ]
        for pat in patterns:
            m = re.search(pat, first_chunk)
            if m:
                return m.group(1).strip().capitalize()
        return None

    async def _search_market_data(self, startup_info: StartupInfo) -> list[SearchResult]:
        """Search for market size and growth data."""
        queries = [
            f"{startup_info.industry} market size TAM",
            f"{startup_info.industry} market growth forecast",
        ]
        results: list[SearchResult] = []
        for q in queries:
            results.extend(await self.search_web(q))
        return results

    async def _estimate_market_size(
        self, startup_info: StartupInfo, search_results: list[SearchResult],
        deck_market: MarketSize | None = None,
    ) -> MarketSize:
        """Use LLM to estimate TAM/SAM/SOM, preserving any values already extracted from the deck."""
        context = "\n".join(
            f"- {r.title}: {r.snippet}" for r in search_results
        ) if search_results else "No web search results available."

        # Tell the LLM what we already know from the deck
        known_parts = []
        if deck_market:
            if deck_market.tam != "Unknown":
                known_parts.append(f"TAM from pitch deck: {deck_market.tam}")
            if deck_market.sam != "Unknown":
                known_parts.append(f"SAM from pitch deck: {deck_market.sam}")
            if deck_market.som != "Unknown":
                known_parts.append(f"SOM from pitch deck: {deck_market.som}")
        known_str = "\n".join(known_parts) if known_parts else "No market data found in pitch deck."

        prompt = (
            f"We are analyzing '{startup_info.product}' in the {startup_info.industry} industry.\n\n"
            f"Data already extracted from the pitch deck:\n{known_str}\n\n"
            f"Additional web research:\n{context}\n\n"
            "IMPORTANT RULES:\n"
            "- If a TAM, SAM, or SOM value was already extracted from the pitch deck, USE THAT EXACT VALUE. Do not change it.\n"
            "- Only estimate values that are marked as 'Unknown'.\n"
            "- For estimated values, clearly mark them as estimates.\n\n"
            "Return ONLY valid JSON with keys: tam, sam, som, sources. "
            "tam/sam/som should be human-readable strings (e.g. '$50B'). "
            "sources should be a list of source descriptions."
        )
        try:
            raw = await _call_llm([
                {"role": "system", "content": "You are a market research analyst. Prioritize data from the pitch deck. Only estimate missing values. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ])
            data = _parse_json_from_llm(raw)

            # Prefer deck values over LLM estimates
            tam = deck_market.tam if (deck_market and deck_market.tam != "Unknown") else data.get("tam", "Unknown")
            sam = deck_market.sam if (deck_market and deck_market.sam != "Unknown") else data.get("sam", "Unknown")
            som = deck_market.som if (deck_market and deck_market.som != "Unknown") else data.get("som", "Unknown")
            
            # Parse sources - handle both string and dict formats
            sources_raw = data.get("sources", [])
            sources = []
            for src in sources_raw:
                if isinstance(src, str):
                    sources.append(src)
                elif isinstance(src, dict):
                    # Convert dict to string description
                    title = src.get("title", "")
                    desc = src.get("description", "")
                    sources.append(f"{title}: {desc}" if desc else title)

            return MarketSize(
                tam=tam, sam=sam, som=som,
                sources=sources,
            )
        except Exception:
            logger.warning("Market size estimation failed, using fallback", exc_info=True)
            if deck_market and deck_market.tam != "Unknown":
                return deck_market
            return MarketSize(tam="Unknown", sam="Unknown", som="Unknown", sources=[])

    async def _extract_market_size_from_deck(self, pitch_text: str) -> MarketSize:
        """Extract TAM/SAM/SOM directly from the pitch deck text."""
        prompt = (
            "Extract the market size numbers (TAM, SAM, SOM) DIRECTLY from this pitch deck text.\n\n"
            "CRITICAL RULES:\n"
            "- ONLY extract numbers that are explicitly stated in the text.\n"
            "- Do NOT estimate, calculate, or invent any numbers.\n"
            "- If a value is not explicitly mentioned, use 'Unknown'.\n"
            "- Look for patterns like '$47B', '$8.2B', '$340M', 'TAM of $X', 'market size $X', etc.\n"
            "- Also look for labels like 'Total Addressable Market', 'Serviceable Addressable Market', "
            "'Serviceable Obtainable Market'.\n\n"
            f"Pitch text:\n{pitch_text[:6000]}\n\n"
            "Return ONLY valid JSON with keys: tam, sam, som, sources. "
            "Use the exact numbers from the deck. sources should describe where in the deck you found each number."
        )
        try:
            raw = await _call_llm([
                {"role": "system", "content": (
                    "You are a precise data extractor. Extract ONLY numbers that are explicitly written "
                    "in the document. Never estimate or invent numbers. If a number is not in the text, "
                    "return 'Unknown'. Return only valid JSON."
                )},
                {"role": "user", "content": prompt},
            ], use_extraction_model=True)
            data = _parse_json_from_llm(raw)
            return MarketSize(
                tam=data.get("tam", "Unknown"),
                sam=data.get("sam", "Unknown"),
                som=data.get("som", "Unknown"),
                sources=data.get("sources", ["Extracted from pitch deck"]),
            )
        except Exception:
            logger.warning("Deck market size extraction failed", exc_info=True)
            return MarketSize(tam="Unknown", sam="Unknown", som="Unknown", sources=[])

    async def _discover_competitors_grounded(
        self, pitch_text: str, startup_info: StartupInfo
    ) -> list[Competitor]:
        """Extract competitors from the pitch deck first, then enrich with web search."""
        # Step 1: Extract competitors mentioned in the pitch deck
        deck_competitors = await self._extract_competitors_from_deck(pitch_text, startup_info)

        # Step 2: Only do web search if deck gave us fewer than 3 competitors
        if len(deck_competitors) >= 3:
            return deck_competitors[:7]

        await asyncio.sleep(PIPELINE_PAUSE)
        web_competitors = await self.discover_competitors(startup_info)

        # Merge: deck competitors first, then add web ones that aren't duplicates
        seen_names = {c.name.lower() for c in deck_competitors}
        merged = list(deck_competitors)
        for c in web_competitors:
            if c.name.lower() not in seen_names:
                merged.append(c)
                seen_names.add(c.name.lower())

        return merged[:7]  # cap at 7

    async def _extract_competitors_from_deck(
        self, pitch_text: str, startup_info: StartupInfo
    ) -> list[Competitor]:
        """Extract competitors explicitly mentioned in the pitch deck."""
        prompt = (
            f"The startup '{startup_info.name}' builds '{startup_info.product}' "
            f"in the {startup_info.industry} industry.\n\n"
            "Extract ONLY the competitors that are explicitly mentioned or named in this pitch deck text.\n\n"
            "CRITICAL RULES:\n"
            "- ONLY include companies that are actually named in the text as competitors.\n"
            "- Do NOT invent or guess competitors.\n"
            "- Look for sections like 'Competition', 'Competitive Landscape', 'Competitors', "
            "'vs', 'compared to', etc.\n"
            "- If no competitors are mentioned, return an empty array [].\n\n"
            f"Pitch text:\n{pitch_text[:6000]}\n\n"
            "Return ONLY a valid JSON array of objects with keys: name, description, funding, differentiator. "
            "Use null for unknown fields."
        )
        try:
            raw = await _call_llm([
                {"role": "system", "content": (
                    "You are a precise data extractor. Extract ONLY information explicitly stated "
                    "in the document. Never invent or guess. Return only valid JSON."
                )},
                {"role": "user", "content": prompt},
            ], use_extraction_model=True)
            data = _parse_json_from_llm(raw)
            if not isinstance(data, list):
                data = data.get("competitors", [])
            return [
                Competitor(
                    name=c.get("name") or "Unknown",
                    description=c.get("description") or "Competitor",
                    funding=c.get("funding"),
                    differentiator=c.get("differentiator"),
                )
                for c in data[:5]
            ]
        except Exception:
            logger.warning("Deck competitor extraction failed", exc_info=True)
            return []

    async def _extract_competitors(
        self, startup_info: StartupInfo, search_results: list[SearchResult]
    ) -> list[Competitor]:
        """Use LLM to extract competitor info from search results."""
        context = "\n".join(
            f"- {r.title}: {r.snippet}" for r in search_results
        )
        prompt = (
            f"Based on the following search results about competitors to "
            f"'{startup_info.name}' ({startup_info.product}) in the {startup_info.industry} industry, "
            "identify up to 5 actual competitor COMPANIES.\n\n"
            f"Search results:\n{context}\n\n"
            "CRITICAL RULES:\n"
            "- Only include actual companies/startups that build competing products.\n"
            "- Do NOT include media outlets, consulting firms, books, blogs, or news sources.\n"
            "- Do NOT include things like 'Deloitte', 'TechCabal', 'The Lean Startup', etc.\n"
            "- Each competitor must be a real company that offers a product in the same space.\n"
            "- If you cannot identify real competitors from the search results, return an empty array [].\n\n"
            "Return ONLY a valid JSON array of objects with keys: name, description, funding, differentiator. "
            "Use null for unknown fields."
        )
        try:
            raw = await _call_llm([
                {"role": "system", "content": (
                    "You are a competitive intelligence analyst. You MUST only return actual "
                    "companies that build competing products or services. NEVER include media "
                    "outlets, consulting firms, books, blogs, accelerators, or news sources. "
                    "If a search result mentions a company name, only include it if that company "
                    "actually builds a product that competes. Return only valid JSON."
                )},
                {"role": "user", "content": prompt},
            ])
            data = _parse_json_from_llm(raw)
            if not isinstance(data, list):
                data = data.get("competitors", [])
            return [
                Competitor(
                    name=c.get("name") or "Unknown",
                    description=c.get("description") or "Competitor",
                    funding=c.get("funding"),
                    differentiator=c.get("differentiator"),
                )
                for c in data[:5]
            ]
        except Exception:
            logger.warning("Competitor extraction failed, using fallback", exc_info=True)
            return []

    async def _competitors_from_pitch(self, startup_info: StartupInfo) -> list[Competitor]:
        """Fallback: ask LLM to infer competitors from startup info alone."""
        prompt = (
            f"The startup '{startup_info.name}' builds '{startup_info.product}' "
            f"in the {startup_info.industry} industry. "
            "List up to 3 likely competitors. "
            "Return ONLY a valid JSON array of objects with keys: name, description, funding, differentiator. "
            "Use null for unknown fields."
        )
        try:
            raw = await _call_llm([
                {"role": "system", "content": "You are a competitive intelligence analyst. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ])
            data = _parse_json_from_llm(raw)
            if not isinstance(data, list):
                data = data.get("competitors", [])
            return [
                Competitor(
                    name=c.get("name") or "Unknown",
                    description=c.get("description") or "Competitor",
                    funding=c.get("funding"),
                    differentiator=c.get("differentiator"),
                )
                for c in data[:3]
            ]
        except Exception:
            logger.warning("Pitch-only competitor inference failed", exc_info=True)
            return []

    async def _extract_traction(self, pitch_text: str) -> list[str]:
        """Extract traction signals from the structured extraction — NO LLM call needed."""
        signals = []
        # Pull from the pitch text using simple keyword matching
        import re
        # Look for common traction patterns
        patterns = [
            (r'(\d[\d,]*\+?\s*(?:users|customers|clients|merchants|farmers|businesses))', 'Customer count'),
            (r'(\$[\d,.]+[MBK]?\s*(?:ARR|MRR|revenue|GMV))', 'Revenue'),
            (r'([\d.]+[xX]\s*(?:MoM|YoY|growth|month[- ]over[- ]month|year[- ]over[- ]year))', 'Growth'),
            (r'(\d+%\s*(?:growth|increase|retention|conversion))', 'Growth metric'),
            (r'(raised?\s*\$[\d,.]+[MBK]?)', 'Funding'),
            (r'(partnership\s+with\s+\w[\w\s]*)', 'Partnership'),
        ]
        text_lower = pitch_text[:6000]
        for pat, label in patterns:
            matches = re.findall(pat, text_lower, re.IGNORECASE)
            for m in matches[:2]:
                signals.append(m.strip())
        return signals[:8] if signals else ["No explicit traction signals found in deck"]


    async def _build_ecosystem_and_benchmarks(
        self,
        extraction: StructuredExtraction,
        startup_info: StartupInfo,
        competitors: list[Competitor],
    ) -> tuple[EcosystemMap | None, MarketBenchmark | None]:
        """COMBINED LLM call: ecosystem map + market benchmarking in one shot."""
        if not competitors:
            return None, None

        competitor_details = "\n".join(
            f"- {c.name}: {c.description}" for c in competitors
        )

        # Gather web data for benchmarking (DuckDuckGo, no LLM)
        comp_names = [c.name for c in competitors[:4]]
        search_results: list[SearchResult] = []
        for name in comp_names[:2]:
            results = await self.search_web(
                f"{name} {startup_info.industry} revenue funding valuation 2024 2025"
            )
            search_results.extend(results)
        sector_results = await self.search_web(
            f"{startup_info.industry} startup benchmarks median revenue growth 2024 2025"
        )
        search_results.extend(sector_results)

        web_context = "\n".join(
            f"- {r.title}: {r.snippet}" for r in search_results[:10]
        ) if search_results else "No web data found."

        # Startup metrics from deck
        startup_metrics = []
        if extraction.arr:
            startup_metrics.append(f"ARR: {extraction.arr}")
        if extraction.mrr:
            startup_metrics.append(f"MRR: {extraction.mrr}")
        if extraction.growth:
            startup_metrics.append(f"Growth: {extraction.growth}")
        if extraction.customers:
            startup_metrics.append(f"Customers: {extraction.customers}")
        if extraction.funding_ask:
            startup_metrics.append(f"Raising: {extraction.funding_ask}")
        startup_data = "\n".join(startup_metrics) if startup_metrics else "Limited data from deck."

        prompt = (
            f"You are analyzing '{startup_info.name}' ({startup_info.product}) "
            f"in the {startup_info.industry} industry.\n\n"
            f"Competitors:\n{competitor_details}\n\n"
            f"Startup metrics from deck:\n{startup_data}\n\n"
            f"Web research on competitors:\n{web_context}\n\n"
            "Do TWO tasks in a single response:\n\n"
            "═══ TASK 1: ECOSYSTEM MAP ═══\n"
            f"Group ALL companies (including '{startup_info.name}') into 2-5 market segments.\n"
            f"'{startup_info.name}' MUST appear in at least one category.\n\n"
            "═══ TASK 2: MARKET BENCHMARKING ═══\n"
            "Create 3-5 benchmark categories (Revenue Multiple, Growth Rate, Customer Count, "
            "Funding Raised, etc.). Include the startup + competitors + sector median.\n"
            "For the startup, use ONLY deck data. For competitors, use web research.\n"
            "Mark estimates with '~' prefix. Include startup_percentile and startup_verdict.\n\n"
            "CRITICAL — NORMALIZE ALL GROWTH METRICS:\n"
            "- Convert ALL growth rates to the SAME time scale (annualized / YoY).\n"
            "- Use the CORRECT compound formula: (1 + monthly_rate)^12 - 1\n"
            "  Example: 18% MoM → (1.18)^12 - 1 = 6.44 = 644% YoY. NOT 18×12.\n"
            "  Example: 4.1x MoM means +310% MoM → (4.1)^12 ≈ enormous. State 'Hypergrowth (4.1x MoM)'.\n"
            "  Example: 10% MoM → (1.10)^12 - 1 = 2.14 = 214% YoY.\n"
            "- If a competitor reports '20% YoY', keep as-is.\n"
            "- Always show the normalized annual rate FIRST, then the original in parentheses.\n"
            "- This ensures apples-to-apples comparison across all entities.\n\n"
            "CRITICAL — METRIC CONSISTENCY PER CATEGORY:\n"
            "- Each benchmark category MUST compare the EXACT SAME metric type for ALL entities.\n"
            "- If the category is 'Revenue Multiple', every entry must be a revenue multiple (valuation/revenue).\n"
            "  Do NOT mix revenue multiples with raw revenue numbers or growth rates.\n"
            "- If the category is 'Growth Rate', every entry must be a growth rate (% YoY).\n"
            "  Do NOT mix growth rates with absolute revenue or funding amounts.\n"
            "- If the category is 'Funding Raised', every entry must be a dollar amount of funding.\n"
            "- If you cannot find the SAME metric for a competitor, use 'N/A' as the value.\n"
            "  Do NOT substitute a different metric to fill the gap.\n"
            "- WRONG: Revenue Multiple category with entries '8.6x', '$2.35B', '15%'\n"
            "- RIGHT: Revenue Multiple category with entries '8.6x', '12.3x', 'N/A', '10.1x'\n\n"
            "Return ONLY valid JSON:\n"
            '{"ecosystem": {"categories": [{"name": "Segment", "companies": ["Co1", "Co2"]}]}, '
            '"benchmarks": {"categories": [{"metric_name": "Growth Rate", '
            '"startup_percentile": "Top 25%", "startup_verdict": "Above Average", '
            '"entries": [{"entity": "StartupName", "value": "~644% YoY (18% MoM)", '
            '"source": "Pitch Deck", "is_startup": true, "is_median": false}, '
            '{"entity": "Competitor", "value": "20% YoY", "source": "Web Research", '
            '"is_startup": false, "is_median": false}]}], '
            '"overall_position": "One sentence summary"}}'
        )
        try:
            raw = await _call_llm([
                {"role": "system", "content": (
                    "You are a VC research analyst. Build both an ecosystem map and competitive "
                    "benchmarks. Use real data. For the startup, only use deck data. "
                    "Return only valid JSON."
                )},
                {"role": "user", "content": prompt},
            ])
            data = _parse_json_from_llm(raw)

            # Parse ecosystem map
            ecosystem_map = None
            eco_data = data.get("ecosystem", {})
            if isinstance(eco_data, dict):
                eco_cats = eco_data.get("categories", [])
                if isinstance(eco_cats, list) and eco_cats:
                    categories = [
                        EcosystemCategory(
                            name=cat.get("name", "Other"),
                            companies=cat.get("companies", []),
                        )
                        for cat in eco_cats
                        if isinstance(cat, dict) and cat.get("companies")
                    ]
                    if categories:
                        ecosystem_map = EcosystemMap(
                            startup_name=startup_info.name,
                            categories=categories,
                        )

            # Parse benchmarks
            market_benchmark = None
            bench_data = data.get("benchmarks", {})
            if isinstance(bench_data, dict):
                bench_cats = bench_data.get("categories", [])
                if isinstance(bench_cats, list) and bench_cats:
                    bm_categories = []
                    for cat in bench_cats:
                        if not isinstance(cat, dict):
                            continue
                        entries_raw = cat.get("entries", [])
                        if not isinstance(entries_raw, list) or not entries_raw:
                            continue
                        entries = [
                            BenchmarkMetric(
                                entity=e.get("entity", "Unknown"),
                                value=str(e.get("value", "N/A")),
                                source=e.get("source", "Web Research"),
                                is_startup=bool(e.get("is_startup", False)),
                                is_median=bool(e.get("is_median", False)),
                            )
                            for e in entries_raw
                            if isinstance(e, dict) and e.get("entity")
                        ]
                        if entries:
                            bm_categories.append(BenchmarkCategory(
                                metric_name=cat.get("metric_name", "Unknown"),
                                entries=entries,
                                startup_percentile=cat.get("startup_percentile"),
                                startup_verdict=cat.get("startup_verdict"),
                            ))
                    if bm_categories:
                        bm_categories = _validate_benchmark_categories(bm_categories)
                    if bm_categories:
                        market_benchmark = MarketBenchmark(
                            startup_name=startup_info.name,
                            categories=bm_categories,
                            overall_position=bench_data.get("overall_position"),
                        )

            return ecosystem_map, market_benchmark
        except Exception:
            logger.warning("Combined ecosystem+benchmarks call failed", exc_info=True)
            return None, None

    async def _build_ecosystem_map(
        self, startup_info: StartupInfo, competitors: list[Competitor]
    ) -> EcosystemMap | None:
        """Build a competitor ecosystem map grouped by market category."""
        if not competitors:
            return None

        competitor_details = "\n".join(
            f"- {c.name}: {c.description}" for c in competitors
        )

        prompt = (
            f"The startup '{startup_info.name}' builds '{startup_info.product}' "
            f"in the {startup_info.industry} industry.\n\n"
            f"Here are the competitors:\n{competitor_details}\n\n"
            "Group ALL these companies (including the startup itself) into market "
            "categories/segments. Each category should represent a distinct market "
            "segment where these companies operate.\n\n"
            "RULES:\n"
            f"- The startup '{startup_info.name}' MUST appear in at least one category.\n"
            "- Each competitor should appear in the category that best fits them.\n"
            "- A company can appear in multiple categories if relevant.\n"
            "- Use 2-5 categories. Keep category names short (2-4 words).\n"
            "- Categories should be specific market segments, not generic labels.\n\n"
            "Return ONLY valid JSON with this structure:\n"
            '{"categories": [{"name": "Category Name", "companies": ["Company1", "Company2"]}]}'
        )
        try:
            raw = await _call_llm([
                {"role": "system", "content": (
                    "You are a market analyst building a competitive ecosystem map. "
                    "Group companies into meaningful market segments. Return only valid JSON."
                )},
                {"role": "user", "content": prompt},
            ], use_extraction_model=True)
            data = _parse_json_from_llm(raw)
            categories_raw = data.get("categories", [])
            if not isinstance(categories_raw, list):
                return None

            categories = [
                EcosystemCategory(
                    name=cat.get("name", "Other"),
                    companies=cat.get("companies", []),
                )
                for cat in categories_raw
                if isinstance(cat, dict) and cat.get("companies")
            ]

            if not categories:
                return None

            return EcosystemMap(
                startup_name=startup_info.name,
                categories=categories,
            )
        except Exception:
            logger.warning("Ecosystem map generation failed", exc_info=True)
            return None

    async def _build_market_benchmarks(
        self,
        extraction: StructuredExtraction,
        startup_info: StartupInfo,
        competitors: list[Competitor],
    ) -> MarketBenchmark | None:
        """Build live market benchmarks — startup vs competitors and sector medians.

        Uses web search to find competitor financials, then LLM to synthesize
        a structured comparison table.
        """
        if not competitors:
            return None

        # Gather competitor names for search
        comp_names = [c.name for c in competitors[:5]]

        # Search for competitor financials
        search_results: list[SearchResult] = []
        for name in comp_names[:3]:  # limit to 3 searches to stay within rate limits
            results = await self.search_web(
                f"{name} {startup_info.industry} revenue funding valuation 2024 2025"
            )
            search_results.extend(results)

        # Also search for sector benchmarks
        sector_results = await self.search_web(
            f"{startup_info.industry} startup benchmarks median revenue growth rate 2024 2025"
        )
        search_results.extend(sector_results)

        web_context = "\n".join(
            f"- {r.title}: {r.snippet}" for r in search_results[:15]
        ) if search_results else "No web data found."

        # Build deck-known metrics for the startup
        startup_metrics = []
        if extraction.arr:
            startup_metrics.append(f"ARR: {extraction.arr}")
        if extraction.mrr:
            startup_metrics.append(f"MRR: {extraction.mrr}")
        if extraction.growth:
            startup_metrics.append(f"Growth: {extraction.growth}")
        if extraction.customers:
            startup_metrics.append(f"Customers: {extraction.customers}")
        if extraction.funding_ask:
            startup_metrics.append(f"Raising: {extraction.funding_ask}")
        if extraction.tam:
            startup_metrics.append(f"TAM: {extraction.tam}")

        startup_data = "\n".join(startup_metrics) if startup_metrics else "Limited data from deck."

        prompt = (
            f"You are building an ADVANCED competitive benchmarking table for '{startup_info.name}' "
            f"({startup_info.product}) in the {startup_info.industry} industry.\n\n"
            f"Startup's known metrics from pitch deck:\n{startup_data}\n\n"
            f"Competitors: {', '.join(comp_names)}\n\n"
            f"Web research on competitors and sector:\n{web_context}\n\n"
            "Create a benchmarking comparison with 3-5 metric categories. "
            "Good categories include:\n"
            "- Revenue Multiple (valuation / ARR)\n"
            "- Growth Rate (MoM or YoY)\n"
            "- Customer Count\n"
            "- Funding Raised\n"
            "- Market Share\n"
            "- Unit Economics (CAC, LTV, etc.)\n\n"
            "RULES:\n"
            "- Include the startup AND at least 2 competitors in each category.\n"
            "- Include a 'Sector Median' entry where possible.\n"
            "- Use REAL data from the web research. If you can't find exact numbers, "
            "use reasonable estimates and mark them with '~' prefix (e.g. '~$5M').\n"
            "- For the startup, use ONLY data from the pitch deck. Never invent startup numbers.\n"
            "- Each entry needs: entity, value, source, is_startup (bool), is_median (bool).\n"
            "- Keep values short and readable (e.g. '10x', '$2M ARR', '4.1x MoM').\n\n"
            "FOR EACH CATEGORY, also include:\n"
            "- startup_percentile: Where the startup ranks (e.g. 'Top 10%', 'Top 25%', "
            "'Median', 'Bottom 40%', 'Bottom 25%'). Base this on comparing the startup's "
            "value against the competitors and sector median.\n"
            "- startup_verdict: One of 'Outperforming', 'Above Average', 'At Par', "
            "'Below Average', 'Underperforming'. Be honest.\n\n"
            "Also include an 'overall_position' field — a one-sentence summary of where "
            "the startup stands overall vs its competitive set.\n\n"
            "Return ONLY valid JSON:\n"
            '{"categories": [{"metric_name": "Revenue Multiple", '
            '"startup_percentile": "Top 25%", "startup_verdict": "Above Average", '
            '"entries": [{"entity": "CompanyName", "value": "10x", "source": "Web Research", '
            '"is_startup": false, "is_median": false}]}], '
            '"overall_position": "Competitive on growth but trailing on revenue multiples"}'
        )
        try:
            raw = await _call_llm([
                {"role": "system", "content": (
                    "You are a VC research analyst building competitive benchmarking tables. "
                    "Use real data from web research. For the startup, only use deck data. "
                    "Be precise with numbers. Return only valid JSON."
                )},
                {"role": "user", "content": prompt},
            ])
            data = _parse_json_from_llm(raw)
            categories_raw = data.get("categories", [])
            if not isinstance(categories_raw, list) or not categories_raw:
                return None

            categories = []
            for cat in categories_raw:
                if not isinstance(cat, dict):
                    continue
                entries_raw = cat.get("entries", [])
                if not isinstance(entries_raw, list) or not entries_raw:
                    continue
                entries = [
                    BenchmarkMetric(
                        entity=e.get("entity", "Unknown"),
                        value=str(e.get("value", "N/A")),
                        source=e.get("source", "Web Research"),
                        is_startup=bool(e.get("is_startup", False)),
                        is_median=bool(e.get("is_median", False)),
                    )
                    for e in entries_raw
                    if isinstance(e, dict) and e.get("entity")
                ]
                if entries:
                    categories.append(BenchmarkCategory(
                        metric_name=cat.get("metric_name", "Unknown"),
                        entries=entries,
                        startup_percentile=cat.get("startup_percentile"),
                        startup_verdict=cat.get("startup_verdict"),
                    ))

            if not categories:
                return None

            return MarketBenchmark(
                startup_name=startup_info.name,
                categories=categories,
                overall_position=data.get("overall_position"),
            )
        except Exception:
            logger.warning("Market benchmarking failed", exc_info=True)
            return None

    @staticmethod
    def _format_raw_research(
        market_results: list[SearchResult],
        competitor_results: list[SearchResult],
    ) -> str:
        """Format raw search results into a readable string for downstream agents."""
        sections: list[str] = []
        if market_results:
            sections.append("## Market Research\n")
            for r in market_results:
                sections.append(f"- [{r.title}]({r.url}): {r.snippet}")
        if competitor_results:
            sections.append("\n## Competitor Research\n")
            for r in competitor_results:
                sections.append(f"- [{r.title}]({r.url}): {r.snippet}")
        return "\n".join(sections) if sections else "No web research results available."
