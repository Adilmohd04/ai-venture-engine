"""AI Agents and pipeline orchestrator for the Venture Intelligence Engine.

Implements the OpenRouter API client, specialized debate agents (Bull, Bear,
Bull Rebuttal, Bear Rebuttal, Risk Engine, Judge), and the sequential pipeline
orchestrator that streams AgentEvent objects via SSE.
"""

import asyncio
import json
import os
import re
from typing import AsyncGenerator

import httpx

from models import (
    AgentEvent,
    DebateResult,
    ResearchResult,
    RiskAnalysis,
    RiskSignal,
    ScoreBreakdown,
    JudgeVerdict,
)
from financial_calculator import compute_financial_signals, format_financial_context

# Disable SSL verification — Windows Python 3.14 has broken cert chain
SSL_VERIFY = False

# ---------------------------------------------------------------------------
# Environment defaults
# ---------------------------------------------------------------------------
DEFAULT_MODEL = "llama-3.3-70b-versatile"
REQUEST_TIMEOUT = 120.0
MAX_RETRIES = 3  # per provider
RATE_LIMIT_PAUSE = 3  # seconds between agent stages (reduced — load is spread across providers)
RATE_LIMIT_PAUSE_PRIORITY = 1  # seconds for priority (pro/business) users

# Plan-based pause mapping: business gets fastest processing, free gets standard
PAUSE_BY_PLAN = {"business": 1, "pro": 2, "free": 3}

# Multi-provider config — round-robin across 4 providers
# Cerebras promoted to #2 since HuggingFace free tier is exhausted (402)
STREAM_PROVIDERS = [
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

# Round-robin counter for streaming calls
_stream_provider_counter = 0
# Providers that returned 401/403/404 are blacklisted for the session
_stream_blacklisted: set[str] = set()


# ---------------------------------------------------------------------------
# Task 5.1 – Multi-provider streaming client
# ---------------------------------------------------------------------------
async def call_openrouter_streaming(
    model: str,
    api_key: str,
    messages: list[dict],
    temperature: float = 0.7,
    provider_hint: int | None = None,
) -> AsyncGenerator[str, None]:
    """Stream tokens with round-robin provider selection + failover.

    Each call picks the next provider in rotation. If that provider fails,
    it falls through to the remaining providers.
    """
    global _stream_provider_counter

    # Pick starting provider via round-robin or explicit hint
    if provider_hint is not None:
        start_idx = provider_hint % len(STREAM_PROVIDERS)
    else:
        start_idx = _stream_provider_counter % len(STREAM_PROVIDERS)
        _stream_provider_counter += 1

    provider_order = [STREAM_PROVIDERS[(start_idx + i) % len(STREAM_PROVIDERS)] for i in range(len(STREAM_PROVIDERS))]

    for provider in provider_order:
        if provider["name"] in _stream_blacklisted:
            continue

        p_key = os.environ.get(provider["key_env"], "").strip()
        if not p_key:
            continue

        p_model = os.environ.get(provider["model_env"], provider["default_model"])
        p_url = provider["url"]

        headers = {
            "Authorization": f"Bearer {p_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": p_model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
        }

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, verify=SSL_VERIFY) as client:
                    async with client.stream(
                        "POST", p_url, json=payload, headers=headers
                    ) as response:
                        response.raise_for_status()
                        import logging as _log
                        _log.getLogger(__name__).info(
                            "Streaming on %s (model=%s)", provider["name"], p_model,
                        )
                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            if line == "data: [DONE]":
                                return
                            try:
                                chunk = json.loads(line[6:])
                                content = (
                                    chunk.get("choices", [{}])[0]
                                    .get("delta", {})
                                    .get("content", "")
                                )
                                if content:
                                    yield content
                            except (json.JSONDecodeError, IndexError, KeyError):
                                continue
                        return  # stream finished normally
            except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as exc:
                last_error = exc
                if isinstance(exc, httpx.HTTPStatusError):
                    status = exc.response.status_code
                    if status == 429:
                        import logging as _log
                        wait = 2 * (attempt + 1)
                        _log.getLogger(__name__).warning(
                            "%s streaming 429 (attempt %d/%d) — waiting %ds",
                            provider["name"], attempt + 1, MAX_RETRIES, wait,
                        )
                        await asyncio.sleep(wait)
                        if attempt == MAX_RETRIES - 1:
                            break  # next provider
                    elif status in (401, 402, 403, 404):
                        import logging as _log
                        _log.getLogger(__name__).warning(
                            "%s streaming %d — blacklisting for session", provider["name"], status,
                        )
                        _stream_blacklisted.add(provider["name"])
                        break  # don't retry billing/auth errors, move to next provider
                elif attempt < MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    await asyncio.sleep(wait)

    raise RuntimeError("All LLM providers failed for streaming")


