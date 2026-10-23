"""Native PNG outputs, exact payloads, and explicit render failures."""

import json
from xml.etree import ElementTree
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import pytest

from blake.viz.renderers.image_renderer import ImageRenderer
from blake.viz.renderers.network_renderer import NetworkRenderer
from blake.viz.renderers.temporal_renderer import TemporalRenderer
from blake.viz.renderers.text_renderer import TextRenderer
from tests.renderer_fixtures import renderer_config, renderer_inputs

matplotlib.use("Agg")

SAVED = [
    (TextRenderer, "text", "word_cloud"),
    (TextRenderer, "text", "frequency_chart"),
    (TextRenderer, "text", "sentiment_timeline"),
    (ImageRenderer, "image", "color_palette"),
    (ImageRenderer, "image", "color_evolution"),
    (ImageRenderer, "image", "color_distribution"),
    (ImageRenderer, "image", "image_clustering"),
    (TemporalRenderer, "temporal", "work_timeline"),
    (TemporalRenderer, "temporal", "theme_evolution"),
    (TemporalRenderer, "temporal", "creative_periods"),
    (NetworkRenderer, "network", "thematic_network"),
    (NetworkRenderer, "network", "concept_map"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("cls,family,kind", SAVED)
async def test_real_renderer_persists_decodable_nonblank_png(
    tmp_path: Path, cls, family: str, kind: str
) -> None:
    data = renderer_inputs()[family]
    before = data.model_dump(mode="json")
    output = tmp_path / (kind + ".png")
    existing = plt.get_fignums()
    result = await cls().render(kind, data, renderer_config(kind, output))
    assert result["type"] == kind
    assert result["data"]["saved_path"] == str(output)
    with Image.open(output) as image:
        image.load()
        assert image.format == "PNG"
        assert image.width > 100 and image.height > 100
        assert any(high > low for low, high in image.convert("RGB").getextrema())
    if kind in ("word_cloud", "frequency_chart", "work_timeline"):
        payload = json.loads(output.with_suffix(".json").read_text())
        key = {
            "word_cloud": "words",
            "frequency_chart": "labels",
            "work_timeline": "timeline",
        }[kind]
        assert payload[key]
    assert data.model_dump(mode="json") == before
    assert plt.get_fignums() == existing


@pytest.mark.asyncio
@pytest.mark.parametrize("cls,family,kind", SAVED)
async def test_unwritable_render_is_an_error_and_preserves_other_figures(
    tmp_path: Path, cls, family: str, kind: str
) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_bytes(b"preserve")
    unrelated = plt.figure()
    existing = set(plt.get_fignums())
    try:
        with pytest.raises(OSError):
            await cls().render(
                kind,
                renderer_inputs()[family],
                renderer_config(kind, blocker / "bad.png"),
            )
        assert set(plt.get_fignums()) == existing
        assert blocker.read_bytes() == b"preserve"
        assert not list(tmp_path.glob("*.png"))
    finally:
        for number in set(plt.get_fignums()) - existing:
            plt.close(number)
        plt.close(unrelated)


@pytest.mark.asyncio
async def test_network_layout_is_reproducible_for_identical_input(
    tmp_path: Path,
) -> None:
    data = renderer_inputs()["network"]
    first, second = tmp_path / "first.png", tmp_path / "second.png"
    await NetworkRenderer().render(
        "thematic_network", data, renderer_config("thematic_network", first)
    )
    await NetworkRenderer().render(
        "thematic_network", data, renderer_config("thematic_network", second)
    )
    assert first.read_bytes() == second.read_bytes()


@pytest.mark.asyncio
async def test_cluster_render_does_not_reset_callers_random_state(
    tmp_path: Path,
) -> None:
    original = np.random.get_state()
    try:
        np.random.seed(123)
        before = np.random.get_state()
        await ImageRenderer().render(
            "image_clustering",
            renderer_inputs()["image"],
            renderer_config("image_clustering", tmp_path / "clusters.png"),
        )
        after = np.random.get_state()
        assert before[0] == after[0]
        assert np.array_equal(before[1], after[1])
        assert before[2:] == after[2:]
    finally:
        np.random.set_state(original)


@pytest.mark.asyncio
async def test_invalid_timeline_date_refuses_without_overwriting(
    tmp_path: Path,
) -> None:
    data = renderer_inputs()["temporal"]
    data.timeline_points[0]["date"] = "invalid-date"
    output = tmp_path / "prior.png"
    output.write_bytes(b"preserve")
    try:
        with pytest.raises(ValueError, match="date"):
            await TemporalRenderer().render(
                "work_timeline", data, renderer_config("work_timeline", output)
            )
        assert output.read_bytes() == b"preserve"
    finally:
        plt.close("all")


@pytest.mark.asyncio
async def test_cluster_layout_labels_saved_geometry_as_illustrative(
    tmp_path: Path,
) -> None:
    output = tmp_path / "grouping.svg"
    with matplotlib.rc_context({"svg.fonttype": "none"}):
        result = await ImageRenderer().render(
            "image_clustering",
            renderer_inputs()["image"],
            renderer_config("image_clustering", output),
        )
    visible_text = " ".join(ElementTree.parse(output).getroot().itertext())
    assert "positions and distances are not measured" in visible_text
    assert "Synthetic layout position" in visible_text
    layout = result["metadata"]["layout"]
    assert layout["kind"] == "illustrative_grouping"
    assert layout["positions_are_measured"] is False
    assert "not analytical evidence" in layout["note"]
    assert [cluster["size"] for cluster in result["data"]["clusters"]] == [2, 1]
