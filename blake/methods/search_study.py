# Copyright (c) 2026 Daniel Ari Friedman
"""Aggregate literal-search comparisons with complete source-stratum denominators."""

from typing import Literal

from pydantic import Field, model_validator

from .models import FrozenModel, ResearchError
from .models import ProjectionCorpusPin as CorpusPin
from .models import ProjectionPassage as Passage
from .search import search_passages
from .search_models import SearchFacet, SearchRequest


class StudyQuery(FrozenModel):
    query_id: str
    terms: tuple[str, ...]
    eligible_source_units: int
    matched_source_units: int
    total_occurrences: int
    facets: tuple[SearchFacet, ...]


class SearchStudy(FrozenModel):
    schema_version: Literal[1] = 1
    corpus_pin: CorpusPin
    source_units: int = Field(ge=0)
    queries: tuple[StudyQuery, ...]
    method: str = (
        "Literal Unicode casefold; whole-word boundaries; exact whitespace; stored units retained."
    )

    @model_validator(mode="after")
    def reconcile_counts(self) -> "SearchStudy":
        if not self.queries or len({q.query_id for q in self.queries}) != len(self.queries):
            raise ResearchError("search_study_queries", "Require nonempty unique query identities")
        for query in self.queries:
            keys = {(f.work_id, f.plane, f.role) for f in query.facets}
            if (
                len(keys) != len(query.facets)
                or sum(f.source_units for f in query.facets) != self.source_units
                or query.eligible_source_units != self.source_units
                or sum(f.matched_units for f in query.facets) != query.matched_source_units
                or sum(f.occurrences for f in query.facets) != query.total_occurrences
                or any(
                    f.matched_units > f.source_units or f.matched_units > f.occurrences
                    for f in query.facets
                )
            ):
                raise ResearchError("search_study_counts", query.query_id)
        return self


def build_search_study(
    passages: tuple[Passage, ...],
    pin: CorpusPin,
    selected: tuple[tuple[str, tuple[str, ...]], ...],
) -> SearchStudy:
    """Count each selected literal query across every role without releasing contexts."""
    rows: list[StudyQuery] = []
    for identity, terms in selected:
        result = search_passages(passages, SearchRequest(terms=terms, role=None, limit=1))
        if sum(f.source_units for f in result.facets) != len(passages):
            raise ResearchError("search_study_denominator", identity)
        rows.append(
            StudyQuery(
                query_id=identity,
                terms=terms,
                eligible_source_units=result.eligible_source_units,
                matched_source_units=result.matched_source_units,
                total_occurrences=result.total_occurrences,
                facets=result.facets,
            )
        )
    return SearchStudy(corpus_pin=pin, source_units=len(passages), queries=tuple(rows))
