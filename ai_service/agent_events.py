"""
Agent Events — SQLAlchemy model for the AI agent audit trail.

Each row represents ONE action taken by an agent (restock alert raised,
anomaly flagged, insight generated).  The `payload` column stores the full
agent reasoning so managers can audit every AI decision.
"""
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import DeclarativeBase

from database import engine


class Base(DeclarativeBase):
    pass


class AgentEvent(Base):
    __tablename__ = "ai_agent_events"
    __table_args__ = {"schema": "public"}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_name = Column(String(100), nullable=False)          # "RestockSentinel", "GuardianAgent", "InsightAgent"
    event_type = Column(String(50), nullable=False)           # "RESTOCK_ALERT", "ANOMALY_FLAG", "INSIGHT"
    severity = Column(String(20), nullable=True)              # "URGENT", "HIGH", "MEDIUM", "LOW"
    store_id = Column(String(36), nullable=True)
    summary = Column(Text, nullable=False)                    # One-line human-readable outcome
    reasoning = Column(Text, nullable=True)                   # Full agent reasoning chain (tool calls + thoughts)
    payload = Column(JSON, nullable=True)                     # Structured data (products, order IDs, etc.)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


async def create_event_table():
    """Create the ai_agent_events table if it doesn't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
