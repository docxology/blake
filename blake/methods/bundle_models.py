# Copyright (c) 2026 Daniel Ari Friedman
"""Portable-bundle pins and artifact receipts, distinct from projection schemas."""

from typing import Literal

from pydantic import Field

from .common import Digest, FrozenModel


class CorpusPin(FrozenModel):
    schema_version: Literal[1] = 1
    bundle_manifest_sha256: Digest
    captured_manifest_sha256: Digest
    projection_manifest_sha256: Digest
    index_sha256: Digest
    source_repository: str = "https://github.com/docxology/blake"
    scope: str = (
        "Pinned captured source units; not a complete-oeuvre or image inventory."
    )


class Artifact(FrozenModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_-]*\.(json|jsonl|csv|md)$")
    size: int = Field(ge=0)
    sha256: Digest
