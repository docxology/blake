"""Negative controls for component errors and manuscript evidence boundaries."""

import json
from pathlib import Path

import pytest

from manuscript_tools.publication import (
    component_errors,
    publication_tokens,
    validate_manuscript_tokens,
    verify_publication_recovery,
    write_publication_evidence,
)
from blake.corpus.saved_epoch import file_sha256


def test_component_errors_do_not_confuse_top_level_completion_with_availability():
    records = [
        {
            "work_id": "a",
            "results": {
                "error": "work failed",
                "text_analysis": {
                    "topics": {"error": "Insufficient text"},
                    "sentiment": {"error": "unavailable"},
                },
                "visual_analysis": [{"error": "bad image"}],
            },
        },
        {
            "work_id": "b",
            "results": {"text_analysis": {"error": "top-level type failure"}},
        },
    ]
    errors = component_errors(records)
    assert {row["path"] for row in errors} == {
        "text_analysis.topics",
        "text_analysis.sentiment",
        "visual_analysis.0",
    }
    assert len(errors) == 3
    with pytest.raises(ValueError, match="Duplicate"):
        component_errors(records + [records[0]])


def test_required_publication_evidence_cannot_silently_disappear(tmp_path):
    assert publication_tokens(tmp_path, required=False) == {}
    with pytest.raises(ValueError, match="missing"):
        publication_tokens(tmp_path, required=True)
    path = tmp_path / "analysis_output/data/publication_evidence.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"schema_version": True}))
    with pytest.raises(ValueError, match="schema"):
        publication_tokens(tmp_path, required=True)


def test_manuscript_token_gate_rejects_unknown_or_empty_values(tmp_path):
    (tmp_path / "00_abstract.md").write_text("A result: {{COUNT}}; {{DIGEST}}")
    (tmp_path / "AGENTS.md").write_text("Example {{IGNORED}}")
    validate_manuscript_tokens(tmp_path, {"COUNT": "0", "DIGEST": "known"})
    with pytest.raises(ValueError, match="DIGEST"):
        validate_manuscript_tokens(tmp_path, {"COUNT": "0"})
    with pytest.raises(ValueError, match="COUNT"):
        validate_manuscript_tokens(tmp_path, {"COUNT": "", "DIGEST": "known"})


@pytest.fixture
def sealed_fixture(tmp_path):
    """A tiny real offline recovery, backup and corruption drill, never corpus evidence."""
    from blake.recovery import recover_corpus, register_recovery
    from blake.recovery_backup import backup_recovery, restore_drill
    from blake.text_search.recovered import build_recovered_search
    from blake.metadata.database import MetadataDatabase
    from manuscript_tools.epoch import prepare_analysis_epoch
    from tests.recovery_fixtures import COMMIT, seed_sources

    seeded = seed_sources(tmp_path / "seed")
    data = tmp_path / "blake_data"
    seeded.rename(data)
    capture = recover_corpus(data, commit=COMMIT, offline=True, images=False)
    register_recovery(data)
    bundle = backup_recovery(data)
    restore_drill(bundle, data / "restore-check")
    build_recovered_search(data)
    store = prepare_analysis_epoch(tmp_path, "blake_data/publication/test")
    works = MetadataDatabase(store / "metadata/metadata.db").load_all_works()
    output = tmp_path / "analysis_output"
    (output / "analysis").mkdir(parents=True)
    pipeline = {
        "run_id": "synthetic-publication",
        "status": "completed",
        "started_at": "2026-10-23T00:00:00",
    }
    summary = {
        "status": "completed",
        "analysis_results_current": True,
        "works_total": len(works),
    }
    manifest = {
        "run_id": pipeline["run_id"],
        "data_dir": str(store.relative_to(tmp_path)),
        "total_works": len(works),
        "total_images": 0,
        "work_records": [{"id": work.id} for work in works],
    }
    records = [
        {
            "work_id": work.id,
            "results": {
                "text_analysis": {
                    "topics": {"error": "Insufficient text for topic modeling"}
                }
            },
        }
        for work in works
    ]
    for name, value in {
        "pipeline_summary.json": pipeline,
        "corpus_manifest.json": manifest,
        "analysis/analysis_summary.json": summary,
        "analysis/analysis_results.json": records,
    }.items():
        (output / name).write_text(json.dumps(value))
    protected = {
        name: file_sha256(data / name)
        for name in (
            "recovery/manifest.json",
            "recovery/search.sqlite",
            "recovery/passages.jsonl",
            "metadata/metadata.db",
        )
    }
    run = {
        "status": "completed",
        "protected_before": protected,
        "protected_after": dict(protected),
        "pipeline": pipeline,
        "analysis_summary": summary,
        "software_at_analysis": "test-producer",
        "seed": 7,
    }
    integrity = verify_publication_recovery(tmp_path)
    path = write_publication_evidence(tmp_path, run, integrity)
    return tmp_path, run, integrity, path


