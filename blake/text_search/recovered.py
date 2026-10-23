"""Build and open private search projections without altering captured recovery files."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import sqlite3
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pydantic
from pydantic import BaseModel, ConfigDict

from ..recovery import FileReceipt, RecoveryManifest, _atomic_write, _safe_path
from .index import PassageIndex
from .models import SearchError
from .normalize import NORMALIZATION
from .recovered_inputs import CapturedInputs, project_capture
from .recovered_validation import validate_metadata


class Producer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    normalization: str
    python: str
    sqlite: str
    pydantic: str
    files: dict[str, str]

    @property
    def sha256(self) -> str:
        raw = json.dumps(self.model_dump(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class SourceCounts(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    archive_documents: int
    reading_documents: int
    erdman_page_records: int
    erdman_searchable_pages: int
    raw_xml_documents: int
    erdman_xml_parts: int


class RecoveredSearchManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    captured_manifest_sha256: str
    archive_commit: str
    producer: Producer
    inputs: tuple[FileReceipt, ...]
    index: FileReceipt
    passages: int
    passage_ids: tuple[str, ...]
    passages_by_role: dict[str, int]
    passages_by_plane: dict[str, int]
    source_counts: SourceCounts
    empty_erdman_page_ids: tuple[str, ...]


@dataclass(frozen=True)
class RecoveredSearch:
    index: PassageIndex
    manifest: RecoveredSearchManifest
    directory: Path


def _producer() -> Producer:
    package = Path(__file__).resolve().parents[1]
    files = [
        Path(__file__),
        Path(__file__).with_name("recovered_inputs.py"),
        Path(__file__).with_name("recovered_validation.py"),
        Path(__file__).with_name("models.py"),
        Path(__file__).with_name("index.py"),
        Path(__file__).with_name("normalize.py"),
        package.parent / "uv.lock",
        Path(inspect.getfile(RecoveryManifest)),
        Path(inspect.getfile(_safe_path)),
    ]
    bindings = {
        str(p.relative_to(package.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in set(files)
    }
    return Producer(
        normalization=NORMALIZATION,
        python=".".join(map(str, sys.version_info[:3])),
        sqlite=sqlite3.sqlite_version,
        pydantic=pydantic.__version__,
        files=bindings,
    )


def _directory(data_dir: Path, manifest_sha: str, producer: Producer) -> Path:
    return _safe_path(
        data_dir, f"search/recovered/{manifest_sha[:16]}-{producer.sha256[:16]}"
    )


def _open(
    directory: Path, capture: CapturedInputs, producer: Producer
) -> RecoveredSearch:
    metadata = _safe_path(directory, "search-manifest.json")
    if not metadata.is_file():
        raise SearchError(
            "Private search projection is absent; run blake-text build-recovered first"
        )
    manifest = RecoveredSearchManifest.model_validate_json(metadata.read_bytes())
    if (
        manifest.captured_manifest_sha256 != capture.manifest_sha256
        or manifest.producer != producer
    ):
        raise SearchError(
            "Private search projection has different source or producer bindings"
        )
    if manifest.index.path != "passages.sqlite":
        raise SearchError("Unexpected private index receipt path")
    index_path = _safe_path(directory, manifest.index.path)
    raw = index_path.read_bytes()
    if (
        len(raw) != manifest.index.size
        or hashlib.sha256(raw).hexdigest() != manifest.index.sha256
    ):
        raise SearchError("Private search index checksum mismatch")
    index = PassageIndex(index_path, read_only=True)
    validate_metadata(manifest, capture, index)
    return RecoveredSearch(index, manifest, directory)


def open_recovered_search(data_dir: Path) -> RecoveredSearch:
    """Verify the derived index, captured-manifest identity and current producer."""
    capture = CapturedInputs.open(data_dir)
    producer = _producer()
    return _open(
        _directory(data_dir, capture.manifest_sha256, producer), capture, producer
    )


def build_recovered_search(data_dir: Path) -> RecoveredSearch:
    """Create a separate versioned projection; never rebuild the captured index."""
    capture = CapturedInputs.open(data_dir)
    producer = _producer()
    projection = project_capture(capture)
    directory = _directory(data_dir, capture.manifest_sha256, producer)
    if directory.exists():
        capture.revalidate()
        return _open(directory, capture, producer)
    directory.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="search-build-", dir=directory.parent
    ) as temporary:
        stage = Path(temporary)
        path = stage / "passages.sqlite"
        count = PassageIndex(path).build(projection.passages)
        raw = path.read_bytes()
        manifest = RecoveredSearchManifest(
            captured_manifest_sha256=capture.manifest_sha256,
            archive_commit=capture.manifest.archive_commit,
            producer=producer,
            inputs=tuple(capture.used[key] for key in sorted(capture.used)),
            index=FileReceipt(
                path="passages.sqlite",
                size=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
            ),
            passages=count,
            passage_ids=tuple(sorted(p.passage_id for p in projection.passages)),
            passages_by_role=dict(Counter(p.text_role for p in projection.passages)),
            passages_by_plane=dict(
                Counter(p.source_plane for p in projection.passages)
            ),
            source_counts=SourceCounts(
                archive_documents=len(capture.manifest.copies),
                reading_documents=sum(
                    c.text_path is not None for c in capture.manifest.copies
                ),
                erdman_page_records=projection.erdman_page_records,
                erdman_searchable_pages=sum(
                    p.source_plane == "erdman" for p in projection.passages
                ),
                raw_xml_documents=sum(
                    p.source_plane == "xml" for p in projection.passages
                ),
                erdman_xml_parts=len(projection.erdman_xml_parts),
            ),
            empty_erdman_page_ids=projection.empty_erdman_page_ids,
        )
        _atomic_write(
            stage / "search-manifest.json", manifest.model_dump_json(indent=2).encode()
        )
        capture.revalidate()
        if _producer() != producer:
            raise SearchError("Search producer changed while building the projection")
        if directory.exists():
            raise SearchError("Private projection destination became occupied")
        os.rename(stage, directory)
    return _open(directory, capture, producer)
