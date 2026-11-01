"""Independent finite multiplicity oracles for exact depth support."""

from itertools import combinations_with_replacement

import pytest
from pydantic import ValidationError

from blake.methods.common import EvidenceError
from blake.methods.intervals import (
    Interval,
    interval_measure,
    interval_support_at_least,
    interval_union,
)


def test_depth_distinguishes_area_excess_and_record_pairs():
    copies = (Interval(start=0, end=2),) * 3
    assert interval_support_at_least(copies) == copies[:1]
    assert interval_support_at_least(copies, minimum=3) == copies[:1]
    assert interval_support_at_least(copies, minimum=4) == ()
    assert interval_measure(interval_support_at_least(copies)) == 2
    assert sum(s.end - s.start for s in copies) - interval_measure(copies) == 4


def test_endpoint_events_preserve_adjacency_and_recombine_positive_support():
    records = (
        Interval(start=0, end=4),
        Interval(start=0, end=2),
        Interval(start=2, end=4),
        Interval(start=1, end=3),
        Interval(start=2, end=2),
    )
    assert interval_support_at_least(records) == (Interval(start=0, end=4),)
    assert interval_support_at_least(records, minimum=3) == (Interval(start=1, end=3),)
    assert interval_support_at_least(records, minimum=1) == interval_union(records)
    assert interval_support_at_least(()) == ()


@pytest.mark.parametrize("threshold", [True, False, 0, -1, 1.0, "2", None])
def test_invalid_threshold_refuses(threshold):
    with pytest.raises(EvidenceError, match="interval_threshold"):
        interval_support_at_least((), minimum=threshold)


@pytest.mark.parametrize("changes", [{"start": True}, {"end": -1}, {"end": 0}])
def test_depth_revalidates_models_even_when_threshold_exceeds_record_count(changes):
    forged = Interval(start=1, end=2).model_copy(update=changes)
    with pytest.raises(ValidationError):
        interval_support_at_least((forged,), minimum=10)


def test_depth_matches_exhaustive_integer_multiplicity_oracle():
    atoms = tuple(Interval(start=a, end=b) for a in range(4) for b in range(a, 4))
    cases = 0
    for size in range(4):
        for records in combinations_with_replacement(atoms, size):
            before = tuple(s.model_dump() for s in records)
            for minimum in range(1, 5):
                expected = {
                    point
                    for point in range(4)
                    if sum(s.start <= point < s.end for s in records) >= minimum
                }
                actual = interval_support_at_least(iter(records), minimum=minimum)
                assert {x for s in actual for x in range(s.start, s.end)} == expected
                assert interval_union(actual) == actual
                assert tuple(s.model_dump() for s in records) == before
                assert (
                    interval_support_at_least(reversed(records), minimum=minimum)
                    == actual
                )
                cases += 1
    assert cases == 1144
