from __future__ import annotations

import io
import json
import tarfile
import threading
import zipfile
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


COMMIT = "a" * 40


def snapshot(entries: dict[str, bytes], *, unsafe: str | None = None) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, content in entries.items():
            info = tarfile.TarInfo(f"data-{COMMIT}/{name}")
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
        if unsafe is not None:
            info = tarfile.TarInfo(f"data-{COMMIT}/{unsafe}")
            info.type = tarfile.SYMTYPE
            info.linkname = "../../outside"
            archive.addfile(info)
    return buffer.getvalue()


def seed_sources(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    sources = data / "recovery/sources"
    sources.mkdir(parents=True)
    variant = io.BytesIO()
    with zipfile.ZipFile(variant, "w") as archive:
        archive.writestr(
            "mhh.a.xml",
            '<bad work="Marriage"><phystext><l>Another state.</l></phystext></bad>',
        )
        archive.writestr("__MACOSX/._mhh.a.xml", b"resource fork, not XML")
    raw = snapshot(
        {
            "works/__contents__.xml": b"<collection/>",
            "works/mhh.a.xml": b'<bad work="Marriage"><desc dbi="mhh.a.P1"><phystext><l n="1">Eternity is in love</l><l n="2">with time.</l></phystext><note>EDITORIAL</note></desc></bad>',
            "works/mhh.a.xml.zip": variant.getvalue(),
            "works/mhh.b.xml": b'<bad work="Marriage"><phystext><l>Contraries and state.</l></phystext></bad>',
            "works/other.a.xml": b'<bad work="Other author"><phystext><l>federation</l></phystext></bad>',
            "works/drawing.xml": b'<bad work="Drawing"><desc dbi="drawing.P1"/></bad>',
            "works/problem.xml": b"<bad><phystext><l><choice><reg>unattested</reg></choice></l></phystext></bad>",
            "info/context.xml": b"<info>context</info>",
        }
    )
    (sources / f"blakearchive-{COMMIT}.tar.gz").write_bytes(raw)
    (sources / "erdman").mkdir()
    (sources / "erdman/pages.json").write_text(
        json.dumps(
            [
                {
                    "id": 0,
                    "page_id": "I",
                    "contents": "<div>Preface<script>bad</script></div>",
                },
                {
                    "id": 1,
                    "page_id": "1",
                    "contents": "<div><p>Poetry<note>EDITORIAL</note></p></div>",
                },
                {
                    "id": 2,
                    "page_id": "3O2",
                    "contents": "<div>Preserve provider page ID.</div>",
                },
            ]
        ),
        encoding="utf-8",
    )
    return data


@pytest.fixture
def saved_sources(tmp_path: Path) -> Path:
    return seed_sources(tmp_path)


@contextmanager
def local_http(content: bytes, status: int = 200, expected_path: str | None = None):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(
                status if expected_path is None or self.path == expected_path else 404
            )
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *_args) -> None:
            return

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/source"
        finally:
            server.shutdown()
            thread.join()
