import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from middleware import JWTValidationMiddleware
from proxy import router

app = FastAPI(title="NorthStar API Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(JWTValidationMiddleware, public_key_path=os.environ.get("JWT_PUBLIC_KEY_PATH", ""))

app.include_router(router)