# ---------------------------------------------------------------------------
# Task 5.2 – Agent classes
# ---------------------------------------------------------------------------
class BaseAgent:
    """Base class for all debate / analysis agents."""

    system_prompt: str = ""

    def __init__(self, name: str, avatar: str, model: str, api_key: str):
        self.name = name
        self.avatar = avatar
        self.model = model
        self.api_key = api_key

    def _build_user_message(self, context: dict) -> str:
        """Format the accumulated context into a single user message."""
        parts: list[str] = []
        if "pitch" in context:
            parts.append(f"## Pitch Deck\n{context['pitch']}")
        if "structured_extraction" in context:
            se = context["structured_extraction"]
            if isinstance(se, dict):
                se_lines = [f"## Structured Extraction (Knowledge Graph)"]
                for k, v in se.items():
                    if v and k not in ("key_metrics", "missing_info"):
                        se_lines.append(f"- **{k}**: {v}")
                if se.get("key_metrics"):
                    se_lines.append("\n### Key Metrics with Citations")
                    for m in se["key_metrics"]:
                        if isinstance(m, dict):
                            se_lines.append(f"- {m.get('text', '')} (Source: {m.get('source', 'N/A')}, Page {m.get('page', '?')})")
                if se.get("missing_info"):
                    se_lines.append("\n### Missing Information")
                    for mi in se["missing_info"]:
                        se_lines.append(f"- ⚠️ {mi}")
                parts.append("\n".join(se_lines))
        if "research" in context:
            research = context["research"]
            if isinstance(research, dict):
                parts.append(f"## Research Summary\n{json.dumps(research, indent=2)}")
            else:
                parts.append(f"## Research Summary\n{research}")
        if "bull_case" in context:
            parts.append(f"## Bull Case\n{context['bull_case']}")
        if "bear_case" in context:
            parts.append(f"## Bear Case\n{context['bear_case']}")
        if "bull_rebuttal" in context:
            parts.append(f"## Bull Rebuttal\n{context['bull_rebuttal']}")
        if "bear_rebuttal" in context:
            parts.append(f"## Bear Rebuttal\n{context['bear_rebuttal']}")
        if "risks" in context:
            risks = context["risks"]
            if isinstance(risks, dict):
                parts.append(f"## Risk Analysis\n{json.dumps(risks, indent=2)}")
            else:
                parts.append(f"## Risk Analysis\n{risks}")
        if "benchmarks" in context:
            bm = context["benchmarks"]
            if isinstance(bm, dict) and bm.get("categories"):
                bm_lines = [f"## Market Benchmarking: {bm.get('startup_name', 'Startup')} vs Competitors"]
                for cat in bm["categories"]:
                    bm_lines.append(f"\n### {cat.get('metric_name', 'Metric')}")
                    for entry in cat.get("entries", []):
                        bm_lines.append(f"  - {entry.get('entity', '?')}: {entry.get('value', 'N/A')} ({entry.get('source', '')})")
                parts.append("\n".join(bm_lines))
        if "financial_signals" in context:
            parts.append(format_financial_context(context["financial_signals"]))
        return "\n\n".join(parts)

    async def analyze(self, context: dict) -> AsyncGenerator[str, None]:
        """Stream the agent's analysis token-by-token."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self._build_user_message(context)},
        ]
        async for token in call_openrouter_streaming(
            self.model, self.api_key, messages
        ):
            yield token


class BullAnalyst(BaseAgent):
    """Generates the strongest possible argument for the startup's success."""

    system_prompt = (
        "You are a venture capitalist making the strongest possible argument "
        "why this startup will succeed.\n\n"
        "CRITICAL — DO NOT FABRICATE FINANCIAL DATA:\n"
        "- ONLY use numbers explicitly stated in the pitch deck or research.\n"
        "- If burn rate, runway, CAC, LTV, or unit economics are NOT in the deck, say 'not disclosed'.\n"
        "- Do NOT estimate, infer, or calculate financial metrics not provided.\n"
        "- If you mention a number, it must be directly from the source material.\n\n"
        "METRIC INTERPRETATION:\n"
        "- NRR > 140% = Exceptional (top 1% of SaaS, emphasize this strongly)\n"
        "- NRR 120-140% = Elite (top 5%, major competitive advantage)\n"
        "- Government contracts (DARPA, DoD) for defense tech = Strong validation + barrier to entry\n"
        "- Security clearances (SECRET, TOP SECRET) = Significant moat\n"
        "- Proprietary datasets > 1B records = Strong defensibility\n\n"
        "RULES:\n"
        "- Make 3-4 SPECIFIC arguments, each with concrete evidence from the deck.\n"
        "- For each argument, name the specific data point or fact that supports it.\n"
        "  GOOD: 'Their 18% MoM growth over 6 months shows strong product-market fit'\n"
        "  BAD: 'The market opportunity is strong'\n"
        "- Reference specific competitors by name when discussing market position.\n"
        "- If the deck mentions traction numbers, quote them exactly.\n"
        "- Keep it under 400 words. Quality over quantity.\n\n"
        "CONSISTENCY REQUIREMENTS:\n"
        "- Base your analysis on the structured extraction and research data provided\n"
        "- If the research shows exceptional indicators (elite metrics, government validation), emphasize them\n"
        "- Reference specific numbers and facts from the pitch deck"
    )

    def __init__(self, model: str, api_key: str):
        super().__init__("Bull Analyst", "📈", model, api_key)


