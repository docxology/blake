"""Release admission uses fresh outputs and the selected source evidence."""

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from blake.corpus.public_release import (
    write_public_release_package,
    write_public_release_preflight,
)
from blake.corpus.release_preflight import build_rights_gate_report
from tests.test_public_release import _seed_public_release_fixture


def options(root, *, output=None, release=None):
    output = output or root / "analysis_output"
    return {
        "project_root": root,
        "output_dir": output,
        "data_dir": root / "blake_data",
        "release_dir": release or output / "releases" / "fresh",
    }


def seed_matrix(root):
    source = (
        Path(__file__).resolve().parents[1]
        / "docs/manuscript/13_supplement_rights_matrix.md"
    )
    path = root / "docs/manuscript/13_supplement_rights_matrix.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(source.read_bytes())
    return path


def pending_lead(root, target="bb203"):
    path = root / "docs/source-leads.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "leads": [
                    {
                        "target_id": target,
                        "status": "manual_review",
                        "source_owner": "Synthetic library",
                        "url": "https://example.org/catalogue/pending",
                        "evidence_type": "text",
                        "direct_source_basis": "Unreviewed candidate only",
                        "scholarship_note": (
                            "No transcription comparison has been " "performed."
                        ),
                    }
                ]
            }
        )
    )
    manifest = root / "analysis_output/corpus_manifest.json"
    manifest.write_text(json.dumps({"target_records": []}))


@pytest.mark.parametrize(
    "occupied", ["directory", "file", "symlink", "dangling_symlink"]
)
def test_package_preserves_every_occupied_destination(tmp_path, occupied):
    _seed_public_release_fixture(tmp_path)
    destination = tmp_path / "retained-release"
    survivor = tmp_path / "original.bin"
    survivor.write_bytes(b"retained original evidence\x00")
    if occupied == "directory":
        destination.mkdir()
        survivor = destination / "original.bin"
        survivor.write_bytes(b"retained original evidence\x00")
    elif occupied == "file":
        destination.write_bytes(b"occupied file")
        survivor = destination
    else:
        destination.symlink_to(
            survivor if occupied == "symlink" else tmp_path / "missing"
        )
    before = survivor.read_bytes()
    prior_report = tmp_path / "analysis_output/reports/public_release_preflight.json"
    prior_report.write_bytes(b'{"prior_epoch":true}\n')
    with pytest.raises(FileExistsError):
        write_public_release_package(**options(tmp_path, release=destination))
    assert survivor.read_bytes() == before
    assert prior_report.read_bytes() == b'{"prior_epoch":true}\n'
    if occupied.endswith("symlink"):
        assert destination.is_symlink()


def test_occupied_destination_refuses_before_a_blocked_preflight(tmp_path):
    _seed_public_release_fixture(tmp_path)
    pending_lead(tmp_path)
    destination = tmp_path / "retained-release"
    destination.mkdir()
    sentinel = destination / "failed-attempt.json"
    sentinel.write_bytes(b'{"preserve":true}')
    with pytest.raises(FileExistsError):
        write_public_release_package(**options(tmp_path, release=destination))
    assert sentinel.read_bytes() == b'{"preserve":true}'


def test_package_rerun_preserves_the_first_complete_archive(tmp_path):
    _seed_public_release_fixture(tmp_path)
    kwargs = options(tmp_path)
    first = write_public_release_package(**kwargs)
    archive = Path(first["archive_path"])
    before = archive.read_bytes()
    with pytest.raises(FileExistsError):
        write_public_release_package(**kwargs)
    assert archive.read_bytes() == before


def test_package_refuses_a_symlink_parent_without_writing_through_it(tmp_path):
    _seed_public_release_fixture(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "linked-parent"
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="[Ss]ymlink"):
        write_public_release_package(**options(tmp_path, release=link / "fresh"))
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("territory", ["blake", "blake_data"])
def test_package_refuses_new_outputs_in_source_or_captured_data(tmp_path, territory):
    _seed_public_release_fixture(tmp_path)
    destination = tmp_path / territory / "fresh-release"
    with pytest.raises(ValueError, match="[Ss]ource|[Dd]ata|[Oo]verlap"):
        write_public_release_package(**options(tmp_path, release=destination))
    assert not destination.exists()


