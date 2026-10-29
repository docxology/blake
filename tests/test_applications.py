"""Real recovered sources and corruptions exercise the application snapshot boundary."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from blake.applications import ApplicationError, export_recovered, load_bundle, main
from blake.recovery import recover_corpus
from blake.text_search.models import SearchError
from blake.text_search.recovered import build_recovered_search
from tests.recovery_fixtures import COMMIT, seed_sources


def test_portable_reader_does_not_import_source_recovery_stack() -> None:
    """A reader-only application must not load acquisition-only dependencies."""
    source = Path(__file__).resolve().parents[1]
    script = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "from blake.applications import load_bundle; "
        "assert 'blake.recovery' not in sys.modules; "
        "assert 'bs4' not in sys.modules"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(source)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def recovered(tmp_path: Path) -> Path:
    data = seed_sources(tmp_path)
    recover_corpus(data, commit=COMMIT, offline=True, images=False)
    build_recovered_search(data)
    return data


@pytest.fixture
def bundle(recovered: Path, tmp_path: Path) -> tuple[Path, str]:
    directory = tmp_path / "application"
    export_recovered(recovered, directory)
    return directory, digest(directory / "manifest.json")


def rewrite_manifest(directory: Path, metadata: dict) -> str:
    (directory / "manifest.json").write_text(json.dumps(metadata), encoding="utf-8")
    return digest(directory / "manifest.json")


def rewrite_payload(directory: Path, records: list[dict]) -> str:
    payload = directory / "passages.jsonl"
    payload.write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )
    metadata = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    metadata["passages_file"].update(
        size=payload.stat().st_size, sha256=digest(payload)
    )
    return rewrite_manifest(directory, metadata)


def test_export_and_load_preserve_all_source_planes_and_original_bytes(
    recovered: Path, tmp_path: Path
) -> None:
    # Given an actual, separately verified recovered SQLite projection.
    snapshot = build_recovered_search(recovered)
    source_before = digest(snapshot.index.path)
    destination = tmp_path / "application"
    # When the portable private projection is exported and loaded with its pin.
    manifest = export_recovered(recovered, destination)
    result = load_bundle(destination, digest(destination / "manifest.json"))
    # Then every passage is unchanged and the upstream index is untouched.
    assert result.passages == tuple(snapshot.index.inventory())
    assert result.manifest == manifest
    assert manifest.passages == 13
    assert manifest.passages_by_role == {"primary": 3, "unverified": 7, "editorial": 3}
    assert manifest.passages_by_plane == {"reading": 4, "xml": 6, "erdman": 3}
    assert digest(snapshot.index.path) == source_before
    assert not any(
        str(recovered) in value for value in manifest.model_dump_json().splitlines()
    )


@pytest.mark.parametrize("pin", ["", "not-a-hash", "0" * 64])
def test_unpinned_or_wrongly_pinned_manifest_is_refused(
    bundle: tuple[Path, str], pin: str
) -> None:
    directory, _ = bundle
    with pytest.raises(ApplicationError, match="manifest_pin"):
        load_bundle(directory, pin)


def test_changed_manifest_is_refused_under_original_pin(
    bundle: tuple[Path, str],
) -> None:
    directory, pin = bundle
    manifest = directory / "manifest.json"
    manifest.write_bytes(manifest.read_bytes() + b" ")
    with pytest.raises(ApplicationError, match="manifest_pin"):
        load_bundle(directory, pin)


def test_changed_payload_is_refused(bundle: tuple[Path, str]) -> None:
    directory, pin = bundle
    payload = directory / "passages.jsonl"
    payload.write_bytes(payload.read_bytes() + b"changed")
    with pytest.raises(ApplicationError, match="passages_checksum"):
        load_bundle(directory, pin)


@pytest.mark.parametrize("name", ["manifest.json", "passages.jsonl"])
def test_missing_snapshot_file_is_refused(bundle: tuple[Path, str], name: str) -> None:
    directory, pin = bundle
    (directory / name).rename(directory / (name + ".retained"))
    with pytest.raises(ApplicationError, match="missing_regular_file"):
        load_bundle(directory, pin)


@pytest.mark.parametrize(
    "change",
    ["duplicate", "omitted", "text", "source_hash", "role", "author"],
)
def test_rehashed_payload_still_requires_exact_membership_and_bindings(
    bundle: tuple[Path, str], change: str
) -> None:
    directory, _ = bundle
    records = [
        json.loads(line)
        for line in (directory / "passages.jsonl").read_text().split("\n")
        if line
    ]
    primary = next(record for record in records if record["text_role"] == "primary")
    if change == "duplicate":
        records.append(records[0])
    elif change == "omitted":
        records.pop()
    elif change == "text":
        primary["text"] += " altered"
    elif change == "source_hash":
        primary["source_sha256"] = "0" * 64
    elif change == "role":
        primary["text_role"] = "unverified"
    else:
        primary["author_id"] = "different-author"
    pin = rewrite_payload(directory, records)
    with pytest.raises(ApplicationError, match="bundle_membership"):
        load_bundle(directory, pin)


@pytest.mark.parametrize(
    "field",
    [
        "passages",
        "passage_ids",
        "passages_by_role",
        "passages_by_plane",
        "passages_by_author",
    ],
)
def test_repinned_inconsistent_manifest_is_refused(
    bundle: tuple[Path, str], field: str
) -> None:
    directory, _ = bundle
    metadata = json.loads((directory / "manifest.json").read_text())
    if field == "passages":
        metadata[field] += 1
    elif field == "passage_ids":
        metadata[field].reverse()
    else:
        metadata[field] = {}
    pin = rewrite_manifest(directory, metadata)
    with pytest.raises(ApplicationError, match="bundle_membership"):
        load_bundle(directory, pin)


def test_export_never_overwrites_existing_application(
    bundle: tuple[Path, str], recovered: Path
) -> None:
    directory, pin = bundle
    with pytest.raises(ApplicationError, match="occupied_output"):
        export_recovered(recovered, directory)
    assert digest(directory / "manifest.json") == pin


def test_export_refuses_occupied_empty_directory(
    recovered: Path, tmp_path: Path
) -> None:
    destination = tmp_path / "occupied"
    destination.mkdir()
    with pytest.raises(ApplicationError, match="occupied_output"):
        export_recovered(recovered, destination)
    assert list(destination.iterdir()) == []


def test_export_refuses_source_overlap(recovered: Path) -> None:
    with pytest.raises(ApplicationError, match="overlapping_roots"):
        export_recovered(recovered, recovered / "application")
    assert not (recovered / "application").exists()


def test_user_selected_root_can_use_normal_parent_relative_paths(
    recovered: Path, tmp_path: Path
) -> None:
    sibling = tmp_path / "working"
    sibling.mkdir()
    source = sibling / ".." / "data"
    destination = sibling / ".." / "relative-application"
    manifest = export_recovered(source, destination)
    loaded = load_bundle(destination, digest(destination / "manifest.json"))
    assert loaded.manifest == manifest
    assert len(loaded.passages) == 13


def test_export_refuses_symlink_destination_ancestor(
    recovered: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "alias"
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ApplicationError, match="unsafe_path"):
        export_recovered(recovered, link / "application")
    assert list(outside.iterdir()) == []


def test_loader_refuses_symlink_file(bundle: tuple[Path, str], tmp_path: Path) -> None:
    directory, pin = bundle
    payload = directory / "passages.jsonl"
    retained = tmp_path / "retained.jsonl"
    payload.rename(retained)
    payload.symlink_to(retained)
    with pytest.raises(ApplicationError, match="unsafe_path"):
        load_bundle(directory, pin)


def test_changed_retained_input_prevents_export(
    recovered: Path, tmp_path: Path
) -> None:
    source = recovered / "recovery/texts/archive/mhh.a.txt"
    source.write_bytes(source.read_bytes() + b"altered")
    destination = tmp_path / "application"
    with pytest.raises(SearchError, match="checksum"):
        export_recovered(recovered, destination)
    assert not destination.exists()


def test_missing_source_hash_cannot_be_promoted_to_portable_evidence(
    bundle: tuple[Path, str],
) -> None:
    directory, _ = bundle
    records = [
        json.loads(line)
        for line in (directory / "passages.jsonl").read_text().split("\n")
        if line
    ]
    records[0]["source_sha256"] = None
    pin = rewrite_payload(directory, records)
    with pytest.raises(ApplicationError, match="missing_source_hash"):
        load_bundle(directory, pin)


def test_invalid_jsonl_framing_is_refused_even_if_rehashed(
    bundle: tuple[Path, str],
) -> None:
    directory, _ = bundle
    path = directory / "passages.jsonl"
    path.write_bytes(path.read_bytes().rstrip(b"\n"))
    metadata = json.loads((directory / "manifest.json").read_text())
    metadata["passages_file"].update(size=path.stat().st_size, sha256=digest(path))
    pin = rewrite_manifest(directory, metadata)
    with pytest.raises(ApplicationError, match="passages_format"):
        load_bundle(directory, pin)


def test_export_requires_existing_projection_and_does_not_build_one(
    tmp_path: Path,
) -> None:
    data = seed_sources(tmp_path)
    recover_corpus(data, commit=COMMIT, offline=True, images=False)
    with pytest.raises(SearchError, match="absent"):
        export_recovered(data, tmp_path / "application")
    assert not (data / "search").exists()


def test_actual_module_cli_exports_verifies_and_fails_wrong_pin(
    recovered: Path, tmp_path: Path
) -> None:
    destination = tmp_path / "cli-application"
    command = [sys.executable, "-m", "blake.applications"]
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    exported = subprocess.run(
        [
            *command,
            "export",
            "--data-dir",
            str(recovered),
            "--destination",
            str(destination),
        ],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )
    assert exported.returncode == 0, exported.stderr
    pin = json.loads(exported.stdout)["manifest_sha256"]
    verified = subprocess.run(
        [*command, "verify", "--bundle", str(destination), "--manifest-sha256", pin],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["passages"] == 13
    control = subprocess.run(
        [
            *command,
            "verify",
            "--bundle",
            str(destination),
            "--manifest-sha256",
            "0" * 64,
        ],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )
    assert control.returncode != 0
    assert "manifest_pin" in control.stderr


def test_click_export_reports_a_pin_for_a_new_snapshot(
    recovered: Path, tmp_path: Path
) -> None:
    destination = tmp_path / "click-application"
    result = CliRunner().invoke(
        main,
        ["export", "--data-dir", str(recovered), "--destination", str(destination)],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["manifest_sha256"] == digest(
        destination / "manifest.json"
    )


def test_click_export_reports_overwrite_failure(
    recovered: Path, bundle: tuple[Path, str]
) -> None:
    directory, pin = bundle
    result = CliRunner().invoke(
        main,
        ["export", "--data-dir", str(recovered), "--destination", str(directory)],
    )
    assert result.exit_code != 0
    assert "occupied_output" in result.output
    assert digest(directory / "manifest.json") == pin


def test_click_verification_reports_a_valid_snapshot(bundle: tuple[Path, str]) -> None:
    directory, pin = bundle
    result = CliRunner().invoke(
        main, ["verify", "--bundle", str(directory), "--manifest-sha256", pin]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["passages"] == 13


def test_click_verification_reports_bad_pin(bundle: tuple[Path, str]) -> None:
    directory, _ = bundle
    result = CliRunner().invoke(
        main,
        ["verify", "--bundle", str(directory), "--manifest-sha256", "0" * 64],
    )
    assert result.exit_code != 0
    assert "manifest_pin" in result.output
