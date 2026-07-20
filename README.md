# sitebox

Self-hosted static site host — upload pages via REST API or MCP, serve them immediately.

- **Upload** files or ZIP archives to named destinations
- **Serve** from `/dest/path` instantly
- **Auth** — shared API key for uploads, optional password-protected pages
- **TTL** — auto-expire pages after a set time
- **MCP** — AI agents can manage pages via the built-in Model Context Protocol server

## Quick start

```bash
docker run -e API_KEY=my-secret-key -p 8000:8000 ghcr.io/zarguell/sitebox
```

Upload a page:

```bash
curl -X POST http://localhost:8000/api/upload \
  -H "X-API-Key: my-secret-key" \
  -F "file=@index.html" \
  -F "dest=myapp"
```

Open `http://localhost:8000/myapp/index.html` in your browser.

## Features

### REST API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload` | Upload file or ZIP to a destination |
| `GET`  | `/api/pages` | List all pages |
| `DELETE` | `/api/pages/{dest}` | Delete a page |

All require `X-API-Key` header matching the `API_KEY` environment variable.

**Upload parameters (multipart form):**

| Field | Required | Description |
|-------|----------|-------------|
| `file` | yes | The file (ZIP auto-extracts and flattens) |
| `dest` | yes | Destination path (e.g. `myapp` or `blog/post1`) |
| `auth_required` | no | `true` to require login before viewing |
| `ttl_seconds` | no | Auto-delete after N seconds |

### MCP Server

Connect an MCP-compatible AI agent (Cursor, Claude Desktop) to `http://host:8000/mcp` with header `X-API-Key`.

Available tools:
- `upload_page` — upload base64 content or ZIP
- `list_pages` — browse page tree
- `read_file` — read file content
- `delete_page` — remove a page

### Browser Auth

When `auth_required=true` on upload, visitors are redirected to a login form. The password is the shared `API_KEY`. Sessions last 24 hours (in-memory).

## Configuration

| Env var | Required | Default | Description |
|---------|----------|---------|-------------|
| `API_KEY` | yes | `""` | Shared secret for all auth (upload + login) |

## Development

```bash
git clone https://github.com/zarguell/sitebox
cd sitebox
uv sync
API_KEY=dev-key uv run uvicorn sitebox.app:app --reload
```

## Design

- **config.py** — shared env vars and in-memory state (`AUTH_PREFIXES`, `DATA_DIR`)
- **storage.py** — file operations (stdlib only)
- **auth.py** — login form, session tokens, browser auth helper
- **rest_api.py** — REST endpoints with API key check
- **mcp_api.py** — MCP server with Streamable HTTP transport
- **app.py** — FastAPI wiring, middleware, mounts

`ponytail:` session tokens and auth prefixes are in-memory (lost on restart). Add Redis or SQLite when multi-process persistence is needed.
