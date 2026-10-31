"""Independent invariants and refusing cases for bounded review workloads."""

from __future__ import annotations

from collections import Counter
from itertools import permutations, product

import pytest
from pydantic import ValidationError

from blake.methods.models import EvidenceError
from blake.methods.review_planning import plan_review
from blake.methods.review_planning_models import (
    ReviewPlan,
    ReviewPlanSpec,
    ReviewSelection,
)
from tests.review_planning_fixtures import make_hit


def spec(size: int = 3, cap: int = 1) -> ReviewPlanSpec:
    return ReviewPlanSpec(
        source_run_sha256="a" * 64,
        source_context_sha256="b" * 64,
        selection=ReviewSelection(
            target_size=size,
            seed="golden",
            strata_fields=("term_id",),
            unit_field="text_sha256",
            max_per_unit=cap,
        ),
    )


def test_golden_round_robin_when_independent_units_are_available():
    # Given: byte-grammar ranks independently calculated before implementation.
    hits = tuple(make_hit(i, "alpha" if i < 3 else "beta", f"p{i}") for i in range(6))
    # When: a three-row workload is planned.
    result = plan_review(hits, spec())
    # Then: stratum order beta/alpha and within-stratum ranks select 5, 2, 4.
    assert result.selected_hit_ids == tuple(hits[i].hit_id for i in (5, 2, 4))
    assert (result.candidate_hits, result.eligible_hits, result.selected_hits) == (
        6,
        6,
        3,
    )
    assert result.shortfall == 0


def test_input_permutations_when_the_same_pool_is_provided():
    # Given: every ordering of four source-bound candidates.
    hits = tuple(make_hit(i, str(i % 2), f"p{i}") for i in range(4))
    expected = plan_review(hits, spec())
    # When/Then: neither ranks nor the all-field pool digest depend on order.
    assert all(plan_review(order, spec()) == expected for order in permutations(hits))


