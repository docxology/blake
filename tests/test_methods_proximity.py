"""Synthetic grid and denominator controls, with no application vocabulary."""

import pytest
from pydantic import ValidationError
from blake.methods.proximity import (
    ProximityGrid,
    ProximityStudy,
    ProximityRow,
    build_proximity_study,
)
from blake.methods.models import ProjectionCorpusPin, ResearchError, Role
from blake.methods.search_models import SearchRequest
from .test_methods_statistics import unit


def pin():
    return ProjectionCorpusPin(
        upstream_commit="synthetic",
        captured_manifest_sha256="0" * 64,
        projection_manifest_sha256="1" * 64,
        projection_relative_path="search/test",
        index_sha256="2" * 64,
        unresolved_images=0,
        scope_note="invented",
    )


def grid(**changes):
    return ProximityGrid(
        requests=tuple(
            SearchRequest.model_validate(
                dict(
                    terms=("seed", "leaf"),
                    mode="all",
                    window_words=width,
                    limit=1,
                    context_chars=0,
                )
                | changes
            )
            for width in (2, 4, None)
        )
    )


def test_width_grid_counts_original_tokens_and_copies():
    data = (
        unit("a", "seed x leaf"),
        unit("b", "seed leaf", "w2"),
        unit("c", "seed leaf", "w2"),
    )
    study = build_proximity_study(data, pin(), grid())
    assert [r.matched_source_units for r in study.rows] == [2, 3, 3]
    assert [r.total_occurrences for r in study.rows] == [4, 6, 6]
    assert [r.eligible_word_tokens for r in study.rows] == [7, 7, 7]
    assert ProximityStudy.model_validate_json(study.model_dump_json()) == study


def test_explicit_editorial_eligibility_and_empty_denominator():
    data = (
        unit("a", "seed leaf"),
        unit("b", "seed leaf", text_role="editorial", source_plane="erdman"),
    )
    study = build_proximity_study(
        data, pin(), grid(role=Role.EDITORIAL, plane="erdman")
    )
    assert study.rows[0].eligible_source_units == 1
    assert study.rows[0].total_occurrences == 2
    empty = build_proximity_study(data, pin(), grid(work_id="absent"))
    assert all(r.occurrences_per_10000_tokens is None for r in empty.rows)


@pytest.mark.parametrize(
    "changes",
    [
        {"mode": "any", "window_words": None},
        {"context_chars": 1},
        {"limit": 2},
        {"whole_words": False},
    ],
)
def test_grid_rejects_nonaggregate_requests(changes):
    with pytest.raises((ResearchError, ValidationError)):
        grid(**changes)


def test_grid_rejects_width_reversal_and_mixed_eligibility():
    original = grid()
    for requests in (
        original.requests[::-1],
        (original.requests[0], original.requests[0]),
        (original.requests[0], original.requests[1].model_copy(update={"role": None})),
    ):
        with pytest.raises(ResearchError, match="proximity_grid"):
            ProximityGrid(requests=requests)


@pytest.mark.parametrize(
    "changes",
    [
        {"total_occurrences": 99},
        {"eligible_word_tokens": 99},
        {"matched_source_units": 99},
        {"occurrences_per_10000_tokens": 0},
        {"terms": []},
    ],
)
def test_serialized_row_rejects_false_counts(changes):
    row = build_proximity_study((unit("a", "seed leaf"),), pin(), grid()).rows[0]
    with pytest.raises(ResearchError, match="proximity_row"):
        ProximityRow.model_validate(row.model_dump() | changes)


def test_serialized_study_rejects_missing_rows_and_false_scan():
    study = build_proximity_study((unit("a", "seed leaf"),), pin(), grid())
    for change in ({"rows": []}, {"scanned_source_units": 0}):
        with pytest.raises(ResearchError):
            ProximityStudy.model_validate(study.model_dump() | change)


def test_alternative_vocabulary_grid_requires_no_engine_changes():
    alternate = ProximityGrid(
        requests=tuple(
            SearchRequest(
                terms=("red", "green", "blue"),
                mode="all",
                window_words=width,
                limit=1,
                context_chars=0,
                role=None,
            )
            for width in (3, 5, None)
        )
    )
    study = build_proximity_study((unit("a", "red x green blue"),), pin(), alternate)
    assert [r.total_occurrences for r in study.rows] == [0, 3, 3]


@pytest.mark.parametrize(
    "text,code",
    [
        ("other word", "proximity_monotonicity"),
        ("seed other leaf", "proximity_denominator"),
    ],
)
def test_inconsistent_denominators_or_nonmonotonic_grid_are_rejected(text, code):
    original = build_proximity_study((unit("a", "seed leaf"),), pin(), grid())
    altered = build_proximity_study((unit("a", text),), pin(), grid())
    payload = original.model_dump(mode="json")
    payload["rows"][1] = altered.rows[1].model_dump()
    with pytest.raises(ResearchError, match=code):
        ProximityStudy.model_validate(payload)
