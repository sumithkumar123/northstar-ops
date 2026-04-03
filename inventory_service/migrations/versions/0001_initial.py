"""Initial inventory schema

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
    op.execute("CREATE SCHEMA IF NOT EXISTS inventory")

    op.create_table(
        "categories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        schema="inventory",
    )

    op.create_table(
        "products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("sku", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("inventory.categories.id")),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("reorder_point", sa.Integer, server_default="10"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="inventory",
    )

    op.create_table(
        "inventory",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("store_id", UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("inventory.products.id"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_updated", sa.DateTime, server_default=sa.text("now()")),
        schema="inventory",
    )
    op.create_index("ix_inventory_store_product", "inventory",
                    ["store_id", "product_id"], unique=True, schema="inventory")

    op.create_table(
        "inventory_transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("inventory_id", UUID(as_uuid=True), sa.ForeignKey("inventory.inventory.id"), nullable=False),
        sa.Column("delta", sa.Integer, nullable=False),
        sa.Column("transaction_type", sa.String(20), nullable=False),  # enforced by app layer
        sa.Column("reference_id", sa.String(100)),
        sa.Column("performed_by", UUID(as_uuid=True)),
        sa.Column("note", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="inventory",
    )
    op.create_index("ix_inv_txn_inventory_id", "inventory_transactions",
                    ["inventory_id"], schema="inventory")


def downgrade():
    op.drop_table("inventory_transactions", schema="inventory")
    op.drop_table("inventory", schema="inventory")
    op.drop_table("products", schema="inventory")
    op.drop_table("categories", schema="inventory")
