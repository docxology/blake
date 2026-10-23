from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from blake.recovery import RecoveryError, main, recover_corpus, verify_recovery
from blake.recovery_backup import (
    backup_recovery,
    restore_backup,
    restore_drill,
    verify_backup,
)
from .recovery_fixtures import COMMIT, seed_sources


@pytest.fixture
def saved_sources(tmp_path: Path) -> Path:
    return seed_sources(tmp_path)


def test_bundle_when_restored_without_network_recreates_every_inventoried_byte(
    saved_sources: Path, tmp_path: Path
) -> None:
    original = recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)
    bundle = backup_recovery(saved_sources)
    destination = tmp_path / "restored"

    receipt = restore_backup(bundle, destination)

    assert verify_recovery(destination) == original
    assert len(receipt.restored) == len(original.files) + 1
    assert not receipt.quarantine
    assert verify_backup(bundle) == original
    assert backup_recovery(saved_sources) == bundle


def test_restore_when_local_bytes_are_corrupted_preserves_damage_and_restores_original(
    saved_sources: Path,
) -> None:
    original = recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)
    bundle = backup_recovery(saved_sources)
    target = saved_sources / "recovery/texts/archive/mhh.a.txt"
    target.write_bytes(b"damaged reading layer")
    source = saved_sources / "recovery" / original.files[0].path
    source.unlink()
    with pytest.raises(RecoveryError):
        verify_recovery(saved_sources)

    repaired = restore_backup(bundle, saved_sources)

    assert verify_recovery(saved_sources) == original
    assert len(repaired.quarantine) == 1
    assert (
        saved_sources / "recovery" / repaired.quarantine[0]
    ).read_bytes() == b"damaged reading layer"
    assert "texts/archive/mhh.a.txt" in repaired.restored
    assert target.read_text() == "Eternity is in love\nwith time."


def test_backup_when_outer_bytes_change_refuses_before_touching_destination(
    saved_sources: Path, tmp_path: Path
) -> None:
    recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)
    bundle = backup_recovery(saved_sources)
    with bundle.open("r+b") as handle:
        handle.seek(600)
        handle.write(b"mutated")
    destination = tmp_path / "refused"

    with pytest.raises(RecoveryError, match="SHA-256 mismatch"):
        restore_backup(bundle, destination)

    assert not destination.exists()


@pytest.mark.parametrize(
    "problem",
    ["traversal", "symlink", "extra", "omission", "member_corruption", "duplicate"],
)
def test_backup_when_member_inventory_is_unsafe_or_incomplete_refuses(
    saved_sources: Path, tmp_path: Path, problem: str
) -> None:
    recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)
    original = backup_recovery(saved_sources)
    altered = tmp_path / "altered.tar"
    with tarfile.open(original) as source, tarfile.open(altered, "w") as output:
        for member in source.getmembers():
            if problem == "omission" and member.name == "search.sqlite":
                continue
            body = source.extractfile(member).read()
            if problem == "member_corruption" and member.name == "search.sqlite":
                body = b"x" * len(body)
            output.addfile(member, io.BytesIO(body))
            if problem == "duplicate" and member.name == "search.sqlite":
                output.addfile(member, io.BytesIO(body))
        if problem in {"traversal", "symlink", "extra"}:
            extra = tarfile.TarInfo("../escaped" if problem == "traversal" else "extra")
            if problem == "symlink":
                extra.type = tarfile.SYMTYPE
                extra.linkname = "../../outside"
            output.addfile(extra)
    digest = hashlib.sha256(altered.read_bytes()).hexdigest()

    with pytest.raises(RecoveryError):
        restore_backup(altered, tmp_path / "destination", expected_sha256=digest)

    assert not (tmp_path / "destination").exists()
    assert not (tmp_path / "escaped").exists()


def test_restore_when_already_intact_is_idempotent(saved_sources: Path) -> None:
    manifest = recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)
    bundle = backup_recovery(saved_sources)

    result = restore_backup(bundle, saved_sources)

    assert not result.restored
    assert not result.quarantine
    assert len(result.unchanged) == len(manifest.files) + 1


