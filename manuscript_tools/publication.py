"""Bind publication claims to a completed analysis and verified local recovery."""

from __future__ import annotations

from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any

from blake.corpus.result_errors import component_errors
from blake.corpus.saved_epoch import (
    file_sha256,
    load_saved_analysis_epoch,
    validate_derived_epoch,
)
from blake.recovery_io import _atomic_write, _safe_path


def verify_publication_recovery(project_root: Path) -> dict[str, Any]:
    """Verify existing captured bytes, backup and retained corruption controls."""
    from blake.recovery import verify_recovery
    from blake.recovery_backup import verify_backup
    from blake.text_search.recovered import open_recovered_search

    root = project_root.resolve()
    data = _safe_path(root, "blake_data")
    manifest = verify_recovery(data)
    manifest_sha = file_sha256(data / "recovery/manifest.json")
    bundle = _safe_path(data, "backups/recovery-" + manifest_sha[:16] + ".tar")
    backup = json.loads(bundle.with_name(bundle.name + ".json").read_bytes())
    if verify_backup(bundle, expected_sha256=backup["sha256"]) != manifest:
        raise ValueError("Backup inventory differs from the captured source")
    search = open_recovered_search(data)
    drill_root = _safe_path(data, "restore-check")
    drill_path = _safe_path(drill_root, "restore_drill.json")
    drill = json.loads(drill_path.read_bytes())
    if drill["backup_sha256"] != backup["sha256"] or drill["files_verified"] != len(
        manifest.files
    ):
        raise ValueError("Historical restore drill does not bind this backup inventory")
    expected = {entry.path: entry.sha256 for entry in manifest.files}
    if (
        drill["corrupted_path"] not in drill["repaired_files"]
        or len(drill["quarantine"]) != 1
    ):
        raise ValueError(
            "Restore drill lacks its repair and retained corruption control"
        )
    repaired = _safe_path(drill_root / "recovery", drill["corrupted_path"])
    corrupted = _safe_path(drill_root / "recovery", drill["quarantine"][0])
    if (
        file_sha256(repaired) != expected[drill["corrupted_path"]]
        or file_sha256(corrupted) == expected[drill["corrupted_path"]]
    ):
        raise ValueError(
            "Retained restore controls do not distinguish repaired and corrupted bytes"
        )
    return {
        "status": "passed",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": manifest_sha,
        "files": len(manifest.files),
        "bytes": sum(entry.size for entry in manifest.files),
        "backup_path": str(bundle.relative_to(root)),
        "backup_sha256": backup["sha256"],
        "backup_bytes": bundle.stat().st_size,
        "projection_path": str(search.directory.relative_to(root)),
        "projection_manifest_sha256": file_sha256(
            search.directory / "search-manifest.json"
        ),
        "projection_passages": search.manifest.passages,
        "source_counts": search.manifest.source_counts.model_dump(),
        "historical_drill_files": drill["files_verified"],
        "restore_drill_sha256": file_sha256(drill_path),
        "repaired_copy_matches": True,
        "retained_corruption_differs": True,
        "image_recovery_status": manifest.images.status,
    }


def seal_publication_evidence(project_root: Path, analysis_receipt: Path) -> Path:
    integrity = verify_publication_recovery(project_root)
    verification_path = _safe_path(
        project_root, "analysis_output/data/recovery_verification.json"
    )
    _atomic_write(verification_path, json.dumps(integrity, indent=2).encode())
    return write_publication_evidence(
        project_root, json.loads(analysis_receipt.read_bytes()), integrity
    )


