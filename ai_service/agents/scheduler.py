"""
Autonomous Agent Scheduler
==========================
Uses APScheduler (AsyncIOScheduler) to run background agent loops.

Important optimization:
- Run cheap SQL/rule-based checks first
- Only call the LLM for stores that are already flagged as risky

This keeps the proactive agent behavior while reducing Gemini usage.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from langchain_core.messages import HumanMessage
from sqlalchemy import text

from database import AsyncSessionLocal

logger = logging.getLogger(__name__)

MONITORED_STORES = [
    "b1000000-0000-0000-0000-000000000001",  # NYC Flagship
    "b1000000-0000-0000-0000-000000000002",  # Boston Outlet
    "b1000000-0000-0000-0000-000000000003",  # London Central
]

SEVERITY_RANK = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "URGENT": 4,
}

_agent = None
scheduler = AsyncIOScheduler()


def set_agent(agent):
    global _agent
    _agent = agent


def _max_severity(*values: str) -> str:
    valid = [value for value in values if value in SEVERITY_RANK]
    if not valid:
        return "LOW"
    return max(valid, key=lambda value: SEVERITY_RANK[value])


async def _save_agent_event(
    agent_name: str,
    event_type: str,
    severity: str,
    store_id: str,
    summary: str,
    reasoning: str,
    payload: dict,
):
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            INSERT INTO ai_agent_events
                (id, agent_name, event_type, severity, store_id, summary, reasoning, payload, created_at)
            VALUES
                (:id, :agent_name, :event_type, :severity, :store_id, :summary, :reasoning, CAST(:payload AS JSON), :created_at)
        """), {
            "id": str(uuid.uuid4()),
            "agent_name": agent_name,
            "event_type": event_type,
            "severity": severity,
            "store_id": store_id,
            "summary": summary,
            "reasoning": reasoning,
            "payload": json.dumps(payload),
            "created_at": datetime.now(timezone.utc),
        })
        await db.commit()


async def _prefilter_restock_risk(store_id: str) -> dict:
    """
    Fast SQL check. Only escalate to the LLM if a store already shows
    stockout or near-stockout risk.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            WITH sales_velocity AS (
                SELECT
                    soi.product_id,
                    COALESCE(SUM(soi.quantity)::float / 30, 0) AS daily_velocity
                FROM sales.sales_order_items soi
                JOIN sales.sales_orders so ON so.id = soi.order_id
                WHERE so.store_id = :store_id
                  AND so.status = 'paid'
                  AND so.paid_at >= NOW() - INTERVAL '30 days'
                GROUP BY soi.product_id
            )
            SELECT
                p.id AS product_id,
                p.name,
                p.sku,
                inv.quantity AS current_stock,
                p.reorder_point,
                COALESCE(sv.daily_velocity, 0) AS daily_velocity,
                CASE
                    WHEN COALESCE(sv.daily_velocity, 0) <= 0 THEN 999
                    ELSE ROUND(inv.quantity / NULLIF(sv.daily_velocity, 0), 1)
                END AS days_remaining,
                CASE
                    WHEN inv.quantity = 0 THEN 'URGENT'
                    WHEN inv.quantity <= p.reorder_point THEN 'HIGH'
                    WHEN COALESCE(sv.daily_velocity, 0) > 0
                         AND inv.quantity / NULLIF(sv.daily_velocity, 0) <= 7 THEN 'MEDIUM'
                    ELSE 'LOW'
                END AS severity
            FROM inventory.inventory inv
            JOIN inventory.products p ON p.id = inv.product_id
            LEFT JOIN sales_velocity sv ON sv.product_id = p.id
            WHERE inv.store_id = :store_id
              AND (
                    inv.quantity <= p.reorder_point
                    OR (
                        COALESCE(sv.daily_velocity, 0) > 0
                        AND inv.quantity / NULLIF(sv.daily_velocity, 0) <= 7
                    )
                )
            ORDER BY
                CASE
                    WHEN inv.quantity = 0 THEN 1
                    WHEN inv.quantity <= p.reorder_point THEN 2
                    ELSE 3
                END,
                COALESCE(sv.daily_velocity, 0) DESC,
                inv.quantity ASC
            LIMIT 5
        """), {"store_id": store_id})

        products = []
        for row in result.fetchall():
            days_remaining = float(row.days_remaining)
            products.append({
                "product_id": str(row.product_id),
                "name": row.name,
                "sku": row.sku,
                "current_stock": int(row.current_stock),
                "reorder_point": int(row.reorder_point),
                "daily_velocity": round(float(row.daily_velocity or 0), 2),
                "days_remaining": 999 if days_remaining >= 999 else round(days_remaining, 1),
                "severity": row.severity,
            })

    return {
        "flagged_products": len(products),
        "top_products": products,
        "max_severity": _max_severity(*(item["severity"] for item in products)),
    }


