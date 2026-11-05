"""Real-file controls for publication membership and safe audit export."""

import hashlib
import json
from pathlib import Path

import pytest

from manuscript_tools.publication import publication_tokens, write_publication_evidence
from tests.test_manuscript_publication import sealed_fixture


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def metric_path(root):
    return root / "analysis_output/visualizations/text_metrics.json"


@pytest.mark.parametrize("problem", ["foreign", "duplicate", "missing", "modality"])
def test_publication_reader_refuses_semantically_changed_metric_membership(
    sealed_fixture, problem
):
    root, _, _, _ = sealed_fixture
    path = metric_path(root)
    rows = read(path)
    if problem == "foreign":
        rows[0]["work_id"] = "foreign-same-population-count"
    elif problem == "duplicate":
        rows[-1]["work_id"] = rows[0]["work_id"]
    elif problem == "missing":
        rows.pop()
    else:
        text = next(row for row in rows if row["has_text"])
        image = next(row for row in rows if not row["has_text"])
        text["has_text"], image["has_text"] = False, True
    write(path, rows)
    with pytest.raises(ValueError, match="[Mm]embership|[Mm]odality"):
        publication_tokens(root, required=True)


def test_publication_reader_binds_metric_bytes_not_only_names(sealed_fixture):
    root, _, _, _ = sealed_fixture
    path = metric_path(root)
    rows = read(path)
    rows[0]["word_count"] = 123456
    write(path, rows)
    with pytest.raises(ValueError, match="[Mm]embership|[Mm]etric"):
        publication_tokens(root, required=True)


def test_publication_writer_refuses_equal_count_foreign_result(sealed_fixture):
    root, run, integrity, path = sealed_fixture
    before = path.read_bytes()
    results_path = root / "analysis_output/analysis/analysis_results.json"
    rows = read(results_path)
    rows[0]["work_id"] = "foreign-result-same-population-count"
    write(results_path, rows)
    with pytest.raises(ValueError, match="[Mm]embership"):
        write_publication_evidence(root, run, integrity)
    assert path.read_bytes() == before


def seed_diagnostics(root):
    output = root / "analysis_output"
    epoch = read(output / "data/publication_epoch.json")
    inputs = read(root / epoch["data_dir"] / "epoch-inputs.json")["works"]
    eligible = sorted(row["work_id"] for row in inputs if row["has_text"])
    embedded, filtered = eligible[:-1], eligible[-1:]
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    payload = {
        "schema_version": "1.3",
        "producer": {
            "software_version": "retained-diagnostic-producer",
            "source_sha256": "a" * 64,
            "projection_method": "retained-diagnostic-method",
        },
        "sources": {
            "corpus_manifest_sha256": sha(output / "corpus_manifest.json"),
            "analysis_results_sha256": sha(output / "analysis/analysis_results.json"),
        },
        "membership": {
            "source_sha256": sha(metric_path(root)),
            "legacy_modality_ids": [],
            "invalid_modality_ids": [],
            "text_work_ids": eligible,
            "embedded_work_ids": embedded,
            "missing_text_file_ids": [],
            "empty_or_filtered_text_ids": filtered,
            "excluded_cached_text_ids": [],
            "text_sha256": {
                row["work_id"]: row["text_sha256"]
                for row in inputs
                if row["work_id"] in embedded
            },
        },
        "embedding": {"work_count": len(embedded)},
    }
    path = output / "data/nlp_diagnostics.json"
    write(path, payload)
    return path, payload


