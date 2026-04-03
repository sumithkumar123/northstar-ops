"""
JWT validation middleware.
Validates RS256 token on every inbound request (except /auth/login, /health).
Injects X-User-* headers so downstream services can trust the identity without re-decoding.
"""
import os
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from jose import JWTError, jwt

PUBLIC_KEY_PATH = os.environ["JWT_PUBLIC_KEY_PATH"]
SKIP_PATHS = {"/auth/login", "/auth/refresh", "/health", "/docs", "/openapi.json", "/redoc"}


class JWTValidationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, public_key_path: str):
        super().__init__(app)
        import base64
        b64 = os.environ.get("JWT_PUBLIC_KEY_B64")
        self.public_key = base64.b64decode(b64).decode() if b64 else Path(public_key_path).read_text()

    async def dispatch(self, request: Request, call_next):
        if request.url.path in SKIP_PATHS or request.url.path.startswith("/health"):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse({"detail": "Missing bearer token"}, status_code=401)

        token = auth.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, self.public_key, algorithms=["RS256"])
        except JWTError as e:
            return JSONResponse({"detail": f"Invalid token: {e}"}, status_code=401)

        # Inject verified claims as headers for downstream services
        headers = dict(request.headers)
        headers["x-user-id"] = payload.get("sub", "")
        headers["x-user-role"] = payload.get("role", "")
        headers["x-store-id"] = payload.get("store_id") or ""
        headers["x-region-id"] = payload.get("region_id") or ""

        from starlette.datastructures import MutableHeaders
        mutable = MutableHeaders(scope=request.scope)
        mutable["x-user-id"] = headers["x-user-id"]
        mutable["x-user-role"] = headers["x-user-role"]
        mutable["x-store-id"] = headers["x-store-id"]
        mutable["x-region-id"] = headers["x-region-id"]

        return await call_next(request)
