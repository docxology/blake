"""Check derived coverage against indexed payloads and captured receipt identities."""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import TYPE_CHECKING

from pydantic import HttpUrl, TypeAdapter

from ..recovery_models import ErdmanPage
from .index import PassageIndex
from .models import SearchError
from .recovered_inputs import CapturedInputs

if TYPE_CHECKING:
    from .recovered import RecoveredSearchManifest


def validate_metadata(
    snapshot: RecoveredSearchManifest, capture: CapturedInputs, index: PassageIndex
) -> None:
    """Verify coverage claims without rereading the retained image corpus."""
    rows = index.inventory()
    ids = tuple(p.passage_id for p in rows)
    if ids != snapshot.passage_ids or len(ids) != snapshot.passages:
        raise SearchError("Private search index membership differs from its receipt")
    if snapshot.archive_commit != capture.manifest.archive_commit:
        raise SearchError("Private search archive identity differs")
    if dict(Counter(p.text_role for p in rows)) != snapshot.passages_by_role:
        raise SearchError("Private search role coverage differs from indexed payloads")
    if dict(Counter(p.source_plane for p in rows)) != snapshot.passages_by_plane:
        raise SearchError("Private search plane coverage differs from indexed payloads")
    expected_inputs = {"search.sqlite", "passages.jsonl", "sources/erdman/pages.json"}
    reading = {}
    raw_xml = {}
    for copy in capture.manifest.copies:
        expected_inputs.add(copy.source_path)
        raw_xml[f"xml:{copy.document_id}"] = (
            copy.source_path,
            "unverified",
            "unverified",
            copy.work_id,
        )
        if copy.text_path is not None:
            expected_inputs.add(copy.text_path)
            author = (
                "william-blake-1757-1827"
                if copy.text_role == "primary"
                else "unverified"
            )
            reading[f"archive:{copy.document_id}"] = (
                copy.text_path,
                copy.text_role,
                author,
                copy.work_id,
            )
    parts = []
    if capture.manifest.catalog is not None:
        commit = capture.manifest.catalog.erdman_commit
        for n in range(1, 5):
            relative = f"snapshot/erdman/{commit}/data/erd{n}.xml"
            expected_inputs.add(relative)
            parts.append(relative)
            raw_xml[f"erdman-xml:erd{n}"] = (
                relative,
                "editorial",
                "mixed-edition",
                "erdman",
            )
    page_source = capture.receipts["sources/erdman/pages.json"]
    pages = TypeAdapter(list[ErdmanPage]).validate_json(
        capture.read("sources/erdman/pages.json")
    )
    if tuple(p.page_id for p in pages) != capture.manifest.erdman_page_ids:
        raise SearchError("Private search captured page catalogue differs")
    page_map = {f"erdman:{p.id}": p for p in pages}
    expected_inputs.update(f"texts/erdman/{p.id:04d}.txt" for p in pages)
    inputs = {r.path: r for r in snapshot.inputs}
    if len(inputs) != len(snapshot.inputs) or set(inputs) != expected_inputs:
        raise SearchError("Private search consumed input membership differs")
    for relative, receipt in inputs.items():
        if capture.receipts.get(relative) != receipt:
            raise SearchError(
                f"Private search consumed receipt identity differs: {relative}"
            )
    actual_reading = {p.passage_id for p in rows if p.source_plane == "reading"}
    actual_xml = {p.passage_id for p in rows if p.source_plane == "xml"}
    actual_pages = {p.passage_id for p in rows if p.source_plane == "erdman"}
    if (
        actual_reading != set(reading)
        or actual_xml != set(raw_xml)
        or not actual_pages <= set(page_map)
    ):
        raise SearchError("Private search source-plane membership differs")
    empty = tuple(
        p.page_id
        for p in sorted(pages, key=lambda p: p.id)
        if f"erdman:{p.id}" not in actual_pages
    )
    if snapshot.empty_erdman_page_ids != empty:
        raise SearchError("Private search omitted-page disclosure differs")
    expected_counts = {
        "archive_documents": len(capture.manifest.copies),
        "reading_documents": len(reading),
        "erdman_page_records": len(pages),
        "erdman_searchable_pages": len(actual_pages),
        "raw_xml_documents": len(raw_xml),
        "erdman_xml_parts": len(parts),
    }
    if snapshot.source_counts.model_dump() != expected_counts:
        raise SearchError("Private search source coverage differs")
    for passage in rows:
        if passage.source_plane == "erdman":
            page = page_map[passage.passage_id]
            relative = f"texts/erdman/{page.id:04d}.txt"
            role, author, work = "editorial", "mixed-edition", "erdman"
            source_sha = page_source.sha256
            source_url = page_source.source_url
            if passage.locator != f"page {page.page_id}; provider record {page.id}":
                raise SearchError("Private search page locator differs")
        else:
            selected = reading if passage.source_plane == "reading" else raw_xml
            relative, role, author, work = selected[passage.passage_id]
            if passage.source_plane == "reading":
                document_id = passage.passage_id[len("archive:") :]
                copy = next(
                    c for c in capture.manifest.copies if c.document_id == document_id
                )
                source = capture.receipts[copy.source_path]
            else:
                source = capture.receipts[relative]
            source_sha, source_url = source.sha256, source.source_url
        text_receipt = capture.receipts[relative]
        if (
            hashlib.sha256(passage.text.encode("utf-8")).hexdigest()
            != text_receipt.sha256
            or passage.text_role != role
            or passage.author_id != author
            or passage.work_id != work
            or passage.source_sha256 != source_sha
            or source_url is None
            or passage.source_url != HttpUrl(source_url)
        ):
            raise SearchError(
                f"Private search indexed source binding differs: {passage.passage_id}"
            )
