"""Restore saved analysis payloads and rebuild derived artifacts without model inference."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Any

from blake.corpus.saved_epoch import file_sha256, load_saved_analysis_epoch
from blake.metadata.database import MetadataDatabase
from blake.recovery_io import _atomic_write, _safe_path

_FIELDS = {
    "text_analysis": "text",
    "visual_analysis": "visual",
    "cross_analysis": "cross",
    "ontological_analysis": "ontology",
}


def restore_analysis_results(
    database: MetadataDatabase, records: list[dict[str, Any]]
) -> int:
    """Fill missing canonical result rows; refuse conflicting saved payloads."""
    works = {work.id: work for work in database.load_all_works()}
    identities = [row["work_id"] for row in records]
    if len(set(identities)) != len(identities) or set(identities) != set(works):
        raise ValueError("Saved result membership differs from the database")
    pending = []
    for row in records:
        results = row["results"]
        if not isinstance(results, dict):
            raise ValueError("Saved analysis results must be an object")
        saved = {}
        for entry in database.load_analysis_results(row["work_id"]):
            saved.setdefault(entry["analysis_type"], entry["results"])
        for field, alias in _FIELDS.items():
            if field not in results:
                continue
            payload = results[field]
            if not isinstance(payload, dict):
                raise ValueError("Saved analysis component must be an object")
            if alias in saved and saved[alias] != payload:
                raise ValueError(
                    "Conflicting saved analysis: " + row["work_id"] + "/" + alias
                )
            if alias not in saved:
                pending.append((row["work_id"], alias, payload))
    for identity, alias, payload in pending:
        database.save_analysis_result(identity, alias, payload)
    for row in records:
        work = database.load_work(row["work_id"])
        for field in _FIELDS:
            if (
                field in row["results"]
                and getattr(work, field) != row["results"][field]
            ):
                raise ValueError("Analysis payload did not survive the database reload")
    return len(pending)


def refresh_saved_epoch(project_root: Path) -> Path:
    """Back up and refresh an admitted epoch; reseal it after this operation."""
    root = project_root.resolve()
    output = _safe_path(root, "analysis_output")
    epoch = load_saved_analysis_epoch(root / "blake_data", output)
    if epoch is None:
        raise ValueError("A qualified publication epoch is required")
    store = epoch["store"]
    ledger_path = _safe_path(output, "analysis/analysis_results.json")
    ledger_sha = file_sha256(ledger_path)
    database_path = _safe_path(store, "metadata/metadata.db")
    before_sha = file_sha256(database_path)
    backup = _safe_path(store, "derived-backups/" + before_sha)
    if not backup.exists():
        candidates = [database_path]
        for directory in ("reports", "visualizations"):
            candidates.extend(
                path for path in (output / directory).rglob("*") if path.is_file()
            )
        for path in candidates:
            _safe_path(root, str(path.relative_to(root)))
        backup.mkdir(parents=True)
        for path in candidates:
            destination = _safe_path(backup, str(path.relative_to(root)))
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
    database = MetadataDatabase(database_path)
    restored = restore_analysis_results(database, json.loads(ledger_path.read_bytes()))

    import asyncio
    from blake import __version__
    from blake.corpus import BlakeCorpus, CorpusConfig, CorpusManifest

    config = CorpusConfig(
        data_dir=store, output_dir=output, quick=True, fixture_mode="never"
    )
    corpus = BlakeCorpus(store, output_dir=output, config=config)
    manifest = CorpusManifest.model_validate_json(
        (output / "corpus_manifest.json").read_bytes()
    )
    sources = [
        path
        for path in sorted((root / "blake").rglob("*"))
        if path.is_file() and path.suffix in {".py", ".json"}
    ]
    sources.extend([Path(__file__), root / "uv.lock", root / "pyproject.toml"])
    source_bindings = {
        str(path.relative_to(root)): file_sha256(path) for path in sources
    }

    async def generate():
        works = await corpus.get_all_works()
        visualization = await corpus._run_visualization_phase(config, works, manifest)
        reports = await corpus._run_report_phase(config, works, manifest)
        return [visualization.model_dump(mode="json"), reports.model_dump(mode="json")]

    phases = asyncio.run(generate())
    if any(phase["status"] != "completed" for phase in phases):
        raise ValueError("Derived epoch refresh did not complete")
    if file_sha256(ledger_path) != ledger_sha:
        raise ValueError("Canonical model outputs changed during derived refresh")
    if any(
        file_sha256(root / name) != digest for name, digest in source_bindings.items()
    ):
        raise ValueError("Derived producer source changed during refresh")
    outputs = [database_path]
    for directory in ("reports", "visualizations"):
        outputs.extend(
            path for path in (output / directory).rglob("*") if path.is_file()
        )
    receipt = {
        "schema_version": 1,
        "status": "completed",
        "run_id": epoch["run_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_inference_repeated": False,
        "record_analysis_producer_version": epoch["analysis_software_version"],
        "derived_producer_version": __version__,
        "source_bindings": source_bindings,
        "canonical_results_sha256": ledger_sha,
        "database_before_sha256": before_sha,
        "restored_analysis_rows": restored,
        "backup_dir": str(backup.relative_to(root)),
        "phases": phases,
        "bindings": {
            str(path.relative_to(root)): file_sha256(path) for path in outputs
        },
    }
    path = _safe_path(output, "data/derived_epoch_receipt.json")
    _atomic_write(path, json.dumps(receipt, indent=2).encode())
    return path
