# Copyright (c) 2026 Daniel Ari Friedman
"""Parameterized proximity counts; aggregates never contain source contexts."""

from collections import Counter
from typing import Annotated, Literal, Optional

from pydantic import Field, FiniteFloat, model_validator

from .models import (
    FrozenModel,
    ResearchError,
)
from .models import (
    ProjectionCorpusPin as CorpusPin,
)
from .models import (
    ProjectionPassage as Passage,
)
from .search import matching_spans, search_passages
from .search_models import MIN_WINDOW_TERMS, SearchFacet, SearchRequest

Count = Annotated[int, Field(ge=0, strict=True)]
Rate = Annotated[FiniteFloat, Field(ge=0, strict=True)]


class TermCount(FrozenModel):
    term: str
    occurrences: Count


class ProximityRow(FrozenModel):
    request: SearchRequest
    eligible_source_units: Count
    eligible_word_tokens: Count
    eligible_source_families: Count
    matched_source_units: Count
    matched_source_families: Count
    total_occurrences: Count
    occurrences_per_10000_tokens: Optional[Rate]
    terms: tuple[TermCount, ...]
    facets: tuple[SearchFacet, ...]

    @model_validator(mode="after")
    def reconcile(self) -> "ProximityRow":
        facets = self.facets
        denominator = sum(f.word_tokens for f in facets)
        rate = self.total_occurrences * 10000 / denominator if denominator else None
        if (
            tuple(t.term for t in self.terms) != self.request.terms
            or len({(f.work_id, f.plane, f.role) for f in facets}) != len(facets)
            or any(
                self.request.role is not None and f.role != self.request.role
                for f in facets
            )
            or any(
                self.request.plane is not None and f.plane != self.request.plane
                for f in facets
            )
            or any(
                self.request.work_id is not None and f.work_id != self.request.work_id
                for f in facets
            )
            or sum(f.source_units for f in facets) != self.eligible_source_units
            or denominator != self.eligible_word_tokens
            or len({f.work_id for f in facets}) != self.eligible_source_families
            or sum(f.matched_units for f in facets) != self.matched_source_units
            or len({f.work_id for f in facets if f.matched_units})
            != self.matched_source_families
            or sum(f.occurrences for f in facets) != self.total_occurrences
            or sum(t.occurrences for t in self.terms) != self.total_occurrences
            or any(t.occurrences < self.matched_source_units for t in self.terms)
            or self.occurrences_per_10000_tokens != rate
            or any(
                f.matched_units > f.source_units
                or f.occurrences < len(self.terms) * f.matched_units
                or bool(f.occurrences) != bool(f.matched_units)
                or f.occurrences_per_10000_tokens
                != (f.occurrences * 10000 / f.word_tokens if f.word_tokens else None)
                for f in facets
            )
        ):
            raise ResearchError(
                "proximity_row", "Counts, labels, rates or denominators disagree"
            )
        return self


class ProximityGrid(FrozenModel):
    """An ordered ALL-request grid with explicit eligibility on each request."""

    requests: tuple[SearchRequest, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def reconcile(self) -> "ProximityGrid":
        first = self.requests[0]
        seen: set[tuple[tuple[str, ...], Optional[int]]] = set()
        previous: dict[tuple[str, ...], int] = {}
        for request in self.requests:
            key = (request.terms, request.window_words)
            width = request.window_words if request.window_words is not None else 201
            if (
                request.mode != "all"
                or request.limit != 1
                or request.context_chars != 0
                or not request.whole_words
                or len(request.terms) < MIN_WINDOW_TERMS
                or (request.role, request.plane, request.work_id)
                != (first.role, first.plane, first.work_id)
                or key in seen
                or width <= previous.get(request.terms, 0)
            ):
                raise ResearchError(
                    "proximity_grid",
                    "Require unique increasing ALL widths and one eligibility policy",
                )
            seen.add(key)
            previous[request.terms] = width
        return self


class ProximityStudy(FrozenModel):
    schema_version: Literal[1] = 1
    corpus_pin: CorpusPin
    scanned_source_units: Count
    grid: ProximityGrid
    rows: tuple[ProximityRow, ...]
    method: Literal[
        "literal ALL; original Unicode word-token envelopes; stored copies retained"
    ] = "literal ALL; original Unicode word-token envelopes; stored copies retained"

    @model_validator(mode="after")
    def reconcile(self) -> "ProximityStudy":
        if tuple(r.request for r in self.rows) != self.grid.requests:
            raise ResearchError(
                "proximity_grid", "Rows must match the declared ordered grid"
            )
        denominator = tuple(
            (f.work_id, f.plane, f.role, f.source_units, f.word_tokens)
            for f in self.rows[0].facets
        )
        previous: dict[tuple[str, ...], ProximityRow] = {}
        for row in self.rows:
            if row.eligible_source_units > self.scanned_source_units:
                raise ResearchError(
                    "proximity_request", "Eligible units exceed scanned units"
                )
            if (
                tuple(
                    (f.work_id, f.plane, f.role, f.source_units, f.word_tokens)
                    for f in row.facets
                )
                != denominator
            ):
                raise ResearchError(
                    "proximity_denominator", "Every width uses identical strata"
                )
            prior = previous.get(row.request.terms)
            if prior is not None and (
                prior.matched_source_units > row.matched_source_units
                or prior.matched_source_families > row.matched_source_families
                or any(
                    a.occurrences > b.occurrences
                    for a, b in zip(prior.terms, row.terms)
                )
                or any(
                    a.matched_units > b.matched_units or a.occurrences > b.occurrences
                    for a, b in zip(prior.facets, row.facets)
                )
            ):
                raise ResearchError(
                    "proximity_monotonicity", "Widening cannot remove matches"
                )
            previous[row.request.terms] = row
        return self


def build_proximity_study(
    passages: tuple[Passage, ...], pin: CorpusPin, grid: ProximityGrid
) -> ProximityStudy:
    """Build every requested width with the same explicitly declared eligibility."""
    rows: list[ProximityRow] = []
    for request in grid.requests:
        result = search_passages(passages, request)
        counts: Counter[str] = Counter()
        for passage in passages:
            if (
                (request.role is None or passage.text_role == request.role)
                and (request.plane is None or passage.source_plane == request.plane)
                and (request.work_id is None or passage.work_id == request.work_id)
            ):
                counts.update(
                    term for term, _, _ in matching_spans(passage.text, request)
                )
        tokens = sum(f.word_tokens for f in result.facets)
        rows.append(
            ProximityRow(
                request=request,
                eligible_source_units=result.eligible_source_units,
                eligible_word_tokens=tokens,
                eligible_source_families=len({f.work_id for f in result.facets}),
                matched_source_units=result.matched_source_units,
                matched_source_families=len(
                    {f.work_id for f in result.facets if f.matched_units}
                ),
                total_occurrences=result.total_occurrences,
                occurrences_per_10000_tokens=result.total_occurrences * 10000 / tokens
                if tokens
                else None,
                terms=tuple(
                    TermCount(term=term, occurrences=counts[term])
                    for term in request.terms
                ),
                facets=result.facets,
            )
        )
    return ProximityStudy(
        corpus_pin=pin, scanned_source_units=len(passages), grid=grid, rows=tuple(rows)
    )
