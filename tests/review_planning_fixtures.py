"""Synthetic source-bound hits for the dependency-light review planner."""

from __future__ import annotations

import hashlib

from blake.studies import StudyHit


def make_hit(index: int, term: str, unit: str) -> StudyHit:
    """Keep source metadata identical for repeated occurrences in one unit."""
    text = "test " * 64 + unit
    return StudyHit(
        hit_id=hashlib.sha256(f"hit-{index}".encode()).hexdigest(),
        term_id=term,
        group="synthetic",
        passage_id=unit,
        work_id="work-" + unit,
        title="Synthetic " + unit,
        edition_id="fixture",
        copy_id=None,
        locator="section-" + unit,
        source_url="https://example.invalid/" + unit,
        rights="Synthetic fixture",
        author_id="synthetic-author",
        text_role="unverified",
        source_plane="reading",
        source_sha256=None,
        text_sha256=hashlib.sha256(text.encode()).hexdigest(),
        start=index * 5,
        end=index * 5 + 4,
        expression="test",
        context=text,
        blake_primary=False,
    )
