"""Real SQLite epochs and tampered files exercise dashboard admission."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from blake.corpus.saved_epoch import file_sha256, load_saved_analysis_epoch
from blake.metadata.database import MetadataDatabase
from manuscript_tools.epoch import prepare_analysis_epoch
from tests.gui_fixtures import app_source, seed_gui


def seed_epoch(root: Path):
    data, output = root / "blake_data", root / "analysis_output"
    seed_gui(data)
    store = prepare_analysis_epoch(root, "blake_data/publication/saved")
    database = MetadataDatabase(store / "metadata/metadata.db")
    works = database.load_all_works()
    for work in works:
        work.fully_processed = True
        work.metadata.processed = True
        database.save_work(work)
    (output / "analysis").mkdir(parents=True)
    (output / "data").mkdir()
    payloads = {
        "pipeline_summary.json": {
            "run_id": "saved-epoch",
            "status": "completed",
            "started_at": "2026-10-23T00:00:00",
        },
        "corpus_manifest.json": {
            "run_id": "saved-epoch",
            "data_dir": str(store.relative_to(root)),
            "total_works": 2,
            "total_images": 4,
            "work_records": [{"id": work.id} for work in works],
        },
        "analysis/analysis_summary.json": {
            "status": "completed",
            "analysis_results_current": True,
            "works_total": 2,
        },
        "analysis/analysis_results.json": [
            {
                "work_id": work.id,
                "results": {
                    "text_analysis": {
                        "topics": {"error": "Insufficient text for topic modeling"}
                    }
                },
            }
            for work in works
        ],
    }
    for relative, payload in payloads.items():
        (output / relative).write_text(json.dumps(payload))
    paths = [output / name for name in payloads] + [
        store / "metadata/metadata.db",
        store / "epoch-inputs.json",
        data / "metadata/metadata.db",
    ]
    receipt = {
        "schema_version": 1,
        "run_id": "saved-epoch",
        "data_dir": str(store.relative_to(root)),
        "analysis_software_version": "test-producer",
        "seed": 7,
        "nested_error_count": 2,
        "bindings": {str(path.relative_to(root)): file_sha256(path) for path in paths},
    }
    (output / "data/publication_epoch.json").write_text(json.dumps(receipt))
    return data, output, store, receipt


def test_saved_epoch_loads_the_separate_completed_database(tmp_path):
    data, output, store, receipt = seed_epoch(tmp_path)
    original = (data / "metadata/metadata.db").read_bytes()
    result = load_saved_analysis_epoch(data, output)
    assert result["store"] == store
    assert result["run_id"] == receipt["run_id"]
    assert (data / "metadata/metadata.db").read_bytes() == original
    app = AppTest.from_string(app_source(data, output), default_timeout=20).run()
    assert list(app.exception) == []
    processed = next(
        metric for metric in app.metric if metric.label == "Processed records"
    )
    assert processed.value == "2"
    assert any("test-producer" in message.value for message in app.info)
    assert any("2 unavailable sub-analysis" in message.value for message in app.caption)


@pytest.mark.parametrize(
    "problem",
    [
        "schema",
        "identity",
        "seed",
        "bindings",
        "store",
        "run",
        "status",
        "population",
        "source_database",
        "manifest_store",
        "changed_file",
        "symlink",
        "text_changed",
        "membership",
        "modality",
    ],
)
def test_saved_epoch_rejects_invalid_or_changed_evidence(tmp_path, problem):
    data, output, store, receipt = seed_epoch(tmp_path)
    if problem == "schema":
        receipt["schema_version"] = True
    elif problem == "identity":
        receipt.pop("analysis_software_version")
    elif problem == "seed":
        receipt["seed"] = True
    elif problem == "bindings":
        receipt["bindings"].pop(next(iter(receipt["bindings"])))
    elif problem == "store":
        receipt["data_dir"] = "elsewhere"
    elif problem == "run":
        receipt["run_id"] = "different"
    elif problem in {"status", "population", "manifest_store"}:
        relative = (
            "analysis/analysis_summary.json"
            if problem != "manifest_store"
            else "corpus_manifest.json"
        )
        path = output / relative
        value = json.loads(path.read_text())
        if problem == "status":
            value["analysis_results_current"] = False
        elif problem == "population":
            value["works_total"] = 99
        else:
            value["data_dir"] = "blake_data/publication/other"
        path.write_text(json.dumps(value))
        receipt["bindings"][str(path.relative_to(tmp_path))] = file_sha256(path)
    elif problem == "source_database":
        path = store / "epoch-inputs.json"
        value = json.loads(path.read_text())
        value["source_metadata_sha256"] = "0" * 64
        path.write_text(json.dumps(value))
        receipt["bindings"][str(path.relative_to(tmp_path))] = file_sha256(path)
    elif problem == "changed_file":
        (output / "analysis/analysis_results.json").write_text("[]")
    elif problem == "text_changed":
        (store / "texts/rich.txt").write_text("Different source expression")
    elif problem in {"membership", "modality"}:
        path = store / "epoch-inputs.json"
        value = json.loads(path.read_text())
        if problem == "membership":
            value["works"].append(value["works"][0])
        else:
            value["works"][0]["has_text"] = "yes"
        path.write_text(json.dumps(value))
        receipt["bindings"][str(path.relative_to(tmp_path))] = file_sha256(path)
    else:
        path = output / "analysis/analysis_results.json"
        moved = tmp_path / "moved-results.json"
        path.rename(moved)
        path.symlink_to(moved)
    (output / "data/publication_epoch.json").write_text(json.dumps(receipt))
    reason = {
        "schema": "Unsupported",
        "identity": "identity",
        "seed": "integer seed",
        "bindings": "incomplete",
        "store": "outside",
        "run": "identities",
        "status": "completed and current",
        "population": "population",
        "source_database": "different captured",
        "manifest_store": "different analysis store",
        "changed_file": "changed",
        "symlink": "Symlink",
        "text_changed": "transcription changed",
        "membership": "membership",
        "modality": "modality",
    }[problem]
    with pytest.raises(ValueError, match=reason):
        load_saved_analysis_epoch(data, output)


def test_absent_epoch_is_distinct_from_a_failed_receipt(tmp_path):
    assert load_saved_analysis_epoch(tmp_path / "data", tmp_path / "out") is None


def test_dashboard_discloses_a_changed_epoch_and_browses_captured_records(tmp_path):
    data, output, store, receipt = seed_epoch(tmp_path)
    (output / "analysis/analysis_results.json").write_text("[]")
    app = AppTest.from_string(app_source(data, output), default_timeout=20).run()
    assert list(app.exception) == []
    assert any(
        "Saved analysis unavailable" in message.value
        and "Browsing captured records" in message.value
        for message in app.warning
    )