def test_publication_seal_derives_counts_from_verified_real_files(sealed_fixture):
    root, run, integrity, path = sealed_fixture
    tokens = publication_tokens(root, required=True)
    assert tokens["RECOVERY_FILES"] == str(integrity["files"])
    assert tokens["RECOVERY_READING_RECORDS"] == "4"
    assert tokens["RECOVERY_PRIMARY_RECORDS"] == "3"
    assert tokens["RECOVERY_UNVERIFIED_RECORDS"] == "1"
    assert tokens["UNIQUE_IMAGE_FILES"] == "0"
    assert tokens["ANALYSIS_NESTED_ERROR_COUNT"] == "6"
    assert integrity["retained_corruption_differs"] is True


@pytest.mark.parametrize(
    "problem,reason",
    [
        ("tokens", "token values differ"),
        ("bindings", "incomplete"),
        ("run", "different saved"),
        ("source", "input changed"),
        ("token_type", "invalid token"),
    ],
)
def test_publication_reader_refuses_tampered_claims_or_inputs(
    sealed_fixture, problem, reason
):
    root, run, integrity, path = sealed_fixture
    evidence = json.loads(path.read_text())
    if problem == "tokens":
        evidence["tokens"]["RECOVERY_FILES"] = "99999"
    elif problem == "bindings":
        evidence["bindings"].pop(next(iter(evidence["bindings"])))
    elif problem == "run":
        evidence["run_id"] = "different"
    elif problem == "source":
        (root / "blake_data/recovery/manifest.json").write_text("{}")
    else:
        evidence["tokens"]["RECOVERY_FILES"] = 99
    path.write_text(json.dumps(evidence))
    with pytest.raises(ValueError, match=reason):
        publication_tokens(root, required=True)


@pytest.mark.parametrize(
    "problem,reason",
    [
        ("run_status", "requires completed"),
        ("integrity_status", "requires completed"),
        ("protection", "all captured"),
        ("source_change", "changed during"),
        ("population", "membership differs"),
        ("transcription", "transcription differs"),
    ],
)
def test_publication_writer_refuses_unqualified_or_mismatched_inputs(
    sealed_fixture, problem, reason
):
    root, run, integrity, path = sealed_fixture
    if problem == "run_status":
        run["status"] = "error"
    elif problem == "integrity_status":
        integrity["status"] = "error"
    elif problem == "protection":
        run["protected_before"] = {}
    elif problem == "source_change":
        run["protected_after"]["metadata/metadata.db"] = "0" * 64
    else:
        store = (
            root
            / json.loads((root / "analysis_output/corpus_manifest.json").read_text())[
                "data_dir"
            ]
        )
        inputs_path = store / "epoch-inputs.json"
        inputs = json.loads(inputs_path.read_text())
        if problem == "population":
            inputs["works"].pop()
        else:
            next(row for row in inputs["works"] if row["has_text"])["text_sha256"] = (
                "0" * 64
            )
        inputs_path.write_text(json.dumps(inputs))
    with pytest.raises(ValueError, match=reason):
        write_publication_evidence(root, run, integrity)