def test_rights_matrix_binds_the_actual_canonical_source(tmp_path):
    source = seed_matrix(tmp_path)
    legacy = tmp_path / "manuscript/13_supplement_rights_matrix.md"
    legacy.parent.mkdir()
    legacy.write_text("Unrelated legacy matrix must not override current source.")
    report = build_rights_gate_report(
        tmp_path,
        output_dir=tmp_path / "analysis_output",
        data_dir=tmp_path / "blake_data",
    )
    assert all(row["rights_matrix_row_found"] for row in report["artifact_classes"])
    assert Path(report["rights_matrix_path"]) == source
    assert report["rights_matrix_source"] == {
        "path": "docs/manuscript/13_supplement_rights_matrix.md",
        "status": "available",
        "bytes": source.stat().st_size,
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }


def test_rights_matrix_missing_is_explicit_not_a_legacy_substitution(tmp_path):
    legacy = tmp_path / "manuscript/13_supplement_rights_matrix.md"
    legacy.parent.mkdir()
    legacy.write_text(
        "Project code, tests, scripts, and project-authored documentation"
    )
    report = build_rights_gate_report(
        tmp_path,
        output_dir=tmp_path / "analysis_output",
        data_dir=tmp_path / "blake_data",
    )
    assert not any(row["rights_matrix_row_found"] for row in report["artifact_classes"])
    assert report["rights_matrix_source"] == {
        "path": "docs/manuscript/13_supplement_rights_matrix.md",
        "status": "missing",
        "bytes": None,
        "sha256": None,
    }
    assert report["status"] == "blocked_for_public_redistribution"


def test_rights_matrix_refuses_a_symlink_source(tmp_path):
    source = seed_matrix(tmp_path)
    original = source.read_bytes()
    other = tmp_path / "other-matrix.md"
    other.write_bytes(original)
    source.unlink()
    source.symlink_to(other)
    with pytest.raises(ValueError, match="[Ss]ymlink"):
        build_rights_gate_report(
            tmp_path,
            output_dir=tmp_path / "analysis_output",
            data_dir=tmp_path / "blake_data",
        )
    assert other.read_bytes() == original


def test_selected_output_epoch_controls_evidence_and_copied_bytes(tmp_path):
    root = tmp_path / "project"
    _seed_public_release_fixture(root)
    selected = tmp_path / "private-selected-epoch"
    selected.mkdir()
    selected_bytes = json.dumps(
        {
            "target_records": [
                {"target_id": "bb203", "matched_source_ids": ["selected:bb203"]}
            ],
            "epoch": "selected",
        }
    ).encode()
    (selected / "corpus_manifest.json").write_bytes(selected_bytes)
    (selected / "reports").mkdir()
    (selected / "reports/selected.json").write_text('{"epoch":"selected"}')
    (root / "analysis_output/reports/stale.json").write_text('{"epoch":"stale"}')
    report = write_public_release_preflight(**options(root, output=selected))
    record = report["corroboration"]["validated_targets"][0]
    assert record["corroborating_sources"][0]["source_id"] == "selected:bb203"
    assert report["corroboration"]["source_manifest"] == {
        "path": "analysis_output/corpus_manifest.json",
        "status": "available",
        "bytes": len(selected_bytes),
        "sha256": hashlib.sha256(selected_bytes).hexdigest(),
    }
    assert str(selected) not in json.dumps(report["corroboration"])
    package = write_public_release_package(**options(root, output=selected))
    with zipfile.ZipFile(package["archive_path"]) as archive:
        assert archive.read("analysis_output/corpus_manifest.json") == selected_bytes
        assert "analysis_output/reports/selected.json" in archive.namelist()
        assert "analysis_output/reports/stale.json" not in archive.namelist()
        for name in archive.namelist():
            if name.endswith((".json", ".md", ".txt", ".cff")):
                assert str(selected) not in archive.read(name).decode("utf-8")


