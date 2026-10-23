"""Validated retained-source inventories and recovery outcome contracts."""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field


ARCHIVE_COMMIT: Final = "7063e9ea8b13d18bd5a585e87610164fd75d3f60"
ERDMAN_URL: Final = "https://erdman.blakearchive.org/api/pages"
RIGHTS: Final = (
    "Local research copy; source-provider terms apply; redistribution not granted"
)
MAX_MEMBER_BYTES: Final = 128 * 1024 * 1024


class RecoveryError(ValueError):
    """Recovery cannot establish the requested source or integrity boundary."""


class RecoveryModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FileReceipt(RecoveryModel):
    path: str
    size: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_url: str | None = None


class CopyRecord(RecoveryModel):
    document_id: str
    copy_id: str
    work_id: str
    title: str
    source_path: str
    source_sha256: str
    text_path: str | None = None
    text_role: Literal["primary", "unverified"] = "unverified"
    blocks: int = 0
    object_ids: tuple[str, ...] = ()
    non_image_references: tuple[str, ...] = ()
    extraction_error: str | None = None
    transcription_reviews: tuple[str, ...] = ()


class ErdmanPage(BaseModel):
    """Fields consumed from the reader; provider metadata stays in the raw JSON."""

    model_config = ConfigDict(frozen=True, extra="ignore")
    id: int
    page_id: str = Field(min_length=1)
    contents: str = Field(min_length=1)


class ImageRecovery(RecoveryModel):
    status: str
    expected: int
    downloaded: int
    failures: tuple[str, ...] = ()
    unattempted: tuple[str, ...] = ()
    resolution_counts: dict[str, int] = Field(default_factory=dict)
    lower_resolution_ids: tuple[str, ...] = ()


class CatalogRecovery(RecoveryModel):
    source_paths: tuple[str, ...]
    work_records: int
    copy_records: int
    object_records: int
    extra_image_ids: tuple[str, ...]
    non_image_references: tuple[str, ...]
    erdman_commit: str


class RecoveryManifest(RecoveryModel):
    schema_version: int = 1
    verified_at: str
    archive_commit: str
    scope: str = "Complete pinned Archive repository plus complete Erdman API response"
    source_recovery_status: str
    oeuvre_coverage_status: str = "not_established"
    files: tuple[FileReceipt, ...]
    copies: tuple[CopyRecord, ...]
    erdman_page_ids: tuple[str, ...]
    indexed_passages: int
    images: ImageRecovery
    limitations: tuple[str, ...]
    recipe_path: str | None = None
    catalog: CatalogRecovery | None = None
