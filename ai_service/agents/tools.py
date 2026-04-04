"""
NorthStar Retail Agent Tools
============================
These are the "hands" of the AI agent — callable functions the LLM decides
when and in what order to invoke.  Each tool hits the live PostgreSQL database
and returns structured JSON so the LLM can reason over real data.

The LLM (Gemini Flash) reads the docstring of each tool to decide when to use it.
That's why the docstrings are written in plain English describing business intent.
"""
import json
import math
from datetime import datetime
from typing import Optional

from langchain_core.tools import tool
from sqlalchemy import text

from database import AsyncSessionLocal


# ─────────────────────────────────────────────────────────────────────────────
# Tool 1 — Inventory snapshot
# ─────────────────────────────────────────────────────────────────────────────
@tool
async def check_inventory_levels(store_id: str) -> str:
    """
    Get current inventory levels for all products in a store.
    Returns each product's name, SKU, current quantity, reorder point, and
    whether it is currently below the reorder point (needs restocking).
    Use this first when a manager asks about stock, shortages, or what to order.

    Args:
        store_id: UUID of the store to check (e.g. 'b1000000-0000-0000-0000-000000000001')
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT
                p.name,
                p.sku,
                p.unit_price,
                c.name          AS category,
                inv.quantity    AS current_stock,
                p.reorder_point,
                CASE WHEN inv.quantity <= p.reorder_point THEN true ELSE false END AS needs_restock
            FROM inventory.inventory inv
            JOIN inventory.products p   ON p.id = inv.product_id
            JOIN inventory.categories c ON c.id = p.category_id
            WHERE inv.store_id = :store_id
            ORDER BY inv.quantity ASC
        """), {"store_id": store_id})

        rows = [dict(r._mapping) for r in result.fetchall()]
        for r in rows:
            r["unit_price"] = float(r["unit_price"])
        return json.dumps({"store_id": store_id, "inventory": rows, "total_products": len(rows)})


# ─────────────────────────────────────────────────────────────────────────────
# Tool 2 — Sales velocity analysis
# ─────────────────────────────────────────────────────────────────────────────
@tool
async def analyze_sales_velocity(store_id: str, days: int = 30) -> str:
    """
    Analyze how fast each product is selling (units sold per day) over the past N days.
    Also calculates how many days of stock remain at the current sales rate.
    Use this to understand demand trends, predict stockouts, or identify slow movers.

    Args:
        store_id: UUID of the store
        days: Number of past days to analyze (default: 30)
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT
                p.name,
                p.sku,
                c.name                      AS category,
                inv.quantity                AS current_stock,
                COALESCE(SUM(soi.quantity), 0) AS units_sold,
                COALESCE(SUM(soi.quantity)::float / :days, 0) AS daily_velocity,
                CASE
                    WHEN COALESCE(SUM(soi.quantity), 0) = 0 THEN 999
                    ELSE ROUND(inv.quantity / (COALESCE(SUM(soi.quantity), 0.01)::float / :days))
                END AS days_of_stock_remaining
            FROM inventory.inventory inv
            JOIN inventory.products p   ON p.id = inv.product_id
            JOIN inventory.categories c ON c.id = p.category_id
            LEFT JOIN sales.sales_order_items soi ON soi.product_id = p.id
            LEFT JOIN sales.sales_orders so
                ON so.id = soi.order_id
                AND so.store_id = :store_id
                AND so.status = 'paid'
                AND so.paid_at >= NOW() - make_interval(days => :days)
            WHERE inv.store_id = :store_id
            GROUP BY p.name, p.sku, c.name, inv.quantity
            ORDER BY daily_velocity DESC
        """), {"store_id": store_id, "days": days})

        rows = [dict(r._mapping) for r in result.fetchall()]
        for r in rows:
            r["daily_velocity"] = round(float(r["daily_velocity"]), 2)
            r["days_of_stock_remaining"] = int(r["days_of_stock_remaining"])

        return json.dumps({
            "store_id": store_id,
            "analysis_period_days": days,
            "products": rows
        })


