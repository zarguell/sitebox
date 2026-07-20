from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException

from sitebox import storage
from sitebox.config import get_api_key, AUTH_PREFIXES

router = APIRouter(prefix="/api")


def _check_key(request: Request):
    key = request.headers.get("x-api-key")
    if key != get_api_key():
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    dest: str = Form(...),
    ttl_seconds: int | None = Form(None),
    auth_required: bool = Form(False),
):
    _check_key(request)
    dest = dest.strip("/")
    if dest and not all(c.isalnum() or c in "-_/" for c in dest):
        raise HTTPException(status_code=400, detail="Invalid destination")

    content = await file.read()
    is_zip = bool(file.filename and file.filename.endswith(".zip"))
    storage.save_page(dest, content, filename=file.filename or "index.html", is_zip=is_zip)

    if auth_required:
        AUTH_PREFIXES.add("/" + dest if dest else "/")
    else:
        AUTH_PREFIXES.discard("/" + dest if dest else "/")

    if ttl_seconds and ttl_seconds > 0:
        storage._self_destruct(dest, ttl_seconds)

    return {"dest": dest, "path": "/" + dest if dest else "/", "ttl": ttl_seconds, "auth_required": auth_required}


@router.get("/pages")
async def list_pages(request: Request):
    _check_key(request)
    return {"tree": storage.list_pages()}


@router.delete("/pages/{dest:path}")
async def delete_page(request: Request, dest: str):
    _check_key(request)
    dest = dest.strip("/")
    storage.delete_page(dest)
    AUTH_PREFIXES.discard("/" + dest)
    return {"deleted": dest}