def test_membership_audit_retains_producers_without_text_or_absolute_paths(
    sealed_fixture,
):
    from manuscript_tools.run_membership import build_membership_audit

    root, _, _, _ = sealed_fixture
    _, diagnostics = seed_diagnostics(root)
    result = build_membership_audit(root)
    assert result["run"]["analysis_software_version"] == "test-producer"
    assert result["diagnostic_producer"] == diagnostics["producer"]
    assert (
        result["exporter"]["source_sha256"] != diagnostics["producer"]["source_sha256"]
    )
    assert result["historical_discrepancy"]["status"] == "not_recovered"
    assert result["membership"]["eligible_text"] == len(
        diagnostics["membership"]["text_work_ids"]
    )
    assert result["membership"]["filtered"] == 1
    assert result["membership"]["missing"] == 0
    assert str(root) not in json.dumps(result)
    assert "transcription" not in result
    for source in result["sources"].values():
        assert not Path(source["path"]).is_absolute()
        assert (
            source["sha256"]
            == hashlib.sha256((root / source["path"]).read_bytes()).hexdigest()
        )


@pytest.mark.parametrize("problem", ["source", "partition", "foreign", "text_hash"])
def test_membership_audit_refuses_changed_saved_diagnostics(sealed_fixture, problem):
    from manuscript_tools.run_membership import build_membership_audit

    root, _, _, _ = sealed_fixture
    path, payload = seed_diagnostics(root)
    if problem == "source":
        payload["membership"]["source_sha256"] = "0" * 64
    elif problem == "partition":
        payload["membership"]["empty_or_filtered_text_ids"] = []
    elif problem == "foreign":
        payload["membership"]["text_work_ids"][0] = "foreign"
    else:
        key = next(iter(payload["membership"]["text_sha256"]))
        payload["membership"]["text_sha256"][key] = "0" * 64
    write(path, payload)
    with pytest.raises(ValueError):
        build_membership_audit(root)


def test_membership_audit_requires_retained_diagnostics(sealed_fixture):
    from manuscript_tools.run_membership import build_membership_audit

    root, _, _, _ = sealed_fixture
    with pytest.raises(ValueError, match="[Dd]iagnostic"):
        build_membership_audit(root)


def test_membership_audit_cli_preserves_occupied_output(sealed_fixture, tmp_path):
    from scripts.audit_manuscript_membership import main

    root, _, _, _ = sealed_fixture
    seed_diagnostics(root)
    output = tmp_path / "audit.json"
    assert main(["--evidence-root", str(root), "--output", str(output)]) == 0
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        main(["--evidence-root", str(root), "--output", str(output)])
    assert output.read_bytes() == before


def minimal_run(root):
    output = root / "analysis_output"
    (output / "analysis").mkdir(parents=True)
    (output / "visualizations").mkdir()
    store = root / "blake_data/publication/one"
    store.mkdir(parents=True)
    paths = {
        "inputs": store / "epoch-inputs.json",
        "manifest": output / "corpus_manifest.json",
        "metrics": output / "visualizations/text_metrics.json",
        "results": output / "analysis/analysis_results.json",
    }
    write(paths["inputs"], {"works": [{"work_id": "one", "has_text": True}]})
    write(paths["manifest"], {"total_works": 1, "work_records": [{"id": "one"}]})
    write(paths["metrics"], [{"work_id": "one", "has_text": True}])
    write(paths["results"], [{"work_id": "one", "results": {}}])
    return {"data_dir": "blake_data/publication/one"}, paths


@pytest.mark.parametrize("value", [True, 1.0])
def test_membership_population_requires_an_actual_integer(tmp_path, value):
    from manuscript_tools.run_membership import validate_run_membership

    epoch, paths = minimal_run(tmp_path)
    manifest = read(paths["manifest"])
    manifest["total_works"] = value
    write(paths["manifest"], manifest)
    with pytest.raises(ValueError, match="[Mm]embership|[Pp]opulation"):
        validate_run_membership(tmp_path, epoch)


@pytest.mark.parametrize("name", ["inputs", "manifest", "metrics", "results"])
def test_membership_rejects_malformed_top_level_json(tmp_path, name):
    from manuscript_tools.run_membership import validate_run_membership

    epoch, paths = minimal_run(tmp_path)
    write(paths[name], [] if name in {"inputs", "manifest"} else {})
    with pytest.raises(ValueError):
        validate_run_membership(tmp_path, epoch)


