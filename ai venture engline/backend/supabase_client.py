"""Supabase client for auth verification, profile management, and analysis storage."""

import asyncio
import json
import os
from typing import Optional

import httpx

SSL_VERIFY = False

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

PLAN_LIMITS = {
    "free": 3,
    "pro": 50,
    "business": 999999,  # unlimited
}


def _headers_service() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


def _headers_user(token: str) -> dict:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def verify_token(token: str) -> Optional[dict]:
    """Verify a Supabase JWT and return the user object, or None."""
    async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
        resp = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers=_headers_user(token),
        )
        if resp.status_code == 200:
            return resp.json()
    return None


async def get_profile(user_id: str) -> Optional[dict]:
    """Fetch a user's profile using service role."""
    async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}&select=*",
            headers={**_headers_service(), "Prefer": "return=representation"},
        )
        if resp.status_code == 200:
            data = resp.json()
            return data[0] if data else None
    return None


async def check_credits(user_id: str) -> dict:
    """Check if user has credits remaining. Returns {allowed, used, limit, plan}."""
    profile = await get_profile(user_id)
    if not profile:
        return {"allowed": False, "used": 0, "limit": 0, "plan": "free", "error": "Profile not found"}

    plan = profile.get("plan", "free")

    # If user is on a team, use team credits
    if profile.get("team_id"):
        team = await get_team(profile["team_id"])
        if team:
            used = team.get("team_credits_used", 0)
            limit = team.get("team_credits_limit", 999999)
            return {
                "allowed": used < limit,
                "used": used,
                "limit": limit,
                "plan": plan,
                "team_id": team["id"],
            }

    # Individual credits (existing logic)
    db_limit = profile.get("credits_limit")
    limit = db_limit if db_limit is not None else PLAN_LIMITS.get(plan, 3)
    used = profile.get("credits_used", 0)

    return {
        "allowed": used < limit,
        "used": used,
        "limit": limit,
        "plan": plan,
    }


