"""Validated passage and query contracts, independent of downloaded corpus models."""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SearchError(ValueError):
    """An input cannot be searched or indexed without losing its evidence boundary."""


class SearchMode(str, Enum):
    WORD = "word"
    PHRASE = "phrase"
    LITERAL = "literal"
    VARIANTS = "variants"
    CONCEPT = "concept"


class Passage(BaseModel):
    """One bounded transcription passage, retaining edition and original expression."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=False)
    passage_id: str = Field(min_length=1)
    work_id: str = Field(min_length=1)
    author_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    edition_id: str = Field(min_length=1)
    edition: str = Field(min_length=1)
    copy_id: Optional[str] = None
    locator: str = Field(min_length=1)
    locator_kind: Literal["plate", "page", "folio", "file_lines", "section"]
    source_url: HttpUrl
    rights: str = Field(min_length=1)
    text_role: Literal["primary", "editorial", "unverified"]
    text: str = Field(min_length=1)
    source_sha256: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class Query(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    text: str = Field(min_length=1, max_length=1000)
    mode: SearchMode = SearchMode.WORD
    work_id: Optional[str] = None
    edition_id: Optional[str] = None
    author_id: str = "william-blake-1757-1827"
    limit: int = Field(default=20, ge=1, le=1000)


class MatchSpan(BaseModel):
    model_config = ConfigDict(frozen=True)
    start: int
    end: int
    matched_text: str
    expanded_term: str


class SearchHit(BaseModel):
    model_config = ConfigDict(frozen=True)
    passage: Passage
    text_sha256: str
    matches: tuple[MatchSpan, ...]


class SearchResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    query: Query
    interpretation: str
    expanded_terms: tuple[str, ...]
    total_passages: int
    total_occurrences: int
    truncated: bool
    hits: tuple[SearchHit, ...]


class Concept(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    terms: tuple[str, ...]
    rationale: str
    primary_links: tuple[HttpUrl, ...]
