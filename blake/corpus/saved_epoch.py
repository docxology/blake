"""Read-only admission of a completed, hash-bound local analysis store."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..recovery_io import _safe_path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_saved_analysis_epoch(
    data_dir: Path, output_dir: Path
) -> dict[str, Any] | None:
    """Refuse changed or mismatched evidence instead of presenting it as current."""
    data = data_dir.absolute()
    root = data.parent
    output = output_dir.absolute()
    receipt_path = _safe_path(output, "data/publication_epoch.json")
    if not receipt_path.exists():
        return None
    receipt = json.loads(receipt_path.read_bytes())
    if (
        not isinstance(receipt, dict)
        or type(receipt.get("schema_version")) is not int
        or receipt["schema_version"] != 1
    ):
        raise ValueError("Unsupported saved analysis epoch receipt")
    if any(
        not isinstance(receipt.get(key), str) or not receipt[key]
        for key in ("data_dir", "run_id", "analysis_software_version")
    ):
        raise ValueError("Saved analysis epoch has invalid identity fields")
    if type(receipt.get("seed")) is not int:
        raise ValueError("Saved analysis epoch requires an integer seed")
    store = _safe_path(root, receipt["data_dir"])
    if not store.is_relative_to(data / "publication"):
        raise ValueError(
            "Saved analysis store is outside the publication data boundary"
        )
    required = {
        str(path.relative_to(root))
        for path in (
            output / "pipeline_summary.json",
            output / "corpus_manifest.json",
            output / "analysis/analysis_summary.json",
            output / "analysis/analysis_results.json",
            store / "metadata/metadata.db",
            store / "epoch-inputs.json",
            data / "metadata/metadata.db",
        )
    }
    bindings = receipt.get("bindings")
    if not isinstance(bindings, dict) or set(bindings) != required:
        raise ValueError("Saved analysis epoch has incomplete file bindings")
    for relative, expected in bindings.items():
        if file_sha256(_safe_path(root, relative)) != expected:
            raise ValueError("Saved analysis evidence changed: " + relative)
    manifest = json.loads((output / "corpus_manifest.json").read_bytes())
    pipeline = json.loads((output / "pipeline_summary.json").read_bytes())
    summary = json.loads((output / "analysis/analysis_summary.json").read_bytes())
    inputs = json.loads((store / "epoch-inputs.json").read_bytes())
    recorded_store = Path(manifest["data_dir"])
    if not recorded_store.is_absolute():
        recorded_store = root / recorded_store
    if recorded_store != store:
        raise ValueError("Saved manifest points at a different analysis store")
    if (
        not receipt.get("run_id")
        or receipt["run_id"] != pipeline.get("run_id")
        or receipt["run_id"] != manifest.get("run_id")
    ):
        raise ValueError("Saved analysis run identities do not match")
    if (
        pipeline.get("status") != "completed"
        or summary.get("status") != "completed"
        or summary.get("analysis_results_current") is not True
    ):
        raise ValueError("Saved analysis is not completed and current")
    original_db = str((data / "metadata/metadata.db").relative_to(root))
    if inputs.get("source_metadata_sha256") != bindings[original_db]:
        raise ValueError("Saved analysis refers to a different captured database")
    rows = inputs.get("works")
    if (
        not isinstance(rows, list)
        or len({row["work_id"] for row in rows}) != len(rows)
        or {row["work_id"] for row in rows}
        != {row["id"] for row in manifest["work_records"]}
    ):
        raise ValueError("Saved analysis input membership differs from the manifest")
    for row in rows:
        if type(row.get("has_text")) is not bool:
            raise ValueError("Saved analysis input requires explicit text modality")
        if (
            row["has_text"]
            and file_sha256(_safe_path(store, row["text_path"])) != row["text_sha256"]
        ):
            raise ValueError("Saved analysis transcription changed: " + row["work_id"])
    if summary.get("works_total") != manifest.get("total_works"):
        raise ValueError("Saved analysis population differs from the manifest")
    derived = receipt.get("derived_receipt")
    if derived is not None:
        path = _safe_path(output, "data/derived_epoch_receipt.json")
        if derived != file_sha256(path):
            raise ValueError("Derived epoch receipt changed")
        validate_derived_epoch(root, output, store, receipt["run_id"])
    return {**receipt, "store": store}


def validate_derived_epoch(
    root: Path, output: Path, store: Path, run_id: str
) -> dict[str, Any] | None:
    """Check a separately produced derived-artifact receipt, when one exists."""
    path = _safe_path(output, "data/derived_epoch_receipt.json")
    if not path.exists():
        return None
    payload = json.loads(path.read_bytes())
    if (
        payload.get("schema_version") != 1
        or payload.get("status") != "completed"
        or payload.get("run_id") != run_id
        or payload.get("model_inference_repeated") is not False
        or payload.get("canonical_results_sha256")
        != file_sha256(output / "analysis/analysis_results.json")
    ):
        raise ValueError("Derived epoch does not bind this saved model run")
    bindings = payload.get("bindings", {})
    required = {
        str(path.relative_to(root))
        for path in (
            store / "metadata/metadata.db",
            output / "reports/theme_entity_network.json",
            output / "visualizations/theme_entity_network.json",
        )
    }
    if not isinstance(bindings, dict) or not required <= set(bindings):
        raise ValueError("Derived epoch has incomplete artifact bindings")
    for relative, digest in bindings.items():
        candidate = _safe_path(root, relative)
        if candidate != store / "metadata/metadata.db" and not any(
            candidate.is_relative_to(output / name)
            for name in ("reports", "visualizations")
        ):
            raise ValueError("Derived epoch contains an unexpected artifact path")
        if file_sha256(candidate) != digest:
            raise ValueError("Derived artifact changed: " + relative)
    return payload
