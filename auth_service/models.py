import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Region(Base):
    __tablename__ = "regions"
    __table_args__ = {"schema": "auth"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    country_code = Column(String(2), nullable=False)  # ISO 3166-1 alpha-2
    stores = relationship("Store", back_populates="region")


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = {"schema": "auth"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    region_id = Column(UUID(as_uuid=True), ForeignKey("auth.regions.id"), nullable=False)
    city = Column(String(100))
    country_code = Column(String(2), nullable=False)
    region = relationship("Region", back_populates="stores")
    users = relationship("User", back_populates="store")


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False)
    store_id = Column(UUID(as_uuid=True), ForeignKey("auth.stores.id"), nullable=True)
    region_id = Column(UUID(as_uuid=True), ForeignKey("auth.regions.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    store = relationship("Store", back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = {"schema": "auth"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False)
    token_hash = Column(String(255), nullable=False)   # bcrypt hash of raw token
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="refresh_tokens")