async def increment_credits(user_id: str) -> bool:
    """Increment the user's credits_used by 1."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            # First get current value
            profile = await get_profile(user_id)
            if not profile:
                print(f"❌ increment_credits: Profile not found for user {user_id}")
                print(f"   This usually means the user doesn't exist in the profiles table")
                print(f"   Check if user {user_id} exists in Supabase auth.users")
                return False

            current_count = profile.get("credits_used", 0)
            new_count = current_count + 1

            print(f"\n{'='*60}")
            print(f"📊 CREDIT INCREMENT ATTEMPT")
            print(f"{'='*60}")
            print(f"User ID: {user_id}")
            print(f"Current credits_used: {current_count}")
            print(f"New credits_used: {new_count}")
            print(f"Current profile data: {json.dumps(profile, indent=2)}")
            print(f"{'='*60}\n")

            # Use service role headers to bypass RLS
            url = f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}"
            headers = {**_headers_service(), "Prefer": "return=representation"}
            payload = {"credits_used": new_count}
            
            print(f"🔧 REQUEST DETAILS:")
            print(f"   Method: PATCH")
            print(f"   URL: {url}")
            print(f"   Headers: {json.dumps({k: v[:20] + '...' if len(v) > 20 else v for k, v in headers.items()}, indent=2)}")
            print(f"   Payload: {json.dumps(payload, indent=2)}")
            print()
            
            resp = await client.patch(url, headers=headers, json=payload)

            print(f"📥 RESPONSE DETAILS:")
            print(f"   Status: {resp.status_code}")
            print(f"   Headers: {dict(resp.headers)}")
            print(f"   Body: {resp.text}")
            print()

            success = resp.status_code in (200, 204)

            if not success:
                print(f"❌ INCREMENT FAILED")
                print(f"   Status code: {resp.status_code}")
                print(f"   URL: {resp.url}")
                print(f"   Response: {resp.text}")
                print(f"   This might be an RLS policy issue or database constraint")
                return False

            # Wait a moment for database to commit
            await asyncio.sleep(0.5)

            # Verify the update actually happened
            updated_profile = await get_profile(user_id)
            if updated_profile and updated_profile.get("credits_used") == new_count:
                print(f"✅ SUCCESS: Credit incremented and verified")
                print(f"   User {user_id} now has {new_count} credits used")
                print(f"   Updated profile: {json.dumps(updated_profile, indent=2)}")
                print(f"{'='*60}\n")
                return True
            else:
                actual_count = updated_profile.get("credits_used", 0) if updated_profile else "unknown"
                print(f"❌ VERIFICATION FAILED")
                print(f"   Expected credits_used: {new_count}")
                print(f"   Actual credits_used: {actual_count}")
                print(f"   Updated profile: {json.dumps(updated_profile, indent=2) if updated_profile else 'None'}")
                print(f"   The PATCH succeeded but the database value didn't change")
                print(f"   This might be a database trigger or constraint issue")
                print(f"{'='*60}\n")
                return False

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ EXCEPTION IN increment_credits")
        print(f"{'='*60}")
        print(f"User ID: {user_id}")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        print(f"{'='*60}\n")
        import traceback
        traceback.print_exc()
        return False




async def save_analysis(user_id: str, analysis_id: str, memo_dict: dict) -> bool:
    """Save a completed analysis to the database."""
    row = {
        "user_id": user_id,
        "analysis_id": analysis_id,
        "startup_name": memo_dict.get("startup_overview", "Unknown")[:100],
        "industry": None,
        "stage": None,
        "final_score": memo_dict.get("final_score"),
        "verdict": memo_dict.get("verdict"),
        "memo_json": memo_dict,
    }

    # Extract startup name and industry from structured extraction
    se = memo_dict.get("structured_extraction")
    if se:
        row["startup_name"] = se.get("startup_name", row["startup_name"])
        row["industry"] = se.get("industry")
        row["stage"] = se.get("stage")

    async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/analyses",
            headers={**_headers_service(), "Prefer": "return=minimal"},
            json=row,
        )
        return resp.status_code in (200, 201)


async def get_user_analyses(user_id: str) -> list[dict]:
    """Fetch all analyses for a user, ordered by most recent."""
    async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/analyses"
            f"?user_id=eq.{user_id}"
            f"&select=id,analysis_id,startup_name,industry,stage,final_score,verdict,created_at"
            f"&order=created_at.desc",
            headers=_headers_service(),
        )
        if resp.status_code == 200:
            return resp.json()
    return []


async def get_analysis_memo(user_id: str, analysis_id: str) -> Optional[dict]:
    """Fetch a specific analysis memo for a user."""
    async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/analyses"
            f"?user_id=eq.{user_id}&analysis_id=eq.{analysis_id}"
            f"&select=memo_json",
            headers=_headers_service(),
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return data[0].get("memo_json")
    return None


async def get_startup_history(user_id: str, startup_name: str) -> list[dict]:
    """Fetch historical analyses for the same startup (for score timeline)."""
    async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/analyses"
            f"?user_id=eq.{user_id}&startup_name=ilike.{startup_name}"
            f"&select=analysis_id,final_score,verdict,created_at"
            f"&order=created_at.asc",
            headers=_headers_service(),
        )
        if resp.status_code == 200:
            return resp.json()
    return []


async def save_public_report(user_id: str, public_report) -> bool:
    """Save a public report to the database.
    
    Args:
        user_id: User ID who owns the analysis
        public_report: PublicReport object from report_generator
        
    Returns:
        True if successful, False otherwise
    """
    row = {
        "analysis_id": public_report.analysis_id,
        "user_id": user_id,
        "startup_name": public_report.startup_name,
        "investor_readiness_overall": public_report.investor_readiness_overall,
        "deal_breakers": [db.model_dump() for db in public_report.deal_breakers],
        "key_strengths": [ks.model_dump() for ks in public_report.key_strengths],
    }

    async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
        # Use upsert to handle duplicates
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/public_reports",
            headers={**_headers_service(), "Prefer": "resolution=merge-duplicates,return=minimal"},
            json=row,
        )
        return resp.status_code in (200, 201)


async def get_public_report(analysis_id: str) -> Optional[dict]:
    """Fetch a public report by analysis_id (no auth required).
    
    Args:
        analysis_id: Analysis ID to fetch
        
    Returns:
        Public report dict or None if not found
    """
    async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/public_reports"
            f"?analysis_id=eq.{analysis_id}"
            f"&select=startup_name,investor_readiness_overall,deal_breakers,key_strengths,created_at",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return data[0]
    return None



async def add_credits(user_id: str, amount: int) -> bool:
    """Add credits to a user's account (for purchases)."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            profile = await get_profile(user_id)
            if not profile:
                print(f"❌ add_credits: Profile not found for user {user_id}")
                return False
            
            current_limit = profile.get("credits_limit", 3)
            new_limit = current_limit + amount
            
            print(f"💳 Adding {amount} credits to {user_id}: {current_limit} → {new_limit}")
            
            resp = await client.patch(
                f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}",
                headers={**_headers_service(), "Prefer": "return=minimal"},
                json={"credits_limit": new_limit, "updated_at": "now()"},
            )
            
            success = resp.status_code in (200, 204)
            if not success:
                print(f"❌ add_credits: Failed with status {resp.status_code}: {resp.text}")
            
            return success
    except Exception as e:
        print(f"❌ add_credits: Exception: {e}")
        return False


