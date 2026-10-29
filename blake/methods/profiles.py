# Copyright (c) 2026 Daniel Ari Friedman
"""Named retrieval semantics; profile metadata never enters historical query hashes."""

import platform
import unicodedata
from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from .common import FrozenModel, StringEnum


class RetrievalProfile(StringEnum):
    REGEX_WORDS_V1 = "regex-ignorecase-source-spans-v1"
    LITERAL_CASEFOLD_V1 = "casefold-literal-source-spans-v1"
    NFKC_TOKENS_V2 = "nfkc-casefold-source-spans-v2"


class ProfileDescription(FrozenModel):
    profile: RetrievalProfile
    normalization: str
    boundaries: str
    variants: str
    tokens: str


class RuntimeProfile(FrozenModel):
    semantics: ProfileDescription
    python: str
    unicode: str


PROFILES: Final[Mapping[RetrievalProfile, ProfileDescription]] = MappingProxyType(
    {
        RetrievalProfile.REGEX_WORDS_V1: ProfileDescription(
            profile=RetrievalProfile.REGEX_WORDS_V1,
            normalization="Python re.IGNORECASE; source expression unchanged",
            boundaries=r"(?<!\w) explicit escaped alternatives (?!\w)",
            variants=(
                "Nonoverlapping regex alternation; concordance length-only tie order "
                + "and statistics length-then-lexical tie order remain distinct"
            ),
            tokens=r"Original-text Python Unicode \w+ runs",
        ),
        RetrievalProfile.LITERAL_CASEFOLD_V1: ProfileDescription(
            profile=RetrievalProfile.LITERAL_CASEFOLD_V1,
            normalization="Unicode casefold with original-codepoint boundary mapping",
            boundaries=(
                "Original-source word boundaries; " + "exact punctuation and whitespace"
            ),
            variants=(
                "Independent nonoverlapping literal terms; "
                + "ANY/ALL and complete word windows"
            ),
            tokens=r"Original-text Python Unicode \w+ runs",
        ),
        RetrievalProfile.NFKC_TOKENS_V2: ProfileDescription(
            profile=RetrievalProfile.NFKC_TOKENS_V2,
            normalization="NFKC then Unicode casefold with original-source spans",
            boundaries=(
                "Contiguous normalized tokens; "
                + "punctuation and line breaks separate tokens"
            ),
            variants=(
                "Explicit forms; equivalent same-category spans deduplicated; "
                + "category overlap retained"
            ),
            tokens=r"Unicode \w+ runs after normalization",
        ),
    }
)


def describe_profile(profile: RetrievalProfile) -> ProfileDescription:
    """Return an explicit contract rather than choosing semantics from input shape."""
    return PROFILES[profile]


def runtime_profile(profile: RetrievalProfile) -> RuntimeProfile:
    """Record the actual runtime separately from stable semantic identity."""
    return RuntimeProfile(
        semantics=describe_profile(profile),
        python=platform.python_version(),
        unicode=unicodedata.unidata_version,
    )