async def _prefilter_transaction_risk(store_id: str) -> dict:
    """
    Fast anomaly pre-check. Only escalate to the LLM if the database already
    sees recent statistical outliers.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            WITH stats AS (
                SELECT
                    AVG(total) AS mean_val,
                    STDDEV(total) AS std_val,
                    COUNT(*) AS order_count
                FROM sales.sales_orders
                WHERE store_id = :store_id
                  AND status = 'paid'
                  AND paid_at >= NOW() - INTERVAL '90 days'
            ),
            recent_anomalies AS (
                SELECT
                    o.id,
                    o.total,
                    o.paid_at,
                    ABS(o.total - s.mean_val) / NULLIF(s.std_val, 0) AS z_score
                FROM sales.sales_orders o
                CROSS JOIN stats s
                WHERE o.store_id = :store_id
                  AND o.status = 'paid'
                  AND o.paid_at >= NOW() - INTERVAL '7 days'
                  AND s.order_count >= 5
                  AND s.std_val IS NOT NULL
            )
            SELECT id, total, paid_at, z_score
            FROM recent_anomalies
            WHERE z_score > 2.5
            ORDER BY z_score DESC
            LIMIT 5
        """), {"store_id": store_id})

        anomalies = []
        for row in result.fetchall():
            anomalies.append({
                "order_id": str(row.id),
                "total": round(float(row.total), 2),
                "paid_at": row.paid_at.isoformat() if row.paid_at else None,
                "z_score": round(float(row.z_score), 2),
            })

    max_z_score = max((item["z_score"] for item in anomalies), default=0)
    severity = "LOW"
    if max_z_score >= 4:
        severity = "HIGH"
    elif anomalies:
        severity = "MEDIUM"

    return {
        "flagged_orders": len(anomalies),
        "top_anomalies": anomalies,
        "max_z_score": max_z_score,
        "max_severity": severity,
    }


async def run_restock_sentinel():
    """
    Runs every 10 minutes.
    Step 1: SQL pre-check for risk.
    Step 2: Call the LLM only for flagged stores.
    """
    if _agent is None:
        return

    logger.info("[RestockSentinel] Starting hybrid inventory scan for %d stores", len(MONITORED_STORES))

    for store_id in MONITORED_STORES:
        try:
            prefilter = await _prefilter_restock_risk(store_id)
            if prefilter["flagged_products"] == 0:
                logger.info("[RestockSentinel] Store %s passed SQL pre-check, skipping LLM call", store_id)
                continue

            product_summary = "; ".join(
                f"{item['name']} ({item['current_stock']} left, {item['days_remaining']} days left, {item['severity']})"
                for item in prefilter["top_products"]
            )

            result = await _agent.ainvoke({
                "messages": [HumanMessage(content=(
                    f"You are running an autonomous inventory check for store {store_id}. "
                    f"A SQL pre-check already flagged {prefilter['flagged_products']} product(s): {product_summary}. "
                    "Validate the risk using the retail tools, focus on the flagged products first, "
                    "and only recommend transfers or replenishment for products that truly need action. "
                    "Summarize the final manager action in 2-3 sentences."
                ))]
            })

            messages = result.get("messages", [])
            answer = messages[-1].content if messages else ""

            severity = prefilter["max_severity"]
            answer_lower = answer.lower()
            if "urgent" in answer_lower or "stockout" in answer_lower or "0 units" in answer_lower:
                severity = _max_severity(severity, "URGENT")
            elif "high" in answer_lower or "critical" in answer_lower or "immediately" in answer_lower:
                severity = _max_severity(severity, "HIGH")
            elif "below" in answer_lower or "reorder" in answer_lower:
                severity = _max_severity(severity, "MEDIUM")

            if severity in ("URGENT", "HIGH", "MEDIUM"):
                await _save_agent_event(
                    agent_name="RestockSentinel",
                    event_type="RESTOCK_ALERT",
                    severity=severity,
                    store_id=store_id,
                    summary=answer[:300],
                    reasoning=(
                        f"Triggered only after SQL pre-check flagged {prefilter['flagged_products']} "
                        f"inventory risk(s). Agent then validated with inventory and velocity tools."
                    ),
                    payload={
                        "store_id": store_id,
                        "prefilter": prefilter,
                        "full_response": answer,
                        "tools_used": [
                            {"tool": "check_inventory_levels"},
                            {"tool": "analyze_sales_velocity"},
                            {"tool": "compute_restock_quantities"},
                        ],
                    },
                )
                logger.info("[RestockSentinel] %s alert saved for store %s", severity, store_id)

        except Exception as exc:
            logger.error("[RestockSentinel] Error for store %s: %s", store_id, exc)