def write_publication_evidence(
    project_root: Path, run_receipt: dict[str, Any], integrity: dict[str, Any]
) -> Path:
    root = project_root.resolve()
    output = _safe_path(root, "analysis_output")
    data = _safe_path(root, "blake_data")
    if run_receipt.get("status") != "completed" or integrity.get("status") != "passed":
        raise ValueError(
            "Publication requires completed analysis and passing integrity verification"
        )
    required_protected = {
        "recovery/manifest.json",
        "recovery/search.sqlite",
        "recovery/passages.jsonl",
        "metadata/metadata.db",
    }
    if (
        set(run_receipt.get("protected_before", {})) != required_protected
        or set(run_receipt.get("protected_after", {})) != required_protected
    ):
        raise ValueError("Publication requires all captured-source protections")
    if run_receipt["protected_before"] != run_receipt["protected_after"]:
        raise ValueError("Captured sources changed during analysis")
    for relative, expected in run_receipt["protected_after"].items():
        if file_sha256(_safe_path(data, relative)) != expected:
            raise ValueError("Captured source changed after analysis: " + relative)
    manifest = json.loads((output / "corpus_manifest.json").read_bytes())
    pipeline = json.loads((output / "pipeline_summary.json").read_bytes())
    summary = json.loads((output / "analysis/analysis_summary.json").read_bytes())
    if (
        run_receipt["pipeline"]["run_id"] != pipeline["run_id"]
        or run_receipt["analysis_summary"] != summary
    ):
        raise ValueError(
            "Publication artifacts differ from the terminal analysis receipt"
        )
    store = Path(manifest["data_dir"])
    if not store.is_absolute():
        store = root / store
    store = _safe_path(root, str(store.relative_to(root)))
    paths = [
        output / "pipeline_summary.json",
        output / "corpus_manifest.json",
        output / "analysis/analysis_summary.json",
        output / "analysis/analysis_results.json",
        store / "metadata/metadata.db",
        store / "epoch-inputs.json",
        data / "metadata/metadata.db",
    ]
    epoch = {
        "schema_version": 1,
        "run_id": pipeline["run_id"],
        "analysis_software_version": run_receipt["software_at_analysis"],
        "data_dir": str(store.relative_to(root)),
        "seed": run_receipt["seed"],
        "bindings": {str(path.relative_to(root)): file_sha256(path) for path in paths},
    }
    epoch_path = _safe_path(output, "data/publication_epoch.json")
    derived = validate_derived_epoch(root, output, store, pipeline["run_id"])
    if derived is not None:
        epoch["derived_receipt"] = file_sha256(
            output / "data/derived_epoch_receipt.json"
        )

    recovery_path = _safe_path(data, "recovery/manifest.json")
    recovery = json.loads(recovery_path.read_bytes())
    if file_sha256(recovery_path) != integrity["manifest_sha256"]:
        raise ValueError(
            "Recovery verification belongs to a different captured inventory"
        )
    inputs = json.loads((store / "epoch-inputs.json").read_bytes())
    copies = {"recovered--" + copy["document_id"]: copy for copy in recovery["copies"]}
    input_rows = {row["work_id"]: row for row in inputs["works"]}
    if (
        len(input_rows) != len(inputs["works"])
        or set(input_rows) != set(copies)
        or {row["id"] for row in manifest["work_records"]} != set(copies)
    ):
        raise ValueError(
            "Publication analysis membership differs from the captured documents"
        )
    recovered_files = {row["path"]: row for row in recovery["files"]}
    for identity, copy in copies.items():
        row = input_rows[identity]
        if row["has_text"] != bool(copy.get("text_path")) or (
            row["has_text"]
            and row["text_sha256"] != recovered_files[copy["text_path"]]["sha256"]
        ):
            raise ValueError(
                "Publication transcription differs from the captured reading: "
                + identity
            )
    projection_dir = _safe_path(root, integrity["projection_path"])
    projection_path = _safe_path(projection_dir, "search-manifest.json")
    if file_sha256(projection_path) != integrity["projection_manifest_sha256"]:
        raise ValueError("Verified search projection changed")
    projection = json.loads(projection_path.read_bytes())
    if projection["captured_manifest_sha256"] != integrity["manifest_sha256"]:
        raise ValueError("Search projection belongs to a different source capture")
    backup_path = _safe_path(root, integrity["backup_path"])
    backup_receipt_path = backup_path.with_name(backup_path.name + ".json")
    backup = json.loads(backup_receipt_path.read_bytes())
    if (
        backup["sha256"] != integrity["backup_sha256"]
        or backup_path.stat().st_size != integrity["backup_bytes"]
    ):
        raise ValueError("Backup identity differs from its verified receipt")
    drill_path = _safe_path(data, "restore-check/restore_drill.json")
    if file_sha256(drill_path) != integrity["restore_drill_sha256"]:
        raise ValueError("Historical restore drill receipt changed")
    drill = json.loads(drill_path.read_bytes())
    if drill["backup_sha256"] != backup["sha256"] or drill["files_verified"] != len(
        recovery["files"]
    ):
        raise ValueError("Restore drill does not bind the verified backup inventory")
    with closing(
        sqlite3.connect(
            (store / "metadata/metadata.db").as_uri() + "?mode=ro", uri=True
        )
    ) as connection:
        image_rows = connection.execute("SELECT file_path FROM images").fetchall()
    unique_paths = {
        _safe_path(data, str(Path(row[0]).relative_to(data))) for row in image_rows
    }
    if any(not path.is_file() for path in unique_paths):
        raise ValueError("Analysis image references contain missing files")
    unique_files = {(path.stat().st_dev, path.stat().st_ino) for path in unique_paths}
    if len(image_rows) != manifest["total_images"]:
        raise ValueError("Image associations differ from the saved manifest")
    records_path = output / "analysis/analysis_results.json"
    errors = component_errors(json.loads(records_path.read_bytes()))
    insufficient = sum(
        row["path"] == "text_analysis.topics"
        and "insufficient text" in row["error"].lower()
        for row in errors
    )
    pruned = sum(
        row["path"] == "text_analysis.topics"
        and "after pruning" in row["error"].lower()
        for row in errors
    )
    roles = Counter(
        copy["text_role"] for copy in recovery["copies"] if copy.get("text_path")
    )
    images = recovery["images"]
    resolutions = images["resolution_counts"]
    if set(resolutions) - {"300", "100"}:
        raise ValueError("Unsupported recovery image resolution code")
    high, low = "300", "100"
    tokens = {
        "ANALYSIS_RUN_ID": pipeline["run_id"],
        "ANALYSIS_PRODUCER_VERSION": run_receipt["software_at_analysis"],
        "ANALYSIS_DATA_DIR": str(store.relative_to(root)),
        "ANALYSIS_INPUT_SHA256": file_sha256(store / "epoch-inputs.json"),
        "ANALYSIS_SEED": str(run_receipt["seed"]),
        "PUBLICATION_YEAR": pipeline["started_at"][:4],
        "UNIQUE_IMAGE_FILES": str(len(unique_files)),
        "REUSED_IMAGE_ASSOCIATIONS": str(len(image_rows) - len(unique_files)),
        "ANALYSIS_NESTED_ERROR_COUNT": str(len(errors)),
        "TOPIC_INSUFFICIENT_WORKS": str(insufficient),
        "TOPIC_PRUNED_WORKS": str(pruned),
        "OTHER_NESTED_ERROR_COUNT": str(len(errors) - insufficient - pruned),
        "RECOVERY_FILES": str(len(recovery["files"])),
        "RECOVERY_BYTES": str(sum(row["size"] for row in recovery["files"])),
        "RECOVERY_MANIFEST_SHA256": integrity["manifest_sha256"],
        "RECOVERY_SOURCE_STATUS": recovery["source_recovery_status"],
        "RECOVERY_OEUVRE_STATUS": recovery["oeuvre_coverage_status"],
        "RECOVERY_DOCUMENTS": str(len(recovery["copies"])),
        "RECOVERY_READING_RECORDS": str(sum(roles.values())),
        "RECOVERY_PRIMARY_RECORDS": str(roles["primary"]),
        "RECOVERY_UNVERIFIED_RECORDS": str(roles["unverified"]),
        "RECOVERY_PAGE_RECORDS": str(
            projection["source_counts"]["erdman_page_records"]
        ),
        "RECOVERY_NONEMPTY_PAGES": str(
            projection["source_counts"]["erdman_searchable_pages"]
        ),
        "RECOVERY_PROJECTION_RECORDS": str(projection["passages"]),
        "RECOVERY_IMAGES": str(images["downloaded"]),
        "RECOVERY_IMAGE_REFERENCES": str(images["expected"]),
        "RECOVERY_IMAGE_PCT": (
            f"{100 * images['downloaded'] / images['expected']:.2f}"
            if images["expected"]
            else "0.00"
        ),
        "RECOVERY_UNRESOLVED_IMAGES": str(images["expected"] - images["downloaded"]),
        "RECOVERY_HIGH_RES_IMAGES": str(resolutions.get(high, 0)),
        "RECOVERY_HIGH_RES_CODE": high,
        "RECOVERY_LOW_RES_IMAGES": str(resolutions.get(low, 0)),
        "RECOVERY_LOW_RES_CODE": low,
        "RECOVERY_IMAGE_STATUS": images["status"],
        "RECOVERY_BACKUP_BYTES": str(integrity["backup_bytes"]),
        "RECOVERY_BACKUP_SHA256": integrity["backup_sha256"],
        "RECOVERY_RESTORE_FILES": str(drill["files_verified"]),
        "RECOVERY_RESTORE_DRILL_SHA256": integrity["restore_drill_sha256"],
    }
    epoch["publication_tokens_sha256"] = hashlib.sha256(
        json.dumps(tokens, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    epoch["nested_error_count"] = len(errors)
    _atomic_write(epoch_path, json.dumps(epoch, indent=2).encode())
    load_saved_analysis_epoch(data, output)
    bindings = {
        str(path.relative_to(root)): file_sha256(path)
        for path in (
            epoch_path,
            recovery_path,
            projection_path,
            backup_receipt_path,
            drill_path,
        )
    }
    evidence = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": pipeline["run_id"],
        "bindings": bindings,
        "tokens": tokens,
        "component_error_counts": dict(Counter(row["error"] for row in errors)),
        "image_associations": len(image_rows),
        "unique_image_paths": len(unique_paths),
        "unique_image_files": len(unique_files),
        "integrity_verification": integrity,
    }
    path = _safe_path(output, "data/publication_evidence.json")
    _atomic_write(path, json.dumps(evidence, indent=2).encode())
    return path


def publication_tokens(root: Path, *, required: bool) -> dict[str, str]:
    path = _safe_path(root, "analysis_output/data/publication_evidence.json")
    if not path.exists():
        if required:
            raise ValueError("Verified publication evidence is missing")
        return {}
    evidence = json.loads(path.read_bytes())
    if (
        type(evidence.get("schema_version")) is not int
        or evidence["schema_version"] != 1
    ):
        raise ValueError("Unsupported publication evidence schema")
    epoch = load_saved_analysis_epoch(root / "blake_data", root / "analysis_output")
    if epoch is None or evidence["run_id"] != epoch["run_id"]:
        raise ValueError("Publication evidence has a different saved analysis identity")
    integrity = evidence["integrity_verification"]
    expected_bindings = {
        "analysis_output/data/publication_epoch.json",
        "blake_data/recovery/manifest.json",
        integrity["projection_path"] + "/search-manifest.json",
        integrity["backup_path"] + ".json",
        "blake_data/restore-check/restore_drill.json",
    }
    if (
        not isinstance(evidence.get("bindings"), dict)
        or set(evidence["bindings"]) != expected_bindings
    ):
        raise ValueError("Publication evidence has incomplete input bindings")
    for relative, expected in evidence["bindings"].items():
        if file_sha256(_safe_path(root, relative)) != expected:
            raise ValueError("Publication evidence input changed: " + relative)
    tokens = evidence["tokens"]
    if not isinstance(tokens, dict) or any(
        not isinstance(value, str) or not value for value in tokens.values()
    ):
        raise ValueError("Publication evidence contains invalid token values")
    token_sha = hashlib.sha256(
        json.dumps(tokens, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if token_sha != epoch.get("publication_tokens_sha256"):
        raise ValueError("Publication token values differ from the saved epoch binding")
    return tokens


def validate_manuscript_tokens(source: Path, variables: dict[str, str]) -> None:
    excluded = {
        "AGENTS.md",
        "README.md",
        "MANUSCRIPT_STATUS.md",
        "SYNTAX.md",
        "preamble.md",
    }
    used = {
        token
        for path in source.glob("*.md")
        if path.name not in excluded
        for token in re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", path.read_text())
    }
    unresolved = {key for key in used if not variables.get(key)}
    if unresolved:
        raise ValueError(
            "Unresolved manuscript tokens: " + ", ".join(sorted(unresolved))
        )
