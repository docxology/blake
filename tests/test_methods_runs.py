"""Run publication, corruption and producer sensitivity on real files."""

from pathlib import Path

import pytest

from blake.methods.models import EvidenceError
from blake.methods.producer import SourceBinding, source_binding_sha256
from blake.methods.runs import (
    digest,
    read_regular,
    require_run_pin,
    reserve,
    verify_artifacts,
    write_new,
)


def test_publication_and_corruption(tmp_path: Path):
    target = tmp_path / "run"
    reserve(target)
    receipt = write_new(target / "data.json", b"{}")
    payloads = verify_artifacts(target, (receipt,), {"data.json"})
    assert payloads == {"data.json": b"{}"}
    with pytest.raises(FileExistsError):
        write_new(target / "data.json", b"other")
    (target / "data.json").write_bytes(b"[]")
    assert payloads["data.json"] == b"{}"
    with pytest.raises(EvidenceError, match="artifact_checksum"):
        verify_artifacts(target, (receipt,), {"data.json"})


def test_membership_and_marker(tmp_path):
    receipt = write_new(tmp_path / "data.json", b"{}")
    with pytest.raises(EvidenceError, match="artifact_membership"):
        verify_artifacts(tmp_path, (receipt, receipt), {"data.json"})
    with pytest.raises(EvidenceError, match="artifact_membership"):
        verify_artifacts(tmp_path, (receipt,), {"missing.json"})
    with pytest.raises(FileNotFoundError):
        require_run_pin(tmp_path, "a" * 64)
    write_new(tmp_path / "run.json", b"{}")
    raw = require_run_pin(tmp_path, digest(b"{}"))
    assert raw == b"{}"
    (tmp_path / "run.json").write_bytes(b"[]")
    assert raw == b"{}"
    with pytest.raises(EvidenceError, match="review_run_pin"):
        require_run_pin(tmp_path, "a" * 64)


def test_regular_and_symlink(tmp_path):
    directory = tmp_path / "directory"
    directory.mkdir()
    with pytest.raises(EvidenceError, match="nonregular_artifact"):
        read_regular(directory)
    link = tmp_path / "link"
    link.symlink_to(directory)
    with pytest.raises(EvidenceError, match="symlink_receipt"):
        read_regular(link, "receipt")
    with pytest.raises(EvidenceError, match="symlink_directory"):
        reserve(link / "child")
    with pytest.raises(EvidenceError, match="symlink_output"):
        write_new(link, b"{}")


def test_producer_sensitivity_real_sources(tmp_path, monkeypatch):
    package = tmp_path / "synthetic_producer"
    package.mkdir()
    (package / "__init__.py").write_text("")
    source = package / "delegated.py"
    source.write_text("value = 1\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    bindings = (SourceBinding("synthetic_producer", ("__init__.py", "delegated.py")),)
    before = source_binding_sha256(bindings)
    source.write_text("value = 2\n")
    assert source_binding_sha256(bindings) != before
    with pytest.raises(ValueError, match="duplicate producer source"):
        source_binding_sha256(bindings * 2)