@pytest.mark.parametrize("name", ["inputs", "manifest"])
def test_audit_reports_malformed_hash_bound_json_clearly(sealed_fixture, name):
    from manuscript_tools.run_membership import build_membership_audit

    root, _, _, _ = sealed_fixture
    seed_diagnostics(root)
    epoch_path = root / "analysis_output/data/publication_epoch.json"
    epoch = read(epoch_path)
    relative = (
        epoch["data_dir"] + "/epoch-inputs.json"
        if name == "inputs"
        else "analysis_output/corpus_manifest.json"
    )
    write(root / relative, [])
    epoch["bindings"][relative] = hashlib.sha256(
        (root / relative).read_bytes()
    ).hexdigest()
    write(epoch_path, epoch)
    with pytest.raises(ValueError, match="[Mm]alformed|[Mm]embership"):
        build_membership_audit(root)


@pytest.mark.parametrize("name", ["membership", "sources", "embedding", "producer"])
def test_audit_reports_malformed_diagnostic_objects_clearly(sealed_fixture, name):
    from manuscript_tools.run_membership import build_membership_audit

    root, _, _, _ = sealed_fixture
    path, payload = seed_diagnostics(root)
    payload[name] = []
    write(path, payload)
    with pytest.raises(ValueError, match="[Dd]iagnostic|[Pp]roducer"):
        build_membership_audit(root)


def test_audit_distinguishes_export_review_from_an_older_seal(sealed_fixture):
    from manuscript_tools.run_membership import build_membership_audit

    root, _, _, _ = sealed_fixture
    seed_diagnostics(root)
    path = root / "analysis_output/data/publication_epoch.json"
    epoch = read(path)
    epoch.pop("membership_bindings")
    write(path, epoch)
    result = build_membership_audit(root)
    assert result["metric_binding"] == "reviewed_at_export_only"
    assert result["historical_discrepancy"]["status"] == "not_recovered"


def test_audit_requires_a_seal_instead_of_promoting_legacy_diagnostics(tmp_path):
    from manuscript_tools.run_membership import build_membership_audit

    minimal_run(tmp_path)
    with pytest.raises(ValueError, match="[Ss]ealed"):
        build_membership_audit(tmp_path)


def test_audit_refuses_a_changed_previously_valid_derived_receipt(sealed_fixture):
    from manuscript_tools.run_membership import build_membership_audit

    root, _, _, _ = sealed_fixture
    seed_diagnostics(root)
    output = root / "analysis_output"
    epoch_path = output / "data/publication_epoch.json"
    epoch = read(epoch_path)
    bindings = {}
    for relative in (
        epoch["data_dir"] + "/metadata/metadata.db",
        "analysis_output/reports/theme_entity_network.json",
        "analysis_output/visualizations/theme_entity_network.json",
        "analysis_output/visualizations/text_metrics.json",
    ):
        path = root / relative
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            write(path, {})
        bindings[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    derived_path = output / "data/derived_epoch_receipt.json"
    derived = {
        "schema_version": 1,
        "status": "completed",
        "run_id": epoch["run_id"],
        "model_inference_repeated": False,
        "canonical_results_sha256": hashlib.sha256(
            (output / "analysis/analysis_results.json").read_bytes()
        ).hexdigest(),
        "bindings": bindings,
    }
    write(derived_path, derived)
    epoch.pop("membership_bindings")
    epoch["derived_receipt"] = hashlib.sha256(derived_path.read_bytes()).hexdigest()
    write(epoch_path, epoch)
    assert build_membership_audit(root)["metric_binding"] == "derived_receipt"
    derived["status"] = "changed"
    write(derived_path, derived)
    with pytest.raises(ValueError, match="Derived epoch receipt changed"):
        build_membership_audit(root)
