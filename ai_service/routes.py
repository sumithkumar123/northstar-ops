from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import queries
from database import get_db
import sys
sys.path.insert(0, "/app")
from shared.dependencies import require_role
from shared.schemas import UserRole, TokenPayload

router = APIRouter(prefix="/ai", tags=["ai"])

MANAGER_UP = [UserRole.regional_admin, UserRole.store_manager]

class NLQueryRequest(BaseModel):
    question: str
    store_id: str | None = None

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

@router.get("/health")
async def health():
    return {"status": "ok", "service": "ai"}
