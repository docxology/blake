# Copyright (c) 2026 Daniel Ari Friedman
"""Build a self-contained offline workspace under explicit application policy."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

import base64
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from html import escape
from importlib.resources import files
from typing import Final

from .corpus import load_import
from .models import ProjectionCorpusPin as CorpusPin
from .models import ProjectionPassage as Passage
from .models import ResearchError
from .storage import digest, write_new

RESOURCE_NAMES: Final = ("corpus-search.html", "corpus-search.css", "corpus-search.js")
SEMANTICS: Final = (
    "Unicode casefold; literal strings; exact whitespace; Unicode alphanumeric/underscore "
    "word boundaries; nonoverlapping matches per term; original Unicode-codepoint offsets. "
    "ALL requires every term in one stored source unit. "
    "Optional ALL window (1-200 words, at least two distinct terms) counts only occurrences "
    "in a complete window, including phrase tokens; overlapping terms are allowed. "
    "Word tokens are original-text Unicode alphanumeric/underscore runs. "
    "Facets count all qualifying matches before the hit cap."
)


def unicode_search_tables() -> tuple[dict[str, str], tuple[tuple[int, int], ...]]:
    """Export this Python runtime's case folding and word membership for browser parity."""
    folding: dict[str, str] = {}
    ranges: list[tuple[int, int]] = []
    start: int | None = None
    for code in range(sys.maxunicode + 1):
        character = chr(code)
        folded = character.casefold()
        if folded != character:
            folding[character] = folded
        word = character.isalnum() or character == "_"
        if word and start is None:
            start = code
        if not word and start is not None:
            ranges.append((start, code - 1))
            start = None
    if start is not None:
        ranges.append((start, sys.maxunicode))
    return folding, tuple(ranges)


def json_script(value: object) -> str:
    """Keep source strings inert inside an HTML script data block."""
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _source_data(passages: tuple[Passage, ...]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for passage in sorted(passages, key=lambda unit: unit.passage_id):
        record: dict[str, object] = passage.model_dump(mode="json")
        record["text_sha256"] = hashlib.sha256(passage.text.encode()).hexdigest()
        record["word_tokens"] = sum(1 for _ in re.finditer(r"\w+", passage.text))
        result.append(record)
    return result


def csp_hash(value: str) -> str:
    return base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()


@dataclass(frozen=True)
class WorkspaceBranding:
    """Application-owned visible labels, always HTML-escaped."""

    title: str
    brand: str
    footer: str


def _validate_output(output: Path, private_output_root: Path) -> None:
    """Reject unsafe or occupied destinations before consuming source bytes."""
    if any(
        path.is_symlink()
        for path in (output, *output.parents, private_output_root, *private_output_root.parents)
    ):
        raise ResearchError("symlink_output", str(output))
    if ".." in output.parts or not output.absolute().is_relative_to(private_output_root.absolute()):
        raise ResearchError("private_output_required", str(private_output_root))
    if output.exists():
        raise ResearchError("occupied_output", str(output))


def build_search_workspace_passages(  # noqa: PLR0913 - explicit application custody policy
    passages: tuple[Passage, ...],
    pin: CorpusPin,
    output: Path,
    *,
    branding: WorkspaceBranding,
    producer_version: str,
    private_output_root: Path,
    revalidate: Callable[[], None],
    resource_directory: Path | None = None,
) -> Path:
    """Publish full texts only inside the caller's explicit private output root.

    The callback must raise if source custody has changed; it runs immediately
    before publication. Optional application resources supply HTML/CSS only.
    The JavaScript matcher always comes from this shared package.
    """
    _validate_output(output, private_output_root)
    if len({unit.passage_id for unit in passages}) != len(passages):
        raise ResearchError("duplicate_passage", "Source units need unique identities")
    resources = files("blake.methods").joinpath("resources")
    raw = {name: resources.joinpath(name).read_bytes() for name in RESOURCE_NAMES}
    if resource_directory is not None:
        for name in ("corpus-search.html", "corpus-search.css"):
            raw[name] = (resource_directory / name).read_bytes()
    template = raw["corpus-search.html"].decode()
    css = raw["corpus-search.css"].decode()
    script = raw["corpus-search.js"].decode()
    folding, word_ranges = unicode_search_tables()
    data = {
        "schema_version": 1,
        "producer_version": producer_version,
        "corpus_pin": pin.model_dump(mode="json"),
        "unicode_version": unicodedata.unidata_version,
        "semantics": SEMANTICS,
        "folding": folding,
        "word_ranges": word_ranges,
        "whitespace": [chr(code) for code in range(sys.maxunicode + 1) if chr(code).isspace()],
        "units": _source_data(passages),
    }
    payload = json_script(data)
    replacements = {
        "@@TITLE@@": escape(branding.title),
        "@@BRAND@@": escape(branding.brand),
        "@@FOOTER@@": escape(branding.footer),
        "@@STYLE_HASH@@": csp_hash(css),
        "@@SCRIPT_HASH@@": csp_hash(script),
        "@@STYLE@@": css,
        "@@PAYLOAD@@": payload,
        "@@SCRIPT@@": script,
    }
    markers = re.findall(r"@@[A-Z_]+@@", template)
    if Counter(markers) != Counter(replacements.keys()):
        raise ResearchError("search_template_marker", "Workspace markers must occur exactly once")
    html = re.sub(r"@@[A-Z_]+@@", lambda match: replacements[match.group()], template)
    revalidate()
    try:
        output.mkdir(parents=True)
    except FileExistsError as exc:
        raise ResearchError("occupied_output", str(output)) from exc
    index = output / "index.html"
    write_new(index, html)
    manifest = {
        "schema_version": 1,
        "producer_version": producer_version,
        "privacy": "Local full-text workspace; exclude from source and release archives.",
        "corpus_pin": pin.model_dump(mode="json"),
        "index_sha256": pin.index_sha256,
        "source_units": len(passages),
        "units_by_plane": dict(sorted(Counter(p.source_plane.value for p in passages).items())),
        "units_by_role": dict(sorted(Counter(p.text_role.value for p in passages).items())),
        "unicode_version": unicodedata.unidata_version,
        "semantics": SEMANTICS,
        "payload_bytes": len(payload.encode()),
        "payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "resources": {name: hashlib.sha256(body).hexdigest() for name, body in raw.items()},
        "outputs": [{"path": "index.html", "size": index.stat().st_size, "sha256": digest(index)}],
    }
    write_new(output / "search-manifest.json", json.dumps(manifest, indent=2) + "\n")
    return index


def build_search_workspace(  # noqa: PLR0913 - explicit application custody policy
    directory: Path,
    pin: CorpusPin,
    output: Path,
    *,
    branding: WorkspaceBranding,
    producer_version: str,
    private_output_root: Path,
    resource_directory: Path | None = None,
) -> Path:
    """Verify a pinned import and recheck its index before publishing full texts."""
    _validate_output(output, private_output_root)
    _, passages = load_import(directory, pin)

    def revalidate() -> None:
        if digest(directory / "passages.sqlite") != pin.index_sha256:
            raise ResearchError("search_source_changed", "passages.sqlite")

    return build_search_workspace_passages(
        passages,
        pin,
        output,
        branding=branding,
        producer_version=producer_version,
        private_output_root=private_output_root,
        revalidate=revalidate,
        resource_directory=resource_directory,
    )
