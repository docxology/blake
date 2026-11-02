"""Finite-set and source-boundary checks for the authoring illustration."""

import hashlib
import itertools
from collections.abc import Callable
from pathlib import Path

import pytest

from blake.methods.common import EvidenceError
from blake.methods.intervals import Interval, interval_measure
from manuscript_tools.interval_illustration import (
    _refusal,
    build_interval_illustration,
    interval_tokens,
)

ROOT = Path(__file__).resolve().parents[1]


def test_illustration_support_matches_an_independent_integer_oracle() -> None:
    # Given the actual illustrative input records, when projected, then every set
    # matches.
    result = build_interval_illustration(ROOT)
    records = [set(range(p.start, p.end)) for p in result.records]
    union = set().union(*records)
    mask = set().union(*(set(range(p.start, p.end)) for p in result.mask))

    def expand(parts: tuple[Interval, ...]) -> set[int]:
        return set().union(*(set(range(p.start, p.end)) for p in parts))

    assert expand(result.union) == union
    assert expand(result.intersection) == union & mask
    assert expand(result.difference) == union - mask
    assert result.union_length == len(union)
    assert result.summed_record_length == sum(map(len, records))
    assert expand(result.depth_two) == {
        x for x in union if sum(x in p for p in records) >= 2
    }
    assert expand(result.depth_three) == {
        x for x in union if sum(x in p for p in records) >= 3
    }


def test_illustration_preserves_indexed_pairs_and_empty_adjacency_distinctions() -> (
    None
):
    # Given duplicate, touching and empty indexed records, when counted, then indices
    # survive.
    result = build_interval_illustration(ROOT)
    sets = [set(range(p.start, p.end)) for p in result.records]
    pairs = tuple(
        (i + 1, j + 1)
        for i, j in itertools.combinations(range(len(sets)), 2)
        if sets[i] & sets[j]
    )
    assert result.pair_indices == pairs
    assert result.strict_pairs == len(pairs) == 3
    assert result.union_length == 8
    assert result.summed_record_length == 14
    assert result.records[1] == result.records[2]
    assert result.records[-1].start == result.records[-1].end


def test_actual_scalar_forged_and_threshold_controls_refuse() -> None:
    # Given real invalid API inputs, when the illustration runs, then actual errors are
    # recorded.
    controls = build_interval_illustration(ROOT).controls
    assert {(c.name, c.exception, c.code) for c in controls} == {
        ("strict_scalar", "ValidationError", "int_type"),
        ("forged_order", "ValidationError", "value_error"),
        ("strict_threshold", "EvidenceError", "interval_threshold"),
    }


def test_a_control_that_accepts_cannot_be_reported_as_a_refusal() -> None:
    # Given a valid API action presented as a control, when it accepts, then production
    # refuses.
    with pytest.raises(EvidenceError, match="interval_illustration_control"):
        _refusal("strict_scalar", lambda: interval_measure((Interval(start=1, end=2),)))


def _preserve_missing(path: Path) -> None:
    path.rename(path.with_suffix(".preserved"))


def _change_bytes(path: Path) -> None:
    path.write_bytes(path.read_bytes() + b"\n")


def _replace_with_symlink(path: Path) -> None:
    preserved = path.with_suffix(".preserved")
    path.rename(preserved)
    path.symlink_to(preserved)


@pytest.mark.parametrize(
    "mutation",
    [_preserve_missing, _change_bytes, _replace_with_symlink],
    ids=["missing", "changed", "symlink"],
)
def test_source_boundary_refuses_missing_changed_or_symlinked_bytes(
    tmp_path: Path, mutation: Callable[[Path], None]
) -> None:
    # Given an independent source copy, when its custody changes, then admission
    # refuses.
    original = build_interval_illustration(ROOT)
    for relative in original.source_bindings:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / relative).read_bytes())
    mutation(tmp_path / "blake/methods/intervals.py")
    with pytest.raises(EvidenceError, match="interval_illustration_source_"):
        build_interval_illustration(tmp_path)


def test_tokens_bind_actual_numerical_outputs_and_source_bytes() -> None:
    # Given the actual imported producer, when tokens are generated, then quantities
    # stay derived.
    result = build_interval_illustration(ROOT)
    tokens = interval_tokens()
    assert int(tokens["INTERVAL_EXAMPLE_RECORD_COUNT"]) == len(result.records)
    assert int(tokens["INTERVAL_EXAMPLE_UNION_LENGTH"]) == result.union_length
    assert int(tokens["INTERVAL_EXAMPLE_RAW_LENGTH"]) == result.summed_record_length
    assert int(tokens["INTERVAL_EXAMPLE_PAIRS"]) == result.strict_pairs
    assert tokens["CORE_INTERVAL_SOURCE_SHA256"] == result.source_binding_sha256
    assert all(tokens.values())
    for name, expected in result.source_bindings.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