async def update_stripe_customer(user_id: str, stripe_customer_id: str) -> bool:
    """Update user's Stripe customer ID."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            resp = await client.patch(
                f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}",
                headers={**_headers_service(), "Prefer": "return=minimal"},
                json={"stripe_customer_id": stripe_customer_id, "updated_at": "now()"},
            )
            return resp.status_code in (200, 204)
    except Exception as e:
        print(f"❌ update_stripe_customer: Exception: {e}")
        return False



async def save_payment(
    user_id: str,
    order_id: str,
    amount: float,
    credits_added: int,
    plan: str,
    status: str = "completed"
) -> bool:
    """Save a payment record to prevent duplicate credits."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/payments",
                headers={**_headers_service(), "Prefer": "return=minimal"},
                json={
                    "user_id": user_id,
                    "order_id": order_id,
                    "amount": amount,
                    "credits_added": credits_added,
                    "plan": plan,
                    "status": status,
                    "payment_method": "paypal"
                },
            )
            return resp.status_code in (200, 201)
    except Exception as e:
        print(f"❌ save_payment: Exception: {e}")
        return False


async def get_payment_by_order_id(order_id: str) -> Optional[dict]:
    """Check if a payment already exists (duplicate prevention)."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/payments?order_id=eq.{order_id}",
                headers=_headers_service(),
            )
            if resp.status_code == 200:
                data = resp.json()
                return data[0] if data else None
    except Exception as e:
        print(f"❌ get_payment_by_order_id: Exception: {e}")
    return None


async def get_user_payments(user_id: str) -> list[dict]:
    """Get all payments for a user."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/payments"
                f"?user_id=eq.{user_id}"
                f"&select=id,order_id,amount,credits_added,plan,status,created_at"
                f"&order=created_at.desc",
                headers=_headers_service(),
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"❌ get_user_payments: Exception: {e}")
    return []


async def update_user_plan(user_id: str, plan: str) -> bool:
    """Update user's plan (for unlimited plans)."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            resp = await client.patch(
                f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}",
                headers={**_headers_service(), "Prefer": "return=minimal"},
                json={"plan": plan, "updated_at": "now()"},
            )
            return resp.status_code in (200, 204)
    except Exception as e:
        print(f"❌ update_user_plan: Exception: {e}")
        return False


async def get_score_percentile(score: float) -> dict:
    """Calculate what percentile a score falls in across all analyses.
    
    Args:
        score: The investor readiness score to rank
        
    Returns:
        Dict with total_analyses, rank, and percentile
    """
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            # Get total count of public reports
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/public_reports"
                f"?select=investor_readiness_overall",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                all_scores = [r["investor_readiness_overall"] for r in resp.json()]
                if not all_scores:
                    return {"total_analyses": 0, "percentile": 50, "rank": 1}
                
                total = len(all_scores)
                # Count how many scores are below this one
                below = sum(1 for s in all_scores if s < score)
                percentile = round((below / total) * 100)
                rank = total - below
                
                return {
                    "total_analyses": total,
                    "percentile": min(percentile, 99),  # Cap at 99
                    "rank": max(rank, 1),
                }
    except Exception as e:
        print(f"❌ get_score_percentile: Exception: {e}")
    return {"total_analyses": 0, "percentile": 50, "rank": 1}


async def save_vc_impression(user_id: str, analysis_id: str, impression_data: list) -> bool:
    """Save VC first impression data alongside the public report.
    
    We store this in the public_reports table as an additional column.
    Falls back gracefully if column doesn't exist yet.
    """
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            resp = await client.patch(
                f"{SUPABASE_URL}/rest/v1/public_reports"
                f"?analysis_id=eq.{analysis_id}&user_id=eq.{user_id}",
                headers={**_headers_service(), "Prefer": "return=minimal"},
                json={"vc_impression": impression_data},
            )
            return resp.status_code in (200, 204)
    except Exception as e:
        print(f"⚠️ save_vc_impression: {e} (column may not exist yet)")
    return False


async def get_vc_impression(analysis_id: str) -> list:
    """Get VC first impression data for a public report."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/public_reports"
                f"?analysis_id=eq.{analysis_id}"
                f"&select=vc_impression",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and data[0].get("vc_impression"):
                    return data[0]["vc_impression"]
    except Exception as e:
        print(f"⚠️ get_vc_impression: {e}")
    return []


