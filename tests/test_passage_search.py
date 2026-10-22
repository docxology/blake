"""Search evidence controls; runnable without the legacy NLP conftest/profile."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from blake.text_search import Passage, PassageIndex, Query, SearchMode
from blake.text_search.cache import import_cache
from blake.text_search.index import read_passages
from blake.text_search.models import SearchError
from blake.transcription import extract_primary_blocks, extract_primary_text


@pytest.fixture
def passage() -> Passage:
    return Passage(passage_id="test:1", work_id="mhh", author_id="william-blake-1757-1827",
        title="Title contains federation", edition_id="synthetic-control", edition="Synthetic test only",
        locator="test section", locator_kind="section", source_url="https://example.org/control",
        rights="Synthetic test text", text_role="primary",
        text="State states estate. Eternity is in love\nwith the productions of time. Albion’s ſtates.")


@pytest.mark.parametrize(("word", "expected"), [("state", 1), ("states", 2), ("estate", 1), ("federation", 0), ("Albion", 1), ("is", 1)])
def test_word_boundaries_when_substrings_or_metadata_match(tmp_path: Path, passage: Passage, word: str, expected: int) -> None:
    # Given an index with substring and metadata decoys.
    index = PassageIndex(tmp_path / "index.sqlite")
    index.build([passage])
    # When searching the primary text.
    result = index.search(Query(text=word))
    # Then count whole source tokens only, including the preserved long-s spelling.
    assert result.total_occurrences == expected


def test_phrase_when_wrapped_keeps_original_spans(tmp_path: Path, passage: Passage) -> None:
    # Given a wrapped original passage.
    index = PassageIndex(tmp_path / "index.sqlite")
    index.build([passage])
    # When normalized phrase search retains stopwords.
    result = index.search(Query(text="IS IN LOVE WITH THE", mode=SearchMode.PHRASE))
    # Then source expression and offsets remain exact.
    match = result.hits[0].matches[0]
    assert match.matched_text == "is in love\nwith the"
    assert passage.text[match.start:match.end] == match.matched_text


@pytest.mark.parametrize(("term", "count"), [("State", 1), ("state", 2), ("Eternity is in love with", 0)])
def test_literal_when_case_or_whitespace_differs(tmp_path: Path, passage: Passage, term: str, count: int) -> None:
    # Given mixed case and a line break.
    index = PassageIndex(tmp_path / "index.sqlite")
    index.build([passage])
    # When matching exact characters (including substrings).
    result = index.search(Query(text=term, mode=SearchMode.LITERAL))
    # Then no case or whitespace rewriting is applied.
    assert result.total_occurrences == count


def test_expansion_when_variants_are_requested(tmp_path: Path, passage: Passage) -> None:
    # Given an inflected term and historical character variant.
    index = PassageIndex(tmp_path / "index.sqlite")
    index.build([passage])
    # When the variant family is explicitly selected.
    result = index.search(Query(text="states", mode=SearchMode.VARIANTS))
    # Then record exact forms rather than pretending each is the query string.
    assert result.total_occurrences == 3
    assert {m.matched_text for m in result.hits[0].matches} == {"State", "states", "ſtates"}


@pytest.mark.parametrize("change", [{"author_id": "robert-blake-1598-1657"}, {"text_role": "editorial"}, {"text_role": "unverified"}])
def test_identity_when_nonprimary_or_other_blake_matches(tmp_path: Path, passage: Passage, change: dict[str, str]) -> None:
    # Given an otherwise matching decoy.
    index = PassageIndex(tmp_path / "index.sqlite")
    index.build([passage.model_copy(update=change)])
    # When using the default William Blake primary-text search.
    result = index.search(Query(text="state"))
    # Then the decoy never becomes primary evidence.
    assert result.total_passages == 0


def test_concept_when_federation_has_no_literal_occurrence(tmp_path: Path, passage: Passage) -> None:
    # Given state vocabulary without federation in the source text.
    index = PassageIndex(tmp_path / "index.sqlite")
    index.build([passage])
    # When using the explicitly editorial navigation concept.
    result = index.search(Query(text="federation-hypothesis", mode=SearchMode.CONCEPT))
    # Then returned expressions show the expansion responsible for each match.
    assert result.total_occurrences == 2
    assert {m.expanded_term for hit in result.hits for m in hit.matches} == {"states"}


def test_editions_when_same_work_has_variants(tmp_path: Path, passage: Passage) -> None:
    # Given two source editions with stable distinct passage identities.
    index = PassageIndex(tmp_path / "index.sqlite")
    index.build([passage, passage.model_copy(update={"passage_id": "test:2", "edition_id": "other"})])
    # When filtering by edition and using a display limit.
    result = index.search(Query(text="state", edition_id="other", limit=1))
    # Then no title-based conflation occurs.
    assert [hit.passage.passage_id for hit in result.hits] == ["test:2"]


def test_totals_when_limit_truncates_display(tmp_path: Path, passage: Passage) -> None:
    # Given two distinct matching editions.
    index = PassageIndex(tmp_path / "index.sqlite")
    index.build([passage, passage.model_copy(update={"passage_id": "test:2"})])
    # When limiting only the returned passages.
    result = index.search(Query(text="state", limit=1))
    # Then corpus-snapshot totals remain visible.
    assert (result.total_occurrences, result.total_passages, len(result.hits), result.truncated) == (2, 2, 1, True)


def test_rebuild_when_duplicate_input_fails_preserves_old_index(tmp_path: Path, passage: Passage) -> None:
    # Given a working source snapshot.
    index = PassageIndex(tmp_path / "index.sqlite")
    index.build([passage])
    before = hashlib.sha256(index.path.read_bytes()).hexdigest()
    # When duplicate stable identities invalidate its proposed replacement.
    with pytest.raises(sqlite3.IntegrityError):
        index.build([passage, passage])
    # Then the existing snapshot is byte-for-byte preserved.
    assert hashlib.sha256(index.path.read_bytes()).hexdigest() == before


@pytest.mark.parametrize("term", ["***", "state nation"])
def test_word_input_when_invalid_is_rejected(tmp_path: Path, passage: Passage, term: str) -> None:
    # Given a valid index.
    index = PassageIndex(tmp_path / "index.sqlite")
    index.build([passage])
    # When a punctuation-only or multiword query is passed as one word.
    with pytest.raises(SearchError):
        index.search(Query(text=term))
    # Then the test passes only on an explicit error.


def test_fts_operators_when_present_are_plain_query_text(tmp_path: Path, passage: Passage) -> None:
    # Given two words independently present in a passage.
    index = PassageIndex(tmp_path / "index.sqlite")
    index.build([passage])
    # When a query includes apparent FTS operators.
    result = index.search(Query(text='state OR "time"', mode=SearchMode.PHRASE))
    # Then operators never change query semantics.
    assert result.total_occurrences == 0


@pytest.mark.parametrize("xml", [
    '<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><p>EDITORIAL</p></teiHeader><text><body><div><p><l n="7.16">Eternity<note>EDITORIAL</note> is in love.</l></p></div></body></text></TEI>',
    '<bad><desc><p>EDITORIAL</p><phystext><lg><l n="7.16">Eternity is in love.</l></lg></phystext></desc></bad>',
])
def test_primary_extraction_when_containers_overlap_avoids_duplicates(xml: str) -> None:
    # Given nested containers and modern annotation decoys.
    # When extracting the primary reading layer.
    result = extract_primary_blocks(xml)
    # Then the primary line appears once with its actual identifier.
    assert [(block.locator, block.text) for block in result] == [("7.16", "Eternity is in love.")]


def test_tei_choice_when_corrected_reading_exists_keeps_original() -> None:
    # Given both original and corrected readings.
    xml = '<TEI><text><body><p><choice><orig>tyger</orig><reg>tiger</reg></choice><note>EDITORIAL</note> bright</p></body></text></TEI>'
    # When generating the reading layer.
    result = extract_primary_text(xml)
    # Then original spelling is retained, never concatenated with its correction.
    assert result == "tyger bright"


def test_cache_when_membership_selects_only_current_run(tmp_path: Path) -> None:
    # Given a selected file, its alternate edition, and a stale excluded cache file.
    texts = tmp_path / "data/texts"
    texts.mkdir(parents=True)
    (texts / "current.txt").write_text("state", encoding="utf-8")
    (texts / "current_variant.txt").write_text("states", encoding="utf-8")
    (texts / "stale.txt").write_text("nation", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"fixture_mode": False, "work_records": [
        {"id": "current", "target_id": "mhh", "title": "Marriage", "source": "archive", "source_url": "https://example.org/primary", "has_text": True},
        {"id": "missing", "title": "Missing", "source": "archive", "has_text": True}]}))
    # When importing explicit saved membership.
    result = import_cache(manifest, tmp_path / "data")
    # Then preserve file variants, absent members and the unverified evidence boundary.
    assert (len(result.passages), result.missing_text_ids) == (2, ("missing",))
    assert {row.text_role for row in result.passages} == {"unverified"}
    assert {row.work_id for row in result.passages} == {"mhh"}


@pytest.mark.parametrize("flag", [True, "false", 0])
def test_cache_when_fixture_or_malformed_modality_rejected(tmp_path: Path, flag: bool | str | int) -> None:
    # Given a synthetic/ambiguous saved manifest.
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"fixture_mode": flag, "work_records": []}))
    # When loading it for production text search.
    with pytest.raises((ValidationError, SearchError)):
        import_cache(manifest, tmp_path)
    # Then it cannot silently become source coverage.


def test_real_cli_when_demo_is_built_reports_exact_phrase(tmp_path: Path) -> None:
    # Given the selected public-domain primary excerpts.
    root = Path(__file__).resolve().parents[1]
    prefix = [sys.executable, "-m", "blake.text_search", "--index", str(tmp_path / "demo.sqlite")]
    subprocess.run([*prefix, "build", str(root / "examples/primary-passages.jsonl")], cwd=root, check=True, capture_output=True)
    # When invoking the real user-facing CLI.
    process = subprocess.run([*prefix, "query", "Eternity is in love with the productions of time", "--mode", "phrase"], cwd=root, check=True, capture_output=True, text=True)
    # Then evidence resolves to the selected edition's actual page.
    result = json.loads(process.stdout)
    assert result["total_occurrences"] == 1
    assert result["hits"][0]["passage"]["passage_id"] == "mhh-luce1906-p14-eternity"


def test_demo_when_loaded_has_no_full_work_claim() -> None:
    # Given the documented selection.
    path = Path(__file__).resolve().parents[1] / "examples/primary-passages.jsonl"
    # When loading its membership.
    result = list(read_passages(path))
    # Then count only its seven explicitly located excerpts.
    assert (len(result), {row.work_id for row in result}) == (7, {"mhh"})


@pytest.mark.parametrize("problem", ["symlink", "overlapping_ids", "nonboolean"])
def test_cache_when_source_identity_is_ambiguous_refuses(tmp_path: Path, problem: str) -> None:
    # Given unsafe or ambiguous source selection.
    texts = tmp_path / "data/texts"
    texts.mkdir(parents=True)
    (texts / "work.txt").write_text("primary")
    work = {"id": "work", "title": "Work", "source": "archive", "source_url": "https://example.org/work", "has_text": True}
    records = [work]
    if problem == "symlink":
        (texts / "work.txt").unlink()
        (tmp_path / "private.txt").write_text("unselected private material")
        (texts / "work.txt").symlink_to(tmp_path / "private.txt")
    if problem == "overlapping_ids":
        records.append({**work, "id": "work_other"})
        (texts / "work_other.txt").write_text("different work")
    if problem == "nonboolean":
        records = [{**work, "has_text": "true"}]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"fixture_mode": False, "work_records": records}))
    # When importing the saved cache.
    with pytest.raises((ValidationError, SearchError)):
        import_cache(manifest, tmp_path / "data")
    # Then no inferred primary-source identity is accepted.


def test_package_when_loading_models_does_not_load_nlp() -> None:
    # Given only the minimal search dependencies.
    # When using an existing public model import.
    result = subprocess.run([sys.executable, "-c", "import sys; from blake import BlakeWork; assert 'torch' not in sys.modules; print(BlakeWork.__module__)"], check=True, text=True, capture_output=True)
    # Then no NLP dependency is needed to obtain that public class.
    assert result.stdout.strip() == "blake.models"


@pytest.mark.parametrize(("source", "term", "expected"), [
    ("cafe\u0301", "café", "cafe\u0301"),
    ("½", "1/2", "½"),
    ("℀", "a/c", "℀"),
    ("a½b", "a1", "a½"),
    ("\u1100\u1161", "가", "\u1100\u1161"),
    ("oﬃce", "office", "oﬃce"),
])
def test_unicode_when_normalization_changes_source_token_boundaries(tmp_path: Path, passage: Passage, source: str, term: str, expected: str) -> None:
    # Given original expression whose normalization composes or expands characters.
    index = PassageIndex(tmp_path / "unicode.sqlite")
    index.build([passage.model_copy(update={"text": source})])
    # When searching the normalized phrase through the real FTS index.
    result = index.search(Query(text=term, mode=SearchMode.PHRASE))
    # Then its match is a real unchanged source span, including combining marks.
    assert result.total_occurrences == 1
    match = result.hits[0].matches[0]
    assert match.matched_text == expected == source[match.start:match.end]
