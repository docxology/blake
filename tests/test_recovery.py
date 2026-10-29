from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from blake.recovery_models import RecoveryError
from blake.recovery_pipeline import recover_corpus
from blake.recovery_commands import main
from blake.recovery_integrity import verify_recovery
from blake.text_search import PassageIndex, Query

from .recovery_fixtures import COMMIT
from tests import recovery_fixtures

saved_sources = recovery_fixtures.saved_sources


def test_recovery_when_source_collections_include_copies_and_variants(
    saved_sources: Path,
) -> None:
    manifest = recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)

    assert manifest.source_recovery_status == "complete"
    assert manifest.oeuvre_coverage_status == "not_established"
    assert len(manifest.copies) == 6
    assert len({c.document_id for c in manifest.copies}) == 6
    assert sum(c.copy_id == "mhh.a" for c in manifest.copies) == 2
    assert sum(c.extraction_error is not None for c in manifest.copies) == 1
    assert manifest.erdman_page_ids == ("I", "1", "3O2")
    assert manifest.images.expected == 2
    assert manifest.images.downloaded == 0
    assert manifest.images.status == "incomplete"
    assert verify_recovery(saved_sources) == manifest


def test_search_when_recovery_has_editorial_and_other_author_decoys(
    saved_sources: Path,
) -> None:
    recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)
    index = PassageIndex(saved_sources / "recovery/search.sqlite")

    assert index.search(Query(text="state")).total_occurrences == 2
    assert index.search(Query(text="EDITORIAL")).total_occurrences == 0
    assert index.search(Query(text="federation")).total_occurrences == 0
    assert (
        index.search(
            Query(text="Eternity is in love with time", mode="phrase")
        ).total_occurrences
        == 1
    )


def test_recovery_when_offline_rerun_preserves_sources(saved_sources: Path) -> None:
    before = recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)
    expected = {f.path: f.sha256 for f in before.files if f.path != "search.sqlite"}

    after = recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)

    assert {
        f.path: f.sha256 for f in after.files if f.path != "search.sqlite"
    } == expected
    assert [c.document_id for c in before.copies] == [
        c.document_id for c in after.copies
    ]


def test_recover_when_sources_are_missing_does_not_claim_success(
    tmp_path: Path,
) -> None:
    with pytest.raises(RecoveryError, match="Offline recovery requires"):
        recover_corpus(tmp_path, commit=COMMIT, offline=True)

    assert not (tmp_path / "recovery/manifest.json").exists()


def test_recover_when_revision_is_not_immutable_rejects(tmp_path: Path) -> None:
    with pytest.raises(RecoveryError, match="full 40-character"):
        recover_corpus(tmp_path, commit="master", offline=True)


def test_cli_when_saved_sources_exist_recovers_and_verifies(
    saved_sources: Path,
) -> None:
    prefix = [sys.executable, "-m", "blake.recovery_commands"]
    process = subprocess.run(
        [
            *prefix,
            "recover",
            "--data-dir",
            str(saved_sources),
            "--commit",
            COMMIT,
            "--offline",
            "--no-images",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    verified = subprocess.run(
        [*prefix, "verify", "--data-dir", str(saved_sources)],
        capture_output=True,
        text=True,
        check=True,
    )

    assert json.loads(process.stdout)["verified_files"] > 10
    assert json.loads(verified.stdout)["archive_copy_documents"] == 6


def test_commands_when_recovery_is_valid_and_then_corrupted_reports_errors(
    saved_sources: Path,
) -> None:
    runner = CliRunner()
    arguments = ["--data-dir", str(saved_sources)]
    recovered = runner.invoke(
        main, ["recover", *arguments, "--commit", COMMIT, "--offline", "--no-images"]
    )
    verified = runner.invoke(main, ["verify", *arguments])
    registered = runner.invoke(main, ["register", *arguments])

    assert recovered.exit_code == verified.exit_code == registered.exit_code == 0
    assert json.loads(registered.output)["registered_documents"] == 6

    (saved_sources / "recovery/texts/archive/mhh.a.txt").write_bytes(b"mutated source")
    for command in ("recover", "verify", "register"):
        result = runner.invoke(main, [command, *arguments])
        assert result.exit_code != 0
        assert "Checksum mismatch" in result.output
