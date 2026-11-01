"""Half-open support contracts and strict public input admission."""

from __future__ import annotations

from collections.abc import Callable, Iterable

import pytest
from pydantic import ValidationError

from blake.methods.intervals import (
    Interval,
    count_overlapping_pairs,
    interval_difference,
    interval_intersection,
    interval_measure,
    interval_union,
)


def test_adjacent_support_coalesces_without_an_overlapping_pair() -> None:
    # Given two positive supports that only share an excluded endpoint.
    spans = (Interval(start=0, end=2), Interval(start=2, end=4))
    # When their canonical support is computed.
    result = interval_union(spans)
    # Then adjacency does not leave an artificial gap.
    assert result == (Interval(start=0, end=4),)


@pytest.mark.parametrize(
    "spans,expected",
    [
        ((), 0),
        ((Interval(start=1, end=1), Interval(start=0, end=2)), 0),
        ((Interval(start=0, end=2), Interval(start=2, end=4)), 0),
        ((Interval(start=0, end=2),) * 3, 3),
        ((Interval(start=0, end=5), Interval(start=1, end=2)), 1),
        (
            (
                Interval(start=0, end=3),
                Interval(start=2, end=4),
                Interval(start=3, end=5),
            ),
            2,
        ),
    ],
)
def test_indexed_pairs_preserve_duplicates_but_exclude_empty_contact(
    spans: tuple[Interval, ...], expected: int
) -> None:
    # Given a declared bag, including empty, nested and equal-span records.
    # When unordered intersecting index pairs are counted.
    result = count_overlapping_pairs(iter(spans))
    # Then multiplicity and strict half-open contact stay distinct.
    assert result == expected


@pytest.mark.parametrize(
    "cutters,expected",
    [
        ((), ((0, 10),)),
        (((2, 3), (6, 8)), ((0, 2), (3, 6), (8, 10))),
        (((0, 3), (3, 10)), ()),
        (((0, 12),), ()),
        (((10, 12),), ((0, 10),)),
        (((6, 8), (2, 3), (2, 3)), ((0, 2), (3, 6), (8, 10))),
    ],
)
def test_difference_preserves_every_fragment(
    cutters: tuple[tuple[int, int], ...], expected: tuple[tuple[int, int], ...]
) -> None:
    # Given one support and possibly disjoint, adjacent or repeated cutters.
    left = (Interval(start=0, end=10),)
    right = tuple(Interval(start=a, end=b) for a, b in cutters)
    # When the right support is removed.
    result = interval_difference(iter(left), iter(right))
    # Then the exact surviving locations, not only duration, remain.
    assert tuple((span.start, span.end) for span in result) == expected


def test_union_measure_is_not_raw_length_with_multiplicity() -> None:
    # Given three records on the same two positions and one empty record.
    spans = (Interval(start=0, end=2),) * 3 + (Interval(start=9, end=9),)
    # When support is measured.
    result = interval_measure(iter(spans))
    # Then the two occupied positions are measured once.
    assert result == 2


@pytest.mark.parametrize(
    "raw",
    [
        '{"start":true,"end":4}',
        '{"start":0,"end":false}',
        '{"start":1.0,"end":4}',
        '{"start":"1","end":4}',
        '{"start":null,"end":4}',
        '{"start":-1,"end":4}',
        '{"start":0,"end":-1}',
        '{"start":0,"end":4,"source":"undeclared"}',
        '{"end":4}',
    ],
)
def test_json_boundary_refuses_coercion_and_undeclared_fields(raw: str) -> None:
    # Given ordinary JSON that is outside the explicit coordinate contract.
    # When it crosses the public model boundary.
    with pytest.raises(ValidationError):
        Interval.model_validate_json(raw)
    # Then it cannot become an admitted interval.


def test_reversed_endpoints_have_a_named_failure() -> None:
    # Given a reversed interval, not a valid empty support.
    # When the public constructor admits it.
    with pytest.raises(ValidationError, match="interval_order"):
        Interval(start=4, end=3)
    # Then the ordering failure has a stable machine code.


INVALID = (
    Interval.model_construct(start=3, end=2),
    Interval.model_construct(start=True, end=2),
    Interval.model_construct(start=-1, end=2),
    Interval(start=0, end=1).model_copy(update={"end": "2"}),
)


@pytest.mark.parametrize("invalid", INVALID)
@pytest.mark.parametrize(
    "operation", [interval_union, interval_measure, count_overlapping_pairs]
)
def test_unary_boundaries_reject_bypassed_models(
    invalid: Interval,
    operation: Callable[[Iterable[Interval]], tuple[Interval, ...] | int],
) -> None:
    # Given an instance created through an explicitly unvalidated Pydantic API.
    spans = (invalid,)
    # When any public unary operation admits it.
    with pytest.raises(ValidationError):
        operation(spans)
    # Then frozen object shape alone does not supply admission.


@pytest.mark.parametrize("invalid", INVALID)
@pytest.mark.parametrize("operation", [interval_intersection, interval_difference])
@pytest.mark.parametrize("invalid_right", [False, True])
def test_binary_boundaries_reject_bypassed_models_on_either_side(
    invalid: Interval,
    operation: Callable[[Iterable[Interval], Iterable[Interval]], tuple[Interval, ...]],
    invalid_right: bool,
) -> None:
    # Given a valid support on one side and an unvalidated model on the other.
    valid = (Interval(start=0, end=5),)
    left, right = (valid, (invalid,)) if invalid_right else ((invalid,), valid)
    # When the binary operation admits both inputs.
    with pytest.raises(ValidationError):
        operation(left, right)
    # Then neither operand can hide a forged model.


def test_large_integer_support_and_frozen_roundtrip() -> None:
    # Given coordinates beyond machine-word and floating-point precision.
    origin = 10**30
    span = Interval(start=origin, end=origin + 7)
    restored = Interval.model_validate_json(span.model_dump_json())
    # When an empty cut and an interior cut are applied.
    result = interval_difference(
        (restored,), (Interval(start=origin + 2, end=origin + 4),)
    )
    # Then exact integer coordinates survive unchanged.
    assert result == (
        Interval(start=origin, end=origin + 2),
        Interval(start=origin + 4, end=origin + 7),
    )


def test_admitted_intervals_remain_frozen() -> None:
    # Given an admitted coordinate interval.
    span = Interval(start=0, end=3)
    # When an assignment is attempted through the real model interface.
    with pytest.raises(ValidationError):
        span.__setattr__("end", 8)
    # Then the admitted value cannot be changed in place.
