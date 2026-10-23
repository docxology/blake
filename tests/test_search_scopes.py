from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from click.testing import CliRunner

from blake.text_search import Passage, PassageIndex, Query
from blake.text_search.cli import main
from blake.text_search.models import SearchError


def records() -> list[Passage]:
    base = dict(
        work_id="control",
        title="Synthetic control",
        edition_id="control",
        edition="Synthetic only",
        locator="section 1",
        locator_kind="section",
        source_url="https://example.org/control",
        rights="Synthetic test material",
        text="state",
        author_id="william-blake-1757-1827",
        text_role="primary",
    )
    return [
        Passage(passage_id="primary", **base),
        Passage(passage_id="other-author", **{**base, "author_id": "another-author"}),
        Passage(
            passage_id="letter",
            **{**base, "author_id": "unverified", "text_role": "unverified"},
        ),
        Passage(
            passage_id="edition",
            **{
                **base,
                "author_id": "mixed-edition",
                "text_role": "editorial",
                "source_plane": "erdman",
            },
        ),
        Passage(
            passage_id="apparatus",
            **{
                **base,
                "author_id": "unverified",
                "text_role": "unverified",
                "source_plane": "xml",
                "text": "<del>state</del>",
            },
        ),
    ]


def test_primary_and_exploratory_counts_remain_distinct(tmp_path: Path) -> None:
    index = PassageIndex(tmp_path / "index.sqlite")
    index.build(records())

    primary = index.search(Query(text="state"))
    exploratory = index.search(Query(text="state", scope="exploratory", author_id=None))

    assert primary.total_occurrences == primary.blake_primary_occurrences == 1
    assert exploratory.total_occurrences == 5
    assert exploratory.blake_primary_occurrences == 1
    assert exploratory.occurrences_by_role == {
        "primary": 2,
        "unverified": 2,
        "editorial": 1,
    }
    assert exploratory.occurrences_by_plane == {"reading": 3, "erdman": 1, "xml": 1}
    assert "not Blake-primary" in exploratory.interpretation


@pytest.mark.parametrize(
    "selection",
    [
        {"source_plane": "xml"},
        {"source_plane": "erdman"},
        {"text_role": "editorial"},
        {"text_role": "unverified"},
        {"author_id": None},
    ],
)
def test_primary_scope_rejects_incompatible_filters(
    tmp_path: Path, selection: dict
) -> None:
    index = PassageIndex(tmp_path / "index.sqlite")
    index.build(records())
    with pytest.raises(SearchError, match="Primary scope"):
        index.search(Query(text="state", **selection))


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        ({"source_plane": "xml"}, ["apparatus"]),
        ({"source_plane": "erdman"}, ["edition"]),
        ({"text_role": "unverified"}, ["apparatus", "letter"]),
        ({"author_id": "another-author"}, ["other-author"]),
    ],
)
def test_exploratory_filters_preserve_source_labels(
    tmp_path: Path, filters: dict, expected: list[str]
) -> None:
    index = PassageIndex(tmp_path / "index.sqlite")
    index.build(records())
    result = index.search(
        Query.model_validate(
            {"text": "state", "scope": "exploratory", "author_id": None, **filters}
        )
    )
    assert [hit.passage.passage_id for hit in result.hits] == expected
    assert result.blake_primary_occurrences == 0


def test_read_only_snapshot_refuses_rebuild(tmp_path: Path) -> None:
    path = tmp_path / "index.sqlite"
    PassageIndex(path).build(records())
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(SearchError, match="read-only"):
        PassageIndex(path, read_only=True).build([])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_cli_exploratory_scope_requires_explicit_selection(tmp_path: Path) -> None:
    path = tmp_path / "index.sqlite"
    PassageIndex(path).build(records())
    result = CliRunner().invoke(
        main,
        [
            "--index",
            str(path),
            "query",
            "state",
            "--scope",
            "exploratory",
            "--plane",
            "erdman",
        ],
    )
    assert result.exit_code == 0, result.output
    import json

    payload = json.loads(result.output)
    assert payload["total_occurrences"] == 1
    assert payload["blake_primary_occurrences"] == 0
    assert payload["query"]["scope"] == "exploratory"
