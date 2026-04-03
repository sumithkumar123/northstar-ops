import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from models import Base
from routes import router


def _load_public_key() -> str:
    b64 = os.environ.get("JWT_PUBLIC_KEY_B64")
    if b64:
        import base64
        return base64.b64decode(b64).decode()
    path = os.environ.get("JWT_PUBLIC_KEY_PATH")
    if path:
        return open(path).read()
    raise RuntimeError("Neither JWT_PUBLIC_KEY_B64 nor JWT_PUBLIC_KEY_PATH is set")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[startup] PORT={os.environ.get('PORT', 'NOT SET')}", flush=True)
    print(f"[startup] DB_SCHEMA={os.environ.get('DB_SCHEMA', 'NOT SET')}", flush=True)
    print(f"[startup] JWT_PUBLIC_KEY_B64 set={bool(os.environ.get('JWT_PUBLIC_KEY_B64'))}", flush=True)
    print(f"[startup] JWT_PRIVATE_KEY_B64 set={bool(os.environ.get('JWT_PRIVATE_KEY_B64'))}", flush=True)
    try:
        app.state.public_key = _load_public_key()
        print("[startup] public key loaded OK", flush=True)
    except Exception as e:
        print(f"[startup] FATAL: failed to load public key: {e}", file=sys.stderr, flush=True)
        raise
    app.state.public_key_path = os.environ.get("JWT_PUBLIC_KEY_PATH", "")
    print("[startup] ready", flush=True)
    yield
    await engine.dispose()


app = FastAPI(title="NorthStar Auth Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
