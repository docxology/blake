"""Read-only retained-file and source-membership integrity verification."""

from __future__ import annotations

import sqlite3
import tarfile
from collections import Counter
from contextlib import closing
from pathlib import Path

from pydantic import TypeAdapter


from .recovery_models import RecoveryError, ErdmanPage, RecoveryManifest
from .recovery_io import _digest, _safe_path


def verify_recovery(data_dir: Path) -> RecoveryManifest:
    """Read-only verification of every receipt, including source and derived files."""
    root = data_dir / "recovery"
    manifest = RecoveryManifest.model_validate_json(
        (root / "manifest.json").read_bytes()
    )
    seen: set[str] = set()
    for receipt in manifest.files:
        if receipt.path in seen:
            raise RecoveryError(f"Duplicate file receipt: {receipt.path}")
        seen.add(receipt.path)
        path = _safe_path(root, receipt.path)
        if not path.is_file():
            raise RecoveryError(f"Missing recovered file: {receipt.path}")
        content = path.read_bytes()
        if len(content) != receipt.size or _digest(content) != receipt.sha256:
            raise RecoveryError(f"Checksum mismatch: {receipt.path}")
    if not seen:
        raise RecoveryError("Recovery manifest contains no files")
    _verify_recovery_contract(root, manifest)
    return manifest


def _verify_recovery_contract(root: Path, manifest: RecoveryManifest) -> None:
    receipts = {entry.path: entry for entry in manifest.files}
    archive_path = f"sources/blakearchive-{manifest.archive_commit}.tar.gz"
    if archive_path not in receipts or "sources/erdman/pages.json" not in receipts:
        raise RecoveryError("Recovery manifest omits a required source collection")
    prefix = f"data-{manifest.archive_commit}/"
    with tarfile.open(_safe_path(root, archive_path), mode="r:gz") as archive:
        for member in archive:
            if not member.isfile():
                continue
            if not member.name.startswith(prefix):
                raise RecoveryError("Source archive belongs to a different commit")
            relative = (
                f"snapshot/{manifest.archive_commit}/{member.name[len(prefix) :]}"
            )
            if relative not in receipts:
                raise RecoveryError(f"Uninventoried source member: {relative}")
            handle = archive.extractfile(member)
            if handle is None:
                raise RecoveryError(f"Unreadable source member: {relative}")
            with handle:
                content = handle.read()
            if _digest(content) != receipts[relative].sha256:
                raise RecoveryError(f"Source archive binding differs: {relative}")
    source_paths = {
        entry.path
        for entry in manifest.files
        if (
            entry.path.startswith(f"snapshot/{manifest.archive_commit}/works/")
            or entry.path.startswith("expanded/")
        )
        and entry.path.endswith(".xml")
        and "/__MACOSX/" not in entry.path
        and not Path(entry.path).name.startswith("._")
        and not entry.path.endswith("/__contents__.xml")
    }
    if source_paths != {copy.source_path for copy in manifest.copies}:
        raise RecoveryError(
            "Copy records do not cover the complete XML source inventory"
        )
    if len({copy.document_id for copy in manifest.copies}) != len(manifest.copies):
        raise RecoveryError("Duplicate recovery document identity")
    for copy in manifest.copies:
        if receipts[copy.source_path].sha256 != copy.source_sha256:
            raise RecoveryError(f"Copy source checksum differs: {copy.document_id}")
        if copy.text_path is not None and copy.text_path not in receipts:
            raise RecoveryError(
                f"Copy reading layer lacks a receipt: {copy.document_id}"
            )
    expected_passages = {
        f"archive:{copy.document_id}" for copy in manifest.copies if copy.text_path
    }
    if "search.sqlite" not in receipts or manifest.indexed_passages != len(
        expected_passages
    ):
        raise RecoveryError(
            "Search membership differs from the recovered reading layers"
        )
    with closing(
        sqlite3.connect(
            (root / "search.sqlite").resolve().as_uri() + "?mode=ro", uri=True
        )
    ) as connection:
        actual_passages = {
            row[0] for row in connection.execute("SELECT id FROM passages")
        }
    if actual_passages != expected_passages:
        raise RecoveryError("Search index omits or adds recovered readings")
    pages = TypeAdapter(list[ErdmanPage]).validate_json(
        (root / "sources/erdman/pages.json").read_bytes()
    )
    if tuple(page.page_id for page in pages) != manifest.erdman_page_ids:
        raise RecoveryError("Erdman page inventory differs from the saved source")
    expected_images = {obj for copy in manifest.copies for obj in copy.object_ids}
    if manifest.catalog is not None:
        expected_images.update(manifest.catalog.extra_image_ids)
        if any(path not in receipts for path in manifest.catalog.source_paths):
            raise RecoveryError("Live catalogue source lacks a receipt")
    downloaded = {
        entry.path[len("images/") :].rsplit(".", 2)[0]
        for entry in manifest.files
        if entry.path.startswith("images/")
        and entry.path.endswith((".300.jpg", ".100.jpg"))
    }
    failed = {failure.split(":", 1)[0] for failure in manifest.images.failures}
    unattempted = set(manifest.images.unattempted)
    if (
        downloaded & failed
        or downloaded & unattempted
        or failed & unattempted
        or downloaded | failed | unattempted != expected_images
        or manifest.images.expected != len(expected_images)
        or manifest.images.downloaded != len(downloaded)
    ):
        raise RecoveryError(
            "Image recovery ledger does not partition the source inventory"
        )
    if (manifest.images.status == "complete") != (downloaded == expected_images):
        raise RecoveryError("Image completion status differs from the saved inventory")
    image_receipts = [
        entry
        for entry in manifest.files
        if entry.path.startswith("images/")
        and entry.path.endswith((".300.jpg", ".100.jpg"))
    ]
    resolutions = dict(
        Counter(entry.path.rsplit(".", 2)[1] for entry in image_receipts)
    )
    lower = {
        entry.path[len("images/") : -len(".100.jpg")]
        for entry in image_receipts
        if entry.path.endswith(".100.jpg")
    }
    if (
        manifest.images.resolution_counts
        and manifest.images.resolution_counts != resolutions
    ):
        raise RecoveryError("Image resolution counts differ from the saved files")
    if set(manifest.images.lower_resolution_ids) != lower:
        raise RecoveryError("Lower-resolution image outcomes are not disclosed")
    if manifest.recipe_path is not None and manifest.recipe_path not in receipts:
        raise RecoveryError("Recovery recipe lacks a checksum receipt")
