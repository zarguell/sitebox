import asyncio
import io
import zipfile
from pathlib import Path

import pytest

from sitebox.storage import (
    _self_destruct,
    delete_page,
    list_pages,
    read_page,
    save_page,
)


@pytest.fixture(autouse=True)
def patch_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect DATA_DIR to a temp dir for each test."""
    import sitebox.config as cfg

    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")


def test_save_page_writes_file(tmp_path: Path):
    save_page("mysite", b"hello world")
    target = tmp_path / "data" / "mysite" / "index.html"
    assert target.read_bytes() == b"hello world"


def test_save_page_custom_filename(tmp_path: Path):
    save_page("mysite", b"custom", filename="foo.txt")
    target = tmp_path / "data" / "mysite" / "foo.txt"
    assert target.read_bytes() == b"custom"


def test_save_page_overwrites_existing(tmp_path: Path):
    save_page("mysite", b"first")
    save_page("mysite", b"second")
    target = tmp_path / "data" / "mysite" / "index.html"
    assert target.read_bytes() == b"second"


def test_save_page_zip_extract_and_flatten(tmp_path: Path):
    # Build a zip with a single wrapping dir
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("wrapdir/index.html", "nested")
        zf.writestr("wrapdir/style.css", "body{}")
    buf.seek(0)

    save_page("zipsite", buf.read(), is_zip=True)

    data_dir = tmp_path / "data" / "zipsite"
    assert (data_dir / "index.html").read_bytes() == b"nested"
    assert (data_dir / "style.css").read_bytes() == b"body{}"
    # wrapping dir should be gone
    assert not (data_dir / "wrapdir").exists()


def test_save_page_zip_no_wrapping_dir(tmp_path: Path):
    """If zip has files at root, keep them as-is."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("index.html", "root")
    buf.seek(0)

    save_page("zipsite2", buf.read(), is_zip=True)
    assert (tmp_path / "data" / "zipsite2" / "index.html").read_bytes() == b"root"


def test_delete_page_removes_dir(tmp_path: Path):
    save_page("mysite", b"data")
    delete_page("mysite")
    assert not (tmp_path / "data" / "mysite").exists()


def test_list_pages_shows_tree(tmp_path: Path):
    save_page("site1", b"a")
    save_page("site2", b"b")
    (tmp_path / "data" / "site2" / "nested").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "site2" / "nested" / "deep.html").write_bytes(b"deep")

    tree = list_pages()
    assert "site1" in tree
    assert "site2" in tree
    assert "nested" in tree
    assert "deep.html" in tree


def test_list_pages_subpath(tmp_path: Path):
    save_page("site/sub", b"data")
    tree = list_pages("site")
    assert "sub" in tree


def test_read_page_returns_content(tmp_path: Path):
    save_page("mysite", b"content")
    result = read_page("mysite", "index.html")
    assert result == "content"


def test_read_page_returns_none_if_missing():
    result = read_page("nonexistent", "nosuch.html")
    assert result is None


@pytest.mark.asyncio
async def test_self_destruct_deletes_after_ttl(tmp_path: Path):
    save_page("tempdir", b"temp content")
    target = tmp_path / "data" / "tempdir"
    assert target.exists()

    _self_destruct("tempdir", ttl=0.05)
    await asyncio.sleep(0.2)
    assert not target.exists()
