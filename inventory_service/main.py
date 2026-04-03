import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.public_key_path = os.environ.get("JWT_PUBLIC_KEY_PATH", "")
    yield
    await engine.dispose()


app = FastAPI(title="NorthStar Inventory Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