class BearAnalyst(BaseAgent):
    """Generates skeptical arguments explaining why the startup will fail."""

    system_prompt = (
        "You are a skeptical venture capitalist explaining why this startup "
        "will likely fail.\n\n"
        "CRITICAL — DO NOT FABRICATE FINANCIAL DATA:\n"
        "- ONLY use numbers explicitly stated in the pitch deck or research.\n"
        "- If burn rate, runway, CAC, LTV, or unit economics are NOT in the deck, say 'not disclosed'.\n"
        "- Do NOT estimate, infer, or calculate financial metrics not provided.\n"
        "- If you mention a number, it must be directly from the source material.\n\n"
        "INDUSTRY-SPECIFIC CONTEXT:\n"
        "- Government contracts (DARPA, DoD) for defense tech = Validation, NOT dependency risk\n"
        "- Security clearances = Barrier to entry, NOT a weakness\n"
        "- Do NOT flag strong moat indicators as risks\n\n"
        "RULES:\n"
        "- Make 3-4 SPECIFIC arguments, each attacking a concrete weakness.\n"
        "- Name specific competitors and explain why they have an advantage.\n"
        "  GOOD: 'Headspace and Calm already dominate consumer distribution with "
        "  combined 100M+ downloads. CAC for new mental health apps is extremely high.'\n"
        "  BAD: 'The market is saturated.'\n"
        "- Attack the business model with specific reasoning, not generic concerns.\n"
        "  GOOD: 'B2B2C mental health requires enterprise sales cycles of 6-12 months, "
        "  but the team has no enterprise sales experience.'\n"
        "  BAD: 'Scaling will be difficult.'\n"
        "- If the deck is missing critical data (unit economics, CAC, churn), call it out.\n"
        "- Keep it under 400 words. Quality over quantity.\n\n"
        "CONSISTENCY REQUIREMENTS:\n"
        "- Base your analysis on the structured extraction and research data provided\n"
        "- Do NOT flag strong indicators as weaknesses\n"
        "- Reference specific numbers and facts from the pitch deck"
    )

    def __init__(self, model: str, api_key: str):
        super().__init__("Bear Analyst", "📉", model, api_key)


class BullRebuttal(BaseAgent):
    """Rebuts the bear case and defends the startup."""

    system_prompt = (
        "You are the bull rebuttal agent. Your ONLY job is to respond to the "
        "bear analyst's STRONGEST argument — the single most damaging point they made.\n\n"
        "CRITICAL — DO NOT FABRICATE FINANCIAL DATA:\n"
        "- ONLY use numbers explicitly stated in the pitch deck or research.\n"
        "- Do NOT estimate, infer, or calculate financial metrics not provided.\n\n"
        "RULES:\n"
        "- Identify the bear's #1 strongest argument and QUOTE IT EXACTLY.\n"
        "- Provide a specific, evidence-based counterargument to THAT point.\n"
        "- Do NOT repeat your earlier bull case arguments. Bring NEW evidence or reasoning.\n"
        "- Reference specific data from the pitch deck or research to support your rebuttal.\n"
        "- Keep it focused: 1 strong rebuttal > 5 weak ones.\n"
        "- If the bear raised a valid concern, acknowledge it but explain why it's manageable.\n"
        "- Keep it under 250 words."
    )

    def __init__(self, model: str, api_key: str):
        super().__init__("Bull Rebuttal", "⚔", model, api_key)

    def _build_user_message(self, context: dict) -> str:
        """Override to focus the LLM on the bear case it must rebut."""
        bear_case = context.get("bear_case", "No bear case provided.")
        bull_case = context.get("bull_case", "")
        pitch = context.get("pitch", "")[:3000]
        return (
            "## YOUR TASK\n"
            "Read the Bear Case below. Find the SINGLE STRONGEST argument the bear made. "
            "Quote it. Then destroy it with specific evidence.\n\n"
            "DO NOT repeat anything from the Bull Case. Bring NEW reasoning only.\n\n"
            f"## Bear Case (your opponent — rebut this)\n{bear_case}\n\n"
            f"## Bull Case (your earlier argument — do NOT repeat this)\n{bull_case}\n\n"
            f"## Pitch Deck (reference for evidence)\n{pitch}"
        )


