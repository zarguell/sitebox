import base64

from mcp.server import MCPServer

from sitebox import storage
from sitebox.config import AUTH_PREFIXES

mcp = MCPServer("sitebox")


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


mcp_app = mcp.streamable_http_app(streamable_http_path="/")
