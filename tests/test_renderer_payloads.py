"""Renderer data contracts and empty/unsupported controls."""

import pytest

from blake.viz.models import ImageData, NetworkData, TemporalData, TextData
from blake.viz.renderers.comparative_renderer import ComparativeRenderer
from blake.viz.renderers.image_renderer import ImageRenderer
from blake.viz.renderers.network_renderer import NetworkRenderer
from blake.viz.renderers.temporal_renderer import TemporalRenderer
from blake.viz.renderers.text_renderer import TextRenderer
from tests.renderer_fixtures import renderer_config, renderer_inputs


@pytest.mark.asyncio
async def test_text_payloads_keep_exact_values_and_fallback_ids() -> None:
    renderer = TextRenderer()
    data = renderer_inputs()["text"]
    cloud = await renderer.render("word_cloud", data, renderer_config("word_cloud"))
    assert cloud["data"]["words"] == [
        {"text": "state", "weight": 4},
        {"text": "time", "weight": 2},
    ]
    frequency = await renderer.render(
        "frequency_chart", data, renderer_config("frequency_chart")
    )
    assert frequency["data"]["labels"] == ["state", "time"]
    assert frequency["data"]["values"] == [4, 2]
    timeline = await renderer.render(
        "sentiment_timeline", data, renderer_config("sentiment_timeline")
    )
    assert timeline["data"]["statistics"] == {
        "average_sentiment": 0,
        "positive_works": 1,
        "negative_works": 1,
        "neutral_works": 1,
    }
    heatmap = await renderer.render(
        "sentiment_heatmap", data, renderer_config("sentiment_heatmap")
    )
    assert [r["category"] for r in heatmap["data"]["heatmap"]] == [
        "positive",
        "negative",
        "neutral",
    ]
    assert heatmap["data"]["heatmap"][-1]["work_id"] == "work_2"
    evolution = await renderer.render(
        "style_evolution", data, renderer_config("style_evolution")
    )
    assert evolution["data"]["evolution"][0]["avg_word_length"] == 4
    comparison = await renderer.render(
        "style_comparison", data, renderer_config("style_comparison")
    )
    assert comparison["data"]["comparison"]["metrics"]["vocabulary_richness"] == 0.75


@pytest.mark.asyncio
async def test_image_payloads_keep_counts_dimensions_thresholds_and_membership() -> (
    None
):
    renderer = ImageRenderer()
    data = renderer_inputs()["image"]
    palette = await renderer.render(
        "color_palette", data, renderer_config("color_palette")
    )
    assert palette["data"]["colors"] == [
        {"color": "#ff0000", "count": 2},
        {"color": "#00ff00", "count": 1},
    ]
    evolution = await renderer.render(
        "color_evolution", data, renderer_config("color_evolution")
    )
    assert [r["brightness"] for r in evolution["data"]["evolution"]] == [10, 20, 0]
    composition = await renderer.render(
        "composition_analysis", data, renderer_config("composition_analysis")
    )
    assert composition["data"]["compositions"][0]["composition"] == {"balance": 0.5}
    ratios = await renderer.render(
        "golden_ratio_analysis", data, renderer_config("golden_ratio_analysis")
    )
    assert ratios["data"]["statistics"]["average_golden_ratio"] == pytest.approx(0.6)
    assert ratios["data"]["analysis"][-1]["aspect_ratio"] == 1
    similarity = await renderer.render(
        "image_similarity_network", data, renderer_config("image_similarity_network")
    )
    assert similarity["data"]["edges"] == [
        {"source": "0", "target": "1", "weight": 0.7}
    ]
    clusters = await renderer.render(
        "image_clustering", data, renderer_config("image_clustering")
    )
    assert [r["size"] for r in clusters["data"]["clusters"]] == [2, 1]
    distribution = await renderer.render(
        "color_distribution", data, renderer_config("color_distribution")
    )
    assert distribution["data"]["distribution"][2]["colors"] == []


@pytest.mark.asyncio
async def test_temporal_payloads_preserve_identity_counts_and_source_order() -> None:
    renderer = TemporalRenderer()
    data = renderer_inputs()["temporal"]
    timeline = await renderer.render(
        "work_timeline", data, renderer_config("work_timeline")
    )
    assert [r["work_id"] for r in timeline["data"]["timeline"]] == [
        str(i) for i in range(6)
    ]
    themes = await renderer.render(
        "theme_evolution", data, renderer_config("theme_evolution")
    )
    assert [r["work_count"] for r in themes["data"]["themes"]] == [2, 1]
    periods = await renderer.render(
        "creative_periods", data, renderer_config("creative_periods")
    )
    assert periods["metadata"]["period_count"] == 2
    network = await renderer.render(
        "chronological_network", data, renderer_config("chronological_network")
    )
    assert network["metadata"]["edge_count"] == 10
    phases = await renderer.render(
        "development_phases", data, renderer_config("development_phases")
    )
    assert [r["work_count"] for r in phases["data"]["phases"]] == [5, 1]


@pytest.mark.asyncio
async def test_network_payloads_retain_statistics_and_declared_communities() -> None:
    renderer = NetworkRenderer()
    data = renderer_inputs()["network"]
    thematic = await renderer.render(
        "thematic_network", data, renderer_config("thematic_network")
    )
    assert thematic["data"]["network"]["statistics"]["average_degree"] == pytest.approx(
        4 / 3
    )
    concepts = await renderer.render(
        "concept_map", data, renderer_config("concept_map")
    )
    assert concepts["data"]["map"]["centrality"] == {"degree": [0.5, 1, 0.5]}
    influence = await renderer.render(
        "influence_network", data, renderer_config("influence_network")
    )
    assert influence["metadata"]["community_count"] == 2
    citations = await renderer.render(
        "citation_network", data, renderer_config("citation_network")
    )
    assert citations["data"]["citation_counts"] == [1, 2, 1]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind,key",
    [
        ("side_by_side_comparison", "left"),
        ("parallel_analysis", "dimensions"),
        ("source_comparison", "sources"),
        ("metadata_analysis", "fields"),
    ],
)
async def test_comparative_payloads_preserve_supplied_comparison_values(
    kind: str, key: str
) -> None:
    data = renderer_inputs()["comparative"]
    result = await ComparativeRenderer().render(kind, data, renderer_config(kind))
    assert result["data"][key] == data[key]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cls,data",
    [
        (TextRenderer, TextData(texts=[], metadata=[])),
        (ImageRenderer, ImageData(images=[], metadata=[])),
        (TemporalRenderer, TemporalData(works=[], dates=[])),
        (NetworkRenderer, NetworkData(nodes=[], edges=[])),
        (ComparativeRenderer, {}),
    ],
)
async def test_every_registered_renderer_handles_empty_inputs_and_rejects_unknown(
    cls, data
) -> None:
    renderer = cls()
    supported = renderer.get_supported_types()
    supported.append("unsupported")
    assert "unsupported" not in renderer.get_supported_types()
    for kind in renderer.get_supported_types():
        result = await renderer.render(kind, data, renderer_config(kind))
        assert result["type"] == kind
        assert result["data"].get("saved_path") is None
        for key, value in result["metadata"].items():
            if key.endswith("_count"):
                assert value == 0
    with pytest.raises(ValueError, match="Unsupported"):
        await renderer.render("unsupported", data, renderer_config("word_cloud"))
    renderer.supported_types.append("missing_method")
    with pytest.raises(ValueError, match="method not found"):
        await renderer.render("missing_method", data, renderer_config("word_cloud"))