class BearRebuttal(BaseAgent):
    """Rebuts the bull case and explains why risks remain significant."""

    system_prompt = (
        "You are the bear rebuttal agent. Your ONLY job is to respond to the "
        "bull analyst's STRONGEST argument — the single most compelling point they made.\n\n"
        "CRITICAL — DO NOT FABRICATE FINANCIAL DATA:\n"
        "- ONLY use numbers explicitly stated in the pitch deck or research.\n"
        "- Do NOT estimate, infer, or calculate financial metrics not provided.\n\n"
        "RULES:\n"
        "- Identify the bull's #1 strongest argument and QUOTE IT EXACTLY.\n"
        "- Explain specifically why that argument is weaker than it appears.\n"
        "- Use concrete reasoning. Example of a good rebuttal:\n"
        "  Bull says: 'WhatsApp distribution gives them viral growth.'\n"
        "  Your response: 'This advantage is fragile. WhatsApp is owned by Meta. "
        "  API restrictions, pricing changes, or policy shifts could disrupt the "
        "  entire distribution channel overnight. Building on a platform you don't "
        "  control is a structural risk, not a moat.'\n"
        "- Do NOT repeat your earlier bear case arguments. Bring NEW concerns or data.\n"
        "- Reference specific market data, competitor info, or missing evidence.\n"
        "- Keep it focused: 1 devastating counter > 5 generic worries.\n"
        "- If the bull made a genuinely strong point, acknowledge it but show the hidden risk.\n"
        "- Keep it under 250 words."
    )

    def __init__(self, model: str, api_key: str):
        super().__init__("Bear Rebuttal", "🛑", model, api_key)

    def _build_user_message(self, context: dict) -> str:
        """Override to focus the LLM on the bull case it must rebut."""
        bull_case = context.get("bull_case", "No bull case provided.")
        bear_case = context.get("bear_case", "")
        pitch = context.get("pitch", "")[:3000]
        return (
            "## YOUR TASK\n"
            "Read the Bull Case below. Find the SINGLE STRONGEST argument the bull made. "
            "Quote it. Then explain why it's weaker than it appears, using specific evidence.\n\n"
            "DO NOT repeat anything from the Bear Case. Bring NEW concerns only.\n\n"
            f"## Bull Case (your opponent — rebut this)\n{bull_case}\n\n"
            f"## Bear Case (your earlier argument — do NOT repeat this)\n{bear_case}\n\n"
            f"## Pitch Deck (reference for evidence)\n{pitch}"
        )


class JudgeAgent(BaseAgent):
    """Produces the final investment verdict, scoring, and reasoning."""

    system_prompt = (
        "You are a senior venture capital investment committee partner with 20 years of experience. "
        "You are known for being brutally honest and data-driven. You have seen thousands of pitches "
        "and know that most early-stage startups fail. Based on the full debate, produce a "
        "structured investment analysis.\n\n"
        "METRIC INTERPRETATION GUIDE:\n\n"
        "SaaS Metrics:\n"
        "- NRR 90-110% = Good (industry standard)\n"
        "- NRR 110-120% = Strong (above average)\n"
        "- NRR 120-140% = Elite (top 5% of SaaS companies)\n"
        "- NRR > 140% = Exceptional (top 1%, MUST emphasize this as a major strength)\n\n"
        "Growth Metrics:\n"
        "- 20-50% YoY = Healthy\n"
        "- 50-100% YoY = Strong\n"
        "- 100-200% YoY = Exceptional\n"
        "- > 200% YoY = Hyper-growth (verify sustainability)\n\n"
        "SCORING RUBRIC (0-10):\n"
        "- 8-10: Strong Buy (exceptional metrics, strong moat, clear path to scale)\n"
        "- 6-7.9: Buy (solid metrics, defensible position, good opportunity)\n"
        "- 4-5.9: Pass (concerning metrics or weak moat)\n"
        "- 0-3.9: Hard Pass (major red flags or deal breakers)\n\n"
        "SCORING GUIDELINES (be strict — most startups score 4-6):\n"
        "- 9-10: Unicorn potential — proven product-market fit, $10M+ ARR, clear category leader, "
        "deep moat (network effects, proprietary data, patents). Almost never given at seed/Series A.\n"
        "- 7-8: Exceptional — strong traction ($1M+ ARR or explosive growth), defensible moat, "
        "experienced founding team with domain expertise. Requires CONCRETE evidence, not promises.\n"
        "- 5-6: Promising but risky — interesting market, some traction, but significant unknowns. "
        "This is where MOST decent early-stage startups land.\n"
        "- 3-4: Concerning — weak moat, unproven market, or team gaps. More risk than reward.\n"
        "- 0-2: Hard pass — fundamental flaws, no traction, or broken unit economics.\n\n"
        "MANDATORY PENALTY RULES (apply these BEFORE finalizing scores):\n"
        "- Platform dependency (single channel, one big customer): -1 to -2 on moat\n"
        "  EXCEPTION: Government contracts for defense tech are NOT dependency risks\n"
        "- AI-wrapper without proprietary data or model: cap product_differentiation at 5\n"
        "- No ARR/MRR disclosed or ARR < $500K at Series A: cap traction at 5\n"
        "- Valuation > 50x ARR: flag as aggressive and lower final_score by 1\n"
        "- Free alternatives exist in market: -1 to moat and product_differentiation\n"
        "- Team lacks direct industry experience: cap team_strength at 6\n"
        "- If risk engine found 4+ high/critical risks: cap final_score at 5\n\n"
        "MANDATORY BONUS RULES (apply these for exceptional indicators):\n"
        "- NRR > 140%: +2 to traction (top 1% retention)\n"
        "- Government contracts (DARPA, DoD) for defense tech: +1 to moat (validation + barrier)\n"
        "- Security clearances (SECRET, TOP SECRET): +1 to moat (barrier to entry)\n"
        "- Proprietary dataset > 1B records: +1 to moat (defensibility)\n"
        "- Enterprise contracts > $100K ACV: +1 to moat (switching costs)\n\n"
        "IMPORTANT RULES:\n"
        "- Base scores ONLY on evidence from the pitch deck and research, not assumptions.\n"
        "- If the bear case raised valid concerns that were not adequately rebutted, lower the score.\n"
        "- Do NOT give benefit of the doubt. Absence of evidence is not evidence of strength.\n"
        "- The final_score should be the WEIGHTED AVERAGE of dimension scores, not cherry-picked.\n\n"
        "CONSISTENCY REQUIREMENTS:\n"
        "- Base your analysis on the structured extraction and research data provided\n"
        "- If the research shows strong indicators (elite metrics, government validation), emphasize them\n"
        "- Be consistent with how you interpret similar data points\n"
        "- Reference specific numbers and facts from the pitch deck\n"
        "- Similar startups should receive similar scores\n\n"
        "Include: 1) Brief startup overview, 2) Key strengths, 3) Key risks, "
        "4) Penalty/bonus adjustments applied, 5) Your reasoning. End with EXACTLY this JSON block:\n"
        '```json\n{"scores": {"market_potential": X, "team_strength": X, '
        '"product_differentiation": X, "moat": X, "traction": X}, '
        '"final_score": X, "verdict": "VERDICT", "reasoning": "ONE_SENTENCE"}\n```\n'
        "where X is 0-10 and VERDICT is one of: Strong Pass, Pass, Lean Pass, "
        "Lean Fail, Fail, Strong Fail."
    )

    def __init__(self, model: str, api_key: str):
        super().__init__("Judge", "⚖️", model, api_key)