def test_backup_when_receipt_is_missing_requires_independent_checksum(
    saved_sources: Path,
) -> None:
    recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)
    bundle = backup_recovery(saved_sources)
    metadata = json.loads(bundle.with_name(bundle.name + ".json").read_text())
    bundle.with_name(bundle.name + ".json").unlink()

    with pytest.raises(RecoveryError, match="independent SHA-256"):
        verify_backup(bundle)

    assert (
        verify_backup(bundle, expected_sha256=metadata["sha256"]).archive_commit
        == COMMIT
    )


def test_cli_when_bundle_is_created_verified_and_restored_runs_end_to_end(
    saved_sources: Path, tmp_path: Path
) -> None:
    recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)
    runner = CliRunner()
    created = runner.invoke(main, ["backup", "--data-dir", str(saved_sources)])
    assert created.exit_code == 0, created.output
    bundle = json.loads(created.output)["backup"]

    verified = runner.invoke(main, ["verify-backup", bundle])
    restored = runner.invoke(
        main, ["restore", bundle, "--data-dir", str(tmp_path / "restored")]
    )

    assert verified.exit_code == restored.exit_code == 0
    assert json.loads(restored.output)["restored"]
    assert verify_recovery(tmp_path / "restored").archive_commit == COMMIT


def test_cli_when_backup_or_restore_inputs_are_bad_returns_failure(
    saved_sources: Path, tmp_path: Path
) -> None:
    runner = CliRunner()
    empty = runner.invoke(main, ["backup", "--data-dir", str(saved_sources)])
    assert empty.exit_code != 0
    recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)
    bundle = backup_recovery(saved_sources)
    with bundle.open("r+b") as handle:
        handle.seek(500)
        handle.write(b"corrupted")

    for arguments in (
        ["verify-backup", str(bundle)],
        ["restore", str(bundle), "--data-dir", str(tmp_path / "refused")],
    ):
        result = runner.invoke(main, arguments)
        assert result.exit_code != 0
        assert "SHA-256 mismatch" in result.output
    assert not (tmp_path / "refused").exists()


def test_restore_drill_when_copy_is_fresh_proves_negative_control_and_repair(
    saved_sources: Path, tmp_path: Path
) -> None:
    manifest = recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)
    bundle = backup_recovery(saved_sources)
    destination = tmp_path / "drill"

    result = restore_drill(bundle, destination)

    assert result.files_verified == len(manifest.files)
    assert "Checksum mismatch" in result.detection_error
    assert result.repaired_files == (result.corrupted_path,)
    assert len(result.quarantine) == 1
    assert (
        destination / "recovery" / result.quarantine[0]
    ).read_bytes() == b"DELIBERATE RECOVERY NEGATIVE CONTROL\n"
    assert verify_recovery(destination) == manifest


def test_restore_drill_when_destination_has_user_files_refuses(
    saved_sources: Path, tmp_path: Path
) -> None:
    recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)
    bundle = backup_recovery(saved_sources)
    destination = tmp_path / "occupied"
    destination.mkdir()
    (destination / "owned.txt").write_text("preserve")

    with pytest.raises(RecoveryError, match="empty destination"):
        restore_drill(bundle, destination)

    assert (destination / "owned.txt").read_text() == "preserve"


def test_restore_drill_cli_when_finished_writes_a_durable_receipt(
    saved_sources: Path, tmp_path: Path
) -> None:
    recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)
    bundle = backup_recovery(saved_sources)
    runner = CliRunner()
    destination = tmp_path / "drill-cli"

    result = runner.invoke(
        main, ["restore-drill", str(bundle), "--destination", str(destination)]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == json.loads(
        (destination / "restore_drill.json").read_text()
    )
    refused = runner.invoke(
        main, ["restore-drill", str(bundle), "--destination", str(destination)]
    )
    assert refused.exit_code != 0
