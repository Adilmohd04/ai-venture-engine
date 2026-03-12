"""FastAPI backend for the AI Venture Intelligence Engine."""

import asyncio
import json
import os
import sys
import tempfile
from typing import Optional
from uuid import uuid4

from dotenv import load_dotenv

# Load .env file before anything reads env vars
load_dotenv()

from fastapi import FastAPI, HTTPException, Header, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse
import paypalrestsdk

from agents import AgentOrchestrator
from analysis_queue import AnalysisQueue
from deal_breaker_detector import DealBreakerDetector
from memo_builder import MemoBuilder, parse_judge_verdict
from models import AgentEvent, DebateResult, InvestmentMemo, ResearchResult, RiskAnalysis, UploadResponse, TeamCreate, InviteRequest
from pdf_parser import PDFParser
from pdf_report import generate_memo_pdf
from question_generator import QuestionGenerator
from report_generator import ReportGenerator
from research import ResearchAgent
from slide_analyzer import SlideAnalyzer
import supabase_client as sb

# --- API Key validation ---
_api_key = os.environ.get("GROQ_API_KEY", "").strip()
if not _api_key:
    print(
        "\n❌  GROQ_API_KEY is not set!\n"
        "   Option 1: Create a .env file in this directory with:\n"
        "             GROQ_API_KEY=gsk_your-key-here\n"
        "   Option 2: Set it in your terminal before starting:\n"
        "             set GROQ_API_KEY=gsk_your-key-here\n"
        "   Get a free key at https://console.groq.com/keys\n",
        file=sys.stderr,
    )
    sys.exit(1)

# PayPal configuration
paypalrestsdk.configure({
    "mode": os.environ.get("PAYPAL_MODE", "sandbox"),  # sandbox or live
    "client_id": os.environ.get("PAYPAL_CLIENT_ID", ""),
    "client_secret": os.environ.get("PAYPAL_CLIENT_SECRET", "")
})

# Credit packages
CREDIT_PACKAGES = {
    "pro": {"credits": 50, "price": "9.00", "name": "Pro Plan", "plan": "pro"},
    "business": {"credits": -1, "price": "29.00", "name": "Business Plan", "plan": "business"},  # -1 = unlimited
}

