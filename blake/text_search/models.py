"""Validated passage and query contracts, independent of downloaded corpus models."""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

TextRole = Literal["primary", "editorial", "unverified"]
SourcePlane = Literal["reading", "erdman", "xml"]


class SearchError(ValueError):
    """An input cannot be searched or indexed without losing its evidence boundary."""


class SearchMode(str, Enum):
    WORD = "word"
    PHRASE = "phrase"
    LITERAL = "literal"
    VARIANTS = "variants"
    CONCEPT = "concept"


class SearchScope(str, Enum):
    PRIMARY = "primary"
    EXPLORATORY = "exploratory"


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
    text_role: TextRole
    source_plane: SourcePlane = "reading"
    text: str = Field(min_length=1)
    source_sha256: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def primary_reading_plane(self) -> "Passage":
        if self.text_role == "primary" and self.source_plane != "reading":
            raise SearchError("Primary passages must belong to the reading plane")
        return self


class Query(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    text: str = Field(min_length=1, max_length=1000)
    mode: SearchMode = SearchMode.WORD
    work_id: Optional[str] = None
    edition_id: Optional[str] = None
    author_id: Optional[str] = "william-blake-1757-1827"
    scope: SearchScope = SearchScope.PRIMARY
    text_role: Optional[TextRole] = None
    source_plane: Optional[SourcePlane] = None
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
    blake_primary_occurrences: int = 0
    occurrences_by_role: dict[str, int] = Field(default_factory=dict)
    occurrences_by_plane: dict[str, int] = Field(default_factory=dict)
    occurrences_by_author: dict[str, int] = Field(default_factory=dict)


class Concept(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    terms: tuple[str, ...]
    rationale: str
    primary_links: tuple[HttpUrl, ...]