def test_capacity_oracle_when_units_repeat_across_strata():
    # Given: all small assignments of five hits to two strata and two units.
    for assignments in product(range(4), repeat=5):
        hits = tuple(
            make_hit(i, str(x // 2), str(x % 2)) for i, x in enumerate(assignments)
        )
        for cap in (1, 2):
            expected = min(
                4,
                sum(min(cap, n) for n in Counter(x % 2 for x in assignments).values()),
            )
            # When: the planner visits potentially competing strata.
            result = plan_review(hits, spec(4, cap))
            selected = {
                h.hit_id: h for h in hits if h.hit_id in result.selected_hit_ids
            }
            # Then: only the declared unit capacity creates a shortfall.
            assert result.selected_hits == expected
            assert result.shortfall == 4 - expected
            assert (
                max(Counter(h.text_sha256 for h in selected.values()).values()) <= cap
            )


def test_exclusions_when_one_entire_stratum_is_already_reviewed():
    # Given: a reviewed alpha stratum and one remaining beta candidate.
    hits = (make_hit(0, "alpha", "p0"), make_hit(1, "beta", "p1"))
    request = spec().model_copy(update={"excluded_hit_ids": (hits[0].hit_id,)})
    # When: review planning receives the valid immutable selection spec.
    result = plan_review(hits, request)
    # Then: reviewed IDs stay excluded and the exhausted stratum remains visible.
    assert result.selected_hit_ids == (hits[1].hit_id,)
    assert (result.excluded_hits, result.eligible_hits, result.shortfall) == (1, 1, 2)
    assert [(s.key, s.eligible_hits, s.excluded_hits) for s in result.strata] == [
        (("alpha",), 0, 1),
        (("beta",), 1, 0),
    ]


def test_empty_pool_when_no_candidates_are_supplied():
    # Given/When: an explicitly empty pool, not a failed source read.
    result = plan_review((), spec())
    # Then: SHA256(empty bytes) and the full shortfall are explicit.
    assert (
        result.source_pool_sha256
        == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    assert (
        result.selected_hits,
        result.eligible_units,
        result.shortfall,
        result.strata,
    ) == (0, 0, 3, ())


def test_full_pool_binding_when_an_unselected_context_changes():
    # Given: enough unique source units for some candidates to remain unselected.
    hits = tuple(make_hit(i, "alpha", f"p{i}") for i in range(6))
    original = plan_review(hits, spec(1))
    index = next(
        i for i, h in enumerate(hits) if h.hit_id not in original.selected_hit_ids
    )
    changed = tuple(
        h.model_copy(update={"context": "changed"}) if i == index else h
        for i, h in enumerate(hits)
    )
    # When: only an unselected context changes, preserving source witness identity.
    result = plan_review(changed, spec(1))
    # Then: all supplied evidence, not merely selected IDs, enters the binding.
    assert result.source_pool_sha256 != original.source_pool_sha256
    assert result.selected_hit_ids == original.selected_hit_ids


@pytest.mark.parametrize(
    "field", ["title", "source_url", "text_sha256", "text_role", "blake_primary"]
)
def test_conflicting_passage_identity_when_a_source_witness_disagrees(field):
    # Given: two occurrences claiming the same passage with conflicting metadata.
    first = make_hit(0, "alpha", "p0")
    values = {
        "title": "changed",
        "source_url": "https://different.invalid",
        "text_sha256": "f" * 64,
        "text_role": "editorial",
        "blake_primary": True,
    }
    second = make_hit(1, "beta", "p0").model_copy(update={field: values[field]})
    # When/Then: the planning boundary refuses that cross-record contradiction.
    with pytest.raises(EvidenceError, match="review_passage_identity"):
        plan_review((first, second), spec())


@pytest.mark.parametrize(
    "change", [{"passage_id": " "}, {"term_id": ""}, {"start": 4, "end": 4}]
)
def test_identity_refusal_when_historical_scalar_fields_are_insufficient(change):
    # Given: ordinarily admitted StudyHit scalars that violate new planning semantics.
    hit = make_hit(0, "alpha", "p0").model_copy(update=change)
    # When/Then: invalid source identity or span cannot create a plan.
    with pytest.raises(EvidenceError, match="review_candidate"):
        plan_review((hit,), spec())


def test_membership_refusals_when_ids_duplicate_or_exclusions_are_unknown():
    # Given: one valid hit and a separately admitted exclusion spec.
    hit = make_hit(0, "alpha", "p0")
    request = spec().model_copy(update={"excluded_hit_ids": ("f" * 64,)})
    # When/Then: neither duplicate evidence nor unknown exclusions are dropped.
    with pytest.raises(EvidenceError, match="review_duplicate_hit"):
        plan_review((hit, hit), spec())
    with pytest.raises(EvidenceError, match="review_unknown_exclusion"):
        plan_review((hit,), request)


@pytest.mark.parametrize(
    "change",
    [
        {"target_size": 0},
        {"target_size": True},
        {"max_per_unit": False},
        {"seed": " "},
        {"strata_fields": ()},
        {"strata_fields": ("term_id", "term_id")},
        {"strata_fields": ("copy_id",)},
    ],
)
def test_selection_admission_when_json_values_violate_the_declared_policy(change):
    # Given: real raw JSON for a policy, without model-construction bypasses.
    import json

    raw = spec().selection.model_dump(mode="json")
    raw.update(change)
    # When/Then: strict scalar and semantic policy errors refuse at admission.
    with pytest.raises(ValidationError):
        ReviewSelection.model_validate_json(json.dumps(raw))


def test_duplicate_exclusion_when_an_unordered_set_repeats_a_member():
    # Given: actual JSON for a request repeating the same excluded ID.
    import json

    raw = spec().model_dump(mode="json")
    raw["excluded_hit_ids"] = ["a" * 64, "a" * 64]
    # When/Then: duplicate membership is not silently deduplicated.
    with pytest.raises(ValidationError):
        ReviewPlanSpec.model_validate_json(json.dumps(raw))


def test_plan_admission_when_counts_cannot_describe_the_selected_ids():
    # Given: an actual plan JSON with a forged selected count.
    import json

    raw = plan_review((make_hit(0, "alpha", "p0"),), spec()).model_dump(mode="json")
    raw["selected_hits"] = 2
    # When/Then: a malformed summary cannot be admitted as a completed plan.
    with pytest.raises(ValidationError):
        ReviewPlan.model_validate_json(json.dumps(raw))
