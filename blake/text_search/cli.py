"""Click commands for local passage search; never downloads or publishes source files."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path

import click
from pydantic import ValidationError
from ..version import __version__

from .cache import import_cache
from .index import PassageIndex, read_passages
from .models import Query, SearchError, SearchMode, SearchScope
from .normalize import NORMALIZATION
from .vocabulary import concepts
from .recovered_cli import SearchSession, build_recovered, query_payload

RESEARCH_WORDS = (
    "state",
    "states",
    "nation",
    "nations",
    "generation",
    "generations",
    "emanation",
    "emanations",
    "eternity",
    "time",
    "Albion",
    "Jerusalem",
    "individual",
    "identity",
    "contraries",
    "negation",
    "vision",
    "fourfold",
    "federation",
    "federal",
    "zzzxqvnegativecontrol",
)


@click.group()
@click.version_option(__version__)
@click.option(
    "--index",
    type=click.Path(path_type=Path),
    help="Explicit passage index, including a separately built public demo.",
)
@click.option(
    "--recovered",
    is_flag=True,
    help="Open the separately built private recovered-corpus search snapshot.",
)
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path),
    default="blake_data",
    show_default=True,
)
@click.pass_context
def main(
    ctx: click.Context, index: Path | None, recovered: bool, data_dir: Path
) -> None:
    """Search selected William Blake transcriptions with edition-bound evidence."""
    if index is not None and recovered:
        raise click.UsageError("Choose either --index or --recovered")
    ctx.meta["explicit_index"] = index is not None
    if recovered and ctx.invoked_subcommand != "build-recovered":
        from .recovered import open_recovered_search

        try:
            snapshot = open_recovered_search(data_dir)
        except (OSError, sqlite3.Error, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc
        ctx.obj = SearchSession(snapshot.index, data_dir, snapshot.manifest)
    else:
        ctx.obj = SearchSession(
            PassageIndex(index or Path("blake_data/search/passages.sqlite")), data_dir
        )


main.add_command(build_recovered)


@main.command("build")
@click.argument("jsonl", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.pass_obj
def build(session: SearchSession, jsonl: Path) -> None:
    """Atomically index explicit passage JSONL (keep restricted inputs private)."""
    try:
        count = session.index.build(read_passages(jsonl))
    except (OSError, sqlite3.Error, ValidationError, SearchError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps({"indexed_passages": count, "normalization": NORMALIZATION}))


@main.command("import-cache")
@click.argument(
    "manifest", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.argument(
    "data_dir", type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.pass_obj
def cache(session: SearchSession, manifest: Path, data_dir: Path) -> None:
    """Index saved manifest text IDs only, retaining file variants and missing IDs."""
    try:
        imported = import_cache(manifest, data_dir)
        count = session.index.build(imported.passages)
    except (OSError, UnicodeError, sqlite3.Error, ValidationError, SearchError) as exc:
        raise click.ClickException(str(exc)) from exc
    payload = imported.model_dump(mode="json", exclude={"passages"})
    payload["indexed_passages"] = count
    payload["edition_warning"] = (
        "Cache texts are unverified and excluded from primary occurrence search; they are available only as labeled exploratory source matches. Export reviewed Passage JSONL with explicit author/edition/primary role, then build."
    )
    click.echo(json.dumps(payload, indent=2))


@main.command("query")
@click.argument("text")
@click.option(
    "--mode", type=click.Choice([mode.value for mode in SearchMode]), default="word"
)
@click.option("--work-id")
@click.option("--edition-id")
@click.option(
    "--scope",
    type=click.Choice([scope.value for scope in SearchScope]),
    default="primary",
)
@click.option(
    "--plane", "source_plane", type=click.Choice(["reading", "erdman", "xml"])
)
@click.option(
    "--role", "text_role", type=click.Choice(["primary", "editorial", "unverified"])
)
@click.option(
    "--author-id",
    help="Explicit author filter; exploratory scope otherwise includes every labeled author.",
)
@click.option("--limit", type=click.IntRange(1, 1000), default=20)
@click.pass_obj
def query(session: SearchSession, text: str, **options: str | int | None) -> None:
    """Emit JSON with actual matched text, offsets, provenance and pre-limit totals."""
    try:
        selected = {"text": text, **options}
        if selected.get("author_id") is None and selected["scope"] == "primary":
            selected["author_id"] = "william-blake-1757-1827"
        request = Query.model_validate(selected)
        result = session.index.search(request)
    except (OSError, sqlite3.Error, ValidationError, SearchError) as exc:
        raise click.ClickException(str(exc)) from exc
    payload = query_payload(result, private=session.snapshot is not None)
    payload["index"] = str(session.index.path)
    payload["captured_manifest_sha256"] = (
        session.snapshot.captured_manifest_sha256 if session.snapshot else None
    )
    click.echo(json.dumps(payload, indent=2))


@main.command("coverage")
@click.pass_obj
def coverage(session: SearchSession) -> None:
    """Report indexed membership; absence here is never absence from Blake's oeuvre."""
    try:
        rows = session.index.inventory()
    except (OSError, sqlite3.Error, ValidationError, SearchError) as exc:
        raise click.ClickException(str(exc)) from exc
    payload = {
        "scope": "Only explicitly indexed passages; no whole-oeuvre completeness claim",
        "normalization": NORMALIZATION,
        "index": str(session.index.path),
        "captured_manifest_sha256": session.snapshot.captured_manifest_sha256
        if session.snapshot
        else None,
        "passages": len(rows),
        "works": len({row.work_id for row in rows}),
        "editions": len({(row.work_id, row.edition_id) for row in rows}),
        "roles": dict(Counter(row.text_role for row in rows)),
        "planes": dict(Counter(row.source_plane for row in rows)),
        "authors": dict(Counter(row.author_id for row in rows)),
        "membership": [row.model_dump(mode="json", exclude={"text"}) for row in rows],
    }
    click.echo(json.dumps(payload, indent=2))


@main.command("concepts")
def list_concepts() -> None:
    """List explicit editorial expansions, reasons and primary-source checking links."""
    click.echo(
        json.dumps(
            {key: value.model_dump(mode="json") for key, value in concepts().items()},
            indent=2,
        )
    )


@main.command("suite")
@click.pass_obj
def suite(session: SearchSession) -> None:
    """Run the finite research/control suite; counts belong only to this index."""
    queries = [Query(text=word) for word in RESEARCH_WORDS]
    queries.extend(
        Query(text=word, mode=SearchMode.VARIANTS)
        for word in (
            "state",
            "nation",
            "generation",
            "emanation",
            "fourfold",
            "federal",
        )
    )
    queries.extend(
        Query(text=phrase, mode=SearchMode.PHRASE)
        for phrase in (
            "Eternity is in love with the productions of time",
            "generation to generation",
            "Eternity is at war with time",
        )
    )
    queries.extend(Query(text=name, mode=SearchMode.CONCEPT) for name in concepts())
    try:
        results = [session.index.search(request) for request in queries]
    except (OSError, sqlite3.Error, ValidationError, SearchError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(
        json.dumps(
            {
                "scope": "Explicitly indexed passages only; zero is not oeuvre-wide absence",
                "normalization": NORMALIZATION,
                "queries": [
                    {
                        "query": result.query.text,
                        "mode": result.query.mode.value,
                        "occurrences": result.total_occurrences,
                        "passages": result.total_passages,
                        "expanded_terms": result.expanded_terms,
                        "passage_ids": [hit.passage.passage_id for hit in result.hits],
                    }
                    for result in results
                ],
            },
            indent=2,
        )
    )
