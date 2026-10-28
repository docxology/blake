"""Portable, private corpus snapshots for independently versioned research applications.

The completion manifest is published last. Applications must pin its SHA-256;
source hashes identify retained bytes without attesting a Git checkout or rights.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, ClassVar, Final, Literal

import click
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .text_search.models import Passage, SearchError
from .version import __version__

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
LIMITATIONS: Final = (
    "Private retained source expression; redistribution permission is not granted.",
    "Captured source units are not unique works or a complete oeuvre.",
    "Roles, authors, editions and source planes are inherited without promotion.",
    "Archive commit records source metadata without attesting a Git checkout.",
    "Visual-only references, unavailable sources and uncaptured variants remain gaps.",
)


class ApplicationError(SearchError):
    """A portable snapshot violates a named evidence boundary."""

    def __init__(self, code: str, detail: str) -> None:
        self.code: str = code
        self.detail: str = detail
        super().__init__(f"{code}: {detail}")


class FrozenModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")


class ApplicationProducer(FrozenModel):
    blake_version: str
    python: str
    exporter_sha256: Digest
    projection_producer_sha256: Digest


class ApplicationFile(FrozenModel):
    path: Literal["passages.jsonl"] = "passages.jsonl"
    size: int = Field(ge=1, strict=True)
    sha256: Digest


class PassageBinding(FrozenModel):
    passage_id: str = Field(min_length=1)
    text_sha256: Digest
    source_sha256: Digest


class ApplicationBundleManifest(FrozenModel):
    schema_version: Literal[1] = 1
    captured_manifest_sha256: Digest
    projection_manifest_sha256: Digest
    index_sha256: Digest
    archive_commit: str = Field(min_length=1)
    normalization: str = Field(min_length=1)
    producer: ApplicationProducer
    passages_file: ApplicationFile
    passages: int = Field(ge=1, strict=True)
    passage_ids: tuple[str, ...]
    passage_bindings: tuple[PassageBinding, ...]
    passages_by_role: dict[str, int]
    passages_by_plane: dict[str, int]
    passages_by_author: dict[str, int]
    limitations: tuple[str, ...] = LIMITATIONS


@dataclass(frozen=True)
class ApplicationBundle:
    manifest: ApplicationBundleManifest
    passages: tuple[Passage, ...]


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _check_path(path: Path) -> None:
    """Refuse symlink ancestors while allowing user-selected relative roots."""
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ApplicationError("unsafe_path", str(path))


def _read_regular(path: Path) -> bytes:
    _check_path(path)
    if not path.is_file():
        raise ApplicationError("missing_regular_file", path.name)
    return path.read_bytes()


def _bindings(passages: tuple[Passage, ...]) -> tuple[PassageBinding, ...]:
    result: list[PassageBinding] = []
    for passage in passages:
        if passage.source_sha256 is None:
            raise ApplicationError("missing_source_hash", passage.passage_id)
        result.append(
            PassageBinding(
                passage_id=passage.passage_id,
                text_sha256=_sha256(passage.text.encode("utf-8")),
                source_sha256=passage.source_sha256,
            )
        )
    return tuple(result)


def _verify_membership(
    manifest: ApplicationBundleManifest, passages: tuple[Passage, ...]
) -> None:
    identities = tuple(p.passage_id for p in passages)
    if (
        len(set(identities)) != len(identities)
        or len(passages) != manifest.passages
        or identities != manifest.passage_ids
        or _bindings(passages) != manifest.passage_bindings
        or dict(Counter(p.text_role for p in passages)) != manifest.passages_by_role
        or dict(Counter(p.source_plane for p in passages)) != manifest.passages_by_plane
        or dict(Counter(p.author_id for p in passages)) != manifest.passages_by_author
    ):
        raise ApplicationError(
            "bundle_membership", "Passages differ from the pinned manifest"
        )


def load_bundle(directory: Path, expected_manifest_sha256: str) -> ApplicationBundle:
    """Read a caller-pinned snapshot independently of its producer runtime."""
    if re.fullmatch(r"[a-f0-9]{64}", expected_manifest_sha256) is None:
        raise ApplicationError("manifest_pin", "Supply a lowercase SHA-256 digest")
    _check_path(directory)
    manifest_bytes = _read_regular(directory / "manifest.json")
    if _sha256(manifest_bytes) != expected_manifest_sha256:
        raise ApplicationError(
            "manifest_pin", "Manifest bytes differ from the application pin"
        )
    manifest = ApplicationBundleManifest.model_validate_json(manifest_bytes)
    raw = _read_regular(directory / manifest.passages_file.path)
    if (
        len(raw) != manifest.passages_file.size
        or _sha256(raw) != manifest.passages_file.sha256
    ):
        raise ApplicationError(
            "passages_checksum", "Passage file bytes differ from the manifest"
        )
    if not raw.endswith(b"\n"):
        raise ApplicationError(
            "passages_format", "Expected newline-terminated JSONL records"
        )
    passages = tuple(
        Passage.model_validate_json(line) for line in raw.split(b"\n")[:-1]
    )
    _verify_membership(manifest, passages)
    return ApplicationBundle(manifest, passages)


def export_recovered(data_dir: Path, destination: Path) -> ApplicationBundleManifest:
    """Copy a verified recovered projection into a new private application slot."""
    from .text_search.recovered import open_recovered_search
    from .text_search.recovered_inputs import CapturedInputs

    _check_path(data_dir)
    _check_path(destination)
    upstream = data_dir.resolve()
    target = destination.resolve()
    if target == upstream or upstream in target.parents or target in upstream.parents:
        raise ApplicationError("overlapping_roots", str(destination))
    if destination.exists():
        raise ApplicationError("occupied_output", str(destination))
    snapshot = open_recovered_search(data_dir)
    capture = CapturedInputs.open(data_dir)
    for receipt in snapshot.manifest.inputs:
        _ = capture.read(receipt.path)
    projection_path = snapshot.directory / "search-manifest.json"
    projection_bytes = _read_regular(projection_path)
    passages = tuple(snapshot.index.inventory())
    payload = ("".join(p.model_dump_json() + "\n" for p in passages)).encode("utf-8")
    exporter_bytes = _read_regular(Path(__file__))
    manifest = ApplicationBundleManifest(
        captured_manifest_sha256=snapshot.manifest.captured_manifest_sha256,
        projection_manifest_sha256=_sha256(projection_bytes),
        index_sha256=snapshot.manifest.index.sha256,
        archive_commit=snapshot.manifest.archive_commit,
        normalization=snapshot.manifest.producer.normalization,
        producer=ApplicationProducer(
            blake_version=__version__,
            python=".".join(map(str, sys.version_info[:3])),
            exporter_sha256=_sha256(exporter_bytes),
            projection_producer_sha256=snapshot.manifest.producer.sha256,
        ),
        passages_file=ApplicationFile(size=len(payload), sha256=_sha256(payload)),
        passages=len(passages),
        passage_ids=tuple(p.passage_id for p in passages),
        passage_bindings=_bindings(passages),
        passages_by_role=dict(Counter(p.text_role for p in passages)),
        passages_by_plane=dict(Counter(p.source_plane for p in passages)),
        passages_by_author=dict(Counter(p.author_id for p in passages)),
    )
    _verify_membership(manifest, passages)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="application-export-", dir=destination.parent
    ) as name:
        stage = Path(name)
        _ = (stage / "passages.jsonl").write_bytes(payload)
        manifest_bytes = (manifest.model_dump_json(indent=2) + "\n").encode("utf-8")
        _ = (stage / "manifest.json").write_bytes(manifest_bytes)
        _ = load_bundle(stage, _sha256(manifest_bytes))
        capture.revalidate()
        current = open_recovered_search(data_dir)
        if (
            current.manifest != snapshot.manifest
            or _read_regular(projection_path) != projection_bytes
            or _read_regular(Path(__file__)) != exporter_bytes
        ):
            raise ApplicationError(
                "source_changed", "Source or exporter changed during export"
            )
        _check_path(destination)
        try:
            destination.mkdir()
        except FileExistsError as exc:
            raise ApplicationError("occupied_output", str(destination)) from exc
        # Exclusive directory reservation prevents rename-over-empty-directory clobber.
        # Readers admit the snapshot only after the final atomic completion link.
        os.link(stage / "passages.jsonl", destination / "passages.jsonl")
        os.link(stage / "manifest.json", destination / "manifest.json")
    return manifest


@click.group()
def main() -> None:
    """Export or verify private corpus snapshots for research applications."""


@main.command("export")
@click.option("--data-dir", type=click.Path(path_type=Path), required=True)
@click.option("--destination", type=click.Path(path_type=Path), required=True)
def export_command(data_dir: Path, destination: Path) -> None:
    try:
        manifest = export_recovered(data_dir, destination)
        pin = _sha256(_read_regular(destination / "manifest.json"))
    except (OSError, SearchError, ValidationError, sqlite3.Error) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps({"manifest_sha256": pin, "passages": manifest.passages}))


@main.command("verify")
@click.option("--bundle", type=click.Path(path_type=Path), required=True)
@click.option("--manifest-sha256", required=True)
def verify_command(bundle: Path, manifest_sha256: str) -> None:
    try:
        result = load_bundle(bundle, manifest_sha256)
    except (OSError, SearchError, ValidationError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(
        json.dumps(
            {"manifest_sha256": manifest_sha256, "passages": result.manifest.passages}
        )
    )


if __name__ == "__main__":
    main()
