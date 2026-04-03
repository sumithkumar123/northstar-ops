"""
Inventory business logic.
Key pattern: adjust_stock() uses SELECT FOR UPDATE (pessimistic lock)
to prevent overselling when multiple POS terminals write concurrently.
"""
import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from models import Product, Inventory, InventoryTransaction, Category


async def list_store_inventory(db: AsyncSession, store_id: str) -> List[dict]:
    result = await db.execute(
        select(Inventory, Product)
        .join(Product, Inventory.product_id == Product.id)
        .where(Inventory.store_id == uuid.UUID(store_id))
    )
    rows = result.all()
    return [
        {
            "inventory_id": str(inv.id),
            "store_id": str(inv.store_id),
            "product_id": str(prod.id),
            "sku": prod.sku,
            "name": prod.name,
            "quantity": inv.quantity,
            "unit_price": float(prod.unit_price),
            "reorder_point": prod.reorder_point,
            "below_reorder": inv.quantity <= prod.reorder_point,
            "last_updated": inv.last_updated.isoformat() if inv.last_updated else None,
        }
        for inv, prod in rows
    ]


async def adjust_stock(
    db: AsyncSession,
    store_id: str,
    product_id: str,
    delta: int,
    transaction_type: str,
    performed_by: str,
    reference_id: str | None = None,
    note: str | None = None,
) -> dict:
    """
    Atomically adjust stock for (store_id, product_id).
    Uses SELECT FOR UPDATE so concurrent POS terminals cannot double-decrement.
    Raises 409 if delta would make quantity negative.
    """
    async with db.begin():
        result = await db.execute(
            select(Inventory)
            .where(
                Inventory.store_id == uuid.UUID(store_id),
                Inventory.product_id == uuid.UUID(product_id),
            )
            .with_for_update()   # <-- pessimistic lock: blocks concurrent adjustments on this row
        )
        inv = result.scalar_one_or_none()
        if inv is None:
            raise HTTPException(status_code=404, detail="Inventory record not found for this store/product")

        new_qty = inv.quantity + delta
        if new_qty < 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient stock: have {inv.quantity}, requested {abs(delta)}",
            )

        inv.quantity = new_qty

        txn = InventoryTransaction(
            inventory_id=inv.id,
            delta=delta,
            transaction_type=transaction_type,
            reference_id=reference_id,
            performed_by=uuid.UUID(performed_by) if performed_by else None,
            note=note,
        )
        db.add(txn)

    return {"product_id": product_id, "store_id": store_id, "new_quantity": new_qty}


async def get_product_by_sku(db: AsyncSession, sku: str) -> dict | None:
    result = await db.execute(select(Product).where(Product.sku == sku))
    prod = result.scalar_one_or_none()
    if not prod:
        return None
    return {
        "id": str(prod.id),
        "sku": prod.sku,
        "name": prod.name,
        "unit_price": float(prod.unit_price),
        "reorder_point": prod.reorder_point,
    }


async def create_product(db: AsyncSession, sku: str, name: str, description: str,
                          unit_price: float, reorder_point: int, category_name: str | None) -> dict:
    existing = await db.execute(select(Product).where(Product.sku == sku))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"SKU '{sku}' already exists")

    category_id = None
    if category_name:
        cat_result = await db.execute(select(Category).where(Category.name == category_name))
        cat = cat_result.scalar_one_or_none()
        if not cat:
            cat = Category(name=category_name)
            db.add(cat)
            await db.flush()
        category_id = cat.id

    prod = Product(
        sku=sku, name=name, description=description,
        unit_price=unit_price, reorder_point=reorder_point,
        category_id=category_id,
    )
    db.add(prod)
    await db.commit()
    return {"id": str(prod.id), "sku": prod.sku, "name": prod.name}


async def get_low_stock_alerts(db: AsyncSession, store_id: str) -> list:
    """Return inventory items at or below reorder point."""
    result = await db.execute(
        select(Inventory, Product)
        .join(Product, Inventory.product_id == Product.id)
        .where(
            Inventory.store_id == uuid.UUID(store_id),
            Inventory.quantity <= Product.reorder_point,
        )
    )
    return [
        {
            "inventory_id": str(inv.id),
            "store_id": str(inv.store_id),
            "product_id": str(prod.id),
            "sku": prod.sku,
            "name": prod.name,
            "quantity": inv.quantity,
            "reorder_point": prod.reorder_point,
            "unit_price": float(prod.unit_price),
            "severity": "critical" if inv.quantity == 0 else "warning",
        }
        for inv, prod in result
    ]


async def initialize_store_inventory(db: AsyncSession, store_id: str, product_id: str, quantity: int = 0):
    """Create an inventory record for a store/product pair (used by seed script)."""
    inv = Inventory(store_id=uuid.UUID(store_id), product_id=uuid.UUID(product_id), quantity=quantity)
    db.add(inv)
    await db.commit()
    return inv
