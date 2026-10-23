"""Orchestrate source recovery and report its explicit coverage boundaries."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


from .text_search.index import PassageIndex

from .recovery_models import (
    ARCHIVE_COMMIT,
    ERDMAN_URL,
    RecoveryError,
    FileReceipt,
    CopyRecord,
    RecoveryManifest,
)
from .recovery_io import (
    _digest,
    _safe_path,
    _atomic_write,
    fetch_file,
    _retain,
    _derive,
    retain_recipe,
    unpack_snapshot,
    _work_sources,
)
from .recovery_text import extract_archive, extract_erdman
from .recovery_images import recover_images
from .recovery_integrity import verify_recovery


def recover_corpus(
    data_dir: Path,
    *,
    commit: str = ARCHIVE_COMMIT,
    offline: bool = False,
    images: bool = True,
    image_workers: int = 6,
    full: bool = False,
) -> RecoveryManifest:
    """Recover complete available source collections without altering old caches."""
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise RecoveryError("Archive revision must be a full 40-character commit SHA")
    root = data_dir / "recovery"
    catalog_enabled = full
    if (root / "manifest.json").exists():
        previous = verify_recovery(data_dir)
        catalog_enabled = full or previous.catalog is not None
        if previous.archive_commit != commit:
            raise RecoveryError(
                "Use a separate data directory to recover a different Archive commit"
            )
    archive_url = f"https://codeload.github.com/blakearchive/data/tar.gz/{commit}"
    archive_relative = f"sources/blakearchive-{commit}.tar.gz"
    archive = fetch_file(
        archive_url, _safe_path(root, archive_relative), offline=offline
    )
    files = [_retain(root, archive_relative, archive, archive_url)]
    files.extend(unpack_snapshot(root, archive, commit))
    sources = _work_sources(root, files)
    if not sources:
        raise RecoveryError("Snapshot contains no work copies")
    copies, passages, readings = extract_archive(root, sources)
    files.extend(readings)
    erdman = fetch_file(
        ERDMAN_URL, _safe_path(root, "sources/erdman/pages.json"), offline=offline
    )
    files.append(_retain(root, "sources/erdman/pages.json", erdman, ERDMAN_URL))
    page_ids, readings = extract_erdman(root, erdman)
    files.extend(readings)
    catalog = None
    image_copies = list(copies)
    if catalog_enabled:
        from .recovery_catalog import recover_catalog

        catalog, catalog_files = recover_catalog(root, copies, offline=offline)
        files.extend(catalog_files)
        catalog_sha = next(
            f.sha256 for f in catalog_files if f.path == catalog.source_paths[2]
        )
        image_copies.append(
            CopyRecord(
                document_id="live-catalog-images",
                copy_id="live-catalog-images",
                work_id="live-catalog",
                title="Additional Archive API image inventory",
                source_path=catalog.source_paths[2],
                source_sha256=catalog_sha,
                object_ids=catalog.extra_image_ids,
            )
        )
    jsonl = "".join(p.model_dump_json() + "\n" for p in passages).encode("utf-8")
    files.append(_derive(root, "passages.jsonl", jsonl))
    index_path = _safe_path(root, "search.sqlite")
    indexed = PassageIndex(index_path).build(passages)
    files.append(
        FileReceipt(
            path="search.sqlite",
            size=index_path.stat().st_size,
            sha256=_digest(index_path.read_bytes()),
        )
    )
    image_result, image_files = recover_images(
        root,
        image_copies,
        offline=offline,
        enabled=images,
        workers=image_workers,
        max_consecutive_failures=None,
    )
    files.extend(image_files)
    recipe = retain_recipe(root)
    files.append(recipe)
    extraction_errors = sum(copy.extraction_error is not None for copy in copies)
    limitations = [
        "The pinned Archive repository is a source snapshot, not a complete inventory of all surviving Blake works.",
        "Erdman raw JSON and reading text include editorial matter; they are retained separately and excluded from primary occurrence search.",
        "Archive search marks only ledger-bound text works as primary; other transcriptions remain unverified.",
        "Reading layers omit notes, deletions, and alternate readings; consult retained XML for the diplomatic apparatus.",
        f"{extraction_errors} Archive source files could not be converted to a reading layer; raw bytes remain local.",
    ]
    if image_result.status != "complete":
        limitations.append(
            "Image recovery is incomplete; see failures and unattempted object IDs."
        )
    if image_result.lower_resolution_ids:
        limitations.append(
            f"{len(image_result.lower_resolution_ids)} image objects use 100 dpi fallbacks; requested 300 dpi was unavailable."
        )
    manifest = RecoveryManifest(
        verified_at=datetime.now(timezone.utc).isoformat(),
        archive_commit=commit,
        source_recovery_status="complete",
        files=tuple(files),
        copies=tuple(copies),
        erdman_page_ids=tuple(page_ids),
        indexed_passages=indexed,
        images=image_result,
        limitations=tuple(limitations),
        recipe_path=recipe.path,
        catalog=catalog,
    )
    if (root / "manifest.json").exists():
        previous_bytes = (root / "manifest.json").read_bytes()
        _retain(
            root, f"history/manifest-{_digest(previous_bytes)}.json", previous_bytes
        )
    _atomic_write(
        root / "manifest.json", manifest.model_dump_json(indent=2).encode("utf-8")
    )
    verify_recovery(data_dir)
    return manifest


def recovery_summary(manifest: RecoveryManifest) -> str:
    """Small machine-readable CLI receipt; source text remains in local storage."""
    return json.dumps(
        {
            "source_recovery_status": manifest.source_recovery_status,
            "recovery_status": "partial"
            if any(c.extraction_error for c in manifest.copies)
            or manifest.images.status != "complete"
            or bool(manifest.images.lower_resolution_ids)
            else "complete",
            "oeuvre_coverage_status": manifest.oeuvre_coverage_status,
            "archive_commit": manifest.archive_commit,
            "verified_files": len(manifest.files),
            "archive_copy_documents": len(manifest.copies),
            "archive_reading_texts": sum(
                c.text_path is not None for c in manifest.copies
            ),
            "extraction_errors": sum(
                c.extraction_error is not None for c in manifest.copies
            ),
            "erdman_pages": len(manifest.erdman_page_ids),
            "indexed_passages": manifest.indexed_passages,
            "catalog": manifest.catalog.model_dump(
                exclude={"extra_image_ids", "non_image_references"}
            )
            if manifest.catalog is not None
            else None,
            "search_roles": dict(
                Counter(c.text_role for c in manifest.copies if c.text_path)
            ),
            "images": manifest.images.model_dump(exclude={"unattempted"}),
            "unattempted_images": len(manifest.images.unattempted),
            "limitations": manifest.limitations,
        },
        indent=2,
    )
