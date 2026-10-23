"""Native Streamlit tree/state checks over real local SQLite records."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tests.gui_fixtures import app_source, seed_gui


def by_label(elements, label):
    return next(element for element in elements if element.label == label)


def assert_no_exceptions(app):
    assert list(app.exception) == []


def test_gui_import_and_run_are_single_and_load_real_records(tmp_path: Path) -> None:
    data, output = tmp_path / "data", tmp_path / "out"
    rich, empty = seed_gui(data)
    app = AppTest.from_string(app_source(data, output), default_timeout=20).run()
    assert_no_exceptions(app)
    assert len(app.title) == 1
    assert by_label(app.metric, "Local records").value == "2"
    assert any(rich.metadata.title in expander.label for expander in app.expander)
    assert any(empty.metadata.title in expander.label for expander in app.expander)


def test_gui_loader_and_json_export_use_saved_record_identity(tmp_path: Path) -> None:
    from blake.gui.gui import BlakeGUI

    data = tmp_path / "data"
    seed_gui(data)
    gui = BlakeGUI(data, tmp_path / "out")
    works = sorted(gui._load_works(), key=lambda work: work.id)
    assert [work.id for work in works] == ["empty", "rich"]
    before = [work.model_dump(mode="json") for work in works]
    payload = gui._prepare_export_data(works, "JSON")
    assert [row["id"] for row in payload] == ["empty", "rich"]
    assert payload[1]["text_content"] == works[1].text_content
    assert len(payload[1]["images"]) == 4
    assert payload[1]["provenance"]["source_url"] == works[1].metadata.source_url
    assert [work.model_dump(mode="json") for work in works] == before


def test_gui_search_keeps_multiple_selected_types_and_avoids_duplicate_widgets(
    tmp_path: Path,
) -> None:
    data, output = tmp_path / "data", tmp_path / "out"
    seed_gui(data)
    app = AppTest.from_string(app_source(data, output), default_timeout=20).run()
    assert_no_exceptions(app)
    app.multiselect[0].select("poem").select("letter")
    by_label(app.button, "Search").click().run()
    assert_no_exceptions(app)
    assert any(item.value == "Search Results (2 found)" for item in app.subheader)
    by_label(app.text_input, "Search Query").input("zzzxqvnegativecontrol")
    by_label(app.button, "Search").click().run()
    assert_no_exceptions(app)
    assert any(item.value == "Search Results (0 found)" for item in app.subheader)


@pytest.mark.parametrize(
    "choice,expected",
    [
        ("Theme Analysis", "Most Common Themes"),
        ("Chronological Analysis", "1794-01-02"),
        ("Text Analysis", "Compound Score"),
        ("Visual Analysis", "Analyzed Images"),
        ("Cross Analysis", "Works with Text and Images"),
    ],
)
def test_gui_native_analysis_views_show_actual_saved_values(
    tmp_path: Path, choice: str, expected: str
) -> None:
    data, output = tmp_path / "data", tmp_path / "out"
    seed_gui(data)
    app = AppTest.from_string(app_source(data, output), default_timeout=20).run()
    assert_no_exceptions(app)
    by_label(app.selectbox, "Analysis Type").select(choice).run()
    assert_no_exceptions(app)
    assert any(expected in item.value for item in app.markdown)
    if choice == "Text Analysis":
        assert by_label(app.metric, "Word Count").value == "5"
    if choice == "Cross Analysis":
        assert any(json.loads(item.value) == {"links": ["test"]} for item in app.json)


@pytest.mark.parametrize(
    "choice,warning",
    [
        ("Theme Analysis", "No themes found"),
        ("Chronological Analysis", "No works with creation dates"),
        ("Text Analysis", "No works with text content"),
        ("Visual Analysis", "No images found"),
        ("Cross Analysis", "No works with both text and images"),
    ],
)
def test_gui_native_analysis_discloses_missing_evidence(
    tmp_path: Path, choice: str, warning: str
) -> None:
    data, output = tmp_path / "data", tmp_path / "out"
    seed_gui(data, empty_only=True)
    app = AppTest.from_string(app_source(data, output), default_timeout=20).run()
    assert_no_exceptions(app)
    by_label(app.selectbox, "Analysis Type").select(choice).run()
    assert_no_exceptions(app)
    assert any(warning in item.value for item in app.warning)


def test_gui_export_creates_real_download_control(tmp_path: Path) -> None:
    data, output = tmp_path / "data", tmp_path / "out"
    seed_gui(data)
    app = AppTest.from_string(app_source(data, output), default_timeout=20).run()
    assert_no_exceptions(app)
    by_label(app.button, "Export Data").click().run()
    assert_no_exceptions(app)
    downloads = app.get("download_button")
    assert len(downloads) == 1
    assert downloads[0].proto.label == "Download JSON"
