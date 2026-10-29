# Copyright (c) 2026 Daniel Ari Friedman
"""Search literal terms across verified corpus units with original-text offsets."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import hashlib
import re
from bisect import bisect_left, bisect_right
from collections import defaultdict
from functools import cache
from typing import NamedTuple

from .corpus import load_import
from .models import Plane, ResearchError, Role
from .models import ProjectionCorpusPin as CorpusPin
from .models import ProjectionPassage as Passage
from .search_models import SearchFacet, SearchHit, SearchRequest, SearchResult


class _Expansion(NamedTuple):
    folded_start: int
    folded_end: int
    original_start: int
    delta: int


@cache
def _expansion_pattern() -> re.Pattern[str]:
    """Compile the runtime Unicode characters whose casefold expands."""
    characters = "".join(
        chr(codepoint) for codepoint in range(0x110000) if len(chr(codepoint).casefold()) > 1
    )
    return re.compile("[" + re.escape(characters) + "]")


def _fold_text(text: str) -> tuple[str, tuple[_Expansion, ...]]:
    """Record only casefold expansions, rather than one map entry per character."""
    folded_text = text.casefold()
    # Unicode casefold mappings preserve or expand codepoints; they do not delete them.
    if len(folded_text) == len(text):
        return folded_text, ()
    expansions: list[_Expansion] = []
    delta = 0
    for match in _expansion_pattern().finditer(text):
        index = match.start()
        width = len(match.group().casefold())
        start = index + delta
        delta += width - 1
        expansions.append(_Expansion(start, start + width, index, delta))
    return folded_text, tuple(expansions)


def _original_offset(
    position: int, starts: tuple[int, ...], expansions: tuple[_Expansion, ...]
) -> int | None:
    """Translate a folded boundary; reject a boundary inside an expanded character."""
    index = bisect_right(starts, position) - 1
    if index < 0:
        return position
    expansion = expansions[index]
    if position == expansion.folded_start:
        return expansion.original_start
    if position < expansion.folded_end:
        return None
    return position - expansion.delta


def _word(character: str) -> bool:
    return character.isalnum() or character == "_"


def _spans(
    text: str, terms: tuple[str, ...], *, whole_words: bool
) -> tuple[tuple[str, int, int], ...]:
    folded, expansions = _fold_text(text)
    starts = tuple(expansion.folded_start for expansion in expansions)
    result: list[tuple[str, int, int]] = []
    for term in terms:
        needle = term.casefold()
        cursor = 0
        while (start := folded.find(needle, cursor)) >= 0:
            end = start + len(needle)
            original_start = _original_offset(start, starts, expansions)
            original_end = _original_offset(end, starts, expansions)
            left_boundary = start == 0 or not _word(folded[start - 1])
            right_boundary = end == len(folded) or not _word(folded[end])
            if (
                original_start is not None
                and original_end is not None
                and (not whole_words or (left_boundary and right_boundary))
            ):
                result.append((term, original_start, original_end))
                cursor = end
            else:
                cursor = start + 1
    return tuple(result)


def _window_spans(
    text: str, spans: tuple[tuple[str, int, int], ...], request: SearchRequest
) -> tuple[tuple[str, int, int], ...]:
    """Sweep feasible integer window origins; retain every participating occurrence.

    A span permits origins [right_token_rank - W, left_token_rank]. Complete
    coverage by all terms defines the union of feasible windows. Interval
    intersection then finds participants without enumerating term combinations.
    """
    width = request.window_words
    if width is None:
        return spans
    tokens = tuple(re.finditer(r"\w+", text))
    starts = tuple(token.start() for token in tokens)
    ends = tuple(token.end() for token in tokens)
    intervals: list[tuple[int, int]] = []
    events: list[tuple[int, str, int]] = []
    for term, start, end in spans:
        lower = bisect_left(starts, end) - width
        upper = bisect_right(ends, start)
        intervals.append((lower, upper))
        if lower <= upper:
            events.extend(((lower, term, 1), (upper + 1, term, -1)))
    counts = dict.fromkeys(request.terms, 0)
    complete: list[tuple[int, int]] = []
    active = 0
    previous: int | None = None
    for position, term, delta in sorted(events):
        if previous is not None and previous < position and active == len(counts):
            complete.append((previous, position - 1))
        before = counts[term]
        counts[term] += delta
        active += int(counts[term] > 0) - int(before > 0)
        previous = position
    complete_ends = tuple(end for _, end in complete)
    result: list[tuple[str, int, int]] = []
    for span_index, span in enumerate(spans):
        lower, upper = intervals[span_index]
        index = bisect_left(complete_ends, lower)
        if lower <= upper and index < len(complete) and complete[index][0] <= upper:
            result.append(span)
    return tuple(result)


def matching_spans(text: str, request: SearchRequest) -> tuple[tuple[str, int, int], ...]:
    """Return qualifying (term, original start, original end) tuples before any hit cap.

    Literal matches retain original Unicode-codepoint offsets. ALL requires every
    distinct term in this source unit; an optional word window retains only
    occurrences participating in at least one complete qualifying window.
    """
    spans = _spans(text, request.terms, whole_words=request.whole_words)
    if request.mode == "all" and len({term for term, _, _ in spans}) != len(request.terms):
        return ()
    return _window_spans(text, spans, request)


def _eligible(passage: Passage, request: SearchRequest) -> bool:
    return (
        (request.role is None or passage.text_role == request.role)
        and (request.plane is None or passage.source_plane == request.plane)
        and (request.work_id is None or passage.work_id == request.work_id)
    )


def _hit(passage: Passage, term: str, start: int, end: int, context_chars: int) -> SearchHit:
    context_start = max(0, start - context_chars)
    return SearchHit(
        term=term,
        passage_id=passage.passage_id,
        work_id=passage.work_id,
        title=passage.title,
        edition_id=passage.edition_id,
        locator=passage.locator,
        source_url=passage.source_url,
        rights=passage.rights,
        plane=passage.source_plane,
        role=passage.text_role,
        text_sha256=hashlib.sha256(passage.text.encode()).hexdigest(),
        start=start,
        end=end,
        expression=passage.text[start:end],
        context=passage.text[context_start : end + context_chars],
        context_start=context_start,
    )


def search_passages(passages: tuple[Passage, ...], request: SearchRequest) -> SearchResult:
    """Count every eligible literal match before limiting the returned hit records."""
    if len({passage.passage_id for passage in passages}) != len(passages):
        raise ResearchError("duplicate_passage_id", "Search requires unique source-unit IDs")
    eligible = tuple(passage for passage in passages if _eligible(passage, request))
    grouped: defaultdict[tuple[str, Plane, Role], list[Passage]] = defaultdict(list)
    matches: dict[str, tuple[tuple[str, int, int], ...]] = {}
    for passage in eligible:
        grouped[(passage.work_id, passage.source_plane, passage.text_role)].append(passage)
        matches[passage.passage_id] = matching_spans(passage.text, request)
    facets: list[SearchFacet] = []
    for (work_id, plane, role), units in sorted(grouped.items()):
        tokens = sum(sum(1 for _ in re.finditer(r"\w+", passage.text)) for passage in units)
        occurrences = sum(len(matches[passage.passage_id]) for passage in units)
        facets.append(
            SearchFacet(
                work_id=work_id,
                plane=plane,
                role=role,
                source_units=len(units),
                matched_units=sum(bool(matches[passage.passage_id]) for passage in units),
                occurrences=occurrences,
                word_tokens=tokens,
                occurrences_per_10000_tokens=occurrences * 10000 / tokens if tokens else None,
            )
        )
    ordered = sorted(
        (passage.passage_id, start, end, term)
        for passage in eligible
        for term, start, end in matches[passage.passage_id]
    )
    by_id = {passage.passage_id: passage for passage in eligible}
    hits = tuple(
        _hit(by_id[identity], term, start, end, request.context_chars)
        for identity, start, end, term in ordered[: request.limit]
    )
    return SearchResult(
        request=request,
        scanned_source_units=len(passages),
        eligible_source_units=len(eligible),
        total_occurrences=len(ordered),
        matched_source_units=sum(bool(spans) for spans in matches.values()),
        returned_hits=len(hits),
        truncated=len(ordered) > len(hits),
        facets=tuple(facets),
        hits=hits,
    )


def search_corpus(directory: Path, expected_pin: CorpusPin, request: SearchRequest) -> SearchResult:
    """Verify the pinned local import before searching its complete source projection."""
    _, passages = load_import(directory, expected_pin)
    result = search_passages(passages, request)
    return result.model_copy(update={"corpus_pin": expected_pin})


# Public compatibility seam for historical literal-span consumers.
literal_spans = _spans
