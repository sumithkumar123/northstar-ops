import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = {"schema": "inventory"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"schema": "inventory"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku = Column(String(50), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category_id = Column(UUID(as_uuid=True), ForeignKey("inventory.categories.id"))
    unit_price = Column(Numeric(10, 2), nullable=False)
    reorder_point = Column(Integer, default=10)     # trigger replenishment below this
    created_at = Column(DateTime, default=datetime.utcnow)
    category = relationship("Category", back_populates="products")
    inventory_records = relationship("Inventory", back_populates="product")


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = {"schema": "inventory"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), nullable=False)   # FK to auth.stores (cross-schema reference kept loose)
    product_id = Column(UUID(as_uuid=True), ForeignKey("inventory.products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    product = relationship("Product", back_populates="inventory_records")
    transactions = relationship("InventoryTransaction", back_populates="inventory")


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    __table_args__ = {"schema": "inventory"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_id = Column(UUID(as_uuid=True), ForeignKey("inventory.inventory.id"), nullable=False)
    delta = Column(Integer, nullable=False)          # positive = restock, negative = sale/adjustment
    transaction_type = Column(String(20), nullable=False)
    reference_id = Column(String(100))               # order_id, transfer_id, etc.
    performed_by = Column(UUID(as_uuid=True))        # user_id
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    inventory = relationship("Inventory", back_populates="transactions")