# ── Team CRUD Functions ──────────────────────────────────────────────────────


async def create_team(owner_id: str, name: str) -> Optional[dict]:
    """Create a new team, add the owner as a member, and update their profile."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            # 1. Create the team record
            resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/teams",
                headers={**_headers_service(), "Prefer": "return=representation"},
                json={"name": name, "owner_id": owner_id},
            )
            if resp.status_code not in (200, 201):
                print(f"❌ create_team: Failed to create team: {resp.status_code} {resp.text}")
                return None
            team = resp.json()
            if isinstance(team, list):
                team = team[0]
            team_id = team["id"]

            # 2. Insert owner into team_members
            await client.post(
                f"{SUPABASE_URL}/rest/v1/team_members",
                headers={**_headers_service(), "Prefer": "return=minimal"},
                json={"team_id": team_id, "user_id": owner_id, "role": "owner"},
            )

            # 3. Update owner's profile.team_id
            await client.patch(
                f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{owner_id}",
                headers={**_headers_service(), "Prefer": "return=minimal"},
                json={"team_id": team_id},
            )

            return team
    except Exception as e:
        print(f"❌ create_team: Exception: {e}")
        return None


async def get_team(team_id: str) -> Optional[dict]:
    """Fetch a team by its ID."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/teams?id=eq.{team_id}&select=*",
                headers=_headers_service(),
            )
            if resp.status_code == 200:
                data = resp.json()
                return data[0] if data else None
    except Exception as e:
        print(f"❌ get_team: Exception: {e}")
    return None


async def get_user_team(user_id: str) -> Optional[dict]:
    """Get the team for a user (via their profile.team_id). Returns None if no team."""
    try:
        profile = await get_profile(user_id)
        if not profile or not profile.get("team_id"):
            return None
        return await get_team(profile["team_id"])
    except Exception as e:
        print(f"❌ get_user_team: Exception: {e}")
    return None


async def create_invitation(team_id: str, email: str, invited_by: str) -> Optional[dict]:
    """Create a team invitation for the given email."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/team_invitations",
                headers={**_headers_service(), "Prefer": "return=representation"},
                json={
                    "team_id": team_id,
                    "email": email,
                    "invited_by": invited_by,
                    "status": "pending",
                },
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                return data[0] if isinstance(data, list) else data
            print(f"❌ create_invitation: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"❌ create_invitation: Exception: {e}")
    return None


async def get_pending_invitations(email: str) -> list[dict]:
    """Get all pending invitations for an email, enriched with team name."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            # 1. Fetch pending invitations
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/team_invitations"
                f"?email=eq.{email}&status=eq.pending"
                f"&select=*"
                f"&order=created_at.desc",
                headers=_headers_service(),
            )
            if resp.status_code != 200:
                return []
            invitations = resp.json()
            if not invitations:
                return []

            # 2. Enrich each invitation with the team name
            for inv in invitations:
                team = await get_team(inv["team_id"])
                inv["team_name"] = team["name"] if team else "Unknown"

            return invitations
    except Exception as e:
        print(f"❌ get_pending_invitations: Exception: {e}")
    return []


async def revoke_invitation(invitation_id: str) -> bool:
    """Delete (revoke) a team invitation."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            resp = await client.delete(
                f"{SUPABASE_URL}/rest/v1/team_invitations?id=eq.{invitation_id}",
                headers=_headers_service(),
            )
            return resp.status_code in (200, 204)
    except Exception as e:
        print(f"❌ revoke_invitation: Exception: {e}")
    return False


async def accept_invitation(invitation_id: str, user_id: str) -> bool:
    """Accept a pending invitation: add member, update invitation status, set profile.team_id."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            # (a) GET the invitation and verify it's pending
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/team_invitations?id=eq.{invitation_id}&select=*",
                headers=_headers_service(),
            )
            if resp.status_code != 200:
                return False
            data = resp.json()
            if not data:
                return False
            invitation = data[0]
            if invitation.get("status") != "pending":
                print(f"❌ accept_invitation: Invitation is not pending (status={invitation.get('status')})")
                return False

            team_id = invitation["team_id"]

            # (b) Add user as team member
            if not await add_team_member(team_id, user_id, role="member"):
                print(f"❌ accept_invitation: Failed to add team member")
                return False

            # (c) Update invitation status to "accepted"
            resp = await client.patch(
                f"{SUPABASE_URL}/rest/v1/team_invitations?id=eq.{invitation_id}",
                headers={**_headers_service(), "Prefer": "return=minimal"},
                json={"status": "accepted"},
            )
            if resp.status_code not in (200, 204):
                print(f"❌ accept_invitation: Failed to update invitation status: {resp.status_code}")

            # (d) Update user's profile.team_id
            resp = await client.patch(
                f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}",
                headers={**_headers_service(), "Prefer": "return=minimal"},
                json={"team_id": team_id},
            )
            if resp.status_code not in (200, 204):
                print(f"❌ accept_invitation: Failed to update profile team_id: {resp.status_code}")

            return True
    except Exception as e:
        print(f"❌ accept_invitation: Exception: {e}")
    return False


