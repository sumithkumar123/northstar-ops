"""
Reverse proxy: forwards requests to the correct upstream service.
Route mapping:
  /auth/*        → auth_service:8001
  /inventory/*   → inventory_service:8002
  /sales/*       → sales_service:8003
"""
import os
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok", "service": "gateway"}

UPSTREAMS = {
    "/auth": os.environ.get("AUTH_SERVICE_URL", "http://auth_service:8001"),
    "/inventory": os.environ.get("INVENTORY_SERVICE_URL", "http://inventory_service:8002"),
    "/sales": os.environ.get("SALES_SERVICE_URL", "http://sales_service:8003"),
    "/ai": os.environ.get("AI_SERVICE_URL", "http://ai_service:8004"),
}

# Persistent client for connection pooling
_client = httpx.AsyncClient(timeout=30.0)


async def _proxy(request: Request, upstream_base: str) -> Response:
    path = request.url.path
    query = request.url.query
    url = f"{upstream_base}{path}"
    if query:
        url += f"?{query}"

    body = await request.body()
    # Forward all headers except Host (httpx sets its own)
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}

    upstream_resp = await _client.request(
        method=request.method,
        url=url,
        content=body,
        headers=headers,
    )

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=dict(upstream_resp.headers),
        media_type=upstream_resp.headers.get("content-type"),
    )


@router.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_auth(request: Request, path: str):
    return await _proxy(request, UPSTREAMS["/auth"])


@router.api_route("/inventory/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_inventory(request: Request, path: str):
    return await _proxy(request, UPSTREAMS["/inventory"])


@router.api_route("/sales/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_sales(request: Request, path: str):
    return await _proxy(request, UPSTREAMS["/sales"])


@router.api_route("/ai/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_ai(request: Request, path: str):
    return await _proxy(request, UPSTREAMS["/ai"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "gateway"}