# ─────────────────────────────────────────────────────────────────────────────
# Tool 3 — Transaction anomaly detection
# ─────────────────────────────────────────────────────────────────────────────
@tool
async def detect_transaction_anomalies(store_id: str, lookback_days: int = 90) -> str:
    """
    Detect statistically anomalous transactions using Z-score analysis.
    An order is flagged if its total is more than 2.5 standard deviations from the mean.
    Anomalies could indicate fraud (unusually high), data entry errors (unusually low),
    or system issues. Returns flagged orders with their Z-scores and likely cause.

    Args:
        store_id: UUID of the store to analyze
        lookback_days: How many days of history to analyze (default: 90)
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT id, total, cashier_id, paid_at, payment_method
            FROM sales.sales_orders
            WHERE store_id = :store_id
              AND status = 'paid'
              AND paid_at >= NOW() - make_interval(days => :days)
            ORDER BY paid_at DESC
        """), {"store_id": store_id, "days": lookback_days})

        orders = result.fetchall()

        if len(orders) < 5:
            return json.dumps({
                "status": "insufficient_data",
                "message": f"Only {len(orders)} orders found. Need at least 5 for meaningful anomaly detection.",
                "anomalies": []
            })

        totals = [float(o.total) for o in orders]
        mean = sum(totals) / len(totals)
        std = math.sqrt(sum((x - mean) ** 2 for x in totals) / len(totals)) or 0.001

        anomalies = []
        for o, total_val in zip(orders, totals):
            z = abs(total_val - mean) / std
            if z > 2.5:
                anomalies.append({
                    "order_id": str(o.id),
                    "total": round(total_val, 2),
                    "z_score": round(z, 2),
                    "paid_at": o.paid_at.isoformat(),
                    "payment_method": o.payment_method,
                    "suspected_cause": (
                        "Potential fraud or gift-card stuffing" if total_val > mean
                        else "Possible pricing error or missed items"
                    ),
                })

        return json.dumps({
            "orders_analyzed": len(orders),
            "mean_order_value": round(mean, 2),
            "std_deviation": round(std, 2),
            "anomaly_threshold": "z-score > 2.5",
            "anomalies_found": len(anomalies),
            "anomalies": anomalies
        })


# ─────────────────────────────────────────────────────────────────────────────
# Tool 4 — Seasonal product demand forecast
# ─────────────────────────────────────────────────────────────────────────────
@tool
async def get_seasonal_demand_forecast(store_id: str) -> str:
    """
    Identify which products are most relevant for the current season based on
    category preferences and recent sales velocity. Returns products the agent
    should recommend stocking up on or promoting.

    Seasons mapped to preferred categories:
      - Winter: Apparel, Equipment
      - Spring: Footwear, Apparel
      - Summer: Footwear, Equipment
      - Fall:   Apparel, Equipment

    Args:
        store_id: UUID of the store
    """
    month = datetime.utcnow().month
    if month in (12, 1, 2):
        season, preferred = "Winter", ["Apparel", "Equipment"]
    elif month in (3, 4, 5):
        season, preferred = "Spring", ["Footwear", "Apparel"]
    elif month in (6, 7, 8):
        season, preferred = "Summer", ["Footwear", "Equipment"]
    else:
        season, preferred = "Fall", ["Apparel", "Equipment"]

    cat_filter = ", ".join(f"'{c}'" for c in preferred)

    async with AsyncSessionLocal() as db:
        result = await db.execute(text(f"""
            SELECT
                p.name,
                p.sku,
                c.name          AS category,
                p.unit_price,
                inv.quantity    AS current_stock,
                COALESCE(recent.units_sold, 0) AS units_sold_30d,
                ROUND(COALESCE(recent.units_sold, 0)::numeric / 30, 2) AS daily_velocity
            FROM inventory.inventory inv
            JOIN inventory.products p   ON p.id = inv.product_id
            JOIN inventory.categories c ON c.id = p.category_id
            LEFT JOIN (
                SELECT soi.product_id, SUM(soi.quantity) AS units_sold
                FROM sales.sales_order_items soi
                JOIN sales.sales_orders so ON so.id = soi.order_id
                WHERE so.store_id = :store_id
                  AND so.status = 'paid'
                  AND so.paid_at >= NOW() - INTERVAL '30 days'
                GROUP BY soi.product_id
            ) recent ON recent.product_id = p.id
            WHERE inv.store_id = :store_id
              AND c.name IN ({cat_filter})
              AND inv.quantity > 0
            ORDER BY daily_velocity DESC
        """), {"store_id": store_id})

        products = [dict(r._mapping) for r in result.fetchall()]
        for p in products:
            p["unit_price"] = float(p["unit_price"])
            p["daily_velocity"] = float(p.get("daily_velocity") or 0)

    return json.dumps({
        "current_season": season,
        "preferred_categories": preferred,
        "seasonal_products": products,
        "recommendation": f"Focus merchandising on {', '.join(preferred)} products this {season}"
    })


