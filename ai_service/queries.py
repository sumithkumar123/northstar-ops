"""
AI query logic — read-only against existing schemas.
Uses raw SQL via sqlalchemy.text() to join across inventory + sales schemas.
No ML libraries — algorithms are implemented in pure Python for transparency.
"""
import math
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Season → preferred product categories (business rules, easily defensible)
SEASON_CATEGORIES = {
    "Winter": ["Apparel", "Equipment"],
    "Spring": ["Footwear", "Apparel"],
    "Summer": ["Footwear", "Equipment"],
    "Fall":   ["Apparel", "Equipment"],
}


def _current_season() -> str:
    month = datetime.utcnow().month
    if month in (12, 1, 2):  return "Winter"
    if month in (3, 4, 5):   return "Spring"
    if month in (6, 7, 8):   return "Summer"
    return "Fall"


async def get_recommendations(db: AsyncSession, store_id: str) -> dict:
    """
    Recommend products to push based on:
    1. Current season → preferred categories
    2. Current store stock > 0 (can't sell what you don't have)
    3. Lowest sales velocity in the last 30 days (push slow movers)
    Falls back to highest unit_price items if no sales history exists.
    """
    season = _current_season()
    preferred_cats = SEASON_CATEGORIES[season]
    cat_filter = ", ".join(f"'{c}'" for c in preferred_cats)

    # Products in preferred categories with stock, ordered by least-sold recently
    result = await db.execute(text(f"""
        SELECT
            p.id            AS product_id,
            p.sku,
            p.name,
            c.name          AS category,
            p.unit_price,
            inv.quantity    AS stock,
            COALESCE(recent.units_sold, 0) AS recent_units_sold
        FROM inventory.inventory inv
        JOIN inventory.products p  ON p.id = inv.product_id
        JOIN inventory.categories c ON c.id = p.category_id
        LEFT JOIN (
            SELECT soi.product_id, SUM(soi.quantity) AS units_sold
            FROM sales.sales_order_items soi
            JOIN sales.sales_orders so ON so.id = soi.order_id
            WHERE so.store_id = :store_id
              AND so.status   = 'paid'
              AND so.paid_at >= NOW() - INTERVAL '30 days'
            GROUP BY soi.product_id
        ) recent ON recent.product_id = p.id
        WHERE inv.store_id = :store_id
          AND inv.quantity > 0
          AND c.name IN ({cat_filter})
        ORDER BY recent_units_sold ASC, p.unit_price DESC
        LIMIT 5
    """), {"store_id": store_id})

    rows = result.fetchall()
    if not rows:
        # Fallback: top-priced in-stock items regardless of category
        fallback = await db.execute(text("""
            SELECT p.id AS product_id, p.sku, p.name,
                   c.name AS category, p.unit_price, inv.quantity AS stock
            FROM inventory.inventory inv
            JOIN inventory.products p  ON p.id = inv.product_id
            JOIN inventory.categories c ON c.id = p.category_id
            WHERE inv.store_id = :store_id AND inv.quantity > 0
            ORDER BY p.unit_price DESC LIMIT 5
        """), {"store_id": store_id})
        rows = fallback.fetchall()
        reason = "High-value items currently in stock"
    else:
        reason = f"Low sales velocity — {season} season push"

    return {
        "season": season,
        "preferred_categories": preferred_cats,
        "recommendations": [
            {
                "product_id": str(r.product_id),
                "sku": r.sku,
                "name": r.name,
                "category": r.category,
                "unit_price": float(r.unit_price),
                "reason": reason,
            }
            for r in rows
        ],
    }


