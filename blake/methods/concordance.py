# Copyright (c) 2026 Daniel Ari Friedman
"""Regex-word concordance, distinct from literal casefold retrieval."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import hashlib
import json
import re
from collections import Counter, defaultdict

from .corpus import load_import
from .models import Concordance, CountRow, Hit, Plane, QuerySpec, ResearchError, Role
from .models import ProjectionCorpusPin as CorpusPin
from .models import ProjectionPassage as Passage


def query_fingerprint(queries: tuple[QuerySpec, ...]) -> str:
    payload = json.dumps([q.model_dump(mode="json") for q in queries], sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


def concordance_passages(
    passages: tuple[Passage, ...],
    queries: tuple[QuerySpec, ...],
    pin: CorpusPin,
    interpretation: str,
) -> Concordance:
    """Retain exact case-insensitive word spans in each original source plane and role."""
    if not queries or len({q.query_id for q in queries}) != len(queries):
        raise ResearchError("query_membership", "Provide nonempty, unique query identifiers")
    text_hashes = {p.passage_id: hashlib.sha256(p.text.encode()).hexdigest() for p in passages}
    hits: list[Hit] = []
    rows: list[CountRow] = []
    for query in queries:
        if any(not term.strip() for term in query.variants):
            raise ResearchError("empty_variant", query.query_id)
        expression = (
            r"(?<!\w)(?:"
            + "|".join(
                re.escape(term) for term in sorted(set(query.variants), key=len, reverse=True)
            )
            + r")(?!\w)"
        )
        pattern = re.compile(expression, re.IGNORECASE)
        totals: Counter[tuple[Plane, Role]] = Counter()
        documents: defaultdict[tuple[Plane, Role], set[str]] = defaultdict(set)
        for passage in passages:
            for match in pattern.finditer(passage.text):
                key = (passage.source_plane, passage.text_role)
                totals[key] += 1
                documents[key].add(passage.passage_id)
                hits.append(
                    Hit(
                        query_id=query.query_id,
                        passage_id=passage.passage_id,
                        work_id=passage.work_id,
                        title=passage.title,
                        edition_id=passage.edition_id,
                        locator=passage.locator,
                        source_url=passage.source_url,
                        plane=passage.source_plane,
                        role=passage.text_role,
                        text_sha256=text_hashes[passage.passage_id],
                        start=match.start(),
                        end=match.end(),
                        expression=match.group(),
                        context=passage.text[max(0, match.start() - 100) : match.end() + 100],
                    )
                )
        for plane in Plane:
            for role in Role:
                key = (plane, role)
                rows.append(
                    CountRow(
                        query_id=query.query_id,
                        plane=plane,
                        role=role,
                        occurrences=totals[key],
                        matched_source_documents=len(documents[key]),
                    )
                )
    return Concordance(
        pin=pin,
        query_sha256=query_fingerprint(queries),
        scanned_source_documents=len(passages),
        rows=tuple(rows),
        hits=tuple(hits),
        interpretation=interpretation,
    )


def concordance(
    directory: Path, queries: tuple[QuerySpec, ...], expected_pin: CorpusPin, interpretation: str
) -> Concordance:
    """Verify a local import and retrieve regex-word spans."""
    if not queries or len({q.query_id for q in queries}) != len(queries):
        raise ResearchError("query_membership", "Provide nonempty, unique query identifiers")
    receipt, passages = load_import(directory, expected_pin)
    return concordance_passages(passages, queries, receipt.corpus_pin, interpretation)
