# Copyright (c) 2026 Daniel Ari Friedman
"""Immutable review candidates and application-neutral authored decision inputs."""

import csv
import io
from collections.abc import Sequence
from typing import Final, Protocol

from pydantic import TypeAdapter
from typing_extensions import TypedDict

from ..studies import StudyHit
from .models import Digest, EvidenceError, FrozenModel


class DecisionInput(FrozenModel):
    run_sha256: Digest
    hit_id: str
    decision: str
    reviewer: str
    rationale: str
    verification_locator: str = ""


class DecisionBinding(Protocol):
    @property
    def run_sha256(self) -> str: ...

    @property
    def hit_id(self) -> str: ...


class ReviewQueueRow(TypedDict):
    hit_id: str
    term_id: str
    source_plane: str
    text_role: str
    passage_id: str
    title: str
    locator: str
    source_url: str
    expression: str
    context: str
    decision: str
    reviewer: str
    rationale: str
    verification_locator: str


QUEUE_ADAPTER: Final = TypeAdapter(ReviewQueueRow)


def queue_row(hit: StudyHit) -> ReviewQueueRow:
    """Project known hit fields while preserving blank, unreviewed decisions."""
    return ReviewQueueRow(
        hit_id=hit.hit_id,
        term_id=hit.term_id,
        source_plane=hit.source_plane,
        text_role=hit.text_role,
        passage_id=hit.passage_id,
        title=hit.title,
        locator=hit.locator,
        source_url=hit.source_url,
        expression=hit.expression,
        context=hit.context,
        decision="",
        reviewer="",
        rationale="",
        verification_locator="",
    )


def queue_identity(row: ReviewQueueRow) -> tuple[str, ...]:
    """Select every immutable evidence field from a review queue row."""
    return (
        row["hit_id"],
        row["term_id"],
        row["source_plane"],
        row["text_role"],
        row["passage_id"],
        row["title"],
        row["locator"],
        row["source_url"],
        row["expression"],
        row["context"],
    )


def csv_decisions(
    raw: bytes, hits: tuple[StudyHit, ...], run_sha256: str
) -> tuple[DecisionInput, ...]:
    """Admit annotations only after CSV rows match the pinned candidate evidence."""
    reader = csv.DictReader(
        io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True
    )
    try:
        if tuple(reader.fieldnames or ()) != tuple(ReviewQueueRow.__annotations__):
            raise EvidenceError(
                "csv_header", "Use the unchanged review-queue column header"
            )
        by_id = {hit.hit_id: hit for hit in hits}
        seen: set[str] = set()
        decisions: list[DecisionInput] = []
        for row_number, raw_row in enumerate(reader, start=2):
            if None in raw_row or any(value is None for value in raw_row.values()):
                raise EvidenceError("csv_row_width", str(row_number))
            row = QUEUE_ADAPTER.validate_python(raw_row, strict=True)
            identity = row["hit_id"]
            if identity not in by_id or identity in seen:
                raise EvidenceError("unknown_or_duplicate_hit", identity)
            seen.add(identity)
            if queue_identity(row) != queue_identity(queue_row(by_id[identity])):
                raise EvidenceError("csv_candidate_changed", identity)
            if not row["decision"].strip():
                if any(
                    row[field].strip()
                    for field in ("reviewer", "rationale", "verification_locator")
                ):
                    raise EvidenceError("partial_csv_annotation", identity)
                continue
            decisions.append(
                DecisionInput.model_validate(
                    {
                        "run_sha256": run_sha256,
                        "hit_id": identity,
                        "decision": row["decision"],
                        "reviewer": row["reviewer"],
                        "rationale": row["rationale"],
                        "verification_locator": row["verification_locator"],
                    }
                )
            )
    except csv.Error as exc:
        raise EvidenceError("csv_format", str(exc)) from exc
    return tuple(decisions)


def validate_decision_membership(
    decisions: Sequence[DecisionBinding], hits: Sequence[StudyHit], expected: str
) -> None:
    """Bind authored decisions to one run and unique known candidates."""
    by_id = {hit.hit_id for hit in hits}
    seen: set[str] = set()
    for decision in decisions:
        if decision.run_sha256 != expected:
            raise EvidenceError("decision_run_pin", decision.hit_id)
        if decision.hit_id not in by_id or decision.hit_id in seen:
            raise EvidenceError("unknown_or_duplicate_hit", decision.hit_id)
        seen.add(decision.hit_id)


class DecisionLabel(Protocol):
    @property
    def decision(self) -> str: ...


class ReviewCounts(FrozenModel):
    candidate_hits: int
    reviewed_hits: int
    unreviewed_hits: int
    decisions: dict[str, int]


def count_decisions(
    decisions: Sequence[DecisionLabel], candidate_hits: int, labels: Sequence[str]
) -> ReviewCounts:
    """Count explicitly declared labels after candidate membership validation."""
    counts = dict.fromkeys(labels, 0)
    for decision in decisions:
        if decision.decision not in counts:
            raise EvidenceError("unknown_decision", decision.decision)
        counts[decision.decision] += 1
    if len(decisions) > candidate_hits:
        raise EvidenceError("decision_count", str(candidate_hits))
    return ReviewCounts(
        candidate_hits=candidate_hits,
        reviewed_hits=len(decisions),
        unreviewed_hits=candidate_hits - len(decisions),
        decisions=counts,
    )