async def run_guardian_sentinel():
    """
    Runs every 5 minutes.
    Step 1: SQL anomaly pre-check.
    Step 2: Call the LLM only if recent outliers were found.
    """
    if _agent is None:
        return

    logger.info("[GuardianSentinel] Starting hybrid anomaly scan")

    for store_id in MONITORED_STORES:
        try:
            prefilter = await _prefilter_transaction_risk(store_id)
            if prefilter["flagged_orders"] == 0:
                logger.info("[GuardianSentinel] Store %s passed SQL anomaly pre-check, skipping LLM call", store_id)
                continue

            anomaly_summary = "; ".join(
                f"order {item['order_id']} (${item['total']}, z={item['z_score']})"
                for item in prefilter["top_anomalies"]
            )

            result = await _agent.ainvoke({
                "messages": [HumanMessage(content=(
                    f"Run anomaly detection for store {store_id}. "
                    f"A SQL pre-check already flagged {prefilter['flagged_orders']} recent outlier order(s): {anomaly_summary}. "
                    "Validate whether these look operationally suspicious, explain the likely cause, "
                    "and give the manager a short recommended action."
                ))]
            })

            messages = result.get("messages", [])
            answer = messages[-1].content if messages else ""

            if any(word in answer.lower() for word in ["anomal", "suspicious", "flagged", "unusual", "fraud"]):
                await _save_agent_event(
                    agent_name="GuardianSentinel",
                    event_type="ANOMALY_FLAG",
                    severity=prefilter["max_severity"],
                    store_id=store_id,
                    summary=answer[:300],
                    reasoning=(
                        f"Triggered only after SQL pre-check flagged {prefilter['flagged_orders']} "
                        f"transaction outlier(s). Agent then validated with anomaly analysis."
                    ),
                    payload={
                        "store_id": store_id,
                        "prefilter": prefilter,
                        "full_response": answer,
                        "tools_used": [{"tool": "detect_transaction_anomalies"}],
                    },
                )
                logger.info("[GuardianSentinel] Anomaly event saved for store %s", store_id)

        except Exception as exc:
            logger.error("[GuardianSentinel] Error for store %s: %s", store_id, exc)


def start_scheduler(agent):
    set_agent(agent)

    if agent is None:
        logger.warning("Agent not configured - autonomous scheduling disabled")
        return

    scheduler.add_job(
        run_restock_sentinel,
        trigger="interval",
        minutes=10,
        id="restock_sentinel",
        name="Autonomous Restock Sentinel",
        replace_existing=True,
    )

    scheduler.add_job(
        run_guardian_sentinel,
        trigger="interval",
        minutes=5,
        id="guardian_sentinel",
        name="Transaction Guardian Sentinel",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Autonomous agent scheduler started: SQL pre-checks every 5-10 min, LLM only for flagged stores"
    )


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
