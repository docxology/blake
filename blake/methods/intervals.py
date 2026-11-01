# Copyright (c) 2026 Daniel Ari Friedman
"""Exact half-open integer support within one caller-declared coordinate frame.

Set operations forget multiplicity and coalesce adjacency. Pair counting keeps
record multiplicity and requires strict intersection. Applications own frames,
units, source grouping, time activation and interpretation.
"""

from __future__ import annotations

import heapq
from typing import ClassVar, Iterable

from pydantic import ConfigDict, Field, model_validator
from typing_extensions import Self

from .common import EvidenceError, FrozenModel


class Interval(FrozenModel):
    """A nonnegative integer support [start, end); equal endpoints are empty."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True, extra="forbid", strict=True, revalidate_instances="always"
    )

    start: int = Field(ge=0)
    end: int = Field(ge=0)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.start > self.end:
            raise EvidenceError("interval_order", "Require start <= end")
        return self


def _admit_positive(intervals: Iterable[Interval]) -> list[Interval]:
    """Revalidate each supplied model once, then sort nonempty support."""
    admitted = (Interval.model_validate(span) for span in intervals)
    return sorted(
        (span for span in admitted if span.start < span.end),
        key=lambda span: (span.start, span.end),
    )


def interval_union(intervals: Iterable[Interval]) -> tuple[Interval, ...]:
    """Return maximal sorted union components, merging overlap and adjacency."""
    result: list[Interval] = []
    for span in _admit_positive(intervals):
        if not result or result[-1].end < span.start:
            result.append(span)
        elif result[-1].end < span.end:
            result[-1] = Interval(start=result[-1].start, end=span.end)
    return tuple(result)


def interval_measure(intervals: Iterable[Interval]) -> int:
    """Count union support once, without floating conversion or record weights."""
    return sum(span.end - span.start for span in interval_union(intervals))


def interval_support_at_least(
    intervals: Iterable[Interval], *, minimum: int = 2
) -> tuple[Interval, ...]:
    """Return canonical support covered by at least minimum record indices.

    The threshold must be a positive strict integer. Duplicate positive records
    contribute separately; empty records contribute no support. Endpoint events
    are combined before the next positive segment, preserving half-open bounds.
    """
    if type(minimum) is not int or minimum < 1:
        raise EvidenceError("interval_threshold", "Require a positive strict integer")
    events: dict[int, int] = {}
    for span in _admit_positive(intervals):
        events[span.start] = events.get(span.start, 0) + 1
        events[span.end] = events.get(span.end, 0) - 1
    depth, previous = 0, 0
    parts: list[Interval] = []
    for position, change in sorted(events.items()):
        if depth >= minimum:
            parts.append(Interval(start=previous, end=position))
        depth += change
        previous = position
    return interval_union(parts)


def interval_intersection(
    left: Iterable[Interval], right: Iterable[Interval]
) -> tuple[Interval, ...]:
    """Return the canonical support common to both operands."""
    first, second = interval_union(left), interval_union(right)
    i, j = 0, 0
    result: list[Interval] = []
    while i < len(first) and j < len(second):
        a, b = first[i], second[j]
        start, end = max(a.start, b.start), min(a.end, b.end)
        if start < end:
            result.append(Interval(start=start, end=end))
        if a.end <= b.end:
            i += 1
        else:
            j += 1
    return tuple(result)


def interval_difference(
    left: Iterable[Interval], right: Iterable[Interval]
) -> tuple[Interval, ...]:
    """Return all canonical fragments of left support outside right support."""
    first, second = interval_union(left), interval_union(right)
    result: list[Interval] = []
    j = 0
    for span in first:
        cursor = span.start
        while j < len(second) and second[j].end <= cursor:
            j += 1
        k = j
        while k < len(second) and second[k].start < span.end:
            cutter = second[k]
            if cursor < cutter.start:
                result.append(Interval(start=cursor, end=cutter.start))
            cursor = max(cursor, cutter.end)
            if cursor >= span.end:
                break
            k += 1
        if cursor < span.end:
            result.append(Interval(start=cursor, end=span.end))
        j = k
    return tuple(result)


def count_overlapping_pairs(intervals: Iterable[Interval]) -> int:
    """Count strictly intersecting unordered record-index pairs in O(n log n).

    Empty intervals contribute no pairs. Equal positive intervals retain their
    separate indices; adjacent intervals never intersect. No pair list or
    enumeration of individual coordinate units is materialized.
    """
    ends: list[int] = []
    pairs = 0
    for span in _admit_positive(intervals):
        while ends and ends[0] <= span.start:
            heapq.heappop(ends)
        pairs += len(ends)
        heapq.heappush(ends, span.end)
    return pairs
