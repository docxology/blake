"""Versioned normalization with offsets into unchanged original source text."""

import re
import unicodedata
from array import array
from dataclasses import dataclass
from typing import Final

from .models import MatchSpan

NORMALIZATION: Final = 'nfkc-casefold-source-spans-v2'
TOKEN: Final = re.compile(r'\w+', re.UNICODE)


@dataclass(frozen=True)  # Python 3.9 compatibility: dataclass slots require 3.10.
class SearchText:
    """One normalized token stream bound to its original expression."""
    original: str
    terms: tuple[tuple[str, int, int], ...]


def tokenize(text: str) -> SearchText:
    """Normalize composable clusters, retaining source offsets through expansion."""
    pieces = []
    starts = array('Q')
    ends = array('Q')
    cluster_start = 0
    cluster = ''
    normalized = ''

    def append_piece(end: int) -> None:
        piece = normalized.casefold().replace('’', "'")
        pieces.append(piece)
        starts.extend([cluster_start] * len(piece))
        ends.extend([end] * len(piece))

    for offset, character in enumerate(text):
        single = unicodedata.normalize('NFKC', character)
        combined = unicodedata.normalize('NFKC', cluster + character)
        if cluster and (unicodedata.combining(character) or combined != normalized + single):
            cluster += character
            normalized = combined
        else:
            if cluster:
                append_piece(offset)
            cluster_start = offset
            cluster = character
            normalized = single
    if cluster:
        append_piece(len(text))
    value = ''.join(pieces)
    return SearchText(text, tuple((match.group(), starts[match.start()], ends[match.end() - 1]) for match in TOKEN.finditer(value)))


def tokens(text: str) -> tuple[str, ...]:
    return tuple(term for term, _start, _end in tokenize(text).terms)


def spans(source: SearchText, term: str) -> tuple[MatchSpan, ...]:
    """Find contiguous normalized tokens and return their unchanged source spans."""
    wanted = tokens(term)
    found = []
    for offset in range(len(source.terms) - len(wanted) + 1):
        window = source.terms[offset:offset + len(wanted)]
        if tuple(token for token, _start, _end in window) == wanted:
            start, end = window[0][1], window[-1][2]
            found.append(MatchSpan(start=start, end=end, matched_text=source.original[start:end], expanded_term=term))
    return tuple(found)