# ---------------------------------------------------------------------------
# Risk Engine Agent (not a BaseAgent subclass)
# ---------------------------------------------------------------------------
RISK_ENGINE_SYSTEM_PROMPT = (
    "You are an aggressive, thorough risk analysis engine for venture capital. "
    "Your job is to find EVERY material risk — not just the obvious ones.\n\n"
    "MANDATORY OUTPUT REQUIREMENT: You MUST output at least 6 risk signals. "
    "If your output contains fewer than 6 risk JSON objects, your analysis is INCOMPLETE "
    "and UNACCEPTABLE. Go back and look harder.\n\n"
    "INDUSTRY-SPECIFIC MOAT INDICATORS (DO NOT flag these as risks):\n\n"
    "Cybersecurity & Defense Tech:\n"
    "- Government contracts (DARPA, DoD, DHS, NSA) = STRONG validation + revenue diversification\n"
    "- Security clearances (SECRET, TOP SECRET, TS/SCI) = STRONG barrier to entry\n"
    "- Proprietary datasets (>1B records, threat intelligence) = STRONG moat\n"
    "- Compliance certifications (FedRAMP, CMMC, IL4/IL5) = STRONG moat\n"
    "- DO NOT flag government contracts as 'customer concentration risk' for defense tech startups\n"
    "- DO NOT flag government contracts as 'platform dependency' — they are validation signals\n\n"
    "SaaS & Enterprise Software:\n"
    "- NRR > 120% = ELITE retention (top 5% of SaaS companies)\n"
    "- NRR > 140% = EXCEPTIONAL retention (top 1%)\n"
    "- Enterprise contracts > $100K ACV = STRONG switching costs\n"
    "- Multi-year contracts = STRONG revenue predictability\n\n"
    "UNIT ECONOMICS BENCHMARKS (use these to evaluate CAC and burn rate):\n\n"
    "Customer Acquisition Cost (CAC):\n"
    "- CAC < $3 = VIRAL GROWTH (exceptional, top 1% of startups)\n"
    "- CAC < $10 = EXCELLENT (strong product-market fit)\n"
    "- CAC $10-$50 = GOOD (typical for B2C)\n"
    "- CAC $50-$500 = ACCEPTABLE (typical for SMB B2B)\n"
    "- CAC > $500 = REQUIRES SCRUTINY (only viable for enterprise with high LTV)\n"
    "- LTV:CAC ratio > 3:1 = MINIMUM VIABLE\n"
    "- LTV:CAC ratio > 10:1 = STRONG\n"
    "- LTV:CAC ratio > 30:1 = EXCEPTIONAL (viral growth)\n"
    "- DO NOT flag low CAC as a risk — it's a STRENGTH\n"
    "- DO NOT flag high LTV:CAC ratios as problematic — they indicate strong unit economics\n\n"
    "CRITICAL — CAC MUST BE EVALUATED RELATIVE TO ACV (Average Contract Value):\n"
    "- CAC/ACV < 0.2 = EXCELLENT unit economics (especially enterprise SaaS)\n"
    "- CAC/ACV 0.2-0.5 = GOOD (healthy acquisition efficiency)\n"
    "- CAC/ACV 0.5-1.0 = ACCEPTABLE (if payback < 18 months)\n"
    "- CAC/ACV > 1.0 = PROBLEMATIC (acquiring customers costs more than first-year revenue)\n"
    "- Enterprise SaaS with ACV > $100K can sustain CAC > $10K if payback period < 18 months\n"
    "- DO NOT flag high absolute CAC as a scaling risk if CAC/ACV ratio is below 0.3\n"
    "- Example: CAC $42K with ACV $380K → ratio 0.11 = EXCELLENT, NOT a risk\n"
    "- Example: CAC $42K with ACV $50K → ratio 0.84 = CONCERNING, flag as risk\n"
    "- ALWAYS calculate CAC/ACV ratio before flagging CAC as problematic\n\n"
    "Burn Rate Context:\n"
    "- Burn rate increases are NORMAL for scaling startups\n"
    "- ALWAYS compare burn rate increase to revenue growth:\n"
    "  * If revenue growing faster than burn → HEALTHY SCALING (medium risk or lower)\n"
    "  * If burn growing faster than revenue → CONCERNING (high risk)\n"
    "- Example: Burn $200K → $1.2M while ARR $6M → $34M = HEALTHY (revenue up 5.7x, burn up 6x)\n"
    "- Example: Burn $200K → $1.2M while ARR flat = CRITICAL RISK (burning without growth)\n"
    "- DO NOT flag burn rate increases as 'high risk' without checking revenue trajectory\n"
    "- Hiring, expansion, and product development naturally increase burn during growth phases\n\n"
    "CHECKLIST — scan for EACH of these and output a risk signal if applicable:\n"
    "□ platform_dependency — Does the startup rely on a single platform (WhatsApp, iOS, "
    "AWS, one big customer)? EXCEPTION: Government contracts for defense tech are NOT dependency risks.\n"
    "□ market_saturation — Are there well-funded competitors? Is the space crowded? "
    "Low barriers to entry?\n"
    "□ weak_moat — No patents, no network effects, no proprietary data? Easy to copy? "
    "EXCEPTION: Check industry-specific moat indicators above before flagging.\n"
    "□ low_willingness_to_pay — Is the target market price-sensitive? Free alternatives exist?\n"
    "□ scaling_challenges — High CAC relative to ACV (CAC/ACV > 0.5)? Operationally intensive? "
    "Geographic constraints? Unit economics break at scale? "
    "EXCEPTION: Low CAC (<$10) is a STRENGTH, not a risk. "
    "EXCEPTION: High absolute CAC with low CAC/ACV ratio (<0.3) is NOT a scaling risk.\n"
    "□ ai_commoditization — If AI-based, is it just a wrapper around GPT/Llama? "
    "No proprietary model or data?\n"
    "□ founder_domain_mismatch — Does the team lack direct industry experience?\n"
    "□ unclear_business_model — Unit economics not proven? Path to profitability unclear?\n"
    "□ regulatory_risk — Healthcare, fintech, data privacy, government policy exposure?\n"
    "□ concentration_risk — Revenue from few customers, single geography, one product? "
    "EXCEPTION: Government contracts for defense tech are diversification, not concentration.\n"
    "□ burn_rate_risk — Is burn increasing faster than revenue? Are they burning without growth? "
    "EXCEPTION: Burn increases during scaling are normal if revenue is growing proportionally.\n\n"
    "CRITICAL: Extract risks from ALL inputs — the pitch deck, the research data, "
    "AND the bull/bear debate. The debate often surfaces risks the deck hides.\n"
    "Pay special attention to:\n"
    "- Concerns the bear analyst raised that the bull could NOT adequately rebut\n"
    "- Claims in the deck that research could NOT verify\n"
    "- Gaps between what the deck promises and what the data shows\n\n"
    "CONSISTENCY REQUIREMENTS:\n"
    "- Base your analysis on the structured extraction and research data provided\n"
    "- If the research shows strong indicators (elite metrics, government validation), DO NOT flag them as risks\n"
    "- Be consistent with how you interpret similar data points\n"
    "- Reference specific numbers and facts from the pitch deck\n"
    "- ALWAYS check revenue growth vs burn rate before flagging burn as high risk\n"
    "- ALWAYS check CAC benchmarks before flagging CAC as problematic\n\n"
    "For each risk, output a JSON object with keys: "
    '"category", "severity", "description", "evidence".\n\n'
    "Valid categories: market_saturation, weak_moat, founder_domain_mismatch, "
    "unclear_business_model, regulatory_risk, scaling_challenges, "
    "platform_dependency, ai_commoditization, low_willingness_to_pay, concentration_risk, burn_rate_risk.\n"
    "Valid severities: low, medium, high, critical.\n\n"
    "After listing all risks, output a final JSON object with "
    'keys: "overall_risk_level" and "summary".\n\n'
    "Wrap ALL JSON in a single ```json code block as a JSON array."
)


