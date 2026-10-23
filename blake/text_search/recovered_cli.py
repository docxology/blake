"""Private recovered-search command and typed CLI session context."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import click

from .index import PassageIndex
from .models import SearchResult

if TYPE_CHECKING:
    from .recovered import RecoveredSearchManifest


@dataclass(frozen=True)
class SearchSession:
    index: PassageIndex
    data_dir: Path
    snapshot: RecoveredSearchManifest | None = None


def query_payload(result: SearchResult, *, private: bool) -> dict[str, object]:
    """Bound private CLI display while retaining exact pre-limit query totals."""
    if not private:
        return result.model_dump(mode="json")
    payload = result.model_dump(mode="json", exclude={"hits"})
    hits = []
    for hit in result.hits:
        matches = []
        for match in hit.matches[:20]:
            start = max(0, match.start - 120)
            end = min(len(hit.passage.text), match.end + 120)
            matches.append(
                {
                    **match.model_dump(mode="json"),
                    "context": hit.passage.text[start:end],
                    "context_start": start,
                    "context_end": end,
                }
            )
        hits.append(
            {
                "passage": hit.passage.model_dump(mode="json", exclude={"text"}),
                "text_sha256": hit.text_sha256,
                "match_count": len(hit.matches),
                "matches_truncated": len(hit.matches) > 20,
                "matches": matches,
            }
        )
    payload["hits"] = hits
    payload["display"] = (
        "Private CLI omits full passage bodies and displays up to 20 matches per hit "
        "with 120 characters of context on each side. Counts cover the full selected scope; "
        "the Python API retains complete passages and spans."
    )
    return payload


@click.command("build-recovered")
@click.pass_context
def build_recovered(ctx: click.Context) -> None:
    """Build a private, source-bound projection without changing captured evidence."""
    from .recovered import build_recovered_search

    if ctx.meta["explicit_index"]:
        raise click.UsageError(
            "build-recovered chooses its own bound path; omit --index"
        )
    session: SearchSession = ctx.obj
    try:
        result = build_recovered_search(session.data_dir)
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    receipt = result.manifest
    click.echo(
        json.dumps(
            {
                "directory": str(result.directory),
                "captured_manifest_sha256": receipt.captured_manifest_sha256,
                "index_sha256": receipt.index.sha256,
                "passages": receipt.passages,
                "passages_by_role": receipt.passages_by_role,
                "passages_by_plane": receipt.passages_by_plane,
                "source_counts": receipt.source_counts.model_dump(),
                "empty_erdman_page_ids": receipt.empty_erdman_page_ids,
                "verified_input_files": len(receipt.inputs),
                "verified_input_bytes": sum(r.size for r in receipt.inputs),
            },
            indent=2,
        )
    )
