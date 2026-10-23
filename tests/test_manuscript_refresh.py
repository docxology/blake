"""Real SQLite recovery refuses conflicting and ambiguous analysis payloads."""

import json

import pytest

from blake.corpus.saved_epoch import validate_derived_epoch
from blake.metadata.database import MetadataDatabase
from manuscript_tools.refresh import restore_analysis_results
from tests.gui_fixtures import seed_gui


def test_derived_receipt_and_outputs_are_bound_to_the_saved_model_run(tmp_path):
    from tests.test_saved_analysis_epoch import seed_epoch
    from blake.corpus.saved_epoch import file_sha256, load_saved_analysis_epoch

    data, output, store, epoch = seed_epoch(tmp_path)
    paths = [store / "metadata/metadata.db"]
    for name in ("reports", "visualizations"):
        path = output / name / "theme_entity_network.json"
        path.parent.mkdir()
        path.write_text('{"nodes": [], "edges": []}')
        paths.append(path)
    receipt = {
        "schema_version": 1,
        "status": "completed",
        "run_id": epoch["run_id"],
        "model_inference_repeated": False,
        "canonical_results_sha256": file_sha256(
            output / "analysis/analysis_results.json"
        ),
        "bindings": {str(p.relative_to(tmp_path)): file_sha256(p) for p in paths},
    }
    target = output / "data/derived_epoch_receipt.json"
    target.write_text(json.dumps(receipt))
    epoch["derived_receipt"] = file_sha256(target)
    (output / "data/publication_epoch.json").write_text(json.dumps(epoch))
    assert (
        load_saved_analysis_epoch(data, output)["derived_receipt"]
        == epoch["derived_receipt"]
    )
    paths[-1].write_text('{"nodes": [{"label": "tampered"}]}')
    with pytest.raises(ValueError, match="Derived artifact changed"):
        load_saved_analysis_epoch(data, output)
    paths[-1].write_text('{"nodes": [], "edges": []}')
    receipt["model_inference_repeated"] = True
    target.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="Derived epoch receipt changed"):
        load_saved_analysis_epoch(data, output)
    with pytest.raises(ValueError, match="does not bind"):
        validate_derived_epoch(tmp_path, output, store, epoch["run_id"])


def test_missing_payloads_are_restored_idempotently_and_reload_exactly(tmp_path):
    rich, empty = seed_gui(tmp_path, empty_only=True)
    database = MetadataDatabase(tmp_path / "metadata/metadata.db")
    payload = {"themes": {"vision": 2}, "error": "Explicit retained component limit"}
    records = [{"work_id": empty.id, "results": {"ontological_analysis": payload}}]
    assert restore_analysis_results(database, records) == 1
    assert database.load_work(empty.id).ontological_analysis == payload
    assert restore_analysis_results(database, records) == 0
    assert len(database.load_analysis_results(empty.id)) == 1


@pytest.mark.parametrize(
    "mutation", ["duplicate", "missing", "extra", "component", "results", "conflict"]
)
def test_invalid_restore_is_rejected_before_any_row_is_written(tmp_path, mutation):
    _, empty = seed_gui(tmp_path, empty_only=True)
    database = MetadataDatabase(tmp_path / "metadata/metadata.db")
    row = {
        "work_id": empty.id,
        "results": {
            "text_analysis": {"words": 2},
            "ontological_analysis": {"themes": []},
        },
    }
    records = [row]
    if mutation == "duplicate":
        records.append(row)
    elif mutation == "missing":
        records = []
    elif mutation == "extra":
        records.append({"work_id": "unknown", "results": {}})
    elif mutation == "component":
        row["results"]["ontological_analysis"] = []
    elif mutation == "results":
        row["results"] = []
    else:
        database.save_analysis_result(empty.id, "ontology", {"different": True})
    before = (tmp_path / "metadata/metadata.db").read_bytes()
    with pytest.raises(ValueError):
        restore_analysis_results(database, records)
    assert (tmp_path / "metadata/metadata.db").read_bytes() == before
