"""Integration tests for sitebox app wiring."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sitebox.app import app
from sitebox.config import AUTH_PREFIXES

client = TestClient(app)


@pytest.fixture(autouse=True)
def patch_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import sitebox.config as cfg

    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")
    AUTH_PREFIXES.clear()


class TestFullFlow:
    def test_upload_creates_file(self, tmp_path: Path):
        """Upload a file via REST API, verify it lands on disk."""
        resp = client.post(
            "/api/upload",
            headers={"X-API-Key": "test-sitebox-key"},
            data={"dest": "hello"},
            files={"file": ("index.html", b"<h1>Hello World</h1>", "text/html")},
        )
        assert resp.status_code == 200
        target = tmp_path / "data" / "hello" / "index.html"
        assert target.read_bytes() == b"<h1>Hello World</h1>"

    def test_upload_zip_extracts(self, tmp_path: Path):
        """Upload a ZIP, verify files on disk."""
        import io
        import zipfile

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("page.html", "<h1>From ZIP</h1>")
            zf.writestr("style.css", "body { background: red; }")
        buf.seek(0)

        resp = client.post(
            "/api/upload",
            headers={"X-API-Key": "test-sitebox-key"},
            data={"dest": "myapp"},
            files={"file": ("archive.zip", buf.read(), "application/zip")},
        )
        assert resp.status_code == 200
        assert (tmp_path / "data" / "myapp" / "page.html").read_bytes() == b"<h1>From ZIP</h1>"

    def test_protected_page_redirects_to_login(self):
        """Upload with auth_required, accessing it redirects to login."""
        resp = client.post(
            "/api/upload",
            headers={"X-API-Key": "test-sitebox-key"},
            data={"dest": "secret", "auth_required": "true"},
            files={"file": ("index.html", b"<h1>Secret</h1>", "text/html")},
        )
        assert resp.status_code == 200
        assert "/secret" in AUTH_PREFIXES

        # Without session cookie, redirects to login
        resp2 = client.get("/secret/index.html", follow_redirects=False)
        assert resp2.status_code == 302
        assert "/login?next=" in resp2.headers["location"]

    def test_mcp_auth_required(self):
        """MCP endpoint rejects requests without API key."""
        resp = client.get("/mcp")
        assert resp.status_code == 401
        assert resp.json() == {"error": "Unauthorized"}
