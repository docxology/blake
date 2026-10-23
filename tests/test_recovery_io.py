from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from blake.recovery import (
    RecoveryError,
    extract_erdman,
    fetch_file,
    unpack_snapshot,
)

from .recovery_fixtures import COMMIT, snapshot, local_http
from tests import recovery_fixtures

saved_sources = recovery_fixtures.saved_sources


@pytest.mark.parametrize("unsafe", ["../escape", "/absolute", "works/link"])
def test_unpack_when_archive_contains_unsafe_members_writes_nothing(
    tmp_path: Path, unsafe: str
) -> None:
    payload = snapshot({"works/__contents__.xml": b"<collection/>"}, unsafe=unsafe)

    with pytest.raises(RecoveryError):
        unpack_snapshot(tmp_path, payload, COMMIT)

    assert list(tmp_path.iterdir()) == []


def test_unpack_when_existing_source_differs_preserves_local_bytes(
    tmp_path: Path,
) -> None:
    raw = snapshot({"works/__contents__.xml": b"<collection/>"})
    target = tmp_path / f"snapshot/{COMMIT}/works/__contents__.xml"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"existing source")

    with pytest.raises(RecoveryError, match="differs"):
        unpack_snapshot(tmp_path, raw, COMMIT)

    assert target.read_bytes() == b"existing source"


@pytest.mark.parametrize(
    "pages",
    [
        [],
        [{"id": 0, "page_id": "1", "contents": "text"}] * 2,
        [{"id": 0, "page_id": "1"}],
    ],
)
def test_erdman_when_empty_duplicate_or_malformed_refuses(
    tmp_path: Path, pages: list[dict[str, str | int]]
) -> None:
    with pytest.raises((RecoveryError, ValidationError)):
        extract_erdman(tmp_path, json.dumps(pages).encode())


def test_fetch_when_real_http_succeeds_retains_exact_bytes(tmp_path: Path) -> None:
    target = tmp_path / "source.bin"
    with local_http(b"original source") as url:
        fetched = fetch_file(url, target)

    assert fetched == target.read_bytes() == b"original source"
    assert fetch_file(url, target, offline=True) == fetched


def test_fetch_when_validator_rejects_does_not_save_bad_payload(tmp_path: Path) -> None:
    target = tmp_path / "image.jpg"

    def reject(content: bytes) -> None:
        raise RecoveryError(f"Invalid image: {hashlib.sha256(content).hexdigest()}")

    with local_http(b"<html>not an image</html>") as url:
        with pytest.raises(RecoveryError, match="Invalid image"):
            fetch_file(url, target, validate=reject)

    assert not target.exists()
