"""
Website proxy API — serves teg.ie through our backend for iframe embedding.

Supports GET and POST (required for ASP.NET form postbacks).
"""

from fastapi import APIRouter, Depends, Request

from app.config import Settings, get_settings
from app.services.proxy_service import fetch_proxied

router = APIRouter(prefix="/api/proxy", tags=["proxy"])


async def _handle_proxy(request: Request, path: str, settings: Settings):
    body = await request.body() if request.method == "POST" else None
    return await fetch_proxied(
        settings,
        path=path,
        query=str(request.url.query),
        method=request.method,
        body=body,
        content_type=request.headers.get("content-type"),
        cookie=request.headers.get("cookie"),
    )


@router.api_route("", methods=["GET", "POST"])
@router.api_route("/", methods=["GET", "POST"])
@router.api_route("/{path:path}", methods=["GET", "POST"])
async def proxy_website(
    request: Request,
    path: str = "",
    settings: Settings = Depends(get_settings),
):
    """Proxy GET/POST requests to the configured target website."""
    return await _handle_proxy(request, path, settings)
