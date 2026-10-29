# Copyright (c) 2026 Daniel Ari Friedman
"""Historical projection schemas, retaining their exact validation boundaries."""

from typing import ClassVar, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import Digest, FrozenModel, Plane, ResearchError, Role


class Passage(FrozenModel):
    """Legacy reading/source unit; conversion to the stricter bundle is explicit."""

    passage_id: str
    work_id: str
    author_id: str
    title: str
    edition_id: str
    edition: str
    copy_id: Optional[str] = None
    locator: str
    locator_kind: Literal["plate", "page", "folio", "file_lines", "section"]
    source_url: str
    rights: str
    text_role: Role
    source_plane: Plane
    text: str
    source_sha256: Optional[Digest] = None

    @model_validator(mode="after")
    def preserve_primary_plane(self) -> "Passage":
        if self.text_role == Role.PRIMARY and self.source_plane != Plane.READING:
            raise ResearchError("primary_plane", self.passage_id)
        return self


class FileReceipt(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")
    path: str
    size: int = Field(ge=0)
    sha256: Digest


class Projection(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")
    captured_manifest_sha256: Digest
    index: FileReceipt
    inputs: tuple[FileReceipt, ...]
    passages: int = Field(ge=1)
    passage_ids: tuple[str, ...]
    passages_by_plane: dict[Plane, int]
    passages_by_role: dict[Role, int]


class CorpusPin(FrozenModel):
    upstream_commit: str
    captured_manifest_sha256: Digest
    projection_manifest_sha256: Digest
    projection_relative_path: str
    index_sha256: Digest
    unresolved_images: int = Field(ge=0)
    scope_note: str


class ImportReceipt(FrozenModel):
    schema_version: Literal[1] = 1
    corpus_pin: CorpusPin
    passages: int
    consumed_inputs_verified: int
    passages_by_plane: dict[Plane, int]
    passages_by_role: dict[Role, int]
    source_capture_path: str
    independence: Literal["copied bytes; no upstream writes or linked payloads"]


class QuerySpec(FrozenModel):
    query_id: str
    variants: tuple[str, ...] = Field(min_length=1)
    note: str


class Hit(FrozenModel):
    query_id: str
    passage_id: str
    work_id: str
    title: str
    edition_id: str
    locator: str
    source_url: str
    plane: Plane
    role: Role
    text_sha256: Digest
    start: int
    end: int
    expression: str
    context: str


class CountRow(FrozenModel):
    query_id: str
    plane: Plane
    role: Role
    occurrences: int
    matched_source_documents: int


class Concordance(FrozenModel):
    """Generic retrieval result; the calling paper supplies its interpretation note."""

    schema_version: Literal[1] = 1
    pin: CorpusPin
    query_sha256: Digest
    scanned_source_documents: int
    rows: tuple[CountRow, ...]
    hits: tuple[Hit, ...]
    interpretation: str
