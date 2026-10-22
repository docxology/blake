"""SQLite FTS candidate index with exact source-span verification and atomic rebuilds."""

import hashlib
import os
import re
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Iterable

from .models import Passage, Query, SearchError, SearchHit, SearchMode, SearchResult, MatchSpan
from .normalize import NORMALIZATION, spans, tokens, tokenize
from .vocabulary import concepts, variants


class PassageIndex:
    """An explicitly built local snapshot, never an implicit whole-Blake corpus."""

    def __init__(self, path: Path):
        self.path = path

    def build(self, passages: Iterable[Passage]) -> int:
        """Rebuild atomically; validation/duplicate failures retain the previous index."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=self.path.parent, suffix=".sqlite", delete=False) as temp:
            temporary = Path(temp.name)
        try:
            with closing(sqlite3.connect(temporary)) as conn, conn:
                conn.execute("CREATE TABLE info (normalization TEXT NOT NULL)")
                conn.execute("INSERT INTO info VALUES (?)", (NORMALIZATION,))
                conn.execute("CREATE TABLE passages (id TEXT PRIMARY KEY, payload TEXT NOT NULL, sha256 TEXT NOT NULL)")
                conn.execute("CREATE VIRTUAL TABLE terms USING fts5(normalized, tokenize='unicode61 remove_diacritics 0')")
                count = 0
                for passage in passages:
                    digest = hashlib.sha256(passage.text.encode("utf-8")).hexdigest()
                    cursor = conn.execute("INSERT INTO passages VALUES (?,?,?)", (passage.passage_id, passage.model_dump_json(), digest))
                    conn.execute("INSERT INTO terms(rowid,normalized) VALUES (?,?)", (cursor.lastrowid, " ".join(tokens(passage.text))))
                    count += 1
            os.replace(temporary, self.path)
            return count
        finally:
            temporary.unlink(missing_ok=True)

    def _connect(self) -> sqlite3.Connection:
        """Open existing evidence read-only; a missing index never becomes an empty one."""
        conn = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            if conn.execute("SELECT normalization FROM info").fetchone() != (NORMALIZATION,):
                message = "Index normalization is incompatible; rebuild it"
                raise SearchError(message)
        except (sqlite3.Error, SearchError):
            conn.close()
            raise
        return conn

    def search(self, query: Query) -> SearchResult:
        """Return actual occurrence totals before applying the display limit."""
        wanted = tokens(query.text)
        if not wanted:
            message = "Query must contain a word"
            raise SearchError(message)
        interpretation = "Primary transcription occurrences only; metadata is not searched."
        if query.mode is SearchMode.WORD and len(wanted) != 1:
            message = "Word mode requires one token; use phrase mode"
            raise SearchError(message)
        terms = (query.text,)
        if query.mode is SearchMode.VARIANTS:
            terms = variants(query.text)
            interpretation = "Explicit spelling/inflection expansion; inspect matched_text, not the query label."
        if query.mode is SearchMode.CONCEPT:
            concept = concepts().get(query.text.casefold())
            if concept is None:
                message = "Unknown concept; list concepts before querying"
                raise SearchError(message)
            terms = concept.terms
            interpretation = "Editorial concept navigation, not literal occurrence of the concept label. " + concept.rationale
        expression = " OR ".join('"' + " ".join(tokens(term)).replace('"', '""') + '"' for term in terms)
        hits = []
        with closing(self._connect()) as conn:
            if query.mode is SearchMode.LITERAL:
                rows = conn.execute("SELECT payload,sha256 FROM passages ORDER BY id")
            else:
                rows = conn.execute("SELECT p.payload,p.sha256 FROM terms JOIN passages p ON p.rowid=terms.rowid WHERE terms MATCH ? ORDER BY p.id", (expression,))
            for payload, digest in rows:
                passage = Passage.model_validate_json(payload)
                if (passage.author_id != query.author_id or passage.text_role != "primary"
                    or (query.work_id and passage.work_id != query.work_id)
                    or (query.edition_id and passage.edition_id != query.edition_id)):
                    continue
                if query.mode is SearchMode.LITERAL:
                    matches = tuple(MatchSpan(start=m.start(), end=m.end(), matched_text=m.group(), expanded_term=query.text) for m in re.finditer(re.escape(query.text), passage.text))
                else:
                    source = tokenize(passage.text)
                    unique = {(m.start, m.end): m for term in terms for m in spans(source, term)}
                    matches = tuple(unique[key] for key in sorted(unique))
                if matches:
                    hits.append(SearchHit(passage=passage, text_sha256=digest, matches=matches))
        return SearchResult(query=query, interpretation=interpretation, expanded_terms=terms,
            total_passages=len(hits), total_occurrences=sum(len(hit.matches) for hit in hits),
            truncated=len(hits) > query.limit, hits=tuple(hits[:query.limit]))

    def inventory(self) -> list[Passage]:
        """Describe the exact indexed records, including roles excluded from search."""
        with closing(self._connect()) as conn:
            return [Passage.model_validate_json(row[0]) for row in conn.execute("SELECT payload FROM passages ORDER BY id")]


def read_passages(path: Path) -> Iterable[Passage]:
    """Stream explicit JSONL membership; no folder crawling or implicit acquisition."""
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield Passage.model_validate_json(line)
