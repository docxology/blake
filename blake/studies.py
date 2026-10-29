# Copyright (c) 2026 Daniel Ari Friedman
"""Uncapped, source-span lexical studies over an explicit application corpus.

Applications supply the vocabulary and interpret the retrieved candidates. This
module owns matching, provenance, complete zero cells and source denominators.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, ClassVar, Final, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .text_search import models as passage_models
from .text_search import normalize
from .text_search.models import SourcePlane, TextRole  # noqa: TC001

# Pydantic resolves these source-role types at class construction time.
if TYPE_CHECKING:
    from .text_search.models import Passage

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
ROLES: Final[tuple[TextRole, ...]] = ("primary", "editorial", "unverified")
PLANES: Final[tuple[SourcePlane, ...]] = ("reading", "erdman", "xml")
BLAKE_AUTHOR: Final = "william-blake-1757-1827"
CONTEXT_CHARACTERS: Final = 120


class StudyError(ValueError):
    """A vocabulary or corpus boundary prevents a reproducible study."""

    def __init__(self, code: str, detail: str) -> None:
        self.code: str = code
        self.detail: str = detail
        super().__init__(f"{code}: {detail}")


class FrozenModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")


class StudyTerm(FrozenModel):
    """One application-defined category with explicit token/phrase forms."""

    term_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    forms: tuple[str, ...] = Field(min_length=1)
    group: str = Field(min_length=1)
    note: str = ""

    @model_validator(mode="after")
    def searchable_forms(self) -> StudyTerm:
        for form in self.forms:
            if not normalize.tokens(form):
                code = "empty_normalized_form"
                raise StudyError(code, self.term_id)
        return self


class StudySpec(FrozenModel):
    """An exact vocabulary registry; its canonical JSON receives a digest."""

    study_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    terms: tuple[StudyTerm, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_term_ids(self) -> StudySpec:
        identities = tuple(term.term_id for term in self.terms)
        if len(set(identities)) != len(identities):
            code = "duplicate_term_id"
            raise StudyError(code, self.study_id)
        return self


class StudyHit(FrozenModel):
    """A category and original source span, awaiting application adjudication."""

    hit_id: Digest
    term_id: str
    group: str
    passage_id: str
    work_id: str
    title: str
    edition_id: str
    copy_id: Optional[str]
    locator: str
    source_url: str
    rights: str
    author_id: str
    text_role: TextRole
    source_plane: SourcePlane
    source_sha256: Optional[Digest]
    text_sha256: Digest
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    expression: str
    context: str
    blake_primary: bool


class StudyRow(FrozenModel):
    """One category/role/plane cell, including declared zero-result cells."""

    term_id: str
    group: str
    text_role: TextRole
    source_plane: SourcePlane
    occurrences: int = Field(ge=0)
    matched_passages: int = Field(ge=0)
    matched_editions: int = Field(ge=0)
    exact_text_groups: int = Field(ge=0)


class StudyDenominator(FrozenModel):
    """Captured source units and tokenizer tokens, not unique historical works."""

    text_role: TextRole
    source_plane: SourcePlane
    author_id: str
    passages: int = Field(ge=0)
    word_tokens: int = Field(ge=0)
    exact_text_groups: int = Field(ge=0)


class StudyResult(FrozenModel):
    """Every declared category-span candidate; no pagination or display cap."""

    schema_version: Literal[1] = 1
    study_id: str
    title: str
    spec_sha256: Digest
    normalization: str
    methods_sha256: Digest
    scanned_passages: int = Field(ge=0)
    hits: tuple[StudyHit, ...]
    rows: tuple[StudyRow, ...]
    denominators: tuple[StudyDenominator, ...]
    hit_definition: Literal["category-source-span"] = "category-source-span"


class StudySummary(FrozenModel):
    """Text-free aggregates; provider expression and context are omitted."""

    schema_version: Literal[1] = 1
    study_id: str
    title: str
    spec_sha256: Digest
    normalization: str
    methods_sha256: Digest
    scanned_passages: int = Field(ge=0)
    total_occurrences: int = Field(ge=0)
    blake_primary_occurrences: int = Field(ge=0)
    matched_passages: int = Field(ge=0)
    matched_editions: int = Field(ge=0)
    exact_text_groups: int = Field(ge=0)
    rows: tuple[StudyRow, ...]
    denominators: tuple[StudyDenominator, ...]
    hit_definition: Literal["category-source-span"] = "category-source-span"


@dataclass
class _Tally:
    """Mutable accumulator; snapshots become frozen public count records."""

    occurrences: int = 0
    passage_ids: set[str] = field(default_factory=set)
    editions: set[tuple[str, str]] = field(default_factory=set)
    text_hashes: set[str] = field(default_factory=set)


@dataclass
class _Denominator:
    """Mutable source-unit accumulator used only during a scan."""

    passages: int = 0
    word_tokens: int = 0
    text_hashes: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class _CompiledForm:
    term: StudyTerm
    tokens: tuple[str, ...]


@dataclass
class _Counts:
    """Mutable scan-owned maps, exposed only as frozen public rows."""

    tallies: dict[tuple[str, TextRole, SourcePlane], _Tally] = field(
        default_factory=lambda: defaultdict(_Tally)
    )
    sources: dict[tuple[TextRole, SourcePlane, str], _Denominator] = field(
        default_factory=lambda: defaultdict(_Denominator)
    )


def _canonical_sha(value: tuple[str | int, ...]) -> str:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _methods_sha() -> str:
    """Bind this matcher and the shared source contract and normalization code."""
    files = (
        ("blake/studies.py", Path(__file__)),
        ("blake/text_search/models.py", Path(passage_models.__file__)),
        ("blake/text_search/normalize.py", Path(normalize.__file__)),
    )
    bindings = tuple(
        (name, hashlib.sha256(path.read_bytes()).hexdigest()) for name, path in files
    )
    raw = json.dumps(bindings, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _count_rows(spec: StudySpec, counts: _Counts) -> tuple[StudyRow, ...]:
    rows: list[StudyRow] = []
    for term in spec.terms:
        for role in ROLES:
            for plane in PLANES:
                tally = counts.tallies[(term.term_id, role, plane)]
                rows.append(
                    StudyRow(
                        term_id=term.term_id,
                        group=term.group,
                        text_role=role,
                        source_plane=plane,
                        occurrences=tally.occurrences,
                        matched_passages=len(tally.passage_ids),
                        matched_editions=len(tally.editions),
                        exact_text_groups=len(tally.text_hashes),
                    )
                )
    return tuple(rows)


def _denominator_rows(
    passages: tuple[Passage, ...], counts: _Counts
) -> tuple[StudyDenominator, ...]:
    denominators: list[StudyDenominator] = []
    for author in sorted({passage.author_id for passage in passages}):
        for role in ROLES:
            for plane in PLANES:
                denominator = counts.sources[(role, plane, author)]
                denominators.append(
                    StudyDenominator(
                        text_role=role,
                        source_plane=plane,
                        author_id=author,
                        passages=denominator.passages,
                        word_tokens=denominator.word_tokens,
                        exact_text_groups=len(denominator.text_hashes),
                    )
                )
    return tuple(denominators)


def scan_passages(passages: tuple[Passage, ...], spec: StudySpec) -> StudyResult:
    """Scan each source once with explicit, precompiled whole-token forms.

    Punctuation separates tokens exactly as in ``text_search.normalize.spans``.
    Duplicate forms within a category produce one hit per span. Different
    categories may name the same span and remain separate retrieval candidates.
    No source role, author, edition or copy is inferred from a matched word.
    """
    identities = tuple(passage.passage_id for passage in passages)
    if len(set(identities)) != len(identities):
        code = "duplicate_passage_id"
        raise StudyError(code, spec.study_id)
    by_first: dict[str, list[_CompiledForm]] = defaultdict(list)
    for term in spec.terms:
        unique_forms = dict.fromkeys(normalize.tokens(form) for form in term.forms)
        for form in unique_forms:
            by_first[form[0]].append(_CompiledForm(term, form))

    counts = _Counts()
    hits: list[StudyHit] = []
    for passage in sorted(passages, key=lambda row: row.passage_id):
        source = normalize.tokenize(passage.text)
        source_tokens = tuple(token for token, _start, _end in source.terms)
        text_sha = hashlib.sha256(passage.text.encode("utf-8")).hexdigest()
        denominator = counts.sources[
            (passage.text_role, passage.source_plane, passage.author_id)
        ]
        denominator.passages += 1
        denominator.word_tokens += len(source.terms)
        denominator.text_hashes.add(text_sha)
        seen: set[tuple[str, int, int]] = set()
        for offset, (first, start, _end) in enumerate(source.terms):
            for compiled in by_first.get(first, ()):
                length = len(compiled.tokens)
                if source_tokens[offset : offset + length] != compiled.tokens:
                    continue
                end = source.terms[offset + length - 1][2]
                term = compiled.term
                identity = (term.term_id, start, end)
                if identity in seen:
                    continue
                seen.add(identity)
                tally = counts.tallies[
                    (term.term_id, passage.text_role, passage.source_plane)
                ]
                tally.occurrences += 1
                tally.passage_ids.add(passage.passage_id)
                tally.editions.add((passage.work_id, passage.edition_id))
                tally.text_hashes.add(text_sha)
                hits.append(
                    StudyHit(
                        hit_id=_canonical_sha(
                            (passage.passage_id, text_sha, term.term_id, start, end)
                        ),
                        term_id=term.term_id,
                        group=term.group,
                        passage_id=passage.passage_id,
                        work_id=passage.work_id,
                        title=passage.title,
                        edition_id=passage.edition_id,
                        copy_id=passage.copy_id,
                        locator=passage.locator,
                        source_url=str(passage.source_url),
                        rights=passage.rights,
                        author_id=passage.author_id,
                        text_role=passage.text_role,
                        source_plane=passage.source_plane,
                        source_sha256=passage.source_sha256,
                        text_sha256=text_sha,
                        start=start,
                        end=end,
                        expression=passage.text[start:end],
                        context=passage.text[
                            max(0, start - CONTEXT_CHARACTERS) : end
                            + CONTEXT_CHARACTERS
                        ],
                        blake_primary=(
                            passage.author_id == BLAKE_AUTHOR
                            and passage.text_role == "primary"
                            and passage.source_plane == "reading"
                        ),
                    )
                )

    registry = json.dumps(
        spec.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return StudyResult(
        study_id=spec.study_id,
        title=spec.title,
        spec_sha256=hashlib.sha256(registry).hexdigest(),
        normalization=normalize.NORMALIZATION,
        methods_sha256=_methods_sha(),
        scanned_passages=len(passages),
        hits=tuple(hits),
        rows=_count_rows(spec, counts),
        denominators=_denominator_rows(passages, counts),
    )


def summarize(result: StudyResult) -> StudySummary:
    """Return aggregates without source expression, contexts or full passages."""
    return StudySummary(
        study_id=result.study_id,
        title=result.title,
        spec_sha256=result.spec_sha256,
        normalization=result.normalization,
        methods_sha256=result.methods_sha256,
        scanned_passages=result.scanned_passages,
        total_occurrences=len(result.hits),
        blake_primary_occurrences=sum(hit.blake_primary for hit in result.hits),
        matched_passages=len({hit.passage_id for hit in result.hits}),
        matched_editions=len({(hit.work_id, hit.edition_id) for hit in result.hits}),
        exact_text_groups=len({hit.text_sha256 for hit in result.hits}),
        rows=result.rows,
        denominators=result.denominators,
    )