def test_manual_review_lead_remains_pending_and_returns_a_blocked_report(tmp_path):
    _seed_public_release_fixture(tmp_path)
    pending_lead(tmp_path)
    report = write_public_release_preflight(**options(tmp_path))
    record = report["corroboration"]["validated_targets"][0]
    assert record["status"] == "needs_secondary_citation"
    assert (
        record["corroborating_sources"][0]["evidence_role"]
        == "candidate_text_bearing_lead"
    )
    assert record["corroborating_sources"][0]["review_status"] == "manual_review"
    assert report["status"] == "blocked"
    assert report["blocked_reasons"]
    assert report["corroborated_fallback_target_count"] == 0
    assert report["corroboration"]["validated_target_count"] == 1
    assert report["corroboration"]["corroborated_target_count"] == 0
    assert report["corroboration"]["unresolved_target_count"] == 1


def test_unresolved_corroboration_package_retains_a_blocked_attempt(tmp_path):
    _seed_public_release_fixture(tmp_path)
    pending_lead(tmp_path)
    package = write_public_release_package(**options(tmp_path))
    assert package["status"] == "blocked"
    assert package["blocked_reasons"]
    assert Path(package["package_summary_path"]).is_file()
    assert not (Path(package["release_dir"]) / "public_release_bundle.zip").exists()


def test_contextual_identity_match_does_not_claim_text_comparison(tmp_path):
    _seed_public_release_fixture(tmp_path)
    report = write_public_release_preflight(**options(tmp_path))
    record = report["corroboration"]["validated_targets"][0]
    assert record["status"] == "ready"
    assert (
        record["corroborating_sources"][0]["evidence_role"] == "contextual_target_match"
    )
    assert record["corroborating_sources"][0]["text_bearing"] is False
    assert "target identity" in record["note"]
    assert report["corroboration"]["corroborated_target_count"] == 1


@pytest.mark.parametrize("alias_kind", ["source", "data"])
def test_destination_overlap_compares_resolved_input_roots(tmp_path, alias_kind):
    root = tmp_path / "project"
    _seed_public_release_fixture(root)
    alias = tmp_path / "input-alias"
    if alias_kind == "source":
        alias.symlink_to(root, target_is_directory=True)
        kwargs = options(root, release=root / "blake/fresh-release")
        kwargs["project_root"] = alias
    else:
        alias.symlink_to(root / "blake_data", target_is_directory=True)
        kwargs = options(root, release=root / "blake_data/fresh-release")
        kwargs["data_dir"] = alias
    sentinel = root / "blake_data/texts/bb203.txt"
    original = sentinel.read_bytes()
    with pytest.raises(ValueError, match="[Ss]ource|[Dd]ata|[Oo]verlap"):
        write_public_release_package(**kwargs)
    assert sentinel.read_bytes() == original
    assert not kwargs["release_dir"].exists()


@pytest.mark.parametrize(
    "selection", ["data", "source", "project", "ancestor", "symlink"]
)
def test_analytical_root_refuses_source_data_overlap_before_any_writes(
    tmp_path, selection
):
    root = tmp_path / "project"
    _seed_public_release_fixture(root)
    sentinel = root / "blake_data/texts/bb203.txt"
    before = sentinel.read_bytes()
    if selection == "data":
        output = root / "blake_data"
    elif selection == "source":
        output = root / "blake"
    elif selection == "project":
        output = root
    elif selection == "ancestor":
        output = tmp_path
    else:
        real = tmp_path / "separate-analysis"
        real.mkdir()
        output = tmp_path / "analysis-alias"
        output.symlink_to(real, target_is_directory=True)
    public_report = output / "reports/public_release_preflight.json"
    assert not public_report.exists()
    with pytest.raises(ValueError, match="[Ss]ymlink|[Ss]ource|[Dd]ata|[Oo]verlap"):
        write_public_release_preflight(**options(root, output=output))
    assert sentinel.read_bytes() == before
    assert not public_report.exists()
    assert not (output / "releases/fresh").exists()


