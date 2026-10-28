# Copyright (c) 2026 Daniel Ari Friedman
"""Typed, text-free outputs of copy-sensitive corpus statistics."""

from typing import Literal, Optional

from pydantic import Field, model_validator

from .models import Digest, FrozenModel, Plane, QuerySpec, ResearchError, Role


class SourceCensus(FrozenModel):
    plane: Plane
    role: Role
    units: int


class SourceUnit(FrozenModel):
    passage_id: str
    work_id: str
    title: str
    edition_id: str
    copy_id: Optional[str]
    text_sha256: Digest
    tokens: int
    occurrences: dict[str, int]


class Measure(FrozenModel):
    source_units: int = Field(ge=0)
    tokens: int = Field(ge=0)
    occurrences: int = Field(ge=0)
    matched_units: int = Field(ge=0)
    rate_per_10000_tokens: Optional[float]
    coverage_fraction: Optional[float]

    @model_validator(mode="after")
    def reconcile_denominators(self) -> "Measure":
        if self.matched_units > min(self.source_units, self.occurrences):
            raise ResearchError(
                "measure_membership", "Matched units exceed units or occurrences"
            )
        if not self.source_units and self.occurrences:
            raise ResearchError(
                "measure_membership", "An empty source set cannot contain matches"
            )
        rate = 10000 * self.occurrences / self.tokens if self.tokens else None
        coverage = self.matched_units / self.source_units if self.source_units else None
        if self.rate_per_10000_tokens != rate or self.coverage_fraction != coverage:
            raise ResearchError(
                "measure_denominator", "Stored rate or coverage differs from its counts"
            )
        return self


class QueryMeasure(FrozenModel):
    query_id: str
    measure: Measure


class Stratum(FrozenModel):
    dimension: Literal["work", "edition", "copy"]
    key: tuple[Optional[str], ...]
    titles: tuple[str, ...]
    member_passage_ids: tuple[str, ...]
    source_units: int
    tokens: int
    queries: tuple[QueryMeasure, ...]


class DuplicateGroup(FrozenModel):
    text_sha256: Digest
    passage_ids: tuple[str, ...]


class Omission(FrozenModel):
    omitted_work_id: str
    remaining: Measure


class QuerySummary(FrozenModel):
    query_id: str
    copy_retaining: Measure
    exact_text: Measure
    work_balanced_rate_per_10000_tokens: Optional[float]
    rate_work_groups: int
    work_balanced_coverage_fraction: float
    maximum_work_occurrence_share: Optional[float]
    work_occurrence_hhi: Optional[float]
    leave_one_work_out: tuple[Omission, ...]


class Cooccurrence(FrozenModel):
    universe: Literal["copy_retaining", "exact_text", "work_presence"]
    left_query: str
    right_query: str
    unit_count: int
    left_matches: int
    right_matches: int
    both_matches: int
    either_matches: int
    jaccard: Optional[float]
    right_given_left: Optional[float]
    left_given_right: Optional[float]
    lift: Optional[float]


class CorpusStatistics(FrozenModel):
    schema_version: Literal[1] = 1
    source_sha256: Digest
    query_sha256: Digest
    total_source_units: int
    primary_source_units: int
    primary_work_groups: int
    primary_tokens: int
    source_census: tuple[SourceCensus, ...]
    query_specs: tuple[QuerySpec, ...]
    units: tuple[SourceUnit, ...]
    deduplicated_passage_ids: tuple[str, ...]
    exact_duplicate_groups: tuple[DuplicateGroup, ...]
    strata: tuple[Stratum, ...]
    queries: tuple[QuerySummary, ...]
    cooccurrences: tuple[Cooccurrence, ...]
    tokenization: Literal[
        r"Python Unicode \w+; case retained; punctuation excluded"
    ] = r"Python Unicode \w+; case retained; punctuation excluded"
    interpretation: str = (
        "Primary reading units only. Rates count whole-word query occurrences per 10,000 "
        "Unicode word tokens. Work IDs group source families and recorded copies; "
        "work-balanced rates average "
        "positive-token work rates. Exact-text sensitivity retains the lexically first "
        "passage ID for identical text. Co-occurrence counts unit presence, not nearby words. "
        "Leave-one-work-out ranges describe this finite collection."
    )


class CountedStatistics(FrozenModel):
    """Descriptive counts with caller-declared retrieval and denominator semantics."""

    profile: str
    tokenization: str
    unicode_version: str
    inventory_sha256: Digest
    query_ids: tuple[str, ...]
    units: tuple[SourceUnit, ...]
    strata: tuple[Stratum, ...]
    queries: tuple[QuerySummary, ...]
    cooccurrences: tuple[Cooccurrence, ...]
