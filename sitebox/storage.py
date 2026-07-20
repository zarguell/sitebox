import asyncio
import io
import shutil
import zipfile
from pathlib import Path

import sitebox.config as cfg


def save_page(dest, content_bytes, filename="index.html", is_zip=False) -> Path:
    target = cfg.DATA_DIR / dest
    # Don't rmtree the data root — only subdirectories
    if dest and target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    if is_zip:
        buf = io.BytesIO(content_bytes)
        with zipfile.ZipFile(buf) as zf:
            zf.extractall(target)
        # flatten single wrapping directory
        children = list(target.iterdir())
        if len(children) == 1 and children[0].is_dir():
            wrap = children[0]
            for f in wrap.iterdir():
                f.rename(target / f.name)
            wrap.rmdir()
        return target
    else:
        path = target / filename
        path.write_bytes(content_bytes)
        return path


def delete_page(dest) -> None:
    target = cfg.DATA_DIR / dest
    if target.exists():
        shutil.rmtree(target)


def list_pages(path="") -> str:
    root = cfg.DATA_DIR / path
    if not root.exists():
        return ""
    return _tree(root, "")


def _tree(dir: Path, prefix: str) -> str:
    lines = []
    entries = sorted(dir.iterdir(), key=lambda p: (not p.is_dir(), p.name))
    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{entry.name}")
        if entry.is_dir():
            ext = "    " if is_last else "│   "
            lines.append(_tree(entry, prefix + ext))
    return "\n".join(lines)


def read_page(dest, path="") -> str | None:
    target = cfg.DATA_DIR / dest / path
    if not target.exists() or not target.is_file():
        return None
    return target.read_text(encoding="utf-8")


def _self_destruct(prefix, ttl) -> None:
    async def _del():
        await asyncio.sleep(ttl)
        target = cfg.DATA_DIR / prefix
        if target.exists():
            shutil.rmtree(target)

    asyncio.create_task(_del())