@pytest.mark.parametrize(
    "records",
    [
        [{"target_id": "bb203", "matched_source_ids": "archive:bb203"}],
        [{"target_id": "bb203", "matched_source_ids": {"archive:bb203": True}}],
        *[
            [{"target_id": "bb203", "matched_source_ids": [value]}]
            for value in [None, 1, True, "", "   "]
        ],
        [
            {
                "target_id": "bb203",
                "matched_source_ids": ["archive:bb203", "archive:bb203"],
            }
        ],
        [
            {"target_id": "bb203", "matched_source_ids": []},
            {"target_id": "bb203", "matched_source_ids": ["archive:bb203"]},
        ],
        [{"target_id": 203, "matched_source_ids": ["archive:bb203"]}],
        [{"target_id": "   ", "matched_source_ids": ["archive:bb203"]}],
    ],
)
def test_selected_manifest_refuses_ambiguous_corroboration_before_copy(
    tmp_path, records
):
    _seed_public_release_fixture(tmp_path)
    manifest = tmp_path / "analysis_output/corpus_manifest.json"
    manifest.write_text(json.dumps({"target_records": records}))
    captured = tmp_path / "blake_data/texts/bb203.txt"
    before = captured.read_bytes()
    kwargs = options(tmp_path)
    with pytest.raises(ValueError, match="[Mm]anifest|[Ss]ource|[Tt]arget"):
        write_public_release_package(**kwargs)
    assert captured.read_bytes() == before
    assert not (kwargs["release_dir"] / "public_release_bundle.zip").exists()


@pytest.mark.parametrize("sources", [{}, {"matched_source_ids": []}])
def test_absent_or_empty_secondary_identity_stays_unresolved(tmp_path, sources):
    _seed_public_release_fixture(tmp_path)
    manifest = tmp_path / "analysis_output/corpus_manifest.json"
    manifest.write_text(
        json.dumps({"target_records": [{"target_id": "bb203", **sources}]})
    )
    report = write_public_release_preflight(**options(tmp_path))
    assert report["status"] == "blocked"
    assert report["corroborated_fallback_target_count"] == 0
    assert (
        report["corroboration"]["validated_targets"][0]["status"]
        == "needs_secondary_citation"
    )


def test_mixed_corroboration_counts_only_the_contextually_matched_target(tmp_path):
    _seed_public_release_fixture(tmp_path)
    pending_lead(tmp_path, target="bb204")
    manifest = tmp_path / "analysis_output/corpus_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "target_records": [
                    {"target_id": "bb203", "matched_source_ids": ["archive:bb203"]}
                ]
            }
        )
    )
    original = tmp_path / "blake_data/texts/bb203.txt"
    (original.parent / "bb204.txt").write_bytes(original.read_bytes())
    first_marker = tmp_path / "blake_data/metadata/fallback_text_validations/bb203.json"
    second_marker = json.loads(first_marker.read_bytes())
    second_marker["target_id"] = "bb204"
    (first_marker.parent / "bb204.json").write_text(json.dumps(second_marker))
    report = write_public_release_preflight(**options(tmp_path))
    assert report["status"] == "blocked"
    assert report["corroboration"]["validated_target_count"] == 2
    assert report["corroboration"]["unresolved_target_count"] == 1
    assert report["corroborated_fallback_target_count"] == 1


def test_fresh_code_only_package_needs_no_corpus_evidence(tmp_path):
    root = tmp_path / "software-only"
    root.mkdir()
    (root / "LICENSE").write_text("MIT")
    (root / "README.md").write_text("Synthetic code-only release")
    (root / "pyproject.toml").write_text(
        'Repository = "https://github.com/docxology/blake"\n'
    )
    (root / "blake").mkdir()
    (root / "blake/__init__.py").write_text("VALUE = 1\n")
    selected = tmp_path / "new-analysis"
    package = write_public_release_package(**options(root, output=selected))
    assert package["status"] == "ready"
    assert package["corroborated_fallback_target_count"] == 0
    with zipfile.ZipFile(package["archive_path"]) as archive:
        assert archive.read("README.md") == b"Synthetic code-only release"
        assert "blake/__init__.py" in archive.namelist()
