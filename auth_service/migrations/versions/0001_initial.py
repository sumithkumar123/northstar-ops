"""Initial auth schema

Revision ID: 0001
Revises:
Create Date: 2026-04-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SCHEMA IF NOT EXISTS auth")

    op.create_table(
        "regions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("country_code", sa.String(2), nullable=False),
        schema="auth",
    )

    op.create_table(
        "stores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("region_id", UUID(as_uuid=True), sa.ForeignKey("auth.regions.id"), nullable=False),
        sa.Column("city", sa.String(100)),
        sa.Column("country_code", sa.String(2), nullable=False),
        schema="auth",
    )

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),   # enforced by Pydantic UserRole enum
        sa.Column("store_id", UUID(as_uuid=True), sa.ForeignKey("auth.stores.id"), nullable=True),
        sa.Column("region_id", UUID(as_uuid=True), sa.ForeignKey("auth.regions.id"), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="auth",
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("auth.users.id"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("revoked", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="auth",
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], schema="auth")


def downgrade():
    op.drop_table("refresh_tokens", schema="auth")
    op.drop_table("users", schema="auth")
    op.drop_table("stores", schema="auth")
    op.drop_table("regions", schema="auth")
