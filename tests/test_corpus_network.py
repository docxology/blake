"""Network inputs match real categorized entities and scored model themes."""

import pytest

from blake.corpus.pipeline import BlakeCorpus
from blake.corpus.visualizations import CorpusVisualizationBuilder
from tests.export_fixtures import export_work


@pytest.mark.parametrize(
    "builder",
    [
        BlakeCorpus._build_theme_entity_network,
        CorpusVisualizationBuilder._theme_entity_network,
    ],
)
def test_network_uses_entity_values_and_deduplicates_record_links(tmp_path, builder):
    work = export_work(tmp_path)
    work.metadata.themes = ["nature", "nature"]
    work.text_analysis = {
        "themes": {"themes": [("nature", 4), ("vision", 2)]},
        "entities": {
            "persons": ["Albion", "Albion"],
            "places": ["London"],
            "organizations": [],
            "other": ["Albion"],
        },
    }
    graph = builder(None, [work])
    labels = {node["label"] for node in graph["nodes"]}
    assert {"nature", "vision", "Albion", "London"} <= labels
    assert not {"persons", "places", "organizations", "other"} & labels
    assert len(graph["edges"]) == 4
    theme = next(edge for edge in graph["edges"] if edge["target"] == "theme:nature")
    assert theme["sources"] == ["metadata", "text_analysis"]


def test_network_retains_legacy_entities_and_rejects_empty_labels(tmp_path):
    work = export_work(tmp_path)
    work.text_analysis = {
        "entities": [{"text": "Albion"}, "London", {"text": ""}, None]
    }
    graph = BlakeCorpus._build_theme_entity_network(None, [work])
    assert {node["label"] for node in graph["nodes"] if node["type"] == "entity"} == {
        "Albion",
        "London",
    }
