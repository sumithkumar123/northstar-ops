"""
AI Service Routes
==================
Combines the original deterministic endpoints (recommendations, anomalies, NL query)
with the new agentic endpoints powered by LangGraph + Gemini Flash.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
import json

import queries
from database import get_db
import sys
sys.path.insert(0, "/app")
from shared.dependencies import require_role
from shared.schemas import UserRole, TokenPayload
from agents.retail_agent import run_agent_query

router = APIRouter(prefix="/ai", tags=["ai"])

MANAGER_UP = [UserRole.regional_admin, UserRole.store_manager]


# ─────────────────────────────────────────────────────────────────────────────
# Original deterministic endpoints (kept for compatibility)
# ─────────────────────────────────────────────────────────────────────────────

class NLQueryRequest(BaseModel):
    question: str
    store_id: Optional[str] = None


@router.get("/recommendations/{store_id}")
async def recommendations(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_role(MANAGER_UP)),
):
    return await queries.get_recommendations(db, store_id)


@router.get("/anomalies")
async def anomalies(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_role(MANAGER_UP)),
):
    return await queries.get_anomalies(db, store_id)


@router.post("/query")
async def nl_query(
    body: NLQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_role(MANAGER_UP)),
):
    return await queries.run_nl_query(db, body.question, body.store_id)


# ─────────────────────────────────────────────────────────────────────────────
# NEW: Agentic endpoints — powered by LangGraph + Gemini Flash
# ─────────────────────────────────────────────────────────────────────────────

class AgentQueryRequest(BaseModel):
    question: str
    store_id: Optional[str] = None


@router.post("/agent/query")
async def agent_query(
    body: AgentQueryRequest,
    request: Request,
    current_user: TokenPayload = Depends(require_role(MANAGER_UP)),
):
    """
    Truly agentic endpoint: the LLM (Gemini Flash) receives the question,
    DECIDES which tools to call, calls them in sequence against live data,
    reasons over the results, and returns a synthesized answer.

    Unlike /ai/query (keyword matching), this endpoint uses a full ReAct loop:
    Reason → call tool → observe result → reason again → final answer.
    """
    agent = getattr(request.app.state, "agent", None)

    # Use the user's store_id from JWT if not specified
    store_id = body.store_id or str(current_user.store_id)

    result = await run_agent_query(
        question=body.question,
        store_id=store_id,
        agent=agent,
    )

    # Save the agent interaction to the audit log
    if "answer" in result and agent is not None:
        from database import AsyncSessionLocal
        import uuid
        from datetime import datetime, timezone
        async with AsyncSessionLocal() as db:
            try:
                await db.execute(text("""
                    INSERT INTO ai_agent_events
                        (id, agent_name, event_type, severity, store_id, summary, reasoning, payload, created_at)
                    VALUES
                        (:id, 'RetailAgent', 'INSIGHT', 'LOW', :store_id, :summary, :reasoning, :payload::json, :created_at)
                """), {
                    "id": str(uuid.uuid4()),
                    "store_id": store_id,
                    "summary": result["answer"][:300] if result.get("answer") else "Query processed",
                    "reasoning": f"Tools invoked: {', '.join(t['tool'] for t in result.get('tools_invoked', []))}",
                    "payload": json.dumps({"question": body.question, "tools_used": result.get("tools_invoked", [])}),
                    "created_at": datetime.now(timezone.utc),
                })
                await db.commit()
            except Exception:
                pass  # Don't fail the query if audit log write fails

    return result


@router.get("/agent/events")
async def agent_events(
    store_id: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_role(MANAGER_UP)),
):
    """
    Fetch the agent audit log — every autonomous decision made by the background
    sentinels and every on-demand query made through /ai/agent/query.
    Managers can see WHAT the AI did, WHEN, and WHY.
    """
    if store_id is None:
        store_id = str(current_user.store_id)

    result = await db.execute(text("""
        SELECT id, agent_name, event_type, severity, store_id,
               summary, reasoning, payload, created_at
        FROM ai_agent_events
        WHERE store_id = :store_id
           OR store_id IS NULL
        ORDER BY created_at DESC
        LIMIT :limit
    """), {"store_id": store_id, "limit": limit})

    rows = result.fetchall()
    events = []
    for r in rows:
        payload = r.payload
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        events.append({
            "id": r.id,
            "agent_name": r.agent_name,
            "event_type": r.event_type,
            "severity": r.severity,
            "store_id": r.store_id,
            "summary": r.summary,
            "reasoning": r.reasoning,
            "payload": payload,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {"events": events, "count": len(events)}


@router.get("/agent/status")
async def agent_status(request: Request):
    """Check if the LangGraph agent is online and which tools are available."""
    agent = getattr(request.app.state, "agent", None)
    from agents.tools import ALL_TOOLS
    from agents.retail_agent import INIT_ERROR
    
    return {
        "agent_online": agent is not None,
        "model": "gemini-1.5-flash" if agent else None,
        "framework": "LangGraph ReAct" if agent else None,
        "tools_available": [t.name for t in ALL_TOOLS],
        "autonomous_loops": ["RestockSentinel (10min)", "GuardianSentinel (5min)"] if agent else [],
        "message": "Agent ready" if agent else "Set GEMINI_API_KEY to enable agentic features",
        "init_error": INIT_ERROR,
    }

@router.get("/agent/models")
async def list_models():
    """Debug route: List all models available to the current API key."""
    import os
    import google.generativeai as genai
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return {"error": "API key not set"}
    try:
        genai.configure(api_key=key)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return {"available_models": models}
    except Exception as e:
        return {"error": str(e)}


@router.get("/health")
async def health():
    return {"status": "ok", "service": "ai", "version": "2.0.0"}
