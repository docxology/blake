"""Human-readable exports checked against their source expressions."""

import importlib.util
from pathlib import Path

from bs4 import BeautifulSoup
import pytest

from blake.exceptions import ExportError
from blake.export.formats import get_exporter
from blake.models import ExportConfig
from tests.export_fixtures import export_work


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method", ["export_work", "export_works", "export_analysis_results"]
)
async def test_html_preserves_literal_title_and_description(
    tmp_path: Path, method: str
) -> None:
    work = export_work(tmp_path / "input")
    work.metadata.title = "Export <Study> & Notes"
    work.metadata.description = "An <original> & literal description"
    work.metadata.themes = ["one <two>", "three & four"]
    work.text_content = "A <B> & C."
    before = work.model_dump(mode="json")
    exporter = get_exporter("html")
    output = tmp_path / "report.html"
    if method == "export_works":
        path = await exporter.export_works(
            [work], tmp_path, ExportConfig(output_dir=tmp_path)
        )
    else:
        path = await getattr(exporter, method)(
            work if method == "export_work" else [work], output
        )
    document = BeautifulSoup(path.read_text(), "html.parser")
    heading = document.find("h1" if method == "export_work" else "h3")
    assert heading.get_text() == work.metadata.title
    assert document.find("study") is None
    if method != "export_analysis_results":
        assert work.metadata.description in document.get_text()
        assert "one <two>, three & four" in document.get_text()
    if method == "export_work":
        assert document.select_one(".work-text").get_text() == work.text_content
    assert work.model_dump(mode="json") == before


@pytest.mark.asyncio
@pytest.mark.parametrize("format_name,limit", [("html", 2000), ("markdown", 1000)])
async def test_long_single_exports_disclose_preview_and_keep_input(
    tmp_path: Path, format_name: str, limit: int
) -> None:
    work = export_work(tmp_path / "input")
    work.text_content = "a" * (limit + 1) + "UNIQUE END"
    before = work.text_content
    output = await get_exporter(format_name).export_work(
        work, tmp_path / ("preview." + format_name)
    )
    assert "a" * limit + "..." in output.read_text()
    assert "UNIQUE END" not in output.read_text()
    assert work.text_content == before


@pytest.mark.asyncio
@pytest.mark.parametrize("format_name", ["html", "markdown", "md"])
async def test_collection_and_analysis_keep_counts_and_empty_works(
    tmp_path: Path, format_name: str
) -> None:
    rich = export_work(tmp_path / "input")
    empty = export_work(tmp_path / "empty", rich=False)
    exporter = get_exporter(format_name)
    collection = await exporter.export_works(
        [rich, empty],
        tmp_path,
        ExportConfig(output_dir=tmp_path, include_analysis=False),
    )
    analysis = await exporter.export_analysis_results(
        [rich, empty], tmp_path / ("analysis." + format_name)
    )
    text = collection.read_text()
    details = analysis.read_text()
    assert "Empty" in text and "Empty" in details
    assert "5" in details and "positive" in details.lower()
    assert "2" in text
    assert "0.75" in details
    if format_name == "html":
        document = BeautifulSoup(text, "html.parser")
        assert [s.get_text() for s in document.select(".stat-number")] == [
            "2",
            "1",
            "1",
        ]
        assert "Words:" not in document.get_text()
        assert document.find("title").get_text() == "William Blake Works Collection"
    else:
        assert "| Total Works | 2 |" in text
        assert "5 words" not in text
        assert "**Checksum:** " + "a" * 64 in text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method", ["export_work", "export_works", "export_analysis_results"]
)
async def test_pdf_failure_is_explicit_and_preserves_existing_bytes(
    tmp_path: Path, method: str
) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_bytes(b"preserve")
    work = export_work(tmp_path / "input")
    exporter = get_exporter("pdf")
    args = (
        ([work], blocker, ExportConfig(output_dir=blocker))
        if method == "export_works"
        else (work if method == "export_work" else [work], blocker / "report.pdf")
    )
    if importlib.util.find_spec("reportlab") is None:
        with pytest.raises(ExportError, match="reportlab not available"):
            await getattr(exporter, method)(*args)
    else:
        with pytest.raises(OSError):
            await getattr(exporter, method)(*args)
    assert blocker.read_bytes() == b"preserve"
    assert list(tmp_path.glob("*.pdf")) == []
