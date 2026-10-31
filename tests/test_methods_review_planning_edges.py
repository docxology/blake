"""Boundary and selection-unit controls beyond the small capacity oracle."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from blake.methods.models import EvidenceError
from blake.methods.review_batches import publish_review_batch, verify_review_batch
from blake.methods.review_planning import plan_review
from blake.methods.review_planning_models import ReviewPlan
from blake.methods.runs import digest
from tests.review_planning_fixtures import make_hit
from tests.test_methods_review_planning import spec


def test_units_when_two_witnesses_share_exact_text():
    # Given: distinct passage identities with the same declared whole text.
    first = make_hit(0, "alpha", "p0")
    second = make_hit(1, "alpha", "p1").model_copy(
        update={
            "text_sha256": first.text_sha256,
            "context": first.context,
        }
    )
    request = spec()
    # When: the caller explicitly chooses source units instead of exact-text units.
    per_passage = request.model_copy(
        update={
            "selection": request.selection.model_copy(
                update={"unit_field": "passage_id"}
            )
        }
    )
    # Then: the two policies have genuinely different declared capacities.
    assert plan_review((first, second), request).selected_hits == 1
    assert plan_review((first, second), per_passage).selected_hits == 2


def test_missing_facet_when_the_source_has_no_work_identifier():
    # Given: a legitimate unknown work field, without a fabricated replacement.
    hit = make_hit(0, "alpha", "p0").model_copy(update={"work_id": ""})
    request = spec()
    policy = request.selection.model_copy(update={"strata_fields": ("work_id",)})
    # When: that raw field is selected for grouping.
    result = plan_review((hit,), request.model_copy(update={"selection": policy}))
    # Then: its explicit empty-value stratum remains visible.
    assert result.strata[0].key == ("",)


@pytest.mark.parametrize("size", [1, 2, 20])
def test_all_reviewed_when_a_pool_has_no_remaining_candidates(size, tmp_path):
    # Given: a real batch request excluding its entire known pool.
    hits = tuple(make_hit(i, "alpha", f"p{i}") for i in range(2))
    request = spec(size).model_copy(
        update={"excluded_hit_ids": tuple(sorted(h.hit_id for h in hits))}
    )
    directory = tmp_path / "batch"
    # When: a bounded blank batch is produced and independently read back.
    publish_review_batch(hits, request, directory)
    result = verify_review_batch(
        directory, digest((directory / "run.json").read_bytes()), hits
    )
    # Then: no artificial candidate or decision fills the declared shortfall.
    assert result.plan.selected_hit_ids == ()
    assert result.plan.shortfall == size


@pytest.mark.parametrize("location", ["seed", "context"])
def test_unicode_refusal_when_values_cannot_encode_as_utf8(location, tmp_path):
    # Given: a Python string containing an unpaired surrogate.
    hit = make_hit(0, "alpha", "p0")
    request = spec()
    if location == "seed":
        request = request.model_copy(
            update={
                "selection": request.selection.model_copy(update={"seed": "\ud800"})
            }
        )
    else:
        hit = hit.model_copy(update={"context": "\ud800"})
    # When/Then: failure is named and occurs before reserving any output.
    with pytest.raises(EvidenceError, match="review_unicode"):
        publish_review_batch((hit,), request, tmp_path / "batch")
    assert not (tmp_path / "batch").exists()


def test_linked_parent_when_a_fresh_output_would_escape_the_declared_tree(tmp_path):
    # Given: a real directory and a symlink used as the output's parent.
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    # When/Then: no child is reserved through the symlink.
    with pytest.raises(EvidenceError, match="symlink_directory"):
        publish_review_batch((make_hit(0, "alpha", "p0"),), spec(), link / "batch")
    assert not (real / "batch").exists()


def test_seed_effect_when_the_same_pool_is_replanned_explicitly():
    # Given: twelve unique source units, more than the one-row effort budget.
    hits = tuple(make_hit(i, "alpha", f"p{i}") for i in range(12))
    base = spec(1)
    requests = tuple(
        base.model_copy(
            update={"selection": base.selection.model_copy(update={"seed": str(i)})}
        )
        for i in range(10)
    )
    # When: callers deliberately request different deterministic rankings.
    selected = {plan_review(hits, request).selected_hit_ids for request in requests}
    # Then: an unused seed or a fixed-first-row implementation would fail this.
    assert len(selected) > 1


@pytest.mark.parametrize(
    "change",
    [
        {"candidate_hits": 8},
        {"excluded_hits": 1},
        {"eligible_hits": 8},
        {"eligible_units": 0},
        {"selected_hits": 0},
        {"shortfall": 5},
        {"selected_hit_ids": []},
        {"strata": []},
        {"selected_hits": True},
    ],
)
def test_plan_count_refusal_when_a_json_summary_is_forged(change):
    # Given: real serialized output with one inconsistent count/membership field.
    raw = plan_review((make_hit(0, "alpha", "p0"),), spec()).model_dump(mode="json")
    raw.update(change)
    # When/Then: malformed serialized plans cannot bypass their count contract.
    with pytest.raises(ValidationError):
        ReviewPlan.model_validate_json(json.dumps(raw))
