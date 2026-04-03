from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import queries
from database import get_db

router = APIRouter(prefix="/ai", tags=["ai"])

MANAGER_ROLES = {"regional_admin", "store_manager"}


def _require_manager(request: Request):
    """Read role from gateway-injected header. Reject sales_associate."""
    role = request.headers.get("x-user-role", "")
    if role not in MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI insights require store_manager or regional_admin role",
        )


class NLQueryRequest(BaseModel):
    question: str
    store_id: str | None = None


@router.get("/recommendations/{store_id}")
async def recommendations(
    store_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _require_manager(request)
    return await queries.get_recommendations(db, store_id)


@router.get("/anomalies")
async def anomalies(
    store_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _require_manager(request)
    return await queries.get_anomalies(db, store_id)


@router.post("/query")
async def nl_query(
    body: NLQueryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _require_manager(request)
    return await queries.run_nl_query(db, body.question, body.store_id)


@router.get("/health")
async def health():
    return {"status": "ok", "service": "ai"}
