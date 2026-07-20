"""MCP API — tool definitions and streamable HTTP app.

Ponytail: re-exports mcp_app and _mcp_lifespan so app.py can wire them
without reaching into SDK internals.
"""
import base64

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from sitebox import storage
from sitebox.config import AUTH_PREFIXES

mcp = MCPServer("sitebox")

# ponytail: disable DNS rebinding protection — self-hosted behind Tailscale/reverse proxy
_no_dpi = TransportSecuritySettings(enable_dns_rebinding_protection=False)


@mcp.tool()
async def upload_page(
    dest: str,
    file_content: str,
    filename: str = "index.html",
    is_zip: bool = False,
    ttl_seconds: int | None = None,
    auth_required: bool = False,
) -> str:
    """Upload content to a page destination."""
    dest = dest.strip("/")
    if not dest or not all(c.isalnum() or c in "-_/" for c in dest):
        return "Error: Invalid destination"
    data = base64.b64decode(file_content)
    storage.save_page(dest, data, filename=filename, is_zip=is_zip)
    if auth_required:
        AUTH_PREFIXES.add("/" + dest)
    else:
        AUTH_PREFIXES.discard("/" + dest)
    if ttl_seconds and ttl_seconds > 0:
        storage._self_destruct(dest, ttl_seconds)
    return f"Uploaded /{dest}"


@mcp.tool()
async def list_pages(path: str = "") -> str:
    """List page destinations and files."""
    tree = storage.list_pages(path)
    return tree or "No pages yet"


@mcp.tool()
async def read_file(dest: str, path: str = "") -> str:
    """Read a file's contents."""
    content = storage.read_page(dest, path)
    return content if content is not None else "File not found"


@mcp.tool()
async def delete_page(dest: str) -> str:
    """Delete a page destination."""
    dest = dest.strip("/")
    storage.delete_page(dest)
    AUTH_PREFIXES.discard("/" + dest)
    return f"Deleted /{dest}"


# ponytail: streamable_http_app creates its own session_manager lazily.
# We capture the app and its lifespan context separately so FastAPI can
# call startup/shutdown (which internally runs session_manager.run()).
mcp_app = mcp.streamable_http_app(streamable_http_path="/mcp", transport_security=_no_dpi)
_mcp_lifespan_ctx = mcp_app.router.lifespan_context
