"""HTTP-level integration tests for the MCP StreamableHTTP transport."""
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _set_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    import sitebox.config as cfg
    d = tmp_path / "data"
    monkeypatch.setattr(cfg, "DATA_DIR", d)
    d.mkdir(exist_ok=True)
    return d


@pytest.fixture
async def mcp_client(data_dir):
    """Create an httpx AsyncClient with the MCP lifespan running.

    ponytail: module-level session_manager is single-use, so we build a fresh
    app per test to avoid "run() can only be called once".
    """
    from sitebox.mcp_api import mcp
    from sitebox.config import DATA_DIR

    mcp_app = mcp.streamable_http_app(streamable_http_path="/mcp")
    _lifespan_ctx = mcp_app.router.lifespan_context

    # Build a minimal FastAPI with the MCP routes
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from collections.abc import AsyncIterator
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app):
        async with _lifespan_ctx(app):
            yield

    mini_app = FastAPI(lifespan=lifespan)

    @mini_app.middleware("http")
    async def auth(request: Request, call_next):
        if request.url.path.startswith("/mcp"):
            key = request.headers.get("x-api-key", "")
            if key != "test-key":
                return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        return await call_next(request)

    for route in mcp_app.routes:
        mini_app.routes.append(route)

    transport = ASGITransport(app=mini_app)
    async with _lifespan_ctx(mini_app):
        async with AsyncClient(transport=transport, base_url="http://localhost") as c:
            yield c


@pytest.mark.anyio
async def test_mcp_get_returns_sse(mcp_client):
    """GET /mcp should not return 405."""
    r = await mcp_client.get("/mcp", headers={"X-API-Key": "test-key", "Accept": "text/event-stream"})
    assert r.status_code != 405, f"Got {r.status_code}: {r.text[:200]}"
    # 200 (SSE stream) or 409 (no active SSE session) are both valid
    assert r.status_code in (200, 204, 409, 421), f"Unexpected: {r.status_code}"


@pytest.mark.anyio
async def test_mcp_post_initialize(mcp_client):
    """POST /mcp with JSON-RPC initialize should return protocol info."""
    r = await mcp_client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        },
        headers={"X-API-Key": "test-key", "Content-Type": "application/json"},
    )
    assert r.status_code == 200, f"Got {r.status_code}: {r.text[:500]}"
    body = r.json()
    assert "result" in body
    assert body["result"]["protocolVersion"]


@pytest.mark.anyio
async def test_mcp_unauthorized(mcp_client):
    """No API key → 401."""
    r = await mcp_client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert r.status_code == 401


@pytest.mark.anyio
async def test_mcp_tools_list(mcp_client):
    """After init + tools/list, should see upload_page et al."""
    h = {"X-API-Key": "test-key", "Content-Type": "application/json"}
    r1 = await mcp_client.post("/mcp", json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}},
    }, headers=h)
    assert r1.status_code == 200

    sid = r1.headers.get("mcp-session-id", "")
    h2 = dict(h)
    if sid:
        h2["mcp-session-id"] = sid

    r2 = await mcp_client.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, headers=h2)
    assert r2.status_code == 200, f"tools/list: {r2.text[:500]}"
    names = [t["name"] for t in r2.json().get("result", {}).get("tools", [])]
    assert "upload_page" in names
    assert "list_pages" in names