async def get_anomalies(db: AsyncSession, store_id: str) -> dict:
    """
    Z-score based anomaly detection on order totals.
    Flags orders where |total - mean| > 2.5 * std_dev.
    Requires at least 5 orders to produce meaningful results.
    """
    result = await db.execute(text("""
        SELECT id, total, cashier_id, paid_at
        FROM sales.sales_orders
        WHERE store_id = :store_id
          AND status   = 'paid'
          AND paid_at >= NOW() - INTERVAL '90 days'
        ORDER BY paid_at DESC
    """), {"store_id": store_id})

    orders = result.fetchall()

    if len(orders) < 5:
        return {
            "message": "Insufficient data for anomaly detection (need at least 5 orders)",
            "order_count": len(orders),
            "anomalies": [],
        }

    totals = [float(o.total) for o in orders]
    mean = sum(totals) / len(totals)
    variance = sum((x - mean) ** 2 for x in totals) / len(totals)
    std = math.sqrt(variance) if variance > 0 else 0.001  # avoid /0

    anomalies = []
    for o, total_val in zip(orders, totals):
        z = abs(total_val - mean) / std
        if z > 2.5:
            anomalies.append({
                "order_id": str(o.id),
                "total": total_val,
                "cashier_id": str(o.cashier_id),
                "paid_at": o.paid_at.isoformat(),
                "z_score": round(z, 2),
                "reason": "Unusually high amount" if total_val > mean else "Unusually low amount",
            })

    return {
        "order_count_analyzed": len(orders),
        "mean_order_value": round(mean, 2),
        "std_dev": round(std, 2),
        "anomaly_threshold": "z-score > 2.5",
        "anomalies": anomalies,
    }


# Natural language → pre-written safe read-only SQL
NL_QUERIES = {
    "revenue":   ("Daily revenue for last 7 days",
                  "SELECT DATE(paid_at) AS day, SUM(total) AS revenue FROM sales.sales_orders "
                  "WHERE status='paid' AND paid_at >= NOW()-INTERVAL '7 days' "
                  "GROUP BY day ORDER BY day"),
    "stock":     ("Current stock levels",
                  "SELECT p.sku, p.name, inv.quantity, p.reorder_point "
                  "FROM inventory.inventory inv JOIN inventory.products p ON p.id=inv.product_id "
                  "ORDER BY inv.quantity ASC LIMIT 20"),
    "inventory": ("Current stock levels",
                  "SELECT p.sku, p.name, inv.quantity, p.reorder_point "
                  "FROM inventory.inventory inv JOIN inventory.products p ON p.id=inv.product_id "
                  "ORDER BY inv.quantity ASC LIMIT 20"),
    "top":       ("Top-selling products",
                  "SELECT soi.sku, soi.product_name, SUM(soi.quantity) AS units_sold "
                  "FROM sales.sales_order_items soi JOIN sales.sales_orders so ON so.id=soi.order_id "
                  "WHERE so.status='paid' GROUP BY soi.sku, soi.product_name "
                  "ORDER BY units_sold DESC LIMIT 10"),
    "best":      ("Best-selling products",
                  "SELECT soi.sku, soi.product_name, SUM(soi.quantity) AS units_sold "
                  "FROM sales.sales_order_items soi JOIN sales.sales_orders so ON so.id=soi.order_id "
                  "WHERE so.status='paid' GROUP BY soi.sku, soi.product_name "
                  "ORDER BY units_sold DESC LIMIT 10"),
    "low":       ("Low stock alerts",
                  "SELECT p.sku, p.name, inv.quantity, p.reorder_point "
                  "FROM inventory.inventory inv JOIN inventory.products p ON p.id=inv.product_id "
                  "WHERE inv.quantity <= p.reorder_point ORDER BY inv.quantity ASC"),
    "order":     ("Recent orders",
                  "SELECT id, total, status, paid_at FROM sales.sales_orders "
                  "WHERE paid_at >= NOW()-INTERVAL '24 hours' ORDER BY paid_at DESC LIMIT 20"),
}


async def run_nl_query(db: AsyncSession, question: str, store_id: str | None) -> dict:
    question_lower = question.lower()
    matched_label, matched_sql = None, None

    for keyword, (label, sql) in NL_QUERIES.items():
        if keyword in question_lower:
            matched_label, matched_sql = label, sql
            break

    if not matched_sql:
        return {
            "error": "Could not understand the query",
            "hint": "Try asking about: revenue, stock/inventory, top/best products, low stock, or orders",
            "results": [],
        }

    # Optionally filter by store_id if the SQL supports it and store_id is provided
    result = await db.execute(text(matched_sql))
    rows = result.fetchall()
    columns = list(result.keys()) if rows else []

    return {
        "question": question,
        "interpreted_as": matched_label,
        "row_count": len(rows),
        "results": [dict(zip(columns, row)) for row in rows],
    }
