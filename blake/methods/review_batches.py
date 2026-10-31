# Copyright (c) 2026 Daniel Ari Friedman
"""Exclusive, source-bound blank review batches and checked typed readback."""

from __future__ import annotations

import csv
import io
import platform
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from pydantic import TypeAdapter

from ..studies import StudyHit
from ..version import __version__
from .annotations import ReviewQueueRow, queue_row
from .common import EvidenceError
from .producer import SourceBinding, source_binding_sha256
from .review_planning import canonical_hit, plan_review
from .review_planning_models import (
    ReviewBatchReceipt,
    ReviewPlan,
    ReviewPlanSpec,
    VerifiedReviewBatch,
)
from .runs import require_run_pin, reserve, verify_artifacts, write_new

HITS: Final = TypeAdapter(tuple[StudyHit, ...])
MEMBERS: Final = frozenset({"plan.json", "hits.jsonl", "review-queue.csv"})


def _producer() -> str:
    return source_binding_sha256(
        (
            SourceBinding(
                "blake",
                (
                    "version.py",
                    "studies.py",
                    "text_search/models.py",
                    "methods/common.py",
                    "methods/models.py",
                    "methods/bundle_models.py",
                    "methods/projection_models.py",
                    "methods/review_planning_models.py",
                    "methods/review_planning.py",
                    "methods/review_batches.py",
                    "methods/annotations.py",
                    "methods/runs.py",
                    "methods/storage.py",
                    "methods/producer.py",
                ),
            ),
        )
    )


def _selected(hits: Sequence[StudyHit], plan: ReviewPlan) -> tuple[StudyHit, ...]:
    by_id = {hit.hit_id: hit for hit in hits}
    return tuple(by_id[identity] for identity in plan.selected_hit_ids)


def _queue(hits: Sequence[StudyHit]) -> bytes:
    with io.StringIO(newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(ReviewQueueRow.__annotations__))
        writer.writeheader()
        writer.writerows(queue_row(hit) for hit in hits)
        return stream.getvalue().encode("utf-8")


def _hit_rows(hits: Sequence[StudyHit]) -> bytes:
    return b"".join(canonical_hit(hit) + b"\n" for hit in hits)


def publish_review_batch(
    hits: Sequence[StudyHit], spec: ReviewPlanSpec, output: Path
) -> ReviewBatchReceipt:
    """Write a fresh batch and last marker; callers own source-path policy."""
    plan = plan_review(hits, spec)
    selected = _selected(hits, plan)
    producer = _producer()
    reserve(output)
    artifacts = (
        write_new(
            output / "plan.json", (plan.model_dump_json(indent=2) + "\n").encode()
        ),
        write_new(output / "hits.jsonl", _hit_rows(selected)),
        write_new(output / "review-queue.csv", _queue(selected)),
    )
    receipt = ReviewBatchReceipt(
        source_run_sha256=spec.source_run_sha256,
        source_context_sha256=spec.source_context_sha256,
        source_pool_sha256=plan.source_pool_sha256,
        candidate_hits=plan.candidate_hits,
        selected_hits=plan.selected_hits,
        producer_sha256=producer,
        producer_sdk_version=__version__,
        producer_python_version=platform.python_version(),
        files=artifacts,
    )
    _ = write_new(
        output / "run.json", (receipt.model_dump_json(indent=2) + "\n").encode()
    )
    return receipt


def verify_review_batch(
    directory: Path, expected_receipt_sha256: str, hits: Sequence[StudyHit]
) -> VerifiedReviewBatch:
    """Return checked models, retaining their original producer and caller pins."""
    raw_receipt = require_run_pin(directory, expected_receipt_sha256)
    receipt = ReviewBatchReceipt.model_validate_json(raw_receipt)
    if {path.name for path in directory.iterdir()} != MEMBERS | {"run.json"}:
        raise EvidenceError("review_batch_membership", str(directory))
    payloads = verify_artifacts(directory, receipt.files, MEMBERS)
    plan = ReviewPlan.model_validate_json(payloads["plan.json"])
    expected = plan_review(hits, plan.spec)
    if plan != expected:
        raise EvidenceError("review_batch_plan", str(directory))
    if (
        receipt.source_run_sha256 != plan.spec.source_run_sha256
        or receipt.source_context_sha256 != plan.spec.source_context_sha256
        or receipt.source_pool_sha256 != plan.source_pool_sha256
        or receipt.candidate_hits != plan.candidate_hits
        or receipt.selected_hits != plan.selected_hits
    ):
        raise EvidenceError("review_batch_receipt", str(directory))
    selected = _selected(hits, plan)
    rows = HITS.validate_json(
        b"[" + b",".join(payloads["hits.jsonl"].splitlines()) + b"]"
    )
    if rows != selected or payloads["hits.jsonl"] != _hit_rows(selected):
        raise EvidenceError("review_batch_hits", str(directory))
    if payloads["review-queue.csv"] != _queue(selected):
        raise EvidenceError("review_batch_queue", str(directory))
    return VerifiedReviewBatch(receipt=receipt, plan=plan)
