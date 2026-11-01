"""Finite point-set oracles, independent of the production sweep algorithms."""

from __future__ import annotations

from itertools import combinations, combinations_with_replacement, permutations
from typing import Iterable, Iterator

from blake.methods.intervals import (
    Interval,
    count_overlapping_pairs,
    interval_difference,
    interval_intersection,
    interval_measure,
    interval_union,
)


def bags(bound: int, size: int) -> Iterator[tuple[Interval, ...]]:
    choices = tuple(
        Interval(start=a, end=b) for a in range(bound + 1) for b in range(a, bound + 1)
    )
    for length in range(size + 1):
        yield from combinations_with_replacement(choices, length)


def points(spans: Iterable[Interval]) -> set[int]:
    return {position for span in spans for position in range(span.start, span.end)}


def canonical(spans: tuple[Interval, ...]) -> bool:
    return all(span.start < span.end for span in spans) and all(
        a.end < b.start for a, b in zip(spans, spans[1:])
    )


def test_union_matches_816_finite_multisets() -> None:
    for spans in bags(4, 3):
        # Given a bag over five explicit integer endpoints, including empties.
        expected = points(spans)
        # When the union is normalized.
        actual = interval_union(iter(spans))
        # Then its exact support and maximal ordered segmentation agree.
        assert points(actual) == expected
        assert canonical(actual)


def test_measure_matches_816_finite_point_sets() -> None:
    for spans in bags(4, 3):
        # Given support independently enumerated as individual integer atoms.
        expected = len(points(spans))
        # When the public measure is computed.
        actual = interval_measure(iter(spans))
        # Then it counts support, not record lengths.
        assert actual == expected


def test_pairs_match_816_indexed_point_set_oracles() -> None:
    for spans in bags(4, 3):
        # Given every unordered pair of record indices, retaining duplicates.
        expected = sum(
            bool(points((a,)) & points((b,))) for a, b in combinations(spans, 2)
        )
        # When strict overlapping pairs are counted.
        actual = count_overlapping_pairs(iter(spans))
        # Then half-open adjacency and empty spans contribute no pairs.
        assert actual == expected


def test_intersection_matches_4356_finite_bag_pairs() -> None:
    family = tuple(bags(3, 2))
    for left in family:
        for right in family:
            # Given two independently enumerated supports.
            expected = points(left) & points(right)
            # When their intersection is computed.
            actual = interval_intersection(iter(left), iter(right))
            # Then all and only common atoms survive canonically.
            assert points(actual) == expected
            assert canonical(actual)


def test_difference_matches_4356_finite_bag_pairs() -> None:
    family = tuple(bags(3, 2))
    for left in family:
        for right in family:
            # Given operand order and support independently defined by sets.
            expected = points(left) - points(right)
            # When right support is subtracted from left support.
            actual = interval_difference(iter(left), iter(right))
            # Then no component or direction can be lost behind equal length.
            assert points(actual) == expected
            assert canonical(actual)


def test_pair_count_is_permutation_invariant() -> None:
    spans = (
        Interval(start=0, end=3),
        Interval(start=2, end=4),
        Interval(start=2, end=4),
        Interval(start=4, end=4),
    )
    for reordered in permutations(spans):
        # Given the same four indexed records in each ordering.
        # When the public count is evaluated.
        actual = count_overlapping_pairs(iter(reordered))
        # Then identity multiplicity is independent of order.
        assert actual == 3


def test_union_does_not_mutate_the_input_inventory() -> None:
    # Given a caller-owned mutable inventory in a noncanonical order.
    spans = [Interval(start=3, end=5), Interval(start=0, end=2)]
    before = tuple(spans)
    # When the public operation normalizes its own result.
    actual = interval_union(spans)
    # Then caller order and values remain unchanged.
    assert tuple(spans) == before
    assert actual == tuple(reversed(before))
