"""Read recorded local evidence without acquiring, repairing or reindexing it."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
from pathlib import Path

from .recovery_io import _safe_path
from .recovery_models import RecoveryError, RecoveryManifest
from .text_search.models import SearchError
from .text_search.recovered import RecoveredSearchManifest, _directory, _producer


@dataclass(frozen=True)
class EvidenceSummary:
    manifest_sha256: str
    captured_at: str
    archive_commit: str
    source_status: str
    oeuvre_coverage: str
    file_count: int
    captured_bytes: int
    archive_documents: int
    reading_passages: int
    roles: dict[str, int]
    expected_images: int
    saved_images: int
    unresolved_images: int
    unattempted_images: int
    lower_resolution_images: int


@dataclass(frozen=True)
class ProjectionSummary:
    status: str
    directory: Path
    producer_sha256: str
    passages: int | None = None


def read_evidence_summary(data_dir: Path) -> EvidenceSummary:
    """Summarize a validated manifest, not a fresh physical inventory check."""
    path = _safe_path(data_dir, "recovery/manifest.json")
    raw = path.read_bytes()
    manifest = RecoveryManifest.model_validate_json(raw)
    if len({item.path for item in manifest.files}) != len(manifest.files):
        raise RecoveryError("Duplicate paths in captured manifest")
    images = manifest.images
    if (
        not 0 <= images.downloaded <= images.expected
        or images.downloaded + len(images.failures) + len(images.unattempted)
        != images.expected
        or (
            images.resolution_counts
            and sum(images.resolution_counts.values()) != images.downloaded
        )
    ):
        raise RecoveryError("Inconsistent recorded image outcomes")
    roles = Counter(copy.text_role for copy in manifest.copies if copy.text_path)
    return EvidenceSummary(
        manifest_sha256=hashlib.sha256(raw).hexdigest(),
        captured_at=manifest.verified_at,
        archive_commit=manifest.archive_commit,
        source_status=manifest.source_recovery_status,
        oeuvre_coverage=manifest.oeuvre_coverage_status,
        file_count=len(manifest.files),
        captured_bytes=sum(item.size for item in manifest.files),
        archive_documents=len(manifest.copies),
        reading_passages=manifest.indexed_passages,
        roles=dict(roles),
        expected_images=images.expected,
        saved_images=images.downloaded,
        unresolved_images=images.expected - images.downloaded,
        unattempted_images=len(images.unattempted),
        lower_resolution_images=len(images.lower_resolution_ids),
    )


def read_projection_summary(
    data_dir: Path, evidence: EvidenceSummary
) -> ProjectionSummary:
    """Inspect producer-bound receipts; full index validation runs on search."""
    producer = _producer()
    directory = _directory(data_dir, evidence.manifest_sha256, producer)
    path = _safe_path(directory, "search-manifest.json")
    if not path.exists():
        return ProjectionSummary("missing", directory, producer.sha256)
    manifest = RecoveredSearchManifest.model_validate_json(path.read_bytes())
    if (
        manifest.captured_manifest_sha256 != evidence.manifest_sha256
        or manifest.producer != producer
    ):
        raise SearchError(
            "Projection receipt has different source or producer bindings"
        )
    if manifest.index.path != "passages.sqlite":
        raise SearchError("Unexpected projection index path")
    index = _safe_path(directory, manifest.index.path)
    if not index.is_file() or index.stat().st_size != manifest.index.size:
        raise SearchError(
            "Projection index is missing or its size differs from the receipt"
        )
    if any(
        sum(counts.values()) != manifest.passages
        for counts in (
            manifest.passages_by_role,
            manifest.passages_by_plane,
        )
    ):
        raise SearchError("Projection receipt has inconsistent passage counts")
    return ProjectionSummary("recorded", directory, producer.sha256, manifest.passages)
