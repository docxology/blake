# Copyright (c) 2026 Daniel Ari Friedman
"""Closed receipts for caller-selected, normally installed Git packages."""

from pathlib import Path
from typing import Annotated, Literal, Optional

from pydantic import Field

from .common import Digest, FrozenModel

GitCommit = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]


class InstalledSelection(FrozenModel):
    package: Annotated[str, Field(strict=True, pattern=r"^[A-Za-z_][A-Za-z_0-9]*$")]
    commit: Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{40}$")]
    distribution_name: Annotated[str, Field(strict=True)] = ""


class GitVCS(FrozenModel):
    vcs: Literal["git"]
    commit_id: GitCommit
    requested_revision: Optional[str] = None


class GitDirectURL(FrozenModel):
    url: Annotated[str, Field(min_length=1)]
    vcs_info: GitVCS
    subdirectory: Optional[str] = None


class InstalledFile(FrozenModel):
    path: str
    size: Annotated[int, Field(ge=0)]
    sha256: Digest


class InstalledGitPackage(FrozenModel):
    """Local consistency evidence, not an authenticated supply-chain attestation."""

    distribution: str
    package: str
    version: str
    commit: GitCommit
    package_root: Path
    direct_url_sha256: Digest
    metadata_sha256: Digest
    record_sha256: Digest
    files: tuple[InstalledFile, ...]
    imported_modules: tuple[str, ...]