# ─────────────────────────────────────────────────────────────────────────────
# Tool 5 — Smart restock quantity calculator
# ─────────────────────────────────────────────────────────────────────────────
@tool
async def compute_restock_quantities(store_id: str) -> str:
    """
    For every product below its reorder point, calculate the optimal quantity to order.
    Uses sales velocity from the last 30 days + a 14-day supply buffer (lead time assumption).
    Returns a prioritized purchase order recommendation the manager can act on immediately.

    Args:
        store_id: UUID of the store
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT
                p.id            AS product_id,
                p.name,
                p.sku,
                p.unit_price,
                p.reorder_point,
                inv.quantity    AS current_stock,
                COALESCE(vel.daily_sold, 0.1) AS daily_velocity
            FROM inventory.inventory inv
            JOIN inventory.products p ON p.id = inv.product_id
            LEFT JOIN (
                SELECT soi.product_id,
                       SUM(soi.quantity)::float / 30 AS daily_sold
                FROM sales.sales_order_items soi
                JOIN sales.sales_orders so ON so.id = soi.order_id
                WHERE so.store_id = :store_id
                  AND so.status = 'paid'
                  AND so.paid_at >= NOW() - INTERVAL '30 days'
                GROUP BY soi.product_id
            ) vel ON vel.product_id = p.id
            WHERE inv.store_id = :store_id
              AND inv.quantity <= p.reorder_point
            ORDER BY inv.quantity ASC
        """), {"store_id": store_id})

        items = []
        for row in result.fetchall():
            daily_vel = float(row.daily_velocity) or 0.1
            # Order enough for 30 days of supply + reorder point as safety buffer
            recommended_qty = max(
                int(daily_vel * 30 + row.reorder_point - row.current_stock),
                int(row.reorder_point * 2)
            )
            urgency = "URGENT" if row.current_stock == 0 else (
                "HIGH" if row.current_stock <= row.reorder_point * 0.5 else "MEDIUM"
            )
            items.append({
                "product_id": str(row.product_id),
                "name": row.name,
                "sku": row.sku,
                "current_stock": row.current_stock,
                "reorder_point": row.reorder_point,
                "daily_velocity": round(daily_vel, 2),
                "days_until_stockout": round(row.current_stock / daily_vel, 1),
                "recommended_order_qty": recommended_qty,
                "estimated_cost": round(float(row.unit_price) * recommended_qty, 2),
                "urgency": urgency,
            })

        total_cost = sum(i["estimated_cost"] for i in items)
        return json.dumps({
            "store_id": store_id,
            "items_needing_restock": len(items),
            "total_estimated_cost": round(total_cost, 2),
            "restock_plan": items
        })


# ─────────────────────────────────────────────────────────────────────────────
# Tool 6 — Revenue & performance summary
# ─────────────────────────────────────────────────────────────────────────────
@tool
async def get_store_performance_summary(store_id: str, days: int = 7) -> str:
    """
    Get a comprehensive performance summary for a store including:
    - Total revenue and order count for the period
    - Daily revenue breakdown
    - Average order value
    - Top-selling products

    Use this to answer questions about store performance, revenue trends,
    or when the manager wants a business health overview.

    Args:
        store_id: UUID of the store
        days: Number of past days to summarize (default: 7)
    """
    async with AsyncSessionLocal() as db:
        # Overall summary
        summary_result = await db.execute(text("""
            SELECT
                COUNT(*)                    AS order_count,
                COALESCE(SUM(total), 0)     AS total_revenue,
                COALESCE(AVG(total), 0)     AS avg_order_value,
                COALESCE(SUM(tax_amount), 0) AS total_tax
            FROM sales.sales_orders
            WHERE store_id = :store_id
              AND status = 'paid'
              AND paid_at >= NOW() - make_interval(days => :days)
        """), {"store_id": store_id, "days": days})

        sm = summary_result.fetchone()

        # Daily breakdown
        daily_result = await db.execute(text("""
            SELECT
                DATE(paid_at) AS day,
                COUNT(*)      AS orders,
                SUM(total)    AS revenue
            FROM sales.sales_orders
            WHERE store_id = :store_id
              AND status = 'paid'
              AND paid_at >= NOW() - make_interval(days => :days)
            GROUP BY DATE(paid_at)
            ORDER BY day DESC
        """), {"store_id": store_id, "days": days})

        daily = [{"day": str(r.day), "orders": r.orders, "revenue": float(r.revenue)} for r in daily_result.fetchall()]

        # Top products
        top_result = await db.execute(text("""
            SELECT soi.product_name, SUM(soi.quantity) AS units_sold, SUM(soi.line_total) AS revenue
            FROM sales.sales_order_items soi
            JOIN sales.sales_orders so ON so.id = soi.order_id
            WHERE so.store_id = :store_id
              AND so.status = 'paid'
              AND so.paid_at >= NOW() - make_interval(days => :days)
            GROUP BY soi.product_name
            ORDER BY units_sold DESC
            LIMIT 5
        """), {"store_id": store_id, "days": days})

        top = [{"product": r.product_name, "units_sold": r.units_sold, "revenue": float(r.revenue)} for r in top_result.fetchall()]

        return json.dumps({
            "period_days": days,
            "summary": {
                "total_orders": int(sm.order_count),
                "total_revenue": round(float(sm.total_revenue), 2),
                "avg_order_value": round(float(sm.avg_order_value), 2),
                "total_tax_collected": round(float(sm.total_tax), 2),
            },
            "daily_breakdown": daily,
            "top_products": top,
        })


# ─────────────────────────────────────────────────────────────────────────────
# All tools exported for agent binding
# ─────────────────────────────────────────────────────────────────────────────
ALL_TOOLS = [
    check_inventory_levels,
    analyze_sales_velocity,
    detect_transaction_anomalies,
    get_seasonal_demand_forecast,
    compute_restock_quantities,
    get_store_performance_summary,
]
