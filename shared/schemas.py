from enum import Enum
from uuid import UUID
from pydantic import BaseModel


class UserRole(str, Enum):
    regional_admin = "regional_admin"
    store_manager = "store_manager"
    sales_associate = "sales_associate"


class OrderStatus(str, Enum):
    draft = "draft"
    confirmed = "confirmed"
    paid = "paid"
    voided = "voided"


class TokenPayload(BaseModel):
    sub: str           # user UUID
    role: UserRole
    store_id: str | None = None
    region_id: str | None = None
    jti: str           # unique token ID for blacklist


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
