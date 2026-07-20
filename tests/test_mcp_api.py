"""Tests for the sitebox MCP API."""
import base64
import io
import zipfile

import pytest

from mcp import Client
from sitebox.mcp_api import mcp


@pytest.fixture(autouse=True)
def patch_data_dir(tmp_path, monkeypatch):
    import sitebox.config as cfg

    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")


@pytest.mark.anyio
async def test_upload_file_creates_page():
    async with Client(mcp, raise_exceptions=True) as client:
        content = base64.b64encode(b"hello world").decode()
        result = await client.call_tool(
            "upload_page",
            {"dest": "mcp-test", "file_content": content, "filename": "index.html"},
        )
        assert "Uploaded" in str(result)

        r2 = await client.call_tool(
            "read_file", {"dest": "mcp-test", "path": "index.html"}
        )
        assert "hello world" in str(r2)


@pytest.mark.anyio
async def test_upload_zip_extracts():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("page.html", "<h1>zipped</h1>")
        zf.writestr("style.css", "body {}")
    buf.seek(0)
    zip_b64 = base64.b64encode(buf.read()).decode()

    async with Client(mcp, raise_exceptions=True) as client:
        result = await client.call_tool(
            "upload_page",
            {"dest": "mcp-zip", "file_content": zip_b64, "is_zip": True},
        )
        assert "Uploaded" in str(result)

        r1 = await client.call_tool(
            "read_file", {"dest": "mcp-zip", "path": "page.html"}
        )
        assert "zipped" in str(r1)

        r2 = await client.call_tool(
            "read_file", {"dest": "mcp-zip", "path": "style.css"}
        )
        assert "body" in str(r2)


@pytest.mark.anyio
async def test_list_pages():
    async with Client(mcp, raise_exceptions=True) as client:
        content = base64.b64encode(b"listme").decode()
        await client.call_tool(
            "upload_page", {"dest": "list-test", "file_content": content}
        )

        result = await client.call_tool("list_pages", {})
        assert "list-test" in str(result)


@pytest.mark.anyio
async def test_read_file_not_found():
    async with Client(mcp, raise_exceptions=True) as client:
        result = await client.call_tool(
            "read_file", {"dest": "nonexistent", "path": "no.html"}
        )
        assert "not found" in str(result).lower()


@pytest.mark.anyio
async def test_delete_page():
    async with Client(mcp, raise_exceptions=True) as client:
        content = base64.b64encode(b"delete me").decode()
        await client.call_tool(
            "upload_page", {"dest": "delete-test", "file_content": content}
        )

        # Verify it exists
        r = await client.call_tool(
            "read_file", {"dest": "delete-test", "path": "index.html"}
        )
        assert "delete me" in str(r)

        # Delete it
        await client.call_tool("delete_page", {"dest": "delete-test"})

        # Verify gone
        r2 = await client.call_tool(
            "read_file", {"dest": "delete-test", "path": "index.html"}
        )
        assert "not found" in str(r2).lower()


@pytest.mark.anyio
async def test_upload_with_auth():
    async with Client(mcp, raise_exceptions=True) as client:
        content = base64.b64encode(b"auth content").decode()
        await client.call_tool(
            "upload_page",
            {"dest": "auth-test", "file_content": content, "auth_required": True},
        )

        from sitebox.config import AUTH_PREFIXES

        assert "/auth-test" in AUTH_PREFIXES


@pytest.mark.anyio
async def test_upload_invalid_dest():
    async with Client(mcp, raise_exceptions=True) as client:
        content = base64.b64encode(b"whatever").decode()
        result = await client.call_tool(
            "upload_page", {"dest": "../bad", "file_content": content}
        )
        assert "error" in str(result).lower()
