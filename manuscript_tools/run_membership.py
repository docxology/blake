"""Check one saved publication run and export aggregate membership evidence."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from blake.corpus.saved_epoch import file_sha256, load_saved_analysis_epoch
from blake.recovery_io import _safe_path
from blake.version import __version__
from manuscript_tools.nlp_diagnostics import validate_membership


def _read(root: Path, relative: str) -> tuple[Any, dict[str, Any]]:
    path = _safe_path(root, relative)
    if not path.is_file():
        raise ValueError("Saved membership input is missing: " + relative)
    raw = path.read_bytes()
    return json.loads(raw), {
        "path": relative,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _identified(rows: Any, identity: str, *, modality: bool = False) -> dict:
    if not isinstance(rows, list) or any(
        not isinstance(row, dict)
        or not isinstance(row.get(identity), str)
        or not row[identity]
        or (modality and type(row.get("has_text")) is not bool)
        for row in rows
    ):
        raise ValueError(
            "Saved membership requires identified rows and boolean modality"
        )
    result = {row[identity]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError("Saved membership contains duplicate identities")
    return result


def validate_run_membership(root: Path, epoch: dict) -> dict:
    """Compare identities and modalities, including equal-sized substitutions.

    The caller admits the publication epoch and its input bindings separately.
    This semantic check neither repeats inference nor repairs a saved artifact.
    """
    root = root.resolve()
    store = _safe_path(root, epoch["data_dir"])
    input_name = str((store / "epoch-inputs.json").relative_to(root))
    inputs, input_source = _read(root, input_name)
    manifest, manifest_source = _read(root, "analysis_output/corpus_manifest.json")
    metrics, metric_source = _read(
        root, "analysis_output/visualizations/text_metrics.json"
    )
    results, result_source = _read(
        root, "analysis_output/analysis/analysis_results.json"
    )
    if not isinstance(inputs, dict) or not isinstance(manifest, dict):
        raise ValueError("Saved membership inputs and manifest must be objects")
    input_rows = _identified(inputs.get("works"), "work_id", modality=True)
    manifest_rows = _identified(manifest.get("work_records"), "id")
    metric_rows = _identified(metrics, "work_id", modality=True)
    result_rows = _identified(results, "work_id")
    if (
        set(input_rows) != set(manifest_rows)
        or set(input_rows) != set(metric_rows)
        or set(input_rows) != set(result_rows)
        or type(manifest.get("total_works")) is not int
        or manifest.get("total_works") != len(input_rows)
        or any(not isinstance(row.get("results"), dict) for row in result_rows.values())
    ):
        raise ValueError("Saved publication membership differs between run artifacts")
    if any(
        row["has_text"] != metric_rows[identity]["has_text"]
        for identity, row in input_rows.items()
    ):
        raise ValueError("Saved publication membership modality differs")
    sources = {
        "inputs": input_source,
        "manifest": manifest_source,
        "metrics": metric_source,
        "results": result_source,
    }
    bindings = {source["path"]: source["sha256"] for source in sources.values()}
    if "membership_bindings" in epoch and epoch["membership_bindings"] != bindings:
        raise ValueError("Saved publication membership metric/input bytes changed")
    return {
        "inputs": input_rows,
        "eligible": {key for key, row in input_rows.items() if row["has_text"]},
        "sources": sources,
        "bindings": bindings,
    }


def _identity_digest(values: set[str]) -> str:
    return hashlib.sha256(
        json.dumps(sorted(values), ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def build_membership_audit(evidence_root: Path | str) -> dict:
    """Validate retained files and describe current membership without provider text."""
    root = Path(evidence_root).resolve()
    try:
        epoch = load_saved_analysis_epoch(root / "blake_data", root / "analysis_output")
    except (AttributeError, KeyError, TypeError) as exc:
        raise ValueError("Malformed saved publication membership evidence") from exc
    if epoch is None:
        raise ValueError(
            "A sealed publication epoch is required for a membership audit"
        )
    run = validate_run_membership(root, epoch)
    diagnostic_name = "analysis_output/data/nlp_diagnostics.json"
    if not (root / diagnostic_name).is_file():
        raise ValueError("Retained diagnostic evidence is required")
    diagnostics, diagnostic_source = _read(root, diagnostic_name)
    if not isinstance(diagnostics, dict) or any(
        not isinstance(diagnostics.get(name), dict)
        for name in ("membership", "sources", "embedding", "producer")
    ):
        raise ValueError(
            "Retained diagnostic evidence requires object-shaped components"
        )
    sources = run["sources"]
    membership = diagnostics.get("membership", {})
    diagnostic_sources = diagnostics.get("sources", {})
    if (
        membership.get("source_sha256") != sources["metrics"]["sha256"]
        or diagnostic_sources.get("corpus_manifest_sha256")
        != sources["manifest"]["sha256"]
        or diagnostic_sources.get("analysis_results_sha256")
        != sources["results"]["sha256"]
    ):
        raise ValueError("Retained diagnostic source bindings differ from this run")
    counts = validate_membership(
        diagnostics, publication=True, coverage_count=len(run["eligible"])
    )
    if set(membership["text_work_ids"]) != run["eligible"]:
        raise ValueError("Retained diagnostic membership differs from this run")
    embedded = set(membership["embedded_work_ids"])
    hashes = membership.get("text_sha256")
    if (
        not isinstance(hashes, dict)
        or set(hashes) != embedded
        or any(hashes[key] != run["inputs"][key].get("text_sha256") for key in embedded)
    ):
        raise ValueError("Retained diagnostic text bindings differ from epoch inputs")
    producer = diagnostics.get("producer")
    allowed = {
        "software_version",
        "source_sha256",
        "numpy_version",
        "projection_method",
    }
    if (
        not isinstance(producer, dict)
        or not {"software_version", "source_sha256"} <= producer.keys()
    ):
        raise ValueError("Retained diagnostic producer identity is missing")
    diagnostic_producer = {
        key: value for key, value in producer.items() if key in allowed
    }
    if any(
        not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.+-]+", value)
        for value in diagnostic_producer.values()
    ) or not re.fullmatch(r"[0-9a-f]{64}", diagnostic_producer["source_sha256"]):
        raise ValueError("Retained diagnostic producer identity is invalid")
    _, epoch_source = _read(root, "analysis_output/data/publication_epoch.json")
    sources = {
        **sources,
        "publication_epoch": epoch_source,
        "diagnostics": diagnostic_source,
    }
    metric_binding = "reviewed_at_export_only"
    if "membership_bindings" in epoch:
        metric_binding = "publication_membership_bindings"
    elif epoch.get("derived_receipt"):
        derived, derived_source = _read(
            root, "analysis_output/data/derived_epoch_receipt.json"
        )
        if (
            derived.get("bindings", {}).get(run["sources"]["metrics"]["path"])
            == run["sources"]["metrics"]["sha256"]
        ):
            metric_binding = "derived_receipt"
        sources["derived_receipt"] = derived_source
    return {
        "schema_version": "1.0",
        "status": "matched_current_saved_epoch",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run": {
            "run_id": epoch["run_id"],
            "analysis_software_version": epoch["analysis_software_version"],
            "seed": epoch["seed"],
        },
        "diagnostic_producer": diagnostic_producer,
        "exporter": {
            "software_version": __version__,
            "source": "manuscript_tools/run_membership.py",
            "source_sha256": file_sha256(Path(__file__)),
        },
        "sources": sources,
        "metric_binding": metric_binding,
        "membership": {
            "total_records": len(run["inputs"]),
            "eligible_text": counts["saved"],
            "embedded": counts["embedded"],
            "missing": counts["missing"],
            "filtered": counts["filtered"],
            "excluded_cache": counts["excluded"],
            "record_ids_sha256": _identity_digest(set(run["inputs"])),
            "eligible_text_ids_sha256": _identity_digest(run["eligible"]),
            "embedded_ids_sha256": _identity_digest(embedded),
        },
        "historical_discrepancy": {
            "status": "not_recovered",
            "source": "docs/publication-consistency-review.md",
            "scope": (
                "Current saved-run agreement does not identify or correct the older "
                "publication's differing membership."
            ),
        },
        "review_scope": (
            "Stored run identities, artifact bytes, text-modality membership and "
            "retained diagnostic partition only; no acquisition, model inference, "
            "literary adjudication, scientific confirmation or whole-oeuvre claim."
        ),
    }
