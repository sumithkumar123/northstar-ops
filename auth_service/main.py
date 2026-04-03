import os
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
    return open(os.environ["JWT_PUBLIC_KEY_PATH"]).read()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.public_key = _load_public_key()
    app.state.public_key_path = os.environ.get("JWT_PUBLIC_KEY_PATH", "")
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
