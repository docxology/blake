"""Native component state over a real synthetic SQLite corpus."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from blake.metadata.database import MetadataDatabase
from tests.gui_fixtures import seed_gui


def by_label(elements, label):
    return next(element for element in elements if element.label == label)


def component_app(data: Path, component: str, extra: str = ""):
    return (
        "from pathlib import Path\n"
        "import streamlit as st\n"
        "from blake.gui.components import WorkBrowser, AnalysisViewer, SearchInterface\n"
        "from blake.gui.gui import BlakeGUI\n"
        "from blake.metadata.database import MetadataDatabase\n"
        f"data = Path({str(data)!r})\n"
        "database = MetadataDatabase(data / 'metadata/metadata.db')\n"
        "works = database.load_all_works()\n" + extra + "\n" + component + "\n"
    )


def run(source):
    app = AppTest.from_string(source, default_timeout=20).run()
    assert list(app.exception) == []
    return app


def test_browser_renders_and_filters_real_records(tmp_path):
    data = tmp_path / "data"
    rich, empty = seed_gui(data)
    rich.metadata.processed = True
    MetadataDatabase(data / "metadata/metadata.db").save_work(rich)
    app = run(component_app(data, "WorkBrowser().render(works)"))
    assert len(app.expander) == 2
    markdown = "\n".join(item.value for item in app.markdown)
    for value in (
        rich.metadata.description,
        "Images:",
        "Text:",
        "Processed",
        "Unknown",
    ):
        assert value in markdown
    by_label(app.selectbox, "Work Type").select("letter").run()
    assert list(app.exception) == []
    assert len(app.expander) == 1 and empty.metadata.title in app.expander[0].label
    by_label(app.selectbox, "Source").select("project_gutenberg").run()
    assert len(app.expander) == 1
    by_label(app.selectbox, "Work Type").select("All").run()
    assert len(app.expander) == 2
    no_works = run(component_app(data, "WorkBrowser().render([])"))
    assert no_works.warning[0].value == "No works found."


def test_analysis_component_shows_saved_values_and_handles_sparse_records(tmp_path):
    data = tmp_path / "data"
    rich, _ = seed_gui(data)
    database = MetadataDatabase(data / "metadata/metadata.db")
    database.save_analysis_result(
        rich.id,
        "visual",
        {
            "plate": {"basic_properties": {"width": 4, "height": 2, "aspect_ratio": 2}},
            "note": "retained non-image value",
            "unmeasured": {},
        },
    )
    database.save_analysis_result(
        rich.id,
        "cross",
        {
            "text_image_correlation": {"jaccard_similarity": 0.25},
        },
    )
    source = component_app(
        data, "AnalysisViewer().render(next(w for w in works if w.id == 'rich'))"
    )
    app = run(source)
    assert by_label(app.metric, "Word Count").value == "5"
    assert by_label(app.metric, "Sentences").value == "2"
    assert by_label(app.metric, "Vocabulary Richness").value == "0.75"
    markdown = "\n".join(item.value for item in app.markdown)
    for value in ("positive", "0.500", "4x2", "2.00", "0.250"):
        assert value in markdown
    database.save_analysis_result(rich.id, "text", {"sentiment": {}})
    database.save_analysis_result(
        rich.id, "visual", {"plate": {"basic_properties": {}}}
    )
    database.save_analysis_result(rich.id, "cross", {"text_image_correlation": {}})
    sparse = run(source)
    markdown = "\n".join(item.value for item in sparse.markdown)
    assert "Unknown" in markdown and "0x0" in markdown
    assert len(sparse.metric) == 0
    database.save_analysis_result(rich.id, "text", {"note": "no measured stats"})
    database.save_analysis_result(rich.id, "cross", {"note": "no measured correlation"})
    assert list(run(source).exception) == []
    empty = run(
        component_app(
            data, "AnalysisViewer().render(next(w for w in works if w.id == 'empty'))"
        )
    )
    assert len(empty.subheader) == 1 and len(empty.metric) == 0


def test_search_component_filters_use_actual_gui_adapter(tmp_path):
    data = tmp_path / "data"
    seed_gui(data)
    extra = (
        "gui = BlakeGUI(data, data / 'output')\n"
        "def search(query, filters):\n"
        "    st.session_state['result_ids'] = [w.id for w in gui._search_works(query, filters)]\n"
    )
    app = run(component_app(data, "SearchInterface().render(search)", extra))
    by_label(app.button, "Search").click().run()
    assert sorted(app.session_state["result_ids"]) == ["empty", "rich"]
    by_label(app.multiselect, "Work Types").select("letter")
    by_label(app.button, "Search").click().run()
    assert app.session_state["result_ids"] == ["empty"]
    by_label(app.multiselect, "Work Types").select("poem")
    by_label(app.multiselect, "Sources").select("blake_archive")
    by_label(app.button, "Search").click().run()
    assert app.session_state["result_ids"] == []
    by_label(app.multiselect, "Sources").select("project_gutenberg")
    by_label(app.selectbox, "Has Images").select("Yes")
    by_label(app.selectbox, "Has Text").select("Yes")
    by_label(app.button, "Search").click().run()
    assert app.session_state["result_ids"] == ["rich"]
    by_label(app.selectbox, "Has Images").select("No")
    by_label(app.selectbox, "Has Text").select("No")
    by_label(app.button, "Search").click().run()
    assert app.session_state["result_ids"] == ["empty"]
    by_label(app.text_input, "Search Query").input("unfindable-token")
    by_label(app.button, "Search").click().run()
    assert app.session_state["result_ids"] == []
    assert list(app.exception) == []
