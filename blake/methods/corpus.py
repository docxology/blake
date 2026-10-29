# Copyright (c) 2026 Daniel Ari Friedman
"""Import and search an independent, pinned local projection without changing Blake."""

import hashlib
import shutil
import sqlite3
import tempfile
from collections import Counter
from contextlib import closing
from pathlib import Path
from typing import Final

from pydantic import TypeAdapter

from .models import (
    FileReceipt,
    ImportReceipt,
    Projection,
    ResearchError,
)
from .models import (
    ProjectionCorpusPin as CorpusPin,
)
from .models import (
    ProjectionPassage as Passage,
)
from .storage import digest, publish_projection, safe_path, verify_file

ROWS: Final = TypeAdapter(tuple[tuple[str, str, str], ...])


def read_passages(index: Path) -> tuple[Passage, ...]:
    """Parse all SQLite payloads and independently verify each stored text digest."""
    result: list[Passage] = []
    with closing(
        sqlite3.connect(index.resolve().as_uri() + "?mode=ro", uri=True)
    ) as conn:
        if conn.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise ResearchError("sqlite_integrity", str(index))
        rows = ROWS.validate_python(
            conn.execute(
                "SELECT id,payload,sha256 FROM passages ORDER BY id",
            ).fetchall()
        )
        for identity, payload, text_sha in rows:
            passage = Passage.model_validate_json(payload)
            actual = hashlib.sha256(passage.text.encode()).hexdigest()
            if identity != passage.passage_id or text_sha != actual:
                raise ResearchError("passage_binding", identity)
            result.append(passage)
    return tuple(result)


def import_corpus(data_root: Path, destination: Path, pin: CorpusPin) -> ImportReceipt:
    """Verify every consumed input, then copy only the text projection into a new slot."""
    upstream = data_root.resolve()
    target = destination.resolve()
    if target.is_relative_to(upstream) or upstream.is_relative_to(target):
        raise ResearchError("overlapping_roots", str(target))
    if destination.exists():
        raise ResearchError("occupied_output", str(destination))
    if any(p.is_symlink() for p in (destination, *destination.parents)):
        raise ResearchError("symlink_output", str(destination))
    capture = safe_path(data_root, "recovery/manifest.json")
    metadata = safe_path(
        data_root, pin.projection_relative_path + "/search-manifest.json"
    )
    if digest(capture) != pin.captured_manifest_sha256:
        raise ResearchError("capture_pin", str(capture))
    if digest(metadata) != pin.projection_manifest_sha256:
        raise ResearchError("projection_pin", str(metadata))
    projection = Projection.model_validate_json(metadata.read_bytes())
    if projection.captured_manifest_sha256 != pin.captured_manifest_sha256:
        raise ResearchError("source_binding", str(metadata))
    if (
        projection.index.sha256 != pin.index_sha256
        or projection.index.path != "passages.sqlite"
    ):
        raise ResearchError("index_pin", str(metadata))
    source = verify_file(
        metadata.parent,
        projection.index.path,
        projection.index.size,
        pin.index_sha256,
    )
    paths = [
        verify_file(data_root / "recovery", r.path, r.size, r.sha256)
        for r in projection.inputs
    ]
    passages = read_passages(source)
    identities = tuple(p.passage_id for p in passages)
    if (
        len(passages) != projection.passages
        or len(set(projection.passage_ids)) != projection.passages
        or set(identities) != set(projection.passage_ids)
        or dict(Counter(p.source_plane for p in passages))
        != projection.passages_by_plane
        or dict(Counter(p.text_role for p in passages)) != projection.passages_by_role
    ):
        raise ResearchError("projection_membership", str(metadata))
    receipt = ImportReceipt(
        corpus_pin=pin,
        passages=len(passages),
        consumed_inputs_verified=len(paths),
        passages_by_plane=projection.passages_by_plane,
        passages_by_role=projection.passages_by_role,
        source_capture_path=str(data_root.absolute()),
        independence="copied bytes; no upstream writes or linked payloads",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="import-", dir=destination.parent
    ) as temporary:
        stage = Path(temporary)
        _ = shutil.copyfile(source, stage / "passages.sqlite")
        _ = shutil.copyfile(metadata, stage / "search-manifest.json")
        _ = shutil.copyfile(capture, stage / "capture-manifest.json")
        _ = (stage / "import-receipt.json").write_text(
            receipt.model_dump_json(indent=2) + "\n"
        )
        checks = (
            ("passages.sqlite", pin.index_sha256),
            ("search-manifest.json", pin.projection_manifest_sha256),
            ("capture-manifest.json", pin.captured_manifest_sha256),
        )
        if any(digest(stage / name) != expected for name, expected in checks):
            raise ResearchError("copy_integrity", str(stage))
        for r in projection.inputs:
            _ = verify_file(data_root / "recovery", r.path, r.size, r.sha256)
        if (
            digest(capture) != pin.captured_manifest_sha256
            or digest(metadata) != pin.projection_manifest_sha256
            or digest(source) != pin.index_sha256
        ):
            raise ResearchError("source_changed", str(data_root))
        files = tuple(
            FileReceipt(path=name, size=(stage / name).stat().st_size, sha256=expected)
            for name, expected in checks
        )
        publish_projection(
            stage, destination, files, receipt.model_dump_json(indent=2) + "\n"
        )
    return receipt


def load_import(
    directory: Path, expected_pin: CorpusPin
) -> tuple[ImportReceipt, tuple[Passage, ...]]:
    receipt = ImportReceipt.model_validate_json(
        safe_path(directory, "import-receipt.json").read_bytes(),
    )
    pin = receipt.corpus_pin
    if pin != expected_pin:
        raise ResearchError("untrusted_import_pin", str(directory))
    for relative, expected in (
        ("passages.sqlite", pin.index_sha256),
        ("search-manifest.json", pin.projection_manifest_sha256),
        ("capture-manifest.json", pin.captured_manifest_sha256),
    ):
        if digest(safe_path(directory, relative)) != expected:
            raise ResearchError("import_checksum", relative)
    passages = read_passages(directory / "passages.sqlite")
    if len(passages) != receipt.passages:
        raise ResearchError("import_membership", str(directory))
    return receipt, passages
