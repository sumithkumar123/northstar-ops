import sys, os
sys.path.insert(0, "/app")

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import services
from database import get_db
from shared.dependencies import require_role, require_store_access
from shared.schemas import UserRole, TokenPayload

router = APIRouter(prefix="/inventory", tags=["inventory"])

ALL_ROLES = [UserRole.regional_admin, UserRole.store_manager, UserRole.sales_associate]
MANAGER_UP = [UserRole.regional_admin, UserRole.store_manager]


class AdjustRequest(BaseModel):
    delta: int
    transaction_type: str   # sale | restock | adjustment | transfer_in | transfer_out
    reference_id: str | None = None
    note: str | None = None


class CreateProductRequest(BaseModel):
    sku: str
    name: str
    description: str = ""
    unit_price: float
    reorder_point: int = 10
    category_name: str | None = None


class InitInventoryRequest(BaseModel):
    product_id: str
    quantity: int = 0


@router.get("/stores/{store_id}")
async def get_store_inventory(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_store_access()),
):
    return await services.list_store_inventory(db, store_id)


@router.patch("/stores/{store_id}/products/{product_id}")
async def adjust_stock(
    store_id: str,
    product_id: str,
    body: AdjustRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_role(MANAGER_UP)),
):
    return await services.adjust_stock(
        db, store_id, product_id, body.delta, body.transaction_type,
        str(current_user.sub), body.reference_id, body.note,
    )


@router.post("/products")
async def create_product(
    body: CreateProductRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_role([UserRole.regional_admin])),
):
    return await services.create_product(
        db, body.sku, body.name, body.description,
        body.unit_price, body.reorder_point, body.category_name,
    )


@router.get("/products/{sku}")
async def get_product(
    sku: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_role(ALL_ROLES)),
):
    prod = await services.get_product_by_sku(db, sku)
    if not prod:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Product not found")
    return prod


@router.post("/stores/{store_id}/init")
async def init_inventory(
    store_id: str,
    body: InitInventoryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_role([UserRole.regional_admin])),
):
    inv = await services.initialize_store_inventory(db, store_id, body.product_id, body.quantity)
    return {"store_id": store_id, "product_id": body.product_id, "quantity": body.quantity}


@router.get("/stores/{store_id}/alerts")
async def get_low_stock_alerts(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_store_access()),
):
    return await services.get_low_stock_alerts(db, store_id)


@router.get("/health")
async def health():
    return {"status": "ok", "service": "inventory"}
