"""
Auth business logic: credential verification, JWT issuance, refresh token rotation.
"""
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, RefreshToken

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _load_private_key() -> str:
    b64 = os.environ.get("JWT_PRIVATE_KEY_B64")
    if b64:
        import base64
        return base64.b64decode(b64).decode()
    return Path(os.environ["JWT_PRIVATE_KEY_PATH"]).read_text()

PRIVATE_KEY = _load_private_key()
ACCESS_TOKEN_TTL = int(os.environ.get("ACCESS_TOKEN_TTL", 900))      # seconds
REFRESH_TOKEN_TTL = int(os.environ.get("REFRESH_TOKEN_TTL", 86400))  # seconds


def _issue_access_token(user: User) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "store_id": str(user.store_id) if user.store_id else None,
        "region_id": str(user.region_id) if user.region_id else None,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=ACCESS_TOKEN_TTL),
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")


async def authenticate(db: AsyncSession, username: str, password: str) -> dict:
    result = await db.execute(select(User).where(User.username == username, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user or not pwd_ctx.verify(password, user.hashed_password):
        return None

    access_token = _issue_access_token(user)

    raw_refresh = str(uuid.uuid4())
    refresh_hash = pwd_ctx.hash(raw_refresh)
    db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=datetime.utcnow() + timedelta(seconds=REFRESH_TOKEN_TTL),
    )
    db.add(db_refresh)
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "expires_in": ACCESS_TOKEN_TTL,
    }


async def rotate_refresh_token(db: AsyncSession, raw_refresh: str) -> dict | None:
    """
    Validate a refresh token, revoke it, and issue a new pair.
    Brute-force protected: we hash-compare rather than store raw tokens.
    """
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow(),
        )
    )
    # Must iterate to find matching hash (no index on hash by design)
    token_row = None
    for row in result.scalars():
        if pwd_ctx.verify(raw_refresh, row.token_hash):
            token_row = row
            break

    if not token_row:
        return None

    token_row.revoked = True
    await db.flush()

    user_result = await db.execute(select(User).where(User.id == token_row.user_id))
    user = user_result.scalar_one()

    access_token = _issue_access_token(user)
    new_raw = str(uuid.uuid4())
    new_row = RefreshToken(
        user_id=user.id,
        token_hash=pwd_ctx.hash(new_raw),
        expires_at=datetime.utcnow() + timedelta(seconds=REFRESH_TOKEN_TTL),
    )
    db.add(new_row)
    await db.commit()
    return {"access_token": access_token, "refresh_token": new_raw, "expires_in": ACCESS_TOKEN_TTL}


def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)