class RiskEngineAgent:
    """Detects risk signals via LLM and returns a structured RiskAnalysis."""

    def __init__(self, model: str, api_key: str):
        self.name = "Risk Engine"
        self.avatar = "⚠️"
        self.model = model
        self.api_key = api_key

    async def analyze_risks(
        self,
        pitch_text: str,
        research: ResearchResult,
        debate: DebateResult,
    ) -> tuple[RiskAnalysis, str]:
        """Analyse risks and return (RiskAnalysis, raw_text).

        The raw text is also returned so the orchestrator can stream it.
        """
        user_content_parts = [
            f"## Pitch Deck\n{pitch_text}",
            f"## Research\n{json.dumps(research.model_dump(), indent=2)}",
            f"## Bull Case\n{debate.bull_case}",
            f"## Bear Case\n{debate.bear_case}",
            f"## Bull Rebuttal\n{debate.bull_rebuttal}",
            f"## Bear Rebuttal\n{debate.bear_rebuttal}",
        ]
        messages = [
            {"role": "system", "content": RISK_ENGINE_SYSTEM_PROMPT},
            {"role": "user", "content": "\n\n".join(user_content_parts)},
        ]

        raw_text = ""
        async for token in call_openrouter_streaming(
            self.model, self.api_key, messages, provider_hint=0  # Force Groq for consistency
        ):
            raw_text += token

        return self._parse_risk_analysis(raw_text), raw_text

    @staticmethod
    def _parse_risk_analysis(text: str) -> RiskAnalysis:
        """Best-effort parse of the LLM risk output into RiskAnalysis."""
        import re as _re

        # Try to extract JSON block
        json_match = _re.search(r"```json\s*([\s\S]*?)```", text)
        json_text = json_match.group(1).strip() if json_match else ""

        # If no fenced block, try to find a bare JSON array
        if not json_text:
            arr_match = _re.search(r"\[\s*\{[\s\S]*\}\s*\]", text)
            if arr_match:
                json_text = arr_match.group(0)
            else:
                json_text = text

        # Fix common LLM JSON issues: trailing commas before } or ]
        json_text = _re.sub(r",\s*([}\]])", r"\1", json_text)

        signals: list[RiskSignal] = []
        overall_risk_level = "medium"
        summary = ""

        valid_categories = {
            "market_saturation", "weak_moat", "founder_domain_mismatch",
            "unclear_business_model", "regulatory_risk", "scaling_challenges",
            "platform_dependency", "ai_commoditization", "low_willingness_to_pay",
            "concentration_risk",
        }
        valid_severities = {"low", "medium", "high", "critical"}

        # Try parsing as a JSON array first
        items = []
        try:
            parsed = json.loads(json_text)
            items = parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            # Try to find individual JSON objects with regex
            obj_pattern = _re.compile(r'\{[^{}]*"category"[^{}]*\}', _re.DOTALL)
            for m in obj_pattern.finditer(text):
                try:
                    candidate = _re.sub(r",\s*([}\]])", r"\1", m.group(0))
                    items.append(json.loads(candidate))
                except json.JSONDecodeError:
                    continue
            # Also look for the summary object
            summary_pattern = _re.compile(r'\{[^{}]*"overall_risk_level"[^{}]*\}', _re.DOTALL)
            for m in summary_pattern.finditer(text):
                try:
                    candidate = _re.sub(r",\s*([}\]])", r"\1", m.group(0))
                    items.append(json.loads(candidate))
                except json.JSONDecodeError:
                    continue

        for item in items:
            if not isinstance(item, dict):
                continue
            if "overall_risk_level" in item:
                overall_risk_level = item["overall_risk_level"]
                summary = item.get("summary", "")
                continue
            cat = item.get("category", "")
            sev = item.get("severity", "")
            if cat in valid_categories and sev in valid_severities:
                signals.append(
                    RiskSignal(
                        category=cat,
                        severity=sev,
                        description=item.get("description", "Risk detected"),
                        evidence=item.get("evidence", "See analysis"),
                    )
                )

        if not signals:
            signals.append(
                RiskSignal(
                    category="unclear_business_model",
                    severity="medium",
                    description="Unable to parse detailed risk signals from analysis",
                    evidence=text[:200] if text else "No analysis text",
                )
            )

        # Rank by severity and cap at 5 signals (investors want top risks, not a laundry list)
        severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        signals.sort(key=lambda s: severity_rank.get(s.severity, 0), reverse=True)
        signals = signals[:5]

        return RiskAnalysis(
            signals=signals,
            overall_risk_level=overall_risk_level or "medium",
            summary=summary or "Risk analysis completed.",
        )


