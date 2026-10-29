# Copyright (c) 2026 Daniel Ari Friedman
"""Deterministic aggregations over an explicit primary-unit inventory."""

from collections import defaultdict
from itertools import combinations
from typing import Literal, Optional

from .statistics_models import (
    Cooccurrence,
    Measure,
    QueryMeasure,
    SourceUnit,
    Stratum,
)


def measure(units: tuple[SourceUnit, ...], query_id: str) -> Measure:
    tokens = sum(u.tokens for u in units)
    occurrences = sum(u.occurrences[query_id] for u in units)
    matched = sum(u.occurrences[query_id] > 0 for u in units)
    return Measure(
        source_units=len(units),
        tokens=tokens,
        occurrences=occurrences,
        matched_units=matched,
        rate_per_10000_tokens=10000 * occurrences / tokens if tokens else None,
        coverage_fraction=matched / len(units) if units else None,
    )


def stratify(
    units: tuple[SourceUnit, ...], query_ids: tuple[str, ...]
) -> tuple[Stratum, ...]:
    result: list[Stratum] = []
    dimensions: tuple[Literal["work", "edition", "copy"], ...] = (
        "work",
        "edition",
        "copy",
    )
    for dimension in dimensions:
        groups: defaultdict[tuple[Optional[str], ...], list[SourceUnit]] = defaultdict(
            list
        )
        for unit in units:
            key = (
                (unit.work_id,)
                if dimension == "work"
                else (unit.work_id, unit.edition_id)
                if dimension == "edition"
                else (unit.work_id, unit.copy_id)
            )
            groups[key].append(unit)
        for key in sorted(
            groups, key=lambda k: tuple((v is not None, v or "") for v in k)
        ):
            members = tuple(groups[key])
            result.append(
                Stratum(
                    dimension=dimension,
                    key=key,
                    titles=tuple(sorted({u.title for u in members})),
                    member_passage_ids=tuple(u.passage_id for u in members),
                    source_units=len(members),
                    tokens=sum(u.tokens for u in members),
                    queries=tuple(
                        QueryMeasure(query_id=q, measure=measure(members, q))
                        for q in query_ids
                    ),
                )
            )
    return tuple(result)


def associations(
    units: tuple[SourceUnit, ...],
    query_ids: tuple[str, ...],
    universe: Literal["copy_retaining", "exact_text", "work_presence"],
) -> tuple[Cooccurrence, ...]:
    memberships: defaultdict[str, set[str]] = defaultdict(set)
    identities: set[str] = set()
    for unit in units:
        identity = unit.work_id if universe == "work_presence" else unit.passage_id
        identities.add(identity)
        for q in query_ids:
            if unit.occurrences[q]:
                memberships[q].add(identity)
    result: list[Cooccurrence] = []
    for left, right in combinations(query_ids, 2):
        a, b = memberships[left], memberships[right]
        both, either = len(a & b), len(a | b)
        result.append(
            Cooccurrence(
                universe=universe,
                left_query=left,
                right_query=right,
                unit_count=len(identities),
                left_matches=len(a),
                right_matches=len(b),
                both_matches=both,
                either_matches=either,
                jaccard=both / either if either else None,
                right_given_left=both / len(a) if a else None,
                left_given_right=both / len(b) if b else None,
                lift=both * len(identities) / (len(a) * len(b)) if a and b else None,
            )
        )
    return tuple(result)
