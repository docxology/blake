"""Metadata navigation over records round-tripped through real SQLite."""

from datetime import datetime

import pytest

from blake.metadata.search import MetadataSearcher
from blake.models import SourceType, WorkType
from tests import metadata_search_fixtures

stored_works = metadata_search_fixtures.stored_works


@pytest.mark.parametrize(
    "filters,expected",
    [
        ({"work_type": WorkType.POEM}, ["a", "c"]),
        ({"source": SourceType.PROJECT_GUTENBERG}, ["b"]),
        ({"date_range": (datetime(1794, 1, 1), datetime(1794, 1, 1))}, ["a"]),
        ({"tags": "ALPHA"}, ["a", "c"]),
        ({"tags": ["alpha", "beta"]}, ["a", "b", "c"]),
        ({"themes": "time"}, ["a", "b"]),
        ({"themes": ["TIME"]}, ["a", "b"]),
        ({"subjects": "mind"}, ["a", "c"]),
        ({"subjects": ["MIND"]}, ["a", "c"]),
        ({"has_images": True}, ["a", "c"]),
        ({"has_images": False}, ["b", "d"]),
        ({"has_text": True}, ["a", "b"]),
        ({"has_text": False}, ["c", "d"]),
        ({"processed": True}, ["a"]),
        ({"processed": False}, ["b", "c", "d"]),
        ({"has_text": True, "source": SourceType.PROJECT_GUTENBERG}, ["b"]),
        (
            {"has_text": None, "has_images": None, "processed": None},
            ["a", "b", "c", "d"],
        ),
    ],
)
def test_filters_select_saved_identity_and_leave_records_unchanged(
    stored_works, filters, expected
) -> None:
    before = [work.model_dump(mode="json") for work in stored_works]
    result = MetadataSearcher().search_works(stored_works, "", filters)
    assert [work.id for work in result] == expected
    assert [work.model_dump(mode="json") for work in stored_works] == before


def test_relevance_ranks_title_and_metadata_ahead_of_body(stored_works) -> None:
    searcher = MetadataSearcher()
    assert [w.id for w in searcher.search_works(stored_works, "STATE time")] == [
        "a",
        "b",
    ]
    assert [
        w.id
        for w in searcher.search_works(stored_works, "state", {"has_images": False})
    ] == ["b"]
    assert searcher.search_works(stored_works, "zzzxqvnegativecontrol") == []
    assert searcher.search_works(stored_works, "the and") == []
    assert searcher.search_works(stored_works, "") == stored_works


def test_suggestions_keep_distinct_source_spelling_and_bound_results(
    stored_works,
) -> None:
    searcher = MetadataSearcher()
    assert searcher.get_search_suggestions(stored_works, "mi") == ["Mind"]
    assert searcher.get_search_suggestions(stored_works, "time") == ["TIME", "Time"]
    stored_works[0].metadata.tags = [f"Alpha{i:02d}" for i in range(20)] * 2
    assert searcher.get_search_suggestions(stored_works, "alpha") == [
        f"Alpha{i:02d}" for i in range(10)
    ]
    assert searcher.get_search_suggestions(stored_works, "zzzxqv") == []


def test_facet_counts_and_dates_describe_actual_saved_membership(stored_works) -> None:
    searcher = MetadataSearcher()
    facets = searcher.get_facet_counts(stored_works)
    assert facets["work_types"] == {"poem": 2, "letter": 1, "manuscript": 1}
    assert facets["sources"] == {
        "blake_archive": 2,
        "project_gutenberg": 1,
        "internet_archive": 1,
    }
    assert facets["tags"] == {"state": 1, "alpha": 2, "beta": 1}
    assert facets["themes"] == {"Time": 1, "TIME": 1}
    assert facets["subjects"] == {"Mind": 2, "Other": 1}
    assert facets["series"] == {"A": 2, "B": 1}
    assert searcher.get_date_range(stored_works) == (
        datetime(1794, 1, 1),
        datetime(1800, 1, 1),
    )
    assert searcher.get_date_range([stored_works[-1]]) is None
    assert searcher.get_facet_counts([]) == {key: {} for key in facets}


def test_related_works_exclude_self_and_rank_shared_series(stored_works) -> None:
    searcher = MetadataSearcher()
    assert [
        w.id for w in searcher.get_related_works(stored_works[0], stored_works)
    ] == ["b", "c"]
    assert [
        w.id
        for w in searcher.get_related_works(
            stored_works[0], stored_works, max_results=1
        )
    ] == ["b"]
    assert (
        searcher.get_related_works(stored_works[0], stored_works, max_results=0) == []
    )
    assert searcher.get_related_works(stored_works[-1], stored_works) == []
