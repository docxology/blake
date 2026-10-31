# Copyright (c) 2026 Daniel Ari Friedman
"""Frozen contracts for declared review workloads, without authored decisions."""

from __future__ import annotations

from typing import Annotated, ClassVar, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from .common import Digest, EvidenceError, FrozenModel
from .models import Artifact

StratumField = Literal[
    "term_id",
    "group",
    "source_plane",
    "text_role",
    "work_id",
    "edition_id",
    "author_id",
]
UnitField = Literal["passage_id", "text_sha256"]
Count = Annotated[int, Field(ge=0, strict=True)]
PositiveCount = Annotated[int, Field(gt=0, strict=True)]


class _PlanningModel(FrozenModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True, extra="forbid", strict=True
    )


class ReviewSelection(_PlanningModel):
    """Caller-chosen effort and source-facet policy, not a sampling estimator."""

    target_size: PositiveCount
    seed: str
    strata_fields: tuple[StratumField, ...]
    unit_field: UnitField
    max_per_unit: PositiveCount

    @model_validator(mode="after")
    def declared_policy(self) -> ReviewSelection:
        if not self.seed.strip():
            raise EvidenceError("review_seed", "Declare a nonblank seed")
        if not self.strata_fields or len(set(self.strata_fields)) != len(
            self.strata_fields
        ):
            raise EvidenceError(
                "review_strata", "Declare unique nonempty strata fields"
            )
        return self


class ReviewPlanSpec(_PlanningModel):
    """Pins originate with the caller; the shared method cannot attest their origin."""

    source_run_sha256: Digest
    source_context_sha256: Digest
    selection: ReviewSelection
    excluded_hit_ids: tuple[Digest, ...] = ()

    @field_validator("excluded_hit_ids")
    @classmethod
    def canonical_exclusions(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise EvidenceError("review_duplicate_exclusion", "Excluded IDs form a set")
        return tuple(sorted(values))


class StratumPlan(_PlanningModel):
    key: tuple[str, ...]
    eligible_hits: Count
    excluded_hits: Count
    selected_hits: Count


class ReviewPlan(_PlanningModel):
    profile: Literal["hash-round-robin-review-v1"] = "hash-round-robin-review-v1"
    spec: ReviewPlanSpec
    source_pool_sha256: Digest
    candidate_hits: Count
    excluded_hits: Count
    eligible_hits: Count
    eligible_units: Count
    selected_hit_ids: tuple[Digest, ...]
    selected_hits: Count
    shortfall: Count
    strata: tuple[StratumPlan, ...]

    @model_validator(mode="after")
    def consistent_counts(self) -> ReviewPlan:
        keys = tuple(row.key for row in self.strata)
        if (
            self.candidate_hits != self.eligible_hits + self.excluded_hits
            or self.excluded_hits != len(self.spec.excluded_hit_ids)
            or not set(self.selected_hit_ids).isdisjoint(self.spec.excluded_hit_ids)
            or self.selected_hits != len(self.selected_hit_ids)
            or len(set(self.selected_hit_ids)) != self.selected_hits
            or self.selected_hits
            > min(self.eligible_hits, self.spec.selection.target_size)
            or self.eligible_units > self.eligible_hits
            or self.selected_hits
            > self.eligible_units * self.spec.selection.max_per_unit
            or self.shortfall != self.spec.selection.target_size - self.selected_hits
            or sum(row.eligible_hits for row in self.strata) != self.eligible_hits
            or sum(row.excluded_hits for row in self.strata) != self.excluded_hits
            or sum(row.selected_hits for row in self.strata) != self.selected_hits
            or any(row.selected_hits > row.eligible_hits for row in self.strata)
            or keys != tuple(sorted(set(keys)))
            or any(len(key) != len(self.spec.selection.strata_fields) for key in keys)
        ):
            raise EvidenceError("review_plan_counts", "Plan membership/counts disagree")
        return self


class ReviewBatchReceipt(_PlanningModel):
    schema_version: Literal[1] = 1
    profile: Literal["review-batch-v1"] = "review-batch-v1"
    source_run_sha256: Digest
    source_context_sha256: Digest
    source_pool_sha256: Digest
    candidate_hits: Count
    selected_hits: Count
    producer_sha256: Digest
    producer_sdk_version: str = Field(min_length=1)
    producer_python_version: str = Field(min_length=1)
    files: tuple[Artifact, ...]


class VerifiedReviewBatch(_PlanningModel):
    """Already checked receipt and plan; consumers must not reopen their paths."""

    receipt: ReviewBatchReceipt
    plan: ReviewPlan