app = FastAPI(title="AI Venture Intelligence Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://ai-venture-engine.vercel.app",
        "https://ventureengine.in",
        "https://www.ventureengine.in",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

# In-memory stores (still used for active streaming sessions)
pending_analyses: dict[str, dict] = {}       # analysis_id -> {pitch_text, user_id}
completed_memos: dict[str, InvestmentMemo] = {}  # analysis_id -> memo
analysis_queue = AnalysisQueue()


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------
async def _get_user(authorization: Optional[str] = Header(None)) -> dict:
    """Extract and verify the user from the Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization.split(" ", 1)[1]
    user = await sb.verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


# ---------------------------------------------------------------------------
# Health check endpoint (no auth required)
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    """Simple health check endpoint for monitoring services."""
    return {"status": "healthy", "service": "AI Venture Intelligence Engine"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "AI Venture Intelligence Engine API", "status": "running"}


# ---------------------------------------------------------------------------
# Auth-aware endpoints
# ---------------------------------------------------------------------------
@app.get("/api/profile")
async def get_profile(authorization: Optional[str] = Header(None)):
    """Return the current user's profile with credit info."""
    user = await _get_user(authorization)
    profile = await sb.get_profile(user["id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    credits = await sb.check_credits(user["id"])
    return {**profile, **credits}


@app.get("/api/credits")
async def check_credits(authorization: Optional[str] = Header(None)):
    """Check remaining credits for the current user."""
    user = await _get_user(authorization)
    return await sb.check_credits(user["id"])


@app.get("/api/analyses")
async def list_analyses(authorization: Optional[str] = Header(None)):
    """List all analyses for the current user (deal flow dashboard)."""
    user = await _get_user(authorization)
    return await sb.get_user_analyses(user["id"])


@app.get("/api/analyses/{analysis_id}")
async def get_saved_analysis(analysis_id: str, authorization: Optional[str] = Header(None)):
    """Fetch a specific saved analysis memo."""
    user = await _get_user(authorization)
    memo = await sb.get_analysis_memo(user["id"], analysis_id)
    if not memo:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return memo


@app.get("/api/history/{startup_name}")
async def get_startup_history(startup_name: str, authorization: Optional[str] = Header(None)):
    """Get historical score timeline for a startup."""
    user = await _get_user(authorization)
    return await sb.get_startup_history(user["id"], startup_name)


# ---------------------------------------------------------------------------
# Upload (now with auth + credit check)
# ---------------------------------------------------------------------------
@app.post("/upload", response_model=UploadResponse)
async def upload_pitch_deck(file: UploadFile, authorization: Optional[str] = Header(None)):
    """Accept a PDF pitch deck, extract text, and return an analysis_id."""
    user = await _get_user(authorization)
    user_id = user["id"]

    # Check credits
    credits = await sb.check_credits(user_id)
    if not credits["allowed"]:
        raise HTTPException(
            status_code=403,
            detail=f"No credits remaining. You've used {credits['used']}/{credits['limit']} "
                   f"on the {credits['plan']} plan. Upgrade for more analyses.",
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 20MB size limit.")

    # Save to temp file for pdfplumber
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        tmp.write(content)
        tmp.close()
        parser = PDFParser()
        structured = parser.extract_structured(tmp.name)
        page_parts = []
        for page_num, page_text in sorted(structured.items()):
            if page_text.strip():
                page_parts.append(f"--- PAGE {page_num} ---\n{page_text}")
        pitch_text = "\n\n".join(page_parts) if page_parts else ""
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    if not pitch_text.strip():
        raise HTTPException(
            status_code=422,
            detail="No extractable text found in the PDF. Please upload a text-based PDF.",
        )

    analysis_id = str(uuid4())
    pending_analyses[analysis_id] = {
        "pitch_text": pitch_text,
        "user_id": user_id,
        "slides_dict": structured,  # Store slide structure
        "plan": credits["plan"],
    }

    # Enqueue the job with priority based on user's plan
    analysis_queue.enqueue(analysis_id, user_id, credits["plan"])

    # Credits are deducted AFTER successful completion, not here

    return UploadResponse(analysis_id=analysis_id, status="ready")


# ---------------------------------------------------------------------------
# Stream analysis (auth-aware, saves to Supabase on completion)
# ---------------------------------------------------------------------------
@app.get("/stream-analysis")
async def stream_analysis(
    analysis_id: str,
    token: str = None,
    authorization: Optional[str] = Header(None),
):
    """Stream the full agent pipeline via Server-Sent Events."""
    # EventSource can't send headers, so accept token as query param too
    if token and not authorization:
        authorization = f"Bearer {token}"
    user = await _get_user(authorization)

    if analysis_id not in pending_analyses:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    session = pending_analyses[analysis_id]
    pitch_text = session["pitch_text"]
    slides_dict = session.get("slides_dict", {})
    user_id = session["user_id"]
    plan = session.get("plan", "free")

    if user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized for this analysis.")

    # Track whether credits have been incremented for this analysis
    credit_incremented_key = f"credit_{analysis_id}"

    async def _increment_credits_background(uid: str, aid: str):
        """Background task to increment credits - runs independently of SSE stream."""
        try:
            print(f"\n🎯 BACKGROUND CREDIT INCREMENT for user {uid}, analysis {aid}")
            result = await sb.increment_credits(uid)
            if result:
                print(f"✅ BACKGROUND CREDIT INCREMENT SUCCESSFUL for {uid}")
            else:
                print(f"❌ BACKGROUND CREDIT INCREMENT FAILED for {uid}")
        except Exception as e:
            print(f"❌ BACKGROUND CREDIT INCREMENT EXCEPTION: {e}")

    async def event_generator():
        try:
            # Emit priority indicator
            yield {
                "event": "analysis_start",
                "data": json.dumps({
                    "analysis_id": analysis_id,
                    "priority": plan == "business",
                }),
            }

            # Phase 1: Research
            yield {
                "event": "agent_start",
                "data": json.dumps({"agent": "research", "avatar": "🔎", "content": ""}),
            }
            research_agent = ResearchAgent()

            # Stream research progress to frontend
            async def on_research_progress(msg: str):
                pass  # placeholder — SSE yields happen below

            # We can't yield from inside a callback, so we use a queue
            import asyncio as _aio
            progress_queue: _aio.Queue[str] = _aio.Queue()

            async def _progress_cb(msg: str):
                await progress_queue.put(msg)

            # Run research in background task, stream progress tokens
            research_task = _aio.create_task(
                research_agent.research_startup(pitch_text, on_progress=_progress_cb)
            )

            while not research_task.done():
                try:
                    msg = await _aio.wait_for(progress_queue.get(), timeout=0.5)
                    yield {
                        "event": "agent_token",
                        "data": json.dumps({"agent": "research", "content": msg + "\n"}),
                    }
                except _aio.TimeoutError:
                    pass

            # Drain any remaining progress messages
            while not progress_queue.empty():
                msg = await progress_queue.get()
                yield {
                    "event": "agent_token",
                    "data": json.dumps({"agent": "research", "content": msg + "\n"}),
                }

            research_result = research_task.result()
            yield {
                "event": "agent_complete",
                "data": json.dumps({
                    "agent": "research",
                    "avatar": "🔎",
                    "content": json.dumps(research_result.model_dump()),
                }),
            }

            # Brief pause before agent pipeline (load is spread across providers)
            await asyncio.sleep(3)

            # Phase 2-7: Agent pipeline
            orchestrator = AgentOrchestrator(plan=plan)
            agent_outputs: dict[str, str] = {}

            async for event in orchestrator.run_pipeline(pitch_text, research_result):
                if event.event == "agent_complete" and event.agent:
                    agent_outputs[event.agent] = event.data
                
                # When pipeline_complete arrives, build memo and increment credits
                # BEFORE yielding, because the frontend will close the SSE connection
                # after receiving pipeline_complete, which cancels this generator.
                if event.event == "pipeline_complete":
                    # Build memo NOW before the connection drops
                    judge_text = agent_outputs.get("judge", "")
                    judge_verdict = parse_judge_verdict(judge_text)

                    risk_data = agent_outputs.get("risk", "{}")
                    try:
                        risk_analysis = RiskAnalysis.model_validate_json(risk_data)
                    except Exception:
                        risk_analysis = RiskAnalysis(
                            signals=[], overall_risk_level="medium", summary="Unable to parse risk data."
                        )

                    memo = MemoBuilder().build_memo(
                        analysis_id=analysis_id,
                        research=research_result,
                        bull_case=agent_outputs.get("bull", ""),
                        bear_case=agent_outputs.get("bear", ""),
                        bull_rebuttal=agent_outputs.get("bull_rebuttal", ""),
                        bear_rebuttal=agent_outputs.get("bear_rebuttal", ""),
                        risks=risk_analysis,
                        judge_verdict=judge_verdict,
                    )

                    # Generate deal breakers, questions, and slide feedback
                    deal_breaker_detector = DealBreakerDetector()
                    deal_breakers = deal_breaker_detector.detect_deal_breakers(memo)
                    
                    question_generator = QuestionGenerator()
                    questions = question_generator.generate_questions(memo)
                    
                    slide_analyzer = SlideAnalyzer()
                    slide_feedback = slide_analyzer.analyze_slides(slides_dict, memo)
                    
                    memo.deal_breakers = deal_breakers
                    memo.investor_questions = questions
                    memo.slide_feedback = slide_feedback
                    
                    completed_memos[analysis_id] = memo

                    # Save to Supabase
                    save_success = await sb.save_analysis(user_id, analysis_id, memo.model_dump())
                    if not save_success:
                        print(f"⚠️  Warning: Failed to save analysis to database for user {user_id}")

                    # Generate and save public report
                    report_generator = ReportGenerator()
                    public_report = report_generator.generate_report(memo, deal_breakers)
                    report_success = await sb.save_public_report(user_id, public_report)
                    if not report_success:
                        print(f"⚠️  Warning: Failed to save public report for user {user_id}")

                    # Save VC first impression data (slide-level rejection signals)
                    vc_impression = []
                    if slide_feedback:
                        for sf in slide_feedback:
                            if sf.severity in ("critical", "high") and sf.problem:
                                vc_impression.append({
                                    "slide": sf.slide_number,
                                    "title": sf.slide_title,
                                    "type": sf.slide_type,
                                    "problem": sf.problem,
                                    "reaction": sf.investor_reaction,
                                    "severity": sf.severity,
                                })
                    await sb.save_vc_impression(user_id, analysis_id, vc_impression)

                    # CRITICAL: Fire credit increment as background task
                    # This runs independently even if SSE connection drops
                    print(f"\n🎯 FIRING CREDIT INCREMENT for user {user_id}")
                    asyncio.create_task(_increment_credits_background(user_id, analysis_id))

                # Now yield the event to the frontend
                yield {
                    "event": event.event,
                    "data": json.dumps({
                        "agent": event.agent,
                        "avatar": event.avatar,
                        "content": event.data,
                    }),
                }

        except Exception as exc:
            # Even if analysis fails, try to increment credits if memo was created
            if analysis_id in completed_memos:
                print(f"⚠️  Exception but memo exists - firing background credit increment")
                asyncio.create_task(_increment_credits_background(user_id, analysis_id))
            
            yield {
                "event": "error",
                "data": json.dumps({"message": str(exc)}),
            }

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# Memo endpoints
# ---------------------------------------------------------------------------
@app.get("/memo")
async def get_memo(analysis_id: str, authorization: Optional[str] = Header(None)):
    """Return the completed investment memo (in-memory or from Supabase)."""
    user = await _get_user(authorization)

    # Try in-memory first (for active sessions)
    if analysis_id in completed_memos:
        return completed_memos[analysis_id].model_dump()

    # Fall back to Supabase
    memo = await sb.get_analysis_memo(user["id"], analysis_id)
    if memo:
        return memo

    raise HTTPException(status_code=404, detail="Memo not found or not yet complete.")


@app.get("/memo/pdf")
async def download_memo_pdf(analysis_id: str, authorization: Optional[str] = Header(None)):
    """Generate and return a professional PDF of the investment memo."""
    user = await _get_user(authorization)

    memo_data = None
    if analysis_id in completed_memos:
        memo = completed_memos[analysis_id]
        memo_data = memo
    else:
        saved = await sb.get_analysis_memo(user["id"], analysis_id)
        if saved:
            memo_data = InvestmentMemo.model_validate(saved)

    if not memo_data:
        raise HTTPException(status_code=404, detail="Memo not found or not yet complete.")

    try:
        pdf_bytes = generate_memo_pdf(memo_data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")

    startup_name = "investment-memo"
    if memo_data.startup_overview and "building" in memo_data.startup_overview.lower():
        parts = memo_data.startup_overview.split(" is building")
        if parts[0] and parts[0].strip():
            startup_name = parts[0].strip().lower().replace(" ", "-")
    elif memo_data.startup_overview:
        startup_name = memo_data.startup_overview[:30].strip().lower().replace(" ", "-")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{startup_name}-memo.pdf"'},
    )


# ---------------------------------------------------------------------------
# VC Workflow Enhancement Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/analyses/{analysis_id}/deal-breakers")
async def get_deal_breakers(analysis_id: str, authorization: Optional[str] = Header(None)):
    """Return the top 3 deal breakers for an analysis."""
    user = await _get_user(authorization)

    # Try in-memory first
    if analysis_id in completed_memos:
        memo = completed_memos[analysis_id]
        if memo.deal_breakers:
            return {"deal_breakers": [db.model_dump() for db in memo.deal_breakers]}
        # Generate on-the-fly if not cached
        detector = DealBreakerDetector()
        deal_breakers = detector.detect_deal_breakers(memo)
        return {"deal_breakers": [db.model_dump() for db in deal_breakers]}

    # Fall back to Supabase
    saved = await sb.get_analysis_memo(user["id"], analysis_id)
    if not saved:
        raise HTTPException(status_code=404, detail="Analysis not found")

    memo = InvestmentMemo.model_validate(saved)
    if memo.deal_breakers:
        return {"deal_breakers": [db.model_dump() for db in memo.deal_breakers]}

    # Generate on-the-fly
    detector = DealBreakerDetector()
    deal_breakers = detector.detect_deal_breakers(memo)
    return {"deal_breakers": [db.model_dump() for db in deal_breakers]}


@app.get("/api/analyses/{analysis_id}/questions")
async def get_investor_questions(analysis_id: str, authorization: Optional[str] = Header(None)):
    """Return 5-8 tough investor questions for an analysis."""
    user = await _get_user(authorization)

    # Try in-memory first
    if analysis_id in completed_memos:
        memo = completed_memos[analysis_id]
        if memo.investor_questions:
            return {"questions": memo.investor_questions}
        # Generate on-the-fly if not cached
        generator = QuestionGenerator()
        questions = generator.generate_questions(memo)
        return {"questions": questions}

    # Fall back to Supabase
    saved = await sb.get_analysis_memo(user["id"], analysis_id)
    if not saved:
        raise HTTPException(status_code=404, detail="Analysis not found")

    memo = InvestmentMemo.model_validate(saved)
    if memo.investor_questions:
        return {"questions": memo.investor_questions}

    # Generate on-the-fly
    generator = QuestionGenerator()
    questions = generator.generate_questions(memo)
    return {"questions": questions}


@app.get("/report/{analysis_id}")
async def get_public_report(analysis_id: str):
    """Return the public report with percentile ranking (no auth required)."""
    report = await sb.get_public_report(analysis_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Add percentile ranking
    percentile_data = await sb.get_score_percentile(report["investor_readiness_overall"])
    report["percentile"] = percentile_data["percentile"]
    report["total_analyses"] = percentile_data["total_analyses"]

    # Add VC first impression data
    vc_impression = await sb.get_vc_impression(analysis_id)
    report["vc_impression"] = vc_impression

    return report


@app.get("/api/analyses/{analysis_id}/slide-feedback")
async def get_slide_feedback(analysis_id: str, authorization: Optional[str] = Header(None)):
    """Return slide-level feedback for an analysis."""
    user = await _get_user(authorization)

    # Try in-memory first
    if analysis_id in completed_memos:
        memo = completed_memos[analysis_id]
        if memo.slide_feedback:
            return {"slide_feedback": [sf.model_dump() for sf in memo.slide_feedback]}
        return {"slide_feedback": []}

    # Fall back to Supabase
    saved = await sb.get_analysis_memo(user["id"], analysis_id)
    if not saved:
        raise HTTPException(status_code=404, detail="Analysis not found")

    memo = InvestmentMemo.model_validate(saved)
    if memo.slide_feedback:
        return {"slide_feedback": [sf.model_dump() for sf in memo.slide_feedback]}
    
    return {"slide_feedback": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)





# ---------------------------------------------------------------------------
# PayPal Payment Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/paypal/create-order")
async def create_paypal_order(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """Create a PayPal order for credit purchase."""
    user = await _get_user(authorization)
    body = await request.json()
    package_id = body.get("package_id")
    
    if package_id not in CREDIT_PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid package ID")
    
    package = CREDIT_PACKAGES[package_id]
    
    try:
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": f"https://ventureengine.in/dashboard?payment=success",
                "cancel_url": f"https://ventureengine.in/dashboard?payment=cancelled"
            },
            "transactions": [{
                "amount": {
                    "total": package["price"],
                    "currency": "USD"
                },
                "description": f"{package['name']} - {package['credits']} credits" if package['credits'] > 0 else f"{package['name']} - Unlimited credits",
                "custom": json.dumps({"user_id": user["id"], "package_id": package_id})
            }]
        })
        
        if payment.create():
            # Find approval URL
            approval_url = None
            for link in payment.links:
                if link.rel == "approval_url":
                    approval_url = link.href
                    break
            
            if approval_url:
                return {"approval_url": approval_url, "payment_id": payment.id}
            else:
                raise HTTPException(status_code=500, detail="No approval URL found")
        else:
            print(f"❌ PayPal payment creation error: {payment.error}")
            raise HTTPException(status_code=500, detail=f"Payment creation failed: {payment.error}")
    
    except Exception as e:
        print(f"❌ PayPal order error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")


@app.post("/api/paypal/execute-payment")
async def execute_paypal_payment(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """Execute PayPal payment after user approval (CRITICAL: Server-side verification)."""
    user = await _get_user(authorization)
    body = await request.json()
    payment_id = body.get("payment_id")
    payer_id = body.get("payer_id")
    
    try:
        # Get payment from PayPal
        payment = paypalrestsdk.Payment.find(payment_id)
        
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Execute the payment
        if payment.execute({"payer_id": payer_id}):
            # Payment successful - verify and add credits
            transaction = payment.transactions[0]
            custom_data = json.loads(transaction.custom)
            package_id = custom_data["package_id"]
            
            # Verify user matches
            if custom_data["user_id"] != user["id"]:
                raise HTTPException(status_code=403, detail="User mismatch")
            
            # Check for duplicate payment
            existing = await sb.get_payment_by_order_id(payment_id)
            if existing:
                print(f"⚠️  Duplicate payment attempt: {payment_id}")
                return {"status": "already_processed", "message": "Payment already processed"}
            
            # Get package details
            package = CREDIT_PACKAGES[package_id]
            amount = float(transaction.amount.total)
            
            # Store payment record
            await sb.save_payment(
                user_id=user["id"],
                order_id=payment_id,
                amount=amount,
                credits_added=package["credits"],
                plan=package["plan"],
                status="completed"
            )
            
            # Add credits to user
            if package["credits"] == -1:
                # Unlimited plan - update plan type
                await sb.update_user_plan(user["id"], "business")
            else:
                # Add credits
                await sb.add_credits(user["id"], package["credits"])
            
            print(f"✅ Payment successful: Added {package['credits']} credits to user {user['id']}")
            
            return {
                "status": "success",
                "credits_added": package["credits"],
                "plan": package["plan"]
            }
        else:
            print(f"❌ Payment execution failed: {payment.error}")
            raise HTTPException(status_code=400, detail=f"Payment execution failed: {payment.error}")
    
    except Exception as e:
        print(f"❌ Payment execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute payment: {str(e)}")


@app.get("/api/payments")
async def get_payment_history(authorization: Optional[str] = Header(None)):
    """Get user's payment history."""
    user = await _get_user(authorization)
    payments = await sb.get_user_payments(user["id"])
    return payments


# ---------------------------------------------------------------------------
# Team CRUD Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/teams")
async def create_team(body: TeamCreate, authorization: Optional[str] = Header(None)):
    """Create a new team (Business plan only)."""
    user = await _get_user(authorization)
    user_id = user["id"]

    # Check plan is business
    profile = await sb.get_profile(user_id)
    if not profile or profile.get("plan") != "business":
        raise HTTPException(status_code=403, detail="Team features require a Business plan")

    # Check user doesn't already have a team
    if profile.get("team_id"):
        raise HTTPException(status_code=400, detail="User already belongs to a team")

    team = await sb.create_team(user_id, body.name)
    if not team:
        raise HTTPException(status_code=500, detail="Failed to create team")
    return team


@app.get("/api/teams/mine")
async def get_my_team(authorization: Optional[str] = Header(None)):
    """Get the current user's team info with members list."""
    user = await _get_user(authorization)
    user_id = user["id"]

    team = await sb.get_user_team(user_id)
    if not team:
        return {"team": None}

    members = await sb.get_team_members(team["id"])
    team["members"] = members
    return team


@app.post("/api/teams/{team_id}/invite", status_code=201)
async def invite_team_member(team_id: str, body: InviteRequest, authorization: Optional[str] = Header(None)):
    """Invite a user to the team by email (owner only)."""
    user = await _get_user(authorization)

    # Verify caller is the team owner
    team = await sb.get_team(team_id)
    if not team or team["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only the team owner can invite members")

    # Check member count < 10
    members = await sb.get_team_members(team_id)
    if len(members) >= 10:
        raise HTTPException(status_code=400, detail="Team member limit reached")

    invitation = await sb.create_invitation(team_id, body.email, user["id"])
    if not invitation:
        raise HTTPException(status_code=500, detail="Failed to create invitation")
    return invitation


@app.delete("/api/teams/{team_id}/invitations/{inv_id}")
async def revoke_invitation(team_id: str, inv_id: str, authorization: Optional[str] = Header(None)):
    """Revoke a team invitation (owner only)."""
    user = await _get_user(authorization)

    # Verify caller is the team owner
    team = await sb.get_team(team_id)
    if not team or team["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only the team owner can invite members")

    success = await sb.revoke_invitation(inv_id)
    if not success:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return {"status": "revoked"}


@app.get("/api/invitations")
async def list_pending_invitations(authorization: Optional[str] = Header(None)):
    """List pending invitations for the current user's email."""
    user = await _get_user(authorization)

    profile = await sb.get_profile(user["id"])
    if not profile or not profile.get("email"):
        return []

    invitations = await sb.get_pending_invitations(profile["email"])
    return invitations


@app.post("/api/invitations/{inv_id}/accept")
async def accept_invitation(inv_id: str, authorization: Optional[str] = Header(None)):
    """Accept a team invitation."""
    user = await _get_user(authorization)
    user_id = user["id"]

    # Check user doesn't already have a team
    profile = await sb.get_profile(user_id)
    if profile and profile.get("team_id"):
        raise HTTPException(status_code=400, detail="User is already a member of a team")

    success = await sb.accept_invitation(inv_id, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to accept invitation")
    return {"status": "accepted"}


@app.post("/api/invitations/{inv_id}/decline")
async def decline_invitation(inv_id: str, authorization: Optional[str] = Header(None)):
    """Decline a team invitation."""
    user = await _get_user(authorization)

    success = await sb.decline_invitation(inv_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to decline invitation")
    return {"status": "declined"}


@app.delete("/api/teams/{team_id}/members/{member_user_id}")
async def remove_team_member(team_id: str, member_user_id: str, authorization: Optional[str] = Header(None)):
    """Remove a member from the team (owner only)."""
    user = await _get_user(authorization)

    # Verify caller is the team owner
    team = await sb.get_team(team_id)
    if not team or team["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only the team owner can manage members")

    success = await sb.remove_team_member(team_id, member_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"status": "removed"}


@app.get("/api/teams/{team_id}/analyses")
async def list_team_analyses(team_id: str, authorization: Optional[str] = Header(None)):
    """List all analyses from team members."""
    user = await _get_user(authorization)

    # Verify caller is a team member
    members = await sb.get_team_members(team_id)
    member_ids = [m["user_id"] for m in members]
    if user["id"] not in member_ids:
        raise HTTPException(status_code=403, detail="Not a member of this team")

    analyses = await sb.get_team_analyses(team_id)
    return analyses
