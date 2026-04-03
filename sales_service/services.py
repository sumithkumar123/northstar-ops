"""
Sales business logic.
Order state machine: draft → confirmed → paid (or voided at any pre-paid step).
Inventory decrement via synchronous httpx call to Inventory Service.
offline_id unique constraint makes PWA retries idempotent.
"""
import os
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import List

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models import SalesOrder, SalesOrderItem, Customer
from tax import calculate_tax
from receipt import generate_receipt

INVENTORY_SERVICE_URL = os.environ.get("INVENTORY_SERVICE_URL", "http://inventory_service:8002")


async def _decrement_inventory(
    store_id: str,
    items: List[dict],
    cashier_id: str,
    order_id: str,
    token: str,
) -> None:
    """
    Call Inventory Service to decrement stock for each line item.
    Raises HTTPException(409) on insufficient stock so the transaction rolls back.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        for item in items:
            resp = await client.patch(
                f"{INVENTORY_SERVICE_URL}/inventory/stores/{store_id}/products/{item['product_id']}",
                json={
                    "delta": -item["quantity"],
                    "transaction_type": "sale",
                    "reference_id": order_id,
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 409:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Insufficient stock for product {item['sku']}",
                )
            if resp.status_code not in (200, 201):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Inventory service error for {item['sku']}: {resp.text}",
                )


async def create_order(
    db: AsyncSession,
    store_id: str,
    cashier_id: str,
    items: List[dict],
    payment_method: str,
    country_code: str,
    state_code: str | None,
    token: str,
    offline_id: str | None = None,
    customer_id: str | None = None,
) -> dict:
    # Idempotency: if offline_id already exists, return existing order
    if offline_id:
        existing = await db.execute(
            select(SalesOrder).options(selectinload(SalesOrder.items))
            .where(SalesOrder.offline_id == offline_id)
        )
        existing_order = existing.scalar_one_or_none()
        if existing_order:
            return _serialize_order(existing_order)

    order_id = str(uuid.uuid4())
    subtotal = Decimal("0")
    order_items = []

    for item in items:
        unit_price = Decimal(str(item["unit_price"]))
        qty = item["quantity"]
        line_total = unit_price * qty
        subtotal += line_total
        order_items.append(
            SalesOrderItem(
                order_id=uuid.UUID(order_id),
                product_id=uuid.UUID(item["product_id"]),
                sku=item["sku"],
                product_name=item["product_name"],
                quantity=qty,
                unit_price=unit_price,
                line_total=line_total,
            )
        )

    tax_amount = calculate_tax(subtotal, country_code, state_code)
    total = subtotal + tax_amount
    now = datetime.utcnow()

    order = SalesOrder(
        id=uuid.UUID(order_id),
        offline_id=offline_id,
        store_id=uuid.UUID(store_id),
        customer_id=uuid.UUID(customer_id) if customer_id else None,
        cashier_id=uuid.UUID(cashier_id),
        status="draft",
        subtotal=subtotal,
        tax_amount=tax_amount,
        total=total,
        country_code=country_code,
        payment_method=payment_method,
    )
    db.add(order)
    for oi in order_items:
        db.add(oi)
    await db.flush()  # persist draft before calling inventory

    # Decrement stock — if this fails, the outer transaction rolls back
    await _decrement_inventory(store_id, items, cashier_id, order_id, token)

    order.status = "paid"
    order.paid_at = now
    await db.commit()

    # Re-fetch with eager-loaded items so _serialize_order can access them
    result = await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.items))
        .where(SalesOrder.id == uuid.UUID(order_id))
    )
    order = result.scalar_one()
    return _serialize_order(order)


async def void_order(db: AsyncSession, order_id: str, voided_by: str) -> dict:
    result = await db.execute(select(SalesOrder).where(SalesOrder.id == uuid.UUID(order_id)))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status == "voided":
        raise HTTPException(status_code=409, detail="Order already voided")
    if order.status == "paid":
        raise HTTPException(
            status_code=409,
            detail="Paid orders cannot be voided directly — raise a refund",
        )
    order.status = "voided"
    await db.commit()
    return {"order_id": order_id, "status": "voided"}


async def get_order(db: AsyncSession, order_id: str) -> dict:
    result = await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.items))
        .where(SalesOrder.id == uuid.UUID(order_id))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _serialize_order(order)


async def daily_report(db: AsyncSession, store_id: str, report_date: date) -> dict:
    start = datetime.combine(report_date, datetime.min.time())
    end = datetime.combine(report_date, datetime.max.time())
    result = await db.execute(
        select(
            func.count(SalesOrder.id).label("order_count"),
            func.sum(SalesOrder.total).label("revenue"),
            func.sum(SalesOrder.tax_amount).label("tax_collected"),
        ).where(
            SalesOrder.store_id == uuid.UUID(store_id),
            SalesOrder.status == "paid",
            SalesOrder.paid_at >= start,
            SalesOrder.paid_at <= end,
        )
    )
    row = result.one()
    return {
        "store_id": store_id,
        "date": report_date.isoformat(),
        "order_count": row.order_count or 0,
        "revenue": float(row.revenue or 0),
        "tax_collected": float(row.tax_collected or 0),
    }


async def weekly_report(db: AsyncSession, store_id: str) -> list:
    """7-day revenue grouped by date. Frontend fills in zero-revenue days."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=7)
    result = await db.execute(
        select(
            func.date(SalesOrder.paid_at).label("date"),
            func.sum(SalesOrder.total).label("revenue"),
            func.count(SalesOrder.id).label("order_count"),
        ).where(
            SalesOrder.store_id == uuid.UUID(store_id),
            SalesOrder.status == "paid",
            SalesOrder.paid_at >= cutoff,
        ).group_by(func.date(SalesOrder.paid_at))
        .order_by(func.date(SalesOrder.paid_at))
    )
    return [
        {"date": str(row.date), "revenue": float(row.revenue or 0), "order_count": row.order_count}
        for row in result
    ]


async def top_products(db: AsyncSession, store_id: str) -> list:
    """Best-selling products for the store (all time, top 10 by units sold)."""
    result = await db.execute(
        select(
            SalesOrderItem.sku,
            SalesOrderItem.product_name,
            func.sum(SalesOrderItem.quantity).label("units_sold"),
            func.sum(SalesOrderItem.line_total).label("revenue"),
        )
        .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
        .where(
            SalesOrder.store_id == uuid.UUID(store_id),
            SalesOrder.status == "paid",
        )
        .group_by(SalesOrderItem.sku, SalesOrderItem.product_name)
        .order_by(func.sum(SalesOrderItem.quantity).desc())
        .limit(10)
    )
    return [
        {"sku": r.sku, "product_name": r.product_name,
         "units_sold": int(r.units_sold or 0), "revenue": float(r.revenue or 0)}
        for r in result
    ]


def _serialize_order(order: SalesOrder) -> dict:
    return {
        "id": str(order.id),
        "offline_id": order.offline_id,
        "store_id": str(order.store_id),
        "cashier_id": str(order.cashier_id),
        "status": order.status,
        "subtotal": float(order.subtotal),
        "tax_amount": float(order.tax_amount),
        "total": float(order.total),
        "payment_method": order.payment_method,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "items": [
            {
                "product_id": str(i.product_id),
                "sku": i.sku,
                "product_name": i.product_name,
                "quantity": i.quantity,
                "unit_price": float(i.unit_price),
                "line_total": float(i.line_total),
            }
            for i in (order.items or [])
        ],
    }
