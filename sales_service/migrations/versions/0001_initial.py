"""Initial sales schema

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
    op.execute("CREATE SCHEMA IF NOT EXISTS sales")

    op.create_table(
        "customers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200)),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(30)),
        sa.Column("loyalty_points", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        schema="sales",
    )

    op.create_table(
        "sales_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("offline_id", sa.String(100), unique=True, nullable=True),
        sa.Column("store_id", UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("sales.customers.id"), nullable=True),
        sa.Column("cashier_id", UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("country_code", sa.String(2), server_default="US"),
        sa.Column("payment_method", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("paid_at", sa.DateTime, nullable=True),
        schema="sales",
    )
    op.create_index("ix_sales_orders_store_id", "sales_orders", ["store_id"], schema="sales")
    op.create_index("ix_sales_orders_paid_at", "sales_orders", ["paid_at"], schema="sales")

    op.create_table(
        "sales_order_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id", UUID(as_uuid=True), sa.ForeignKey("sales.sales_orders.id"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(50), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        schema="sales",
    )
    op.create_index("ix_order_items_order_id", "sales_order_items", ["order_id"], schema="sales")


def downgrade():
    op.drop_table("sales_order_items", schema="sales")
    op.drop_table("sales_orders", schema="sales")
    op.drop_table("customers", schema="sales")