async def decline_invitation(invitation_id: str) -> bool:
    """Decline a team invitation by setting its status to 'declined'."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            resp = await client.patch(
                f"{SUPABASE_URL}/rest/v1/team_invitations?id=eq.{invitation_id}",
                headers={**_headers_service(), "Prefer": "return=minimal"},
                json={"status": "declined"},
            )
            return resp.status_code in (200, 204)
    except Exception as e:
        print(f"❌ decline_invitation: Exception: {e}")
    return False


async def add_team_member(team_id: str, user_id: str, role: str = "member") -> bool:
    """Insert a user into the team_members table."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/team_members",
                headers={**_headers_service(), "Prefer": "return=minimal"},
                json={"team_id": team_id, "user_id": user_id, "role": role},
            )
            return resp.status_code in (200, 201)
    except Exception as e:
        print(f"❌ add_team_member: Exception: {e}")
    return False


async def remove_team_member(team_id: str, user_id: str) -> bool:
    """Remove a member from the team and clear their profile.team_id."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            # 1. Delete from team_members
            resp = await client.delete(
                f"{SUPABASE_URL}/rest/v1/team_members?team_id=eq.{team_id}&user_id=eq.{user_id}",
                headers=_headers_service(),
            )
            if resp.status_code not in (200, 204):
                print(f"❌ remove_team_member: Failed to delete member: {resp.status_code}")
                return False

            # 2. Clear profile.team_id
            resp = await client.patch(
                f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}",
                headers={**_headers_service(), "Prefer": "return=minimal"},
                json={"team_id": None},
            )
            if resp.status_code not in (200, 204):
                print(f"❌ remove_team_member: Failed to clear profile team_id: {resp.status_code}")

            return True
    except Exception as e:
        print(f"❌ remove_team_member: Exception: {e}")
    return False


async def get_team_members(team_id: str) -> list[dict]:
    """Get all members of a team."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/team_members?team_id=eq.{team_id}&select=*",
                headers=_headers_service(),
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"❌ get_team_members: Exception: {e}")
    return []


async def get_team_analyses(team_id: str) -> list[dict]:
    """Get all analyses from team members. Queries member user_ids, then fetches their analyses."""
    try:
        # 1. Get all team member user_ids
        members = await get_team_members(team_id)
        if not members:
            return []
        user_ids = [m["user_id"] for m in members]
        ids_param = ",".join(user_ids)

        # 2. Query analyses where user_id is in the member list
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/analyses"
                f"?user_id=in.({ids_param})"
                f"&select=id,analysis_id,user_id,startup_name,industry,stage,final_score,verdict,created_at"
                f"&order=created_at.desc",
                headers=_headers_service(),
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"❌ get_team_analyses: Exception: {e}")
    return []


async def check_team_credits(team_id: str) -> dict:
    """Check team credit usage. Returns {allowed, used, limit}."""
    try:
        team = await get_team(team_id)
        if not team:
            return {"allowed": False, "used": 0, "limit": 0, "error": "Team not found"}
        used = team.get("team_credits_used", 0)
        limit = team.get("team_credits_limit", 999999)
        return {
            "allowed": used < limit,
            "used": used,
            "limit": limit,
        }
    except Exception as e:
        print(f"❌ check_team_credits: Exception: {e}")
    return {"allowed": False, "used": 0, "limit": 0, "error": "Exception"}


async def increment_team_credits(team_id: str) -> bool:
    """Increment the team's team_credits_used by 1."""
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            team = await get_team(team_id)
            if not team:
                print(f"❌ increment_team_credits: Team not found: {team_id}")
                return False

            new_used = team.get("team_credits_used", 0) + 1

            resp = await client.patch(
                f"{SUPABASE_URL}/rest/v1/teams?id=eq.{team_id}",
                headers={**_headers_service(), "Prefer": "return=minimal"},
                json={"team_credits_used": new_used},
            )
            return resp.status_code in (200, 204)
    except Exception as e:
        print(f"❌ increment_team_credits: Exception: {e}")
    return False
