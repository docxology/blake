"""Terminal workflows use native Rich prompts and the actual local corpus API."""

import importlib.util
import io
import json
from pathlib import Path

from rich.console import Console
import pytest

from blake.interactive_orchestrator import InteractiveOrchestrator
from tests import interactive_fixtures

terminal_case = interactive_fixtures.terminal_case


@pytest.mark.asyncio
async def test_work_summary_statistics_and_settings_accept_saved_string_enums(
    terminal_case,
) -> None:
    orchestrator, capture, _ = await terminal_case()
    works = await orchestrator.blake.get_all_works()
    await orchestrator.show_works_summary(works)
    await orchestrator.show_works_statistics(works)
    await orchestrator.show_settings()
    text = capture.getvalue()
    assert "poem" in text and "letter" in text
    assert "Total Works: 2" in text
    assert "Data Directory:" in text and str(orchestrator.data_dir) in text


@pytest.mark.asyncio
async def test_empty_workflows_disclose_absence_without_consuming_analysis_input(
    terminal_case,
) -> None:
    orchestrator, capture, stream = await terminal_case(populated=False)
    await orchestrator.view_available_works()
    await orchestrator.run_text_analysis()
    await orchestrator.show_analysis_summary([])
    text = capture.getvalue()
    assert "No works available" in text
    assert "No works available for analysis" in text
    assert stream.tell() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query,expected",
    [
        ("state\n", "Found 1 works"),
        ("zzzxqv\n", "No works found"),
        ("\n", "cannot be empty"),
    ],
)
async def test_search_prompt_uses_saved_corpus_results(
    terminal_case, query: str, expected: str
) -> None:
    orchestrator, capture, stream = await terminal_case(query)
    await orchestrator.search_works()
    assert expected in capture.getvalue()
    assert stream.tell() == len(query)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "choice,extension", [("1", "json"), ("2", "csv"), ("3", "pdf")]
)
async def test_export_reports_success_only_for_a_real_artifact(
    terminal_case, choice: str, extension: str
) -> None:
    orchestrator, capture, _ = await terminal_case(choice + "\n")
    before = [
        w.model_dump(mode="json") for w in await orchestrator.blake.get_all_works()
    ]
    result = await orchestrator.export_data()
    if extension == "pdf" and importlib.util.find_spec("reportlab") is None:
        assert result is None
        assert "Export failed" in capture.getvalue()
        assert "successfully" not in capture.getvalue().split("Data Export", 1)[-1]
        assert not list(orchestrator.output_dir.rglob("*.pdf"))
    else:
        assert result.is_dir()
        files = list(result.glob("blake_works." + extension))
        assert len(files) == 1
        metadata = json.loads((result / "export_metadata.json").read_text())
        assert metadata["export_info"]["total_works"] == 2
        assert metadata["export_info"]["format"] == extension
        if extension == "json":
            rows = json.loads(files[0].read_text())
            assert {row["id"] for row in rows} == {"empty", "rich"}
            rich = next(row for row in rows if row["id"] == "rich")
            assert rich["text_content"] == 'State, "quoted"\nAlbion’s & time.'
            assert rich["provenance"]["source_url"] == "https://example.test/synthetic"
            assert rich["provenance"]["rights_disposition"] == "conditional_corroboration_required"
        assert str(result) in capture.getvalue()
    assert [
        w.model_dump(mode="json") for w in await orchestrator.blake.get_all_works()
    ] == before


@pytest.mark.asyncio
@pytest.mark.parametrize("score_key", ["compound_score", "compound"])
@pytest.mark.parametrize(
    "topic_records",
    [["state", "time"], {"topics": [{"words": ["state"]}, {"words": ["time"]}]}],
)
async def test_analysis_summary_uses_saved_score_and_topic_records(
    terminal_case, score_key, topic_records
) -> None:
    orchestrator, capture, _ = await terminal_case()
    database = orchestrator.blake.metadata_manager.database
    database.save_analysis_result(
        "rich",
        "text",
        {
            "sentiment": {score_key: 0.5},
            "topics": topic_records,
        },
    )
    await orchestrator.show_analysis_summary(await orchestrator.blake.get_all_works())
    text = capture.getvalue()
    assert "Average Sentiment: 0.50" in text
    assert "Distinct Saved Topic Records: 2" in text
    assert "Total Saved Topic Records: 2" in text


@pytest.mark.asyncio
async def test_view_dashboards_can_decline_creation(terminal_case) -> None:
    orchestrator, capture, stream = await terminal_case("n\n")
    await orchestrator.view_dashboards()
    assert "research" in capture.getvalue()
    assert stream.tell() == 2
    assert "Failed" not in capture.getvalue()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "choice,name", [("1", "Research"), ("2", "Educational"), ("3", "Public")]
)
async def test_dashboard_actions_build_real_components(
    terminal_case, choice: str, name: str
) -> None:
    orchestrator, capture, _ = await terminal_case(choice + "\n")
    await orchestrator.create_dashboard()
    text = capture.getvalue()
    assert name + " Dashboard created successfully" in text
    assert "Components: 0" not in text
    assert "Components: Unknown" not in text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "choice,name", [("1", "Research"), ("2", "Educational"), ("3", "Public")]
)
async def test_report_actions_return_real_report_identity(
    terminal_case, choice: str, name: str
) -> None:
    orchestrator, capture, _ = await terminal_case(choice + "\n")
    await orchestrator.generate_reports()
    assert name + " Report generated successfully" in capture.getvalue()
    assert "Report ID: Unknown" not in capture.getvalue()


@pytest.mark.asyncio
async def test_visualization_prompt_builds_actual_word_counts(terminal_case) -> None:
    orchestrator, capture, _ = await terminal_case("1\n")
    await orchestrator.create_visualizations()
    text = capture.getvalue()
    assert "created successfully" in text
    assert "Visualization creation failed" not in text
    assert "TextRenderer" in text


@pytest.mark.asyncio
async def test_menu_settings_and_exit_use_owned_prompt_stream(terminal_case) -> None:
    orchestrator, capture, stream = await terminal_case("14\n\n15\ny\n")
    await orchestrator.run()
    text = capture.getvalue()
    assert "Main Menu" in text and "Current Settings:" in text and "Goodbye!" in text
    assert "An error occurred" not in text
    assert stream.tell() == len("14\n\n15\ny\n")


@pytest.mark.asyncio
async def test_initialization_filesystem_failure_is_explicit(tmp_path: Path) -> None:
    blocker = tmp_path / "blocked"
    blocker.write_bytes(b"preserve")
    capture = io.StringIO()
    orchestrator = InteractiveOrchestrator(
        str(blocker), output_dir=tmp_path / "out", console=Console(file=capture)
    )
    with pytest.raises(SystemExit) as exc:
        await orchestrator.initialize()
    assert exc.value.code == 1
    assert blocker.read_bytes() == b"preserve"
    assert "Failed to initialize" in capture.getvalue()
