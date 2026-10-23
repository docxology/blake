"""Real Streamlit search, evidence refusal and pagination state."""

import json

from streamlit.testing.v1 import AppTest

from blake.metadata.database import MetadataDatabase
from blake.text_search.recovered import build_recovered_search
from tests.export_fixtures import export_work
from tests.gui_fixtures import app_source, seed_gui

pytest_plugins = ["tests.evidence_fixtures"]


def panel(data):
    source = (
        "from pathlib import Path\n"
        "from blake.gui.evidence_panel import render_evidence_panel\n"
        f"render_evidence_panel(Path({str(data)!r}))\n"
    )
    app = AppTest.from_string(source, default_timeout=20).run()
    assert list(app.exception) == []
    return app


def control(elements, label):
    return next(item for item in elements if item.label == label)


def submit(app, text):
    control(app.text_input, "Occurrence query").input(text)
    control(app.button, "Search recovered corpus").click().run()
    assert list(app.exception) == []


def test_panel_discloses_absent_and_invalid_evidence(tmp_path):
    absent = panel(tmp_path)
    assert "No captured recovery manifest" in absent.info[0].value
    assert len(absent.metric) == 0
    (tmp_path / "recovery").mkdir()
    (tmp_path / "recovery/manifest.json").write_text("{")
    damaged = panel(tmp_path)
    assert "manifest cannot be read" in damaged.error[0].value
    assert len(damaged.metric) == 0


def test_manifest_only_view_never_builds_an_index(captured_evidence):
    app = panel(captured_evidence)
    assert any("does not reverify" in item.value for item in app.caption)
    assert any("No recovered-search index" in item.value for item in app.info)
    assert not (captured_evidence / "search").exists()
    assert len(app.text_input) == 0


def test_primary_and_exploratory_search_keep_roles_and_scope(captured_evidence):
    snapshot = build_recovered_search(captured_evidence)
    before = snapshot.index.path.read_bytes()
    app = panel(captured_evidence)
    submit(app, "state")
    assert control(app.metric, "Occurrences in selected scope").value == "2"
    assert any("Blake-primary occurrences: 2" in item.value for item in app.caption)
    assert all("text" not in json.loads(item.value) for item in app.json)
    control(app.selectbox, "Evidence scope").select("exploratory")
    control(app.selectbox, "Source plane").select("erdman")
    submit(app, "Preface")
    assert control(app.metric, "Occurrences in selected scope").value == "1"
    assert any("Blake-primary occurrences: 0" in item.value for item in app.caption)
    assert any("editorial" in item.value for item in app.caption)
    assert snapshot.index.path.read_bytes() == before


def test_search_modes_and_empty_results_use_actual_index(captured_evidence):
    build_recovered_search(captured_evidence)
    app = panel(captured_evidence)
    for mode, text, expected in (
        ("phrase", "Eternity is in love", "1"),
        ("literal", "eternity", "0"),
        ("variants", "states", "2"),
    ):
        control(app.selectbox, "Occurrence mode").select(mode)
        submit(app, text)
        assert not list(app.error), (mode, [item.value for item in app.error])
        assert control(app.metric, "Occurrences in selected scope").value == expected
    control(app.selectbox, "Occurrence mode").select("concept")
    submit(app, "states-and-identity")
    assert any("Editorial concept navigation" in item.value for item in app.caption)
    control(app.selectbox, "Occurrence mode").select("word")
    submit(app, "zzzxqvnegativecontrol")
    assert any("not whole-oeuvre absence" in item.value for item in app.info)


def test_invalid_requests_and_damaged_projection_are_explicit(captured_evidence):
    snapshot = build_recovered_search(captured_evidence)
    app = panel(captured_evidence)
    submit(app, "  ")
    assert "Enter an occurrence query" in app.error[0].value
    control(app.selectbox, "Source plane").select("xml")
    submit(app, "state")
    assert "requires the reading plane" in app.error[0].value
    control(app.selectbox, "Source plane").select("reading")
    raw = bytearray(snapshot.index.path.read_bytes())
    raw[-1] ^= 1
    snapshot.index.path.write_bytes(raw)
    submit(app, "state")
    assert "checksum" in app.error[0].value
    assert snapshot.index.path.read_bytes() == raw
    path = snapshot.directory / "search-manifest.json"
    path.write_text("{")
    corrupt_receipt = panel(captured_evidence)
    assert "receipt cannot be used" in corrupt_receipt.error[0].value


def test_work_pagination_and_search_results_survive_page_changes(tmp_path):
    data = tmp_path / "data"
    database = MetadataDatabase(data / "metadata/metadata.db")
    for number in range(28):
        work = export_work(tmp_path / "input", rich=False)
        work.id = work.metadata.id = f"work-{number:02d}"
        work.metadata.title = f"Work {number:02d}"
        database.save_work(work)
    app = AppTest.from_string(
        app_source(data, tmp_path / "out"), default_timeout=20
    ).run()
    assert list(app.exception) == []
    assert len(app.expander) == 25
    app.selectbox(key="browse:page").select(2).run()
    assert len(app.expander) == 3
    control(app.button, "Search").click().run()
    assert len(app.expander) == 28
    app.selectbox(key="search:page").select(2).run()
    assert list(app.exception) == []
    assert len(app.expander) == 6
    assert any(item.value == "Search Results (28 found)" for item in app.subheader)


def test_work_details_load_only_when_requested_and_keep_distinct_widget_keys(tmp_path):
    data = tmp_path / "data"
    rich, _ = seed_gui(data)
    app = AppTest.from_string(
        app_source(data, tmp_path / "out"), default_timeout=20
    ).run()
    assert list(app.exception) == []
    assert len(app.text_area) == 0
    assert len(app.get("imgs")) == 0
    app.checkbox(key=f"browse:load:{rich.id}").check().run()
    assert len(app.text_area) == 1
    assert len(app.get("imgs")) == 3
    control(app.button, "Search").click().run()
    assert len(app.text_area) == 1
    app.checkbox(key=f"search:load:{rich.id}").check().run()
    assert list(app.exception) == []
    assert len(app.text_area) == 2
    assert all(item.value == rich.text_content for item in app.text_area)
