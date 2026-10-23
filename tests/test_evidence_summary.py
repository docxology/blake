"""Recorded evidence states use real retained files and SQLite projections."""

import hashlib
import json

import pytest

from blake.evidence import read_evidence_summary, read_projection_summary
from blake.text_search.recovered import build_recovered_search, open_recovered_search


pytest_plugins = ["tests.evidence_fixtures"]


def test_manifest_summary_is_read_only_and_reports_its_identity(captured_evidence):
    path = captured_evidence / "recovery/manifest.json"
    before = path.read_bytes()
    summary = read_evidence_summary(captured_evidence)
    manifest = json.loads(before)
    assert summary.manifest_sha256 == hashlib.sha256(before).hexdigest()
    assert summary.file_count == len(manifest["files"])
    assert summary.captured_bytes == sum(row["size"] for row in manifest["files"])
    assert summary.reading_passages == 4
    assert summary.roles == {"primary": 3, "unverified": 1}
    assert summary.oeuvre_coverage == "not_established"
    assert path.read_bytes() == before


def test_missing_projection_does_not_create_storage(captured_evidence):
    summary = read_evidence_summary(captured_evidence)
    projection = read_projection_summary(captured_evidence, summary)
    assert projection.status == "missing" and projection.passages is None
    assert not (captured_evidence / "search").exists()


def test_recorded_projection_is_explicitly_a_receipt_check(captured_evidence):
    snapshot = build_recovered_search(captured_evidence)
    summary = read_evidence_summary(captured_evidence)
    before = snapshot.index.path.read_bytes()
    projection = read_projection_summary(captured_evidence, summary)
    assert projection.status == "recorded" and projection.passages == 13
    assert projection.directory == snapshot.directory
    assert snapshot.index.path.read_bytes() == before
    # Equal-size damage evades the lightweight receipt view but must fail search.
    damaged = bytearray(before)
    damaged[-1] ^= 1
    snapshot.index.path.write_bytes(damaged)
    assert read_projection_summary(captured_evidence, summary).status == "recorded"
    with pytest.raises(ValueError, match="checksum"):
        open_recovered_search(captured_evidence)


@pytest.mark.parametrize("field", ["duplicate", "image_outcomes", "invalid_json"])
def test_damaged_manifest_is_never_shown_as_empty_or_verified(captured_evidence, field):
    path = captured_evidence / "recovery/manifest.json"
    manifest = json.loads(path.read_text())
    if field == "duplicate":
        manifest["files"].append(manifest["files"][0])
    elif field == "image_outcomes":
        manifest["images"]["downloaded"] = manifest["images"]["expected"] + 1
    path.write_text("{" if field == "invalid_json" else json.dumps(manifest))
    with pytest.raises(ValueError):
        read_evidence_summary(captured_evidence)


@pytest.mark.parametrize("change", ["source", "producer", "path", "size", "counts"])
def test_invalid_projection_receipts_refuse_status(captured_evidence, change):
    snapshot = build_recovered_search(captured_evidence)
    summary = read_evidence_summary(captured_evidence)
    path = snapshot.directory / "search-manifest.json"
    manifest = json.loads(path.read_text())
    if change == "source":
        manifest["captured_manifest_sha256"] = "0" * 64
    elif change == "producer":
        manifest["producer"]["python"] = "different"
    elif change == "path":
        manifest["index"]["path"] = "other.sqlite"
    elif change == "size":
        manifest["index"]["size"] += 1
    else:
        manifest["passages"] += 1
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        read_projection_summary(captured_evidence, summary)


def test_missing_or_symlinked_manifest_is_not_opened(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_evidence_summary(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text("{}")
    (tmp_path / "recovery").mkdir()
    (tmp_path / "recovery/manifest.json").symlink_to(outside)
    with pytest.raises(ValueError):
        read_evidence_summary(tmp_path)
