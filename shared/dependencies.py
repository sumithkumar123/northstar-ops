"""
Shared FastAPI dependencies for JWT validation and RBAC.
Each service imports get_current_user and require_role from here.
"""
import os
from pathlib import Path
from typing import List
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt

from shared.schemas import TokenPayload, UserRole


def _load_public_key(path: str) -> str:
    import base64
    b64 = os.environ.get("JWT_PUBLIC_KEY_B64")
    if b64:
        return base64.b64decode(b64).decode()
    return Path(path).read_text()


def get_current_user(request: Request) -> TokenPayload:
    """
    Decodes RS256 JWT from Authorization header.
    The gateway already validates the token, but services re-verify
    for defence-in-depth (service mesh bypass, direct-to-service calls).
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = auth_header.split(" ", 1)[1]

    try:
        public_key = _load_public_key(getattr(request.app.state, "public_key_path", ""))
        payload = jwt.decode(token, public_key, algorithms=["RS256"])
        return TokenPayload(**payload)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}")


def require_role(allowed_roles: List[UserRole]):
    """
    Factory that returns a dependency enforcing role membership.
    Usage: Depends(require_role([UserRole.store_manager, UserRole.regional_admin]))
    """
    def _check(current_user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not permitted for this action",
            )
        return current_user
    return _check


def require_store_access(store_id_param: str = "store_id"):
    """
    Ensures a sales_associate can only access their own store.
    Regional admins and store managers can access any store.
    """
    def _check(request: Request, current_user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if current_user.role == UserRole.regional_admin:
            return current_user
        path_store_id = request.path_params.get(store_id_param)
        if path_store_id and str(current_user.store_id) != str(path_store_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own store's data",
            )
        return current_user
    return _check
