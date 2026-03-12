"""Pydantic data models for the AI Venture Intelligence Engine."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class StartupInfo(BaseModel):
    """Startup information extracted from a pitch deck."""

    name: str = Field(min_length=1)
    product: str = Field(min_length=1)
    industry: str = Field(min_length=1)
    stage: Optional[str] = None
    founding_team: Optional[str] = None
    traction: Optional[str] = None
    ask: Optional[str] = None


class Citation(BaseModel):
    """A source citation linking a claim to its origin."""

    text: str  # the claim or data point
    source: str  # e.g. "Pitch Deck, Page 3" or "Web Research"
    page: Optional[int] = None


class StructuredExtraction(BaseModel):
    """First-pass structured extraction from the pitch deck — the knowledge graph."""

    startup_name: str
    product: str
    industry: str
    stage: Optional[str] = None
    founding_team: Optional[str] = None
    tam: Optional[str] = None
    sam: Optional[str] = None
    som: Optional[str] = None
    arr: Optional[str] = None
    mrr: Optional[str] = None
    customers: Optional[str] = None
    growth: Optional[str] = None
    funding_ask: Optional[str] = None
    competitors: list[str] = []
    key_metrics: list[Citation] = []
    missing_info: list[str] = []


class ClaimVerification(BaseModel):
    """A verified claim with confidence level."""

    claim: str
    source: str
    confidence: Literal["high", "medium", "low", "unverified"]
    reasoning: str


class MarketSize(BaseModel):
    """Market size estimates (TAM/SAM/SOM)."""

    tam: str
    sam: str
    som: str
    sources: list[str] = []


class Competitor(BaseModel):
    """A competitor discovered during research."""

    name: str
    description: str
    funding: Optional[str] = None
    differentiator: Optional[str] = None
    category: Optional[str] = None  # ecosystem category (e.g. "Rural Diagnostics")


class EcosystemCategory(BaseModel):
    """A category in the competitor ecosystem map."""

    name: str
    companies: list[str]


class BenchmarkMetric(BaseModel):
    """A single metric comparison between the startup and a benchmark."""

    entity: str  # e.g. "Kartavya", "Khatabook", "Sector Median"
    value: str   # e.g. "10x", "4.1x MoM", "$2M"
    source: str = "Web Research"  # where this data came from
    is_startup: bool = False  # whether this is the startup being analyzed
    is_median: bool = False   # whether this is a sector/industry median


class BenchmarkCategory(BaseModel):
    """A benchmarking category (e.g. Revenue Multiple, Growth Rate)."""

    metric_name: str  # e.g. "Revenue Multiple", "Growth Rate"
    entries: list[BenchmarkMetric]
    startup_percentile: Optional[str] = None  # e.g. "Top 25%", "Bottom 40%"
    startup_verdict: Optional[str] = None     # e.g. "Outperforming", "Below Average", "At Par"


class MarketBenchmark(BaseModel):
    """Live market benchmarking — startup vs competitors and sector medians."""

    startup_name: str
    categories: list[BenchmarkCategory]
    overall_position: Optional[str] = None  # e.g. "Competitive but below top-tier peers"


class EcosystemMap(BaseModel):
    """Competitor ecosystem map grouped by market category."""

    startup_name: str
    categories: list[EcosystemCategory]


class SearchResult(BaseModel):
    """A single web search result."""

    title: str
    snippet: str
    url: str


class ResearchResult(BaseModel):
    """Complete research output from the Research Agent."""

    startup_info: StartupInfo
    structured_extraction: Optional[StructuredExtraction] = None
    claim_verifications: list[ClaimVerification] = []
    market_size: MarketSize
    competitors: list[Competitor]
    ecosystem_map: Optional[EcosystemMap] = None
    market_benchmark: Optional[MarketBenchmark] = None
    traction_signals: list[str]
    missing_info: list[str] = []
    confidence_scores: dict[str, str] = {}  # e.g. {"market_estimate": "high"}
    raw_research: str


class DebateResult(BaseModel):
    """Output from the bull/bear debate phase."""

    bull_case: str
    bear_case: str
    bull_rebuttal: str
    bear_rebuttal: str


class RiskSignal(BaseModel):
    """A single detected risk signal."""

    category: Literal[
        "market_saturation",
        "weak_moat",
        "founder_domain_mismatch",
        "unclear_business_model",
        "regulatory_risk",
        "scaling_challenges",
        "platform_dependency",
        "ai_commoditization",
        "low_willingness_to_pay",
        "concentration_risk",
    ]
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    evidence: str


class RiskAnalysis(BaseModel):
    """Aggregated risk analysis from the Risk Engine."""

    signals: list[RiskSignal]
    overall_risk_level: str
    summary: str


class ScoreBreakdown(BaseModel):
    """Five-dimension investment score breakdown, each in [0, 10]."""

    market_potential: float = Field(ge=0, le=10)
    team_strength: float = Field(ge=0, le=10)
    product_differentiation: float = Field(ge=0, le=10)
    moat: float = Field(ge=0, le=10)
    traction: float = Field(ge=0, le=10)


class JudgeVerdict(BaseModel):
    """Final verdict from the Judge Agent."""

    scores: ScoreBreakdown
    final_score: float = Field(ge=0, le=10)
    verdict: Literal[
        "Strong Pass",
        "Pass",
        "Lean Pass",
        "Lean Fail",
        "Fail",
        "Strong Fail",
    ]
    reasoning: str


class InvestorReadiness(BaseModel):
    """Investor Readiness Score — quick-glance assessment at the top of the memo."""

    deck_quality: float = Field(ge=0, le=10)
    market_opportunity: float = Field(ge=0, le=10)
    team_credibility: float = Field(ge=0, le=10)
    business_model_clarity: float = Field(ge=0, le=10)
    defensibility: float = Field(ge=0, le=10)
    overall: float = Field(ge=0, le=10)


class DealBreaker(BaseModel):
    """A single deal breaker signal."""
    rank: int = Field(ge=1, le=3)
    category: str
    description: str


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


class SlideFeedback(BaseModel):
    """Feedback for a single slide."""
    slide_number: int
    slide_title: str
    slide_type: str
    content_summary: str
    problem: Optional[str] = None
    investor_reaction: str
    fix_suggestion: str
    severity: str


class InvestmentMemo(BaseModel):
    """Complete investment memo compiled from all agent outputs."""

    analysis_id: str
    investor_readiness: Optional[InvestorReadiness] = None
    top_investor_concerns: list[str] = []
    startup_overview: str
    structured_extraction: Optional[StructuredExtraction] = None
    claim_verifications: list[ClaimVerification] = []
    market_size: MarketSize
    competitor_landscape: list[Competitor]
    ecosystem_map: Optional[EcosystemMap] = None
    market_benchmark: Optional[MarketBenchmark] = None
    bull_case: str
    bear_case: str
    bull_rebuttal: str
    bear_rebuttal: str
    risk_signals: RiskAnalysis
    score_breakdown: ScoreBreakdown
    final_score: float
    verdict: str
    judge_reasoning: str
    missing_info: list[str] = []
    confidence_scores: dict[str, str] = {}
    created_at: str
    deal_breakers: Optional[list[DealBreaker]] = None
    investor_questions: Optional[list[str]] = None
    slide_feedback: Optional[list[SlideFeedback]] = None


class AgentEvent(BaseModel):
    """SSE event emitted during pipeline execution."""

    event: str
    agent: Optional[str] = None
    avatar: Optional[str] = None
    data: str


class UploadResponse(BaseModel):
    """Response returned after a successful PDF upload."""

    analysis_id: str
    status: str


class TeamCreate(BaseModel):
    """Request body for creating a team."""
    name: str = Field(min_length=1, max_length=100)


class TeamInfo(BaseModel):
    """Team information returned by API."""
    id: str
    name: str
    owner_id: str
    team_credits_used: int = 0
    team_credits_limit: int = 999999
    created_at: str
    members: list[dict] = []


class TeamInvitation(BaseModel):
    """Team invitation record."""
    id: str
    team_id: str
    team_name: str = ""
    email: str
    status: str
    invited_by: str
    created_at: str


class InviteRequest(BaseModel):
    """Request body for inviting a team member."""
    email: str = Field(min_length=5)


def score_to_verdict(score: float) -> str:
    """Map a numeric score to a verdict string.

    Args:
        score: A value in [0, 10].

    Returns:
        One of: "Strong Pass", "Pass", "Lean Pass",
                "Lean Fail", "Fail", "Strong Fail".
    """
    if score >= 8:
        return "Strong Pass"
    if score >= 6:
        return "Pass"
    if score >= 5:
        return "Lean Pass"
    if score >= 4:
        return "Lean Fail"
    if score >= 2:
        return "Fail"
    return "Strong Fail"
