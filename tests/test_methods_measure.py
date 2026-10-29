# Copyright (c) 2026 Daniel Ari Friedman
"""Invalid displayed rates are rejected at the serialized-measure boundary."""

import pytest
from pydantic import ValidationError

from blake.methods.statistics_models import Measure
from blake.methods.models import ResearchError

VALID = {
    "source_units": 4,
    "tokens": 80,
    "occurrences": 3,
    "matched_units": 2,
    "rate_per_10000_tokens": 375.0,
    "coverage_fraction": 0.5,
}


@pytest.mark.parametrize(
    "change",
    [
        {"tokens": 0},
        {"tokens": -1},
        {"occurrences": -1},
        {"source_units": 0},
        {"source_units": 0, "matched_units": 0, "coverage_fraction": None},
        {"matched_units": 5},
        {"matched_units": 4, "coverage_fraction": 1.0},
        {"coverage_fraction": 0.4},
        {"coverage_fraction": None},
        {"rate_per_10000_tokens": 3.75},
        {"rate_per_10000_tokens": None},
        {"rate_per_10000_tokens": float("nan")},
    ],
)
def test_corrupt_measure_cannot_silently_supply_chart_values(change):
    with pytest.raises((ValidationError, ResearchError)):
        Measure.model_validate(VALID | change)


def test_valid_zero_is_distinct_from_undefined_denominators():
    zero = Measure.model_validate(
        VALID
        | {
            "occurrences": 0,
            "matched_units": 0,
            "rate_per_10000_tokens": 0.0,
            "coverage_fraction": 0.0,
        }
    )
    assert zero.rate_per_10000_tokens == zero.coverage_fraction == 0
    empty = Measure(
        source_units=0,
        tokens=0,
        occurrences=0,
        matched_units=0,
        rate_per_10000_tokens=None,
        coverage_fraction=None,
    )
    assert empty.rate_per_10000_tokens is None
    assert empty.coverage_fraction is None
    # A tokenless source is still one eligible source unit.
    tokenless = Measure(
        source_units=1,
        tokens=0,
        occurrences=0,
        matched_units=0,
        rate_per_10000_tokens=None,
        coverage_fraction=0.0,
    )
    assert tokenless.coverage_fraction == 0
    assert tokenless.rate_per_10000_tokens is None


def test_unequal_denominators_keep_rate_and_coverage_distinct():
    result = Measure.model_validate(VALID)
    assert result.rate_per_10000_tokens == 375
    assert result.coverage_fraction == 0.5
