# Copyright (c) 2026 Daniel Ari Friedman
"""Deterministic greedy review workloads over an explicitly supplied hit pool."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict, deque
from collections.abc import Sequence
from typing import Final, Literal, Union

from ..studies import StudyHit
from .common import EvidenceError
from .review_planning_models import (
    ReviewPlan,
    ReviewPlanSpec,
    ReviewSelection,
    StratumPlan,
)

PROFILE: Final = "hash-round-robin-review-v1"
RankIdentity = Union[str, tuple[str, ...]]
WITNESS_EXCLUSIONS: Final = (
    "hit_id",
    "term_id",
    "group",
    "start",
    "end",
    "expression",
    "context",
)


def _utf8(raw: str) -> bytes:
    try:
        return raw.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise EvidenceError(
            "review_unicode", "Use UTF8-encodable evidence and seed"
        ) from exc


def canonical_hit(hit: StudyHit) -> bytes:
    """The v1 all-field row grammar, without a trailing newline."""
    return _utf8(
        json.dumps(
            hit.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )


def _rank(seed: str, kind: Literal["hit", "stratum"], identity: RankIdentity) -> bytes:
    raw = json.dumps(
        [PROFILE, seed, kind, identity],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(_utf8(raw)).digest()


def _stratum(hit: StudyHit, selection: ReviewSelection) -> tuple[str, ...]:
    fields = {
        "term_id": hit.term_id,
        "group": hit.group,
        "source_plane": hit.source_plane,
        "text_role": hit.text_role,
        "work_id": hit.work_id,
        "edition_id": hit.edition_id,
        "author_id": hit.author_id,
    }
    return tuple(fields[field] for field in selection.strata_fields)


def _unit(hit: StudyHit, selection: ReviewSelection) -> str:
    return {"passage_id": hit.passage_id, "text_sha256": hit.text_sha256}[
        selection.unit_field
    ]


def _pool_hash(hits: Sequence[StudyHit]) -> str:
    seen: set[str] = set()
    witnesses: dict[str, bytes] = {}
    fingerprint = hashlib.sha256()
    for hit in sorted(hits, key=lambda value: value.hit_id):
        if hit.hit_id in seen:
            raise EvidenceError("review_duplicate_hit", hit.hit_id)
        seen.add(hit.hit_id)
        if (
            not hit.passage_id.strip()
            or not hit.term_id.strip()
            or hit.end <= hit.start
        ):
            raise EvidenceError("review_candidate_identity", hit.hit_id)
        witness = _utf8(
            json.dumps(
                hit.model_dump(mode="json", exclude=set(WITNESS_EXCLUSIONS)),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
        if hit.passage_id in witnesses and witnesses[hit.passage_id] != witness:
            raise EvidenceError("review_passage_identity", hit.passage_id)
        witnesses[hit.passage_id] = witness
        fingerprint.update(canonical_hit(hit) + b"\n")
    return fingerprint.hexdigest()


def plan_review(hits: Sequence[StudyHit], spec: ReviewPlanSpec) -> ReviewPlan:
    """Plan a workload from validated models.

    Intentional validator bypasses are unsupported.

    Greedy round-robin order is not a quota optimizer or probability sample.
    Missing facets remain literal values; no source role or label is inferred.
    """
    pool_sha256 = _pool_hash(hits)
    known = {hit.hit_id for hit in hits}
    excluded = set(spec.excluded_hit_ids)
    if not excluded <= known:
        raise EvidenceError("review_unknown_exclusion", sorted(excluded - known)[0])
    selection = spec.selection
    # Validate the seed encoding even when the pool is empty.
    _ = _utf8(selection.seed)
    buckets: dict[tuple[str, ...], list[StudyHit]] = defaultdict(list)
    excluded_counts: Counter[tuple[str, ...]] = Counter()
    for hit in hits:
        key = _stratum(hit, selection)
        if hit.hit_id in excluded:
            excluded_counts[key] += 1
        else:
            buckets[key].append(hit)
    eligible_counts = {key: len(values) for key, values in buckets.items()}
    eligible_units = {
        _unit(hit, selection) for values in buckets.values() for hit in values
    }
    queues = {
        key: deque(
            sorted(
                values,
                key=lambda hit: (_rank(selection.seed, "hit", hit.hit_id), hit.hit_id),
            )
        )
        for key, values in buckets.items()
    }
    active = deque(
        sorted(queues, key=lambda key: (_rank(selection.seed, "stratum", key), key))
    )
    unit_counts: Counter[str] = Counter()
    selected_counts: Counter[tuple[str, ...]] = Counter()
    selected: list[str] = []
    while active and len(selected) < selection.target_size:
        key = active.popleft()
        queue = queues[key]
        while queue:
            hit = queue.popleft()
            unit = _unit(hit, selection)
            if unit_counts[unit] >= selection.max_per_unit:
                continue
            selected.append(hit.hit_id)
            unit_counts[unit] += 1
            selected_counts[key] += 1
            break
        if queue:
            active.append(key)
    return ReviewPlan(
        spec=spec,
        source_pool_sha256=pool_sha256,
        candidate_hits=len(hits),
        excluded_hits=len(excluded),
        eligible_hits=len(hits) - len(excluded),
        eligible_units=len(eligible_units),
        selected_hit_ids=tuple(selected),
        selected_hits=len(selected),
        shortfall=selection.target_size - len(selected),
        strata=tuple(
            StratumPlan(
                key=key,
                eligible_hits=eligible_counts.get(key, 0),
                excluded_hits=excluded_counts[key],
                selected_hits=selected_counts[key],
            )
            for key in sorted(set(buckets) | set(excluded_counts))
        ),
    )
