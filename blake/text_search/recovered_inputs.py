"""Project retained text inputs into explicitly labeled private search records."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import HttpUrl, TypeAdapter

from ..recovery import ErdmanPage, FileReceipt, RecoveryManifest, _safe_path
from .models import Passage, SearchError

RIGHTS = (
    "Retained source material for private research; redistribution rights not granted."
)


@dataclass
class CapturedInputs:
    """Read manifest-bound files and accumulate the exact consumed receipt set."""

    root: Path
    manifest_bytes: bytes
    manifest: RecoveryManifest
    receipts: dict[str, FileReceipt]
    used: dict[str, FileReceipt] = field(default_factory=dict)

    @classmethod
    def open(cls, data_dir: Path) -> CapturedInputs:
        root = _safe_path(data_dir, "recovery")
        raw = _safe_path(root, "manifest.json").read_bytes()
        manifest = RecoveryManifest.model_validate_json(raw)
        receipts = {entry.path: entry for entry in manifest.files}
        if len(receipts) != len(manifest.files):
            raise SearchError("Duplicate captured file receipts")
        return cls(root, raw, manifest, receipts)

    @property
    def manifest_sha256(self) -> str:
        return hashlib.sha256(self.manifest_bytes).hexdigest()

    def read(self, relative: str) -> bytes:
        receipt = self.receipts.get(relative)
        if receipt is None:
            raise SearchError(f"Captured input has no receipt: {relative}")
        content = _safe_path(self.root, relative).read_bytes()
        if (
            len(content) != receipt.size
            or hashlib.sha256(content).hexdigest() != receipt.sha256
        ):
            raise SearchError(f"Captured input checksum mismatch: {relative}")
        self.used[relative] = receipt
        return content

    def revalidate(self) -> None:
        if _safe_path(self.root, "manifest.json").read_bytes() != self.manifest_bytes:
            raise SearchError("Captured manifest changed during search projection")
        for relative in tuple(self.used):
            self.read(relative)


@dataclass(frozen=True)
class SearchProjection:
    passages: tuple[Passage, ...]
    empty_erdman_page_ids: tuple[str, ...]
    erdman_page_records: int
    erdman_xml_parts: tuple[str, ...]


def _readings(capture: CapturedInputs) -> list[Passage]:
    expected = {
        f"archive:{copy.document_id}": copy
        for copy in capture.manifest.copies
        if copy.text_path is not None
    }
    passages = [
        Passage.model_validate_json(line)
        for line in capture.read("passages.jsonl").decode("utf-8").split("\n")
        if line.strip()
    ]
    if len(passages) != len(expected) or {p.passage_id for p in passages} != set(
        expected
    ):
        raise SearchError("Captured reading membership differs from its manifest")
    for passage in passages:
        copy = expected[passage.passage_id]
        source = capture.receipts.get(copy.source_path)
        if source is None or source.sha256 != copy.source_sha256:
            raise SearchError("Captured copy source binding differs")
        expected_author = (
            "william-blake-1757-1827" if copy.text_role == "primary" else "unverified"
        )
        if (
            passage.source_sha256 != copy.source_sha256
            or passage.text_role != copy.text_role
            or passage.source_plane != "reading"
            or passage.author_id != expected_author
            or passage.edition_id != passage.passage_id
            or passage.work_id != copy.work_id
            or passage.copy_id != copy.copy_id
            or source.source_url is None
            or passage.source_url != HttpUrl(source.source_url)
        ):
            raise SearchError(
                f"Captured reading identity differs: {passage.passage_id}"
            )
        if copy.text_path is None:
            raise SearchError("Captured reading has no text path")
        if capture.read(copy.text_path).decode("utf-8") != passage.text:
            raise SearchError(f"Captured reading bytes differ: {passage.passage_id}")
    capture.read("search.sqlite")
    return passages


def _source_xml(capture: CapturedInputs) -> list[Passage]:
    passages = []
    for copy in capture.manifest.copies:
        source = capture.receipts.get(copy.source_path)
        if (
            source is None
            or source.sha256 != copy.source_sha256
            or source.source_url is None
        ):
            raise SearchError(f"Copy XML binding differs: {copy.document_id}")
        text = capture.read(copy.source_path).decode("utf-8")
        passages.append(
            Passage(
                passage_id=f"xml:{copy.document_id}",
                work_id=copy.work_id,
                author_id="unverified",
                title=copy.title,
                edition_id=f"xml:{copy.document_id}",
                copy_id=copy.copy_id,
                edition="Raw Archive XML, including markup, metadata and apparatus",
                locator=f"{Path(copy.source_path).name}: raw file lines 1-{len(text.splitlines())}",
                locator_kind="file_lines",
                source_url=source.source_url,
                rights=RIGHTS,
                text_role="unverified",
                source_plane="xml",
                text=text,
                source_sha256=source.sha256,
            )
        )
    return passages


def project_capture(capture: CapturedInputs) -> SearchProjection:
    """Retain role and edition boundaries without re-extracting or promoting texts."""
    passages = _readings(capture)
    passages.extend(_source_xml(capture))
    relative = "sources/erdman/pages.json"
    pages = TypeAdapter(list[ErdmanPage]).validate_json(capture.read(relative))
    if tuple(p.page_id for p in pages) != capture.manifest.erdman_page_ids:
        raise SearchError("Erdman page membership differs from captured manifest")
    source = capture.receipts[relative]
    if source.source_url is None:
        raise SearchError("Erdman page source URL is missing")
    empty = []
    for page in sorted(pages, key=lambda p: p.id):
        text = capture.read(f"texts/erdman/{page.id:04d}.txt").decode("utf-8")
        if not text.strip():
            empty.append(page.page_id)
            continue
        passages.append(
            Passage(
                passage_id=f"erdman:{page.id}",
                work_id="erdman",
                author_id="mixed-edition",
                title=f"Erdman retained page {page.page_id}",
                edition_id=f"erdman-reader:{source.sha256}",
                edition="Retained Erdman reader; primary and editorial matter not segmented",
                locator=f"page {page.page_id}; provider record {page.id}",
                locator_kind="page",
                source_url=source.source_url,
                rights=RIGHTS,
                text_role="editorial",
                source_plane="erdman",
                text=text,
                source_sha256=source.sha256,
            )
        )
    parts = []
    if capture.manifest.catalog is not None:
        commit = capture.manifest.catalog.erdman_commit
        for number in range(1, 5):
            relative = f"snapshot/erdman/{commit}/data/erd{number}.xml"
            text = capture.read(relative).decode("utf-8")
            source = capture.receipts[relative]
            if source.source_url is None:
                raise SearchError("Erdman XML source URL is missing")
            parts.append(relative)
            passages.append(
                Passage(
                    passage_id=f"erdman-xml:erd{number}",
                    work_id="erdman",
                    author_id="mixed-edition",
                    title=f"Erdman source XML part {number}",
                    edition_id=f"erdman-source:{commit}",
                    edition="Raw Erdman edition XML, including markup and editorial matter",
                    locator=f"erd{number}.xml: raw file lines 1-{len(text.splitlines())}",
                    locator_kind="file_lines",
                    source_url=source.source_url,
                    rights=RIGHTS,
                    text_role="editorial",
                    source_plane="xml",
                    text=text,
                    source_sha256=source.sha256,
                )
            )
    return SearchProjection(tuple(passages), tuple(empty), len(pages), tuple(parts))
