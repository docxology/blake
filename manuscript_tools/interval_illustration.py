"""Source-bound mathematical illustration of the public interval API.

Coordinates are arbitrary integers, not corpus observations or application clocks.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from itertools import combinations
from pathlib import Path
from typing import Final, Literal

from pydantic import ValidationError

from blake.methods.common import EvidenceError, FrozenModel
from blake.methods.intervals import (
    Interval,
    count_overlapping_pairs,
    interval_difference,
    interval_intersection,
    interval_measure,
    interval_support_at_least,
    interval_union,
)
from blake.methods.producer import SourceBinding, source_hashes

_BINDINGS: Final = (
    SourceBinding(
        "blake",
        (
            "__init__.py",
            "version.py",
            "methods/__init__.py",
            "methods/common.py",
            "methods/producer.py",
            "methods/intervals.py",
            "methods/storage.py",
            "methods/models.py",
            "methods/projection_models.py",
            "methods/bundle_models.py",
            "text_search/models.py",
        ),
    ),
    SourceBinding(
        "manuscript_tools",
        (
            "__init__.py",
            "interval_illustration.py",
            "interval_figure.py",
            "figure_dispatch.py",
            "core_architecture.py",
            "core_profile_figure.py",
        ),
    ),
)


class RefusalControl(FrozenModel):
    name: Literal["strict_scalar", "forged_order", "strict_threshold"]
    refused: Literal[True] = True
    exception: Literal["ValidationError", "EvidenceError"]
    code: str


class IntervalIllustration(FrozenModel):
    schema_version: Literal["1"] = "1"
    evidence_kind: str = (
        "Mathematical illustration; arbitrary integer units; no corpus observation"
    )
    records: tuple[Interval, ...]
    mask: tuple[Interval, ...]
    union: tuple[Interval, ...]
    intersection: tuple[Interval, ...]
    difference: tuple[Interval, ...]
    depth_two: tuple[Interval, ...]
    depth_three: tuple[Interval, ...]
    union_length: int
    summed_record_length: int
    strict_pairs: int
    pair_indices: tuple[tuple[int, int], ...]
    controls: tuple[RefusalControl, ...]
    source_bindings: dict[str, str]
    source_binding_sha256: str


def _refusal(
    name: Literal["strict_scalar", "forged_order", "strict_threshold"],
    action: Callable[[], int],
) -> RefusalControl:
    """Record an API refusal; acceptance aborts the illustration."""
    try:
        action()
    except ValidationError as error:
        return RefusalControl(
            name=name, exception="ValidationError", code=error.errors()[0]["type"]
        )
    except EvidenceError as error:
        return RefusalControl(name=name, exception="EvidenceError", code=error.code)
    raise EvidenceError(
        "interval_illustration_control", "Invalid control was accepted: " + name
    )


def build_interval_illustration(source_root: Path) -> IntervalIllustration:
    """Compute fixed didactic results through the actual imported, byte-bound API."""
    bindings = source_hashes(_BINDINGS)
    for name, expected in bindings.items():
        path = source_root / name
        if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
            raise EvidenceError("interval_illustration_source_missing", name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise EvidenceError("interval_illustration_source_changed", name)
    records = tuple(
        Interval(start=a, end=b) for a, b in ((1, 5), (3, 7), (3, 7), (7, 9), (4, 4))
    )
    mask = (Interval(start=4, end=8),)
    controls = (
        _refusal(
            "strict_scalar", lambda: interval_measure((Interval(start=True, end=3),))
        ),
        _refusal(
            "forged_order",
            lambda: interval_measure((Interval.model_construct(start=5, end=1),)),
        ),
        _refusal(
            "strict_threshold",
            lambda: interval_measure(interval_support_at_least(records, minimum=True)),
        ),
    )
    payload = json.dumps(bindings, sort_keys=True, separators=(",", ":")).encode()
    return IntervalIllustration(
        records=records,
        mask=mask,
        union=interval_union(records),
        intersection=interval_intersection(records, mask),
        difference=interval_difference(records, mask),
        depth_two=interval_support_at_least(records, minimum=2),
        depth_three=interval_support_at_least(records, minimum=3),
        union_length=interval_measure(records),
        summed_record_length=sum(p.end - p.start for p in records),
        strict_pairs=count_overlapping_pairs(records),
        pair_indices=tuple(
            (i + 1, j + 1)
            for i, j in combinations(range(len(records)), 2)
            if count_overlapping_pairs((records[i], records[j]))
        ),
        controls=controls,
        source_bindings=bindings,
        source_binding_sha256=hashlib.sha256(payload).hexdigest(),
    )


def _support_text(intervals: tuple[Interval, ...]) -> str:
    return "$" + r" \cup ".join(f"[{p.start},{p.end})" for p in intervals) + "$"


def interval_tokens() -> Mapping[str, str]:
    """Hydrate the mathematical example independently of saved analytical metrics."""
    result = build_interval_illustration(Path(__file__).resolve().parents[1])
    return dict(
        CORE_INTERVAL_SOURCE_FILES=str(len(result.source_bindings)),
        CORE_INTERVAL_SOURCE_SHA256=result.source_binding_sha256,
        INTERVAL_EXAMPLE_RECORD_COUNT=str(len(result.records)),
        INTERVAL_EXAMPLE_RECORDS=", ".join(_support_text((p,)) for p in result.records),
        INTERVAL_EXAMPLE_UNION=_support_text(result.union),
        INTERVAL_EXAMPLE_MASK=_support_text(result.mask),
        INTERVAL_EXAMPLE_INTERSECTION=_support_text(result.intersection),
        INTERVAL_EXAMPLE_DIFFERENCE=_support_text(result.difference),
        INTERVAL_EXAMPLE_UNION_LENGTH=str(result.union_length),
        INTERVAL_EXAMPLE_RAW_LENGTH=str(result.summed_record_length),
        INTERVAL_EXAMPLE_DEPTH_TWO=_support_text(result.depth_two),
        INTERVAL_EXAMPLE_DEPTH_TWO_LENGTH=str(interval_measure(result.depth_two)),
        INTERVAL_EXAMPLE_DEPTH_THREE=_support_text(result.depth_three),
        INTERVAL_EXAMPLE_PAIRS=str(result.strict_pairs),
        INTERVAL_BOUNDARY_CONTROLS=str(len(result.controls)),
    )
