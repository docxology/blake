from pathlib import Path

from blake.text_search import PassageIndex, Query
from blake.text_search.recovered_cli import query_payload
from blake.text_search.recovered import build_recovered_search
from tests import test_recovered_search

captured = test_recovered_search.captured


def test_private_display_bounds_bodies_and_matches_without_reducing_totals(
    captured: Path, tmp_path: Path
) -> None:
    snapshot = build_recovered_search(captured)
    passage = (
        snapshot.index.search(Query(text="state"))
        .hits[0]
        .passage.model_copy(update={"text": "state " * 30})
    )
    index = PassageIndex(tmp_path / "display.sqlite")
    index.build([passage])
    result = index.search(Query(text="state"))

    private = query_payload(result, private=True)
    public = query_payload(result, private=False)

    assert private["total_occurrences"] == public["total_occurrences"] == 30
    assert public["hits"][0]["passage"]["text"] == passage.text
    hit = private["hits"][0]
    assert "text" not in hit["passage"]
    assert hit["match_count"] == 30
    assert len(hit["matches"]) == 20
    assert hit["matches_truncated"]
    for match in hit["matches"]:
        assert len(match["context"]) <= 245
        assert passage.text[match["start"] : match["end"]] == "state"
        assert (
            passage.text[match["context_start"] : match["context_end"]]
            == match["context"]
        )
