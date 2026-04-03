import sys
sys.path.insert(0, "/app")

from datetime import date
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

import services
from database import get_db
from shared.dependencies import require_role, require_store_access
from shared.schemas import UserRole, TokenPayload

router = APIRouter(prefix="/sales", tags=["sales"])

ALL_ROLES = [UserRole.regional_admin, UserRole.store_manager, UserRole.sales_associate]
MANAGER_UP = [UserRole.regional_admin, UserRole.store_manager]


class OrderItem(BaseModel):
    product_id: str
    sku: str
    product_name: str
    quantity: int
    unit_price: float


class CreateOrderRequest(BaseModel):
    store_id: str
    items: List[OrderItem]
    payment_method: str = "cash"
    country_code: str = "US"
    state_code: str | None = None
    offline_id: str | None = None
    customer_id: str | None = None


@router.post("/orders")
async def create_order(
    body: CreateOrderRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_role(ALL_ROLES)),
):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    return await services.create_order(
        db,
        store_id=body.store_id,
        cashier_id=str(current_user.sub),
        items=[i.model_dump() for i in body.items],
        payment_method=body.payment_method,
        country_code=body.country_code,
        state_code=body.state_code,
        token=token,
        offline_id=body.offline_id,
        customer_id=body.customer_id,
    )


@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_role(ALL_ROLES)),
):
    return await services.get_order(db, order_id)


@router.post("/orders/{order_id}/void")
async def void_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_role(MANAGER_UP)),
):
    return await services.void_order(db, order_id, str(current_user.sub))


@router.get("/reports/daily")
async def daily_report(
    store_id: str,
    report_date: date = date.today(),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_role(MANAGER_UP)),
):
    return await services.daily_report(db, store_id, report_date)


@router.get("/reports/weekly")
async def weekly_report(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_role(MANAGER_UP)),
):
    return await services.weekly_report(db, store_id)


@router.get("/reports/top-products")
async def top_products(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_role(MANAGER_UP)),
):
    return await services.top_products(db, store_id)


@router.get("/health")
async def health():
    return {"status": "ok", "service": "sales"}
