"""Ordinary JSON admission of standalone public review-plan contracts."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from blake.methods.review_planning import plan_review
from blake.methods.review_planning_models import ReviewPlan
from tests.review_planning_fixtures import make_hit
from tests.test_methods_review_planning import spec


@pytest.mark.parametrize("violation", ["cardinality", "overlap"])
def test_exclusions_refuse_when_json_membership_contradicts_the_plan(violation):
    # Given: a real plan whose ordinary JSON gains inconsistent exclusion facts.
    hits = tuple(make_hit(i, "alpha", f"p{i}") for i in range(2))
    raw = plan_review(hits, spec(1)).model_dump(mode="json")
    selected = raw["selected_hit_ids"][0]
    if violation == "cardinality":
        raw["spec"]["excluded_hit_ids"] = [
            next(hit.hit_id for hit in hits if hit.hit_id != selected)
        ]
    else:
        raw["spec"]["excluded_hit_ids"] = [selected]
        raw.update(excluded_hits=1, eligible_hits=1, eligible_units=1)
        raw["strata"][0].update(excluded_hits=1, eligible_hits=1)
    # When/Then: JSON parsing refuses the local contradiction without a hit pool.
    with pytest.raises(ValidationError, match="review_plan_counts"):
        ReviewPlan.model_validate_json(json.dumps(raw))
