"""Auth routes and helpers for sitebox.

Provides a login form (/login), session management via cookies,
and a check_browser_auth() helper for middleware use.
"""

import secrets
import time

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from sitebox.config import get_api_key, AUTH_PREFIXES

SESSION_TOKENS: dict[str, float] = {}
router = APIRouter()

_PAGE = """\
<!DOCTYPE html>
<html>
<head><title>Login</title></head>
<body>
<form method="post" action="/login">
  <input type="hidden" name="next" value="{next}">
  <label>Password: <input type="password" name="key"></label>
  <button>Login</button>
</form>
{error}
</body>
</html>"""


@router.get("/login")
async def login_form(next: str = "/"):
    return HTMLResponse(_PAGE.format(next=next, error=""))


@router.post("/login")
async def login_submit(next: str = Form(...), key: str = Form(...)):
    if key != get_api_key():
        return HTMLResponse(
            _PAGE.format(next=next, error='<p style="color:red">Invalid key</p>'),
            status_code=401,
        )
    token = secrets.token_urlsafe(32)
    SESSION_TOKENS[token] = time.time() + 86400
    resp = RedirectResponse(url=next, status_code=302)
    resp.set_cookie(key="session", value=token, httponly=True)
    return resp


def check_browser_auth(path: str, cookies: dict) -> bool:
    """Return True if *path* is accessible with *cookies*.

    Paths that don't start with any AUTH_PREFIXES entry are always allowed.
    Protected paths require a valid (non-expired) session token cookie.
    """
    needs_auth = any(path.startswith(p) for p in AUTH_PREFIXES)
    if not needs_auth:
        return True
    token = cookies.get("session")
    # ponytail: in-memory SESSION_TOKENS, lost on restart — add Redis/file
    #           backed store when multi-process or persistence required.
    return token in SESSION_TOKENS and SESSION_TOKENS[token] > time.time()
