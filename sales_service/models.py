import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": "sales"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200))
    email = Column(String(255))
    phone = Column(String(30))
    loyalty_points = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    orders = relationship("SalesOrder", back_populates="customer")


class SalesOrder(Base):
    __tablename__ = "sales_orders"
    __table_args__ = {"schema": "sales"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offline_id = Column(String(100), unique=True, nullable=True)  # PWA offline idempotency key
    store_id = Column(UUID(as_uuid=True), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("sales.customers.id"), nullable=True)
    cashier_id = Column(UUID(as_uuid=True), nullable=False)   # user_id from JWT
    status = Column(String(20), nullable=False, default="draft")
    subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(12, 2), nullable=False, default=0)
    total = Column(Numeric(12, 2), nullable=False, default=0)
    country_code = Column(String(2), default="US")
    payment_method = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    customer = relationship("Customer", back_populates="orders")
    items = relationship("SalesOrderItem", back_populates="order", cascade="all, delete-orphan")


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"
    __table_args__ = {"schema": "sales"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("sales.sales_orders.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), nullable=False)
    sku = Column(String(50), nullable=False)
    product_name = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    line_total = Column(Numeric(12, 2), nullable=False)
    order = relationship("SalesOrder", back_populates="items")
