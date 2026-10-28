# Copyright (c) 2026 Daniel Ari Friedman
"""Literal-query requests and source-bound search results."""

from typing import Annotated, Final, Literal, Optional

from pydantic import Field, model_validator

from .models import Digest, FrozenModel, Plane, Role
from .models import ProjectionCorpusPin as CorpusPin

MIN_WINDOW_TERMS: Final = 2

SearchTerm = Annotated[str, Field(min_length=1, max_length=200)]


class SearchRequest(FrozenModel):
    terms: tuple[SearchTerm, ...] = Field(min_length=1, max_length=8)
    mode: Literal["any", "all"] = "any"
    window_words: Optional[int] = Field(default=None, ge=1, le=200, strict=True)
    role: Optional[Role] = Role.PRIMARY
    plane: Optional[Plane] = None
    work_id: Optional[str] = None
    whole_words: bool = True
    limit: int = Field(default=100, ge=1, le=1000)
    context_chars: int = Field(default=120, ge=0, le=500)

    @model_validator(mode="after")
    def validate_terms(self) -> "SearchRequest":
        if any(not term.strip() for term in self.terms):
            message = "Search terms must contain a non-whitespace character"
            raise ValueError(message)
        if len({term.casefold() for term in self.terms}) != len(self.terms):
            message = "Search terms must be distinct after Unicode casefold"
            raise ValueError(message)
        if self.window_words is not None and (
            self.mode != "all" or len(self.terms) < MIN_WINDOW_TERMS
        ):
            message = "window_words requires ALL mode and at least two distinct terms"
            raise ValueError(message)
        return self


class SearchHit(FrozenModel):
    term: str
    passage_id: str
    work_id: str
    title: str
    edition_id: str
    locator: str
    source_url: str
    rights: str
    plane: Plane
    role: Role
    text_sha256: Digest
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    expression: str
    context: str
    context_start: int = Field(ge=0)


class SearchFacet(FrozenModel):
    work_id: str
    plane: Plane
    role: Role
    source_units: int = Field(ge=1)
    matched_units: int = Field(ge=0)
    occurrences: int = Field(ge=0)
    word_tokens: int = Field(ge=0)
    occurrences_per_10000_tokens: Optional[float] = Field(default=None, ge=0)


class SearchResult(FrozenModel):
    schema_version: Literal[1] = 1
    request: SearchRequest
    corpus_pin: Optional[CorpusPin] = None
    scanned_source_units: int = Field(ge=0)
    eligible_source_units: int = Field(ge=0)
    total_occurrences: int = Field(ge=0)
    matched_source_units: int = Field(ge=0)
    returned_hits: int = Field(ge=0)
    truncated: bool
    facets: tuple[SearchFacet, ...]
    hits: tuple[SearchHit, ...]
