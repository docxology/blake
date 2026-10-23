"""Reading-layer extraction with retained source and authorship boundaries."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup
from pydantic import TypeAdapter

from .text_search.models import Passage
from .recovery_review import reviewed_blocks

from .recovery_models import (
    ERDMAN_URL,
    RIGHTS,
    RecoveryError,
    FileReceipt,
    CopyRecord,
    ErdmanPage,
)
from .recovery_io import _derive


def _primary_ids() -> set[str]:
    """Use the existing ledger's authorship scope without changing its coverage."""
    ledger = json.loads(
        Path(__file__).with_name("corpus").joinpath("canonical_target.json").read_text()
    )
    schema = ledger["schema"]
    rows = [dict(zip(schema, row)) for row in ledger["entries"]]
    return {
        str(row["blake_archive_id"]).casefold()
        for row in rows
        if row["expected_text"] and row["blake_archive_id"]
    }


def extract_archive(
    root: Path, sources: list[FileReceipt]
) -> tuple[list[CopyRecord], list[Passage], list[FileReceipt]]:
    """Produce one reading layer per source file, preserving every copy identity."""
    copies: list[CopyRecord] = []
    passages: list[Passage] = []
    files: list[FileReceipt] = []
    primary_ids = _primary_ids()
    seen: set[str] = set()
    for source in sorted(sources, key=lambda item: item.path):
        content = (root / source.path).read_bytes()
        name = Path(source.path).stem
        document_id = (
            name
            if source.path.startswith("snapshot/")
            else f"{name}--{source.sha256[:12]}"
        )
        if document_id in seen:
            raise RecoveryError(
                f"Ambiguous document ID in source inventory: {document_id}"
            )
        seen.add(document_id)
        if source.source_url is None:
            raise RecoveryError(f"Source document has no provenance URL: {source.path}")
        work_id = name.split(".", 1)[0].casefold()
        title = name
        objects: tuple[str, ...] = ()
        non_images: tuple[str, ...] = ()
        error = None
        blocks = ()
        reviews: tuple[str, ...] = ()
        try:
            xml = content.decode("utf-8-sig")
            tree = ET.fromstring(xml)
            title = tree.get("work") or tree.findtext(".//titlestmt/title/main") or name
            references = tuple(
                dict.fromkeys(
                    e.get("dbi", "")
                    for e in tree.iter()
                    if e.tag == "desc" and e.get("dbi")
                )
            )
            objects = tuple(
                ref for ref in references if re.fullmatch(r"[A-Za-z0-9_.+-]+", ref)
            )
            non_images = tuple(ref for ref in references if ref not in objects)
            blocks, reviews = reviewed_blocks(content)
        except (ET.ParseError, UnicodeError, ValueError) as exc:
            error = str(exc)
        text_path = None
        role: Literal["primary", "unverified"] = (
            "primary" if work_id in primary_ids else "unverified"
        )
        if blocks:
            text = "\n".join(block.text for block in blocks)
            text_path = f"texts/archive/{document_id}.txt"
            files.append(
                _derive(root, text_path, text.encode("utf-8"), source.source_url)
            )
            passages.append(
                Passage(
                    passage_id=f"archive:{document_id}",
                    work_id=work_id,
                    author_id="william-blake-1757-1827"
                    if role == "primary"
                    else "unverified",
                    title=title,
                    edition_id=f"archive:{document_id}",
                    edition="William Blake Archive; original-reading extraction; apparatus retained in source XML",
                    copy_id=name,
                    locator=f"{Path(source.path).name}: reading-layer lines 1-{len(blocks)}",
                    locator_kind="file_lines",
                    source_url=source.source_url,
                    rights=RIGHTS,
                    text_role=role,
                    text=text,
                    source_sha256=source.sha256,
                )
            )
        copies.append(
            CopyRecord(
                document_id=document_id,
                copy_id=name,
                work_id=work_id,
                title=title,
                source_path=source.path,
                source_sha256=source.sha256,
                text_path=text_path,
                text_role=role,
                blocks=len(blocks),
                object_ids=objects,
                non_image_references=non_images,
                extraction_error=error,
                transcription_reviews=reviews,
            )
        )
    return copies, passages, files


def extract_erdman(root: Path, content: bytes) -> tuple[list[str], list[FileReceipt]]:
    """Keep all provider pages, with IDs and order; do not infer primary authorship."""
    pages = TypeAdapter(list[ErdmanPage]).validate_json(content)
    if not pages:
        raise RecoveryError("Erdman reader returned no pages")
    ids = [page.page_id for page in pages]
    if len(set(ids)) != len(ids) or len({p.id for p in pages}) != len(pages):
        raise RecoveryError("Duplicate Erdman page identity")
    files = []
    combined = []
    for page in sorted(pages, key=lambda p: p.id):
        soup = BeautifulSoup(page.contents, "html.parser")
        for excluded in soup.select(
            "script, style, note, .sr-only, .note-reference, .tei-line-note"
        ):
            excluded.decompose()
        for br in soup.find_all("br"):
            br.replace_with("\n")
        text = soup.get_text()
        relative = f"texts/erdman/{page.id:04d}.txt"
        files.append(_derive(root, relative, text.encode("utf-8"), ERDMAN_URL))
        combined.append(
            f"\n\n=== Erdman page {page.page_id} (record {page.id}) ===\n\n{text}"
        )
    files.append(
        _derive(
            root,
            "texts/erdman-complete.txt",
            "".join(combined).encode("utf-8"),
            ERDMAN_URL,
        )
    )
    return ids, files
