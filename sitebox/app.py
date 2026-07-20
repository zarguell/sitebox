"""Sitebox application wiring.

Assembles FastAPI app from auth, rest_api, and mcp_api modules.
Adds middleware for MCP auth (X-API-Key header) and browser auth (session cookie).
Mounts MCP ASGI app at /mcp and StaticFiles at / to serve uploaded pages.
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from sitebox.auth import router as login_router, check_browser_auth
from sitebox.rest_api import router as api_router
from sitebox.mcp_api import mcp, mcp_app
from sitebox.config import get_api_key, AUTH_PREFIXES, DATA_DIR


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    async with mcp.session_manager.run():
        yield


app = FastAPI(lifespan=_lifespan)
app.include_router(login_router)
app.include_router(api_router)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # API, MCP, and login paths bypass browser-auth check
    if path == "/login" or path.startswith("/api/") or path.startswith("/mcp"):
        # MCP requires API key on every request
        if path.startswith("/mcp"):
            key = request.headers.get("x-api-key") or (
                request.headers.get("authorization", "").removeprefix("Bearer ").strip()
                if "authorization" in request.headers
                else ""
            )
            if key != get_api_key():
                return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        return await call_next(request)

    # Browser auth: session cookie check for protected paths
    raw = request.headers.get("cookie", "")
    cookies = {}
    if raw:
        for pair in raw.split("; "):
            if "=" in pair:
                k, v = pair.split("=", 1)
                cookies[k] = v
    if not check_browser_auth(path, cookies):
        return RedirectResponse(url=f"/login?next={path}", status_code=302)

    return await call_next(request)


# Order matters: /mcp mount before / mount so /mcp doesn't fall through to StaticFiles
app.mount("/mcp", mcp_app)

DATA_DIR.mkdir(exist_ok=True)
# ponytail: html=True so /app1 resolves to /app1/index.html if it exists
app.mount("/", StaticFiles(directory=str(DATA_DIR), html=True), name="static")
