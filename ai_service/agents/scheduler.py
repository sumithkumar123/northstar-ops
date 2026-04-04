"""
Autonomous Agent Scheduler
===========================
Uses APScheduler (AsyncIOScheduler) to run agent loops in the background
without any human trigger.  This is what makes the system PROACTIVE — agents
continuously monitor the stores and surface insights automatically.

Two autonomous loops:
  1. Restock Sentinel  — runs every 10 minutes across all stores
  2. Guardian Sentinel — runs every 5 minutes checking recent transactions

When an agent finds something actionable, it writes to `ai_agent_events`
so the manager sees it on their next dashboard load.
"""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from langchain_core.messages import HumanMessage
from sqlalchemy import text

from database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# Stores to monitor proactively (matches seeded data)
# In production, this would be fetched from the auth DB
MONITORED_STORES = [
    "b1000000-0000-0000-0000-000000000001",  # NYC Flagship
    "b1000000-0000-0000-0000-000000000002",  # Boston Outlet
    "b1000000-0000-0000-0000-000000000003",  # London Central
]

_agent = None  # Set by main.py after agent is created
scheduler = AsyncIOScheduler()


def set_agent(agent):
    """Called from main.py to inject the agent instance into the scheduler."""
    global _agent
    _agent = agent


async def _save_agent_event(
    agent_name: str,
    event_type: str,
    severity: str,
    store_id: str,
    summary: str,
    reasoning: str,
    payload: dict,
):
    """Persist an agent decision to the audit log table."""
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


async def run_restock_sentinel():
    """
    RESTOCK SENTINEL — runs every 10 minutes.

    Asks the agent: "Analyze inventory and identify any products needing urgent restocking."
    The agent calls check_inventory_levels + analyze_sales_velocity + compute_restock_quantities,
    reasons over the results, and produces a recommendation.
    Any URGENT or HIGH priority findings are saved as agent events.
    """
    if _agent is None:
        return  # Agent not initialized (no API key)

    logger.info("[RestockSentinel] Starting scheduled inventory scan for %d stores", len(MONITORED_STORES))

    for store_id in MONITORED_STORES:
        try:
            result = await _agent.ainvoke({
                "messages": [HumanMessage(content=(
                    f"You are running an autonomous inventory check for store {store_id}. "
                    "Check current inventory levels and sales velocity. "
                    "Identify any products at risk of stockout in the next 7 days. "
                    "For each at-risk product, compute the recommended order quantity. "
                    "Summarize your findings in 2-3 sentences."
                ))]
            })

            messages = result.get("messages", [])
            answer = messages[-1].content if messages else ""

            # Determine severity from answer content
            severity = "LOW"
            if "urgent" in answer.lower() or "stockout" in answer.lower() or "0 units" in answer.lower():
                severity = "URGENT"
            elif "high" in answer.lower() or "critical" in answer.lower() or "immediately" in answer.lower():
                severity = "HIGH"
            elif "below" in answer.lower() or "reorder" in answer.lower():
                severity = "MEDIUM"

            if severity in ("URGENT", "HIGH", "MEDIUM"):
                await _save_agent_event(
                    agent_name="RestockSentinel",
                    event_type="RESTOCK_ALERT",
                    severity=severity,
                    store_id=store_id,
                    summary=answer[:300],
                    reasoning=f"Agent called: check_inventory_levels + analyze_sales_velocity + compute_restock_quantities",
                    payload={
                        "store_id": store_id,
                        "full_response": answer,
                        "tools_used": [
                            {"tool": "check_inventory_levels"},
                            {"tool": "analyze_sales_velocity"},
                            {"tool": "compute_restock_quantities"},
                        ],
                    },
                )
                logger.info("[RestockSentinel] %s alert saved for store %s", severity, store_id)

        except Exception as e:
            logger.error("[RestockSentinel] Error for store %s: %s", store_id, e)


async def run_guardian_sentinel():
    """
    GUARDIAN SENTINEL — runs every 5 minutes.

    Asks the agent to scan recent transactions for anomalies.
    Uses detect_transaction_anomalies tool and flags suspicious orders.
    """
    if _agent is None:
        return

    logger.info("[GuardianSentinel] Starting anomaly detection scan")

    for store_id in MONITORED_STORES:
        try:
            result = await _agent.ainvoke({
                "messages": [HumanMessage(content=(
                    f"Run anomaly detection for store {store_id}. "
                    "Check recent transactions for statistical outliers. "
                    "Focus on the last 7 days. "
                    "If you find anomalies, explain the likely cause and recommended action. "
                    "If no anomalies, simply confirm the store's transactions look normal."
                ))]
            })

            messages = result.get("messages", [])
            answer = messages[-1].content if messages else ""

            # Only save events if anomalies were found
            if any(word in answer.lower() for word in ["anomal", "suspicious", "flagged", "unusual", "fraud"]):
                await _save_agent_event(
                    agent_name="GuardianSentinel",
                    event_type="ANOMALY_FLAG",
                    severity="HIGH",
                    store_id=store_id,
                    summary=answer[:300],
                    reasoning="Agent called: detect_transaction_anomalies",
                    payload={
                        "store_id": store_id,
                        "full_response": answer,
                        "tools_used": [{"tool": "detect_transaction_anomalies"}],
                    },
                )
                logger.info("[GuardianSentinel] Anomaly event saved for store %s", store_id)

        except Exception as e:
            logger.error("[GuardianSentinel] Error for store %s: %s", store_id, e)


def start_scheduler(agent):
    """Start the autonomous agent scheduler. Called from FastAPI lifespan."""
    set_agent(agent)

    if agent is None:
        logger.warning("Agent not configured — autonomous scheduling disabled")
        return

    # Restock Sentinel: every 10 minutes
    scheduler.add_job(
        run_restock_sentinel,
        trigger="interval",
        minutes=10,
        id="restock_sentinel",
        name="Autonomous Restock Sentinel",
        replace_existing=True,
    )

    # Guardian Sentinel: every 5 minutes
    scheduler.add_job(
        run_guardian_sentinel,
        trigger="interval",
        minutes=5,
        id="guardian_sentinel",
        name="Transaction Guardian Sentinel",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Autonomous agent scheduler started: RestockSentinel(10min) + GuardianSentinel(5min)")


def stop_scheduler():
    """Stop the scheduler gracefully on app shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