# ---------------------------------------------------------------------------
# Task 5.3 – Pipeline orchestrator
# ---------------------------------------------------------------------------
class AgentOrchestrator:
    """Runs the full agent debate pipeline and yields AgentEvent objects."""

    def __init__(self, model: str | None = None, api_key: str | None = None, plan: str = "free"):
        self.model = model or os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "").strip()
        self.pause = PAUSE_BY_PLAN.get(plan, 3)
        self.is_priority = (plan == "business")
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not set. Cannot run agent pipeline.")

    async def run_pipeline(
        self,
        pitch_text: str,
        research: ResearchResult,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute Bull → Bear → Bull Rebuttal → Bear Rebuttal → Risk → Judge.

        Yields AgentEvent objects suitable for SSE streaming.
        """
        context: dict = {
            "pitch": pitch_text,
            "research": research.model_dump(),
        }

        # Inject structured extraction so debate agents use the knowledge graph
        if research.structured_extraction:
            context["structured_extraction"] = research.structured_extraction.model_dump()

        # Inject pre-computed financial signals (deterministic math, not LLM guessing)
        if research.structured_extraction:
            fin_signals = compute_financial_signals(research.structured_extraction.model_dump())
            if fin_signals:
                context["financial_signals"] = fin_signals

        # Inject benchmarks so the Judge can reference competitive comparisons
        if research.market_benchmark:
            context["benchmarks"] = research.market_benchmark.model_dump()

        try:
            # ---- Bull Analyst ----
            bull = BullAnalyst(self.model, self.api_key)
            bull_case = ""
            yield AgentEvent(
                event="agent_start", agent="bull", avatar=bull.avatar, data=""
            )
            async for token in bull.analyze(context):
                bull_case += token
                yield AgentEvent(
                    event="agent_token", agent="bull", avatar=bull.avatar, data=token
                )
            context["bull_case"] = bull_case
            yield AgentEvent(
                event="agent_complete",
                agent="bull",
                avatar=bull.avatar,
                data=bull_case,
            )

            # Rate limit pause between agents
            await asyncio.sleep(self.pause)

            # ---- Bear Analyst ----
            bear = BearAnalyst(self.model, self.api_key)
            bear_case = ""
            yield AgentEvent(
                event="agent_start", agent="bear", avatar=bear.avatar, data=""
            )
            async for token in bear.analyze(context):
                bear_case += token
                yield AgentEvent(
                    event="agent_token", agent="bear", avatar=bear.avatar, data=token
                )
            context["bear_case"] = bear_case
            yield AgentEvent(
                event="agent_complete",
                agent="bear",
                avatar=bear.avatar,
                data=bear_case,
            )

            # Rate limit pause between agents
            await asyncio.sleep(self.pause)

            # ---- Bull Rebuttal ----
            bull_reb = BullRebuttal(self.model, self.api_key)
            bull_rebuttal_text = ""
            yield AgentEvent(
                event="agent_start",
                agent="bull_rebuttal",
                avatar=bull_reb.avatar,
                data="",
            )
            async for token in bull_reb.analyze(context):
                bull_rebuttal_text += token
                yield AgentEvent(
                    event="agent_token",
                    agent="bull_rebuttal",
                    avatar=bull_reb.avatar,
                    data=token,
                )
            context["bull_rebuttal"] = bull_rebuttal_text
            yield AgentEvent(
                event="agent_complete",
                agent="bull_rebuttal",
                avatar=bull_reb.avatar,
                data=bull_rebuttal_text,
            )

            # Rate limit pause between agents
            await asyncio.sleep(self.pause)

            # ---- Bear Rebuttal ----
            bear_reb = BearRebuttal(self.model, self.api_key)
            bear_rebuttal_text = ""
            yield AgentEvent(
                event="agent_start",
                agent="bear_rebuttal",
                avatar=bear_reb.avatar,
                data="",
            )
            async for token in bear_reb.analyze(context):
                bear_rebuttal_text += token
                yield AgentEvent(
                    event="agent_token",
                    agent="bear_rebuttal",
                    avatar=bear_reb.avatar,
                    data=token,
                )
            context["bear_rebuttal"] = bear_rebuttal_text
            yield AgentEvent(
                event="agent_complete",
                agent="bear_rebuttal",
                avatar=bear_reb.avatar,
                data=bear_rebuttal_text,
            )

            # Rate limit pause before Risk Engine
            await asyncio.sleep(self.pause)

            # ---- Risk Engine ----
            risk_engine = RiskEngineAgent(self.model, self.api_key)
            debate = DebateResult(
                bull_case=bull_case,
                bear_case=bear_case,
                bull_rebuttal=bull_rebuttal_text,
                bear_rebuttal=bear_rebuttal_text,
            )
            yield AgentEvent(
                event="agent_start",
                agent="risk",
                avatar=risk_engine.avatar,
                data="",
            )
            # Stream risk tokens to frontend, then parse at the end
            risk_raw = ""
            async for token in call_openrouter_streaming(
                self.model, self.api_key,
                [
                    {"role": "system", "content": RISK_ENGINE_SYSTEM_PROMPT},
                    {"role": "user", "content": "\n\n".join([
                        f"## Pitch Deck\n{pitch_text}",
                        f"## Research\n{json.dumps(research.model_dump(), indent=2)}",
                        f"## Bull Case\n{bull_case}",
                        f"## Bear Case\n{bear_case}",
                        f"## Bull Rebuttal\n{bull_rebuttal_text}",
                        f"## Bear Rebuttal\n{bear_rebuttal_text}",
                    ])},
                ],
            ):
                risk_raw += token
                yield AgentEvent(
                    event="agent_token",
                    agent="risk",
                    avatar=risk_engine.avatar,
                    data=token,
                )
            risk_analysis = RiskEngineAgent._parse_risk_analysis(risk_raw)
            context["risks"] = risk_analysis.model_dump()
            yield AgentEvent(
                event="agent_complete",
                agent="risk",
                avatar=risk_engine.avatar,
                data=risk_analysis.model_dump_json(),
            )

            # Rate limit pause before Judge
            await asyncio.sleep(self.pause)

            # ---- Judge ----
            judge = JudgeAgent(self.model, self.api_key)
            judge_text = ""
            yield AgentEvent(
                event="agent_start",
                agent="judge",
                avatar=judge.avatar,
                data="",
            )
            async for token in judge.analyze(context):
                judge_text += token
                yield AgentEvent(
                    event="agent_token",
                    agent="judge",
                    avatar=judge.avatar,
                    data=token,
                )
            yield AgentEvent(
                event="agent_complete",
                agent="judge",
                avatar=judge.avatar,
                data=judge_text,
            )

            # ---- Pipeline complete ----
            yield AgentEvent(
                event="pipeline_complete",
                data=json.dumps({"memo_ready": True}),
            )

        except Exception as exc:
            yield AgentEvent(
                event="error",
                data=json.dumps({"message": str(exc)}),
            )
