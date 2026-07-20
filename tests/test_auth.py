"""Tests for the sitebox auth module."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sitebox.auth import router, SESSION_TOKENS, check_browser_auth
from sitebox.config import AUTH_PREFIXES

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_login_form_get():
    """GET /login returns 200 with HTML containing a password input."""
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "password" in resp.text.lower()


def test_login_wrong_key():
    """POST /login with wrong key returns 401 with error on the form."""
    resp = client.post("/login", data={"next": "/", "key": "not-the-key"})
    assert resp.status_code == 401
    assert "invalid" in resp.text.lower() or "error" in resp.text.lower()


def test_login_correct_key():
    """POST /login with correct key returns 302 with session cookie."""
    resp = client.post(
        "/login",
        data={"next": "/", "key": "test-sitebox-key"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "session" in resp.cookies


def test_login_next_preserved():
    """POST /login preserves the next param in the redirect."""
    resp = client.post(
        "/login",
        data={"next": "/protected-page", "key": "test-sitebox-key"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/protected-page"


def test_login_form_next_preserved():
    """GET /login with next param preserves it in the form."""
    resp = client.get("/login?next=/somewhere")
    assert resp.status_code == 200
    assert "somewhere" in resp.text or "/somewhere" in resp.text


def test_check_browser_auth_no_prefix():
    """Path not in AUTH_PREFIXES → always allowed."""
    AUTH_PREFIXES.clear()
    assert check_browser_auth("/public/page", {}) is True


def test_check_browser_auth_missing_cookie():
    """Path in AUTH_PREFIXES but no session cookie → blocked."""
    AUTH_PREFIXES.clear()
    AUTH_PREFIXES.add("/admin")
    assert check_browser_auth("/admin/dashboard", {}) is False


def test_check_browser_auth_valid_token():
    """Path in AUTH_PREFIXES with valid session token → allowed."""
    AUTH_PREFIXES.clear()
    AUTH_PREFIXES.add("/admin")
    SESSION_TOKENS.clear()
    SESSION_TOKENS["valid-token"] = float("inf")
    assert check_browser_auth("/admin", {"session": "valid-token"}) is True


def test_check_browser_auth_expired_token():
    """Path in AUTH_PREFIXES with expired session token → blocked."""
    import time

    AUTH_PREFIXES.clear()
    AUTH_PREFIXES.add("/admin")
    SESSION_TOKENS.clear()
    SESSION_TOKENS["stale-token"] = time.time() - 1.0
    assert check_browser_auth("/admin", {"session": "stale-token"}) is False
