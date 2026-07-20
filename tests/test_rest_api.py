"""Tests for the REST API."""
import io
import zipfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sitebox.rest_api import router
from sitebox.config import AUTH_PREFIXES

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def patch_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect DATA_DIR to a temp dir for each test."""
    import sitebox.config as cfg

    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")


class TestUpload:
    def test_401_without_api_key(self):
        resp = client.post(
            "/api/upload",
            data={"dest": "test"},
            files={"file": ("f.html", b"x", "text/html")},
        )
        assert resp.status_code == 401

    def test_401_with_wrong_api_key(self):
        resp = client.post(
            "/api/upload",
            headers={"X-API-Key": "wrong"},
            data={"dest": "test"},
            files={"file": ("f.html", b"x", "text/html")},
        )
        assert resp.status_code == 401

    def test_upload_creates_file(self, tmp_path: Path):
        resp = client.post(
            "/api/upload",
            headers={"X-API-Key": "test-sitebox-key"},
            data={"dest": "mysite"},
            files={"file": ("index.html", b"hello world", "text/html")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["dest"] == "mysite"
        assert data["path"] == "/mysite"
        target = tmp_path / "data" / "mysite" / "index.html"
        assert target.read_bytes() == b"hello world"

    def test_upload_zip_extracts_and_flattens(self, tmp_path: Path):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("wrapdir/index.html", "nested")
            zf.writestr("wrapdir/style.css", "body{}")
        buf.seek(0)

        resp = client.post(
            "/api/upload",
            headers={"X-API-Key": "test-sitebox-key"},
            data={"dest": "zipsite"},
            files={"file": ("site.zip", buf.read(), "application/zip")},
        )
        assert resp.status_code == 200
        data_dir = tmp_path / "data" / "zipsite"
        assert (data_dir / "index.html").read_bytes() == b"nested"
        assert (data_dir / "style.css").read_bytes() == b"body{}"
        assert not (data_dir / "wrapdir").exists()

    def test_auth_required_adds_prefix(self):
        AUTH_PREFIXES.clear()
        resp = client.post(
            "/api/upload",
            headers={"X-API-Key": "test-sitebox-key"},
            data={"dest": "secret", "auth_required": "true"},
            files={"file": ("index.html", b"secret", "text/html")},
        )
        assert resp.status_code == 200
        assert "/secret" in AUTH_PREFIXES
        AUTH_PREFIXES.clear()


class TestListPages:
    def test_401_without_api_key(self):
        resp = client.get("/api/pages")
        assert resp.status_code == 401

    def test_list_pages_returns_tree(self, tmp_path: Path):
        (tmp_path / "data" / "site1").mkdir(parents=True)
        (tmp_path / "data" / "site1" / "index.html").write_bytes(b"a")
        (tmp_path / "data" / "site2").mkdir(parents=True)
        (tmp_path / "data" / "site2" / "index.html").write_bytes(b"b")

        resp = client.get("/api/pages", headers={"X-API-Key": "test-sitebox-key"})
        assert resp.status_code == 200
        data = resp.json()
        assert "site1" in data["tree"]
        assert "site2" in data["tree"]


class TestDeletePage:
    def test_401_without_api_key(self):
        resp = client.delete("/api/pages/test")
        assert resp.status_code == 401

    def test_delete_removes_page(self, tmp_path: Path):
        (tmp_path / "data" / "todelete").mkdir(parents=True)
        (tmp_path / "data" / "todelete" / "index.html").write_bytes(b"data")

        resp = client.delete(
            "/api/pages/todelete",
            headers={"X-API-Key": "test-sitebox-key"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"deleted": "todelete"}
        assert not (tmp_path / "data" / "todelete").exists()
