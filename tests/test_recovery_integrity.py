from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from blake.recovery_models import RecoveryError
from blake.recovery_pipeline import recover_corpus
from blake.recovery_integrity import verify_recovery

from .recovery_fixtures import COMMIT
from tests import recovery_fixtures

saved_sources = recovery_fixtures.saved_sources


@pytest.mark.parametrize("problem", ["corruption", "missing", "symlink"])
def test_verify_when_bytes_are_missing_or_modified_rejects(
    saved_sources: Path, tmp_path: Path, problem: str
) -> None:
    manifest = recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)
    path = saved_sources / "recovery" / manifest.files[0].path
    if problem == "corruption":
        path.write_bytes(b"wrong bytes")
    elif problem == "missing":
        path.unlink()
    else:
        outside = tmp_path / "outside"
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)

    with pytest.raises(RecoveryError):
        verify_recovery(saved_sources)


@pytest.mark.parametrize(
    "problem",
    [
        "omitted_source",
        "copy_binding",
        "false_image_complete",
        "missing_index_record",
        "wrong_pages",
    ],
)
def test_verify_when_hashes_match_but_inventory_contract_is_false_refuses(
    saved_sources: Path, problem: str
) -> None:
    import sqlite3

    recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)
    root = saved_sources / "recovery"
    path = root / "manifest.json"
    manifest = json.loads(path.read_text())
    if problem == "omitted_source":
        omitted = next(
            c["source_path"] for c in manifest["copies"] if c["copy_id"] == "mhh.b"
        )
        manifest["files"] = [
            entry for entry in manifest["files"] if entry["path"] != omitted
        ]
        manifest["copies"] = [
            copy for copy in manifest["copies"] if copy["source_path"] != omitted
        ]
    elif problem == "copy_binding":
        manifest["copies"][0]["source_sha256"] = "f" * 64
    elif problem == "false_image_complete":
        manifest["images"]["status"] = "complete"
    elif problem == "wrong_pages":
        manifest["erdman_page_ids"] = ["not-in-source"]
    else:
        index = root / "search.sqlite"
        with sqlite3.connect(index) as connection:
            connection.execute("DELETE FROM passages WHERE id = 'archive:mhh.a'")
        entry = next(
            entry for entry in manifest["files"] if entry["path"] == "search.sqlite"
        )
        entry["sha256"] = hashlib.sha256(index.read_bytes()).hexdigest()
        entry["size"] = index.stat().st_size
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(RecoveryError):
        verify_recovery(saved_sources)
