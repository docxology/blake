"""Export serialization contracts checked through actual files and readers."""

import csv
import json
from pathlib import Path

import pandas as pd
import pytest

from blake.exceptions import ExportError
from blake.export.formats import BaseExporter, get_exporter
from blake.models import ExportConfig
from tests.export_fixtures import export_work


@pytest.mark.asyncio
@pytest.mark.parametrize("format_name", ["json", "csv", "parquet"])
async def test_collection_single_and_analysis_round_trips(
    tmp_path: Path, format_name: str
) -> None:
    rich = export_work(tmp_path / "input")
    empty = export_work(tmp_path / "empty", rich=False)
    before = [w.model_dump(mode="json") for w in [rich, empty]]
    exporter = get_exporter(format_name.upper())
    config = ExportConfig(output_dir=tmp_path, include_images=True)
    collection = await exporter.export_works([rich, empty], tmp_path, config)
    single = await exporter.export_work(rich, tmp_path / ("single." + format_name))
    analysis = await exporter.export_analysis_results(
        [rich, empty], tmp_path / ("analysis." + format_name)
    )
    if format_name == "json":
        rows = json.loads(collection.read_text())
        assert [row["id"] for row in rows] == ["rich", "empty"]
        assert rows[0]["text_content"] == rich.text_content
        assert rows[0]["images"][0]["file_path"] == str(rich.images[0].file_path)
        assert rows[0]["metadata"]["creation_date"] == "1794-01-02T00:00:00"
        assert rows[0]["provenance"]["checksum"] == "a" * 64
        assert rows[1]["metadata"]["creation_date"] is None
        assert json.loads(single.read_text()) == rows[0]
        analyses = json.loads(analysis.read_text())
        assert analyses[0]["text_analysis"] == rich.text_analysis
        assert analyses[1]["visual_analysis"] == {}
    elif format_name == "csv":
        with collection.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert [row["id"] for row in rows] == ["rich", "empty"]
        assert rows[0]["text_length"] == str(len(rich.text_content))
        assert rows[0]["tags"] == "alpha; beta"
        assert rows[0]["source_url"] == rich.metadata.source_url
        assert rows[0]["num_images"] == "1"
        assert rows[1]["creation_date"] == ""
        assert rows[1]["has_text"] == "False"
        with single.open(newline="") as handle:
            assert list(csv.DictReader(handle))[0]["text_content"] == rich.text_content
        with analysis.open(newline="") as handle:
            analyses = list(csv.DictReader(handle))
        assert analyses[0]["word_count"] == "5"
        assert analyses[0]["sentiment_score"] == "0.5"
        assert analyses[1]["word_count"] == ""
    else:
        rows = pd.read_parquet(collection).to_dict("records")
        assert [row["id"] for row in rows] == ["rich", "empty"]
        assert rows[0]["image_count"] == 1
        assert json.loads(rows[0]["metadata"])["checksum"] == "a" * 64
        assert json.loads(rows[0]["themes"]) == ["states", "time"]
        assert rows[1]["creation_date"] is None
        assert pd.read_parquet(single).iloc[0]["id"] == "rich"
        analyses = pd.read_parquet(analysis).to_dict("records")
        assert json.loads(analyses[0]["text_analysis"]) == rich.text_analysis
        assert json.loads(analyses[1]["cross_analysis"]) == {}
    assert [w.model_dump(mode="json") for w in [rich, empty]] == before


@pytest.mark.asyncio
@pytest.mark.parametrize("metadata", [True, False])
@pytest.mark.parametrize("images", [True, False])
@pytest.mark.parametrize("analysis", [True, False])
async def test_json_inclusion_flags_are_independent(
    tmp_path: Path, metadata: bool, images: bool, analysis: bool
) -> None:
    work = export_work(tmp_path / "input")
    path = await get_exporter("json").export_works(
        [work],
        tmp_path,
        ExportConfig(
            output_dir=tmp_path,
            include_metadata=metadata,
            include_images=images,
            include_analysis=analysis,
        ),
    )
    row = json.loads(path.read_text())[0]
    assert (row["metadata"] is not None) is metadata
    assert ("text_content" in row) is metadata
    assert ("images" in row) is images
    assert ("text_analysis" in row) is analysis
    assert row["provenance"]["source_url"] == work.metadata.source_url


@pytest.mark.asyncio
@pytest.mark.parametrize("format_name", ["json", "csv", "parquet"])
async def test_empty_collections_are_readable(tmp_path: Path, format_name: str) -> None:
    path = await get_exporter(format_name).export_works(
        [], tmp_path, ExportConfig(output_dir=tmp_path)
    )
    if format_name == "json":
        assert json.loads(path.read_text()) == []
    elif format_name == "csv":
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            assert "source_url" in reader.fieldnames
            assert list(reader) == []
    else:
        assert pd.read_parquet(path).empty


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method", ["export_work", "export_works", "export_analysis_results"]
)
async def test_abstract_exporters_refuse_without_writing(
    tmp_path: Path, method: str
) -> None:
    work = export_work(tmp_path / "input", rich=False)
    destination = tmp_path / "untouched"
    args = (
        ([work], tmp_path, ExportConfig(output_dir=tmp_path))
        if method == "export_works"
        else ((work if method == "export_work" else [work]), destination)
    )
    with pytest.raises(NotImplementedError):
        await getattr(BaseExporter(), method)(*args)
    assert not destination.exists()


def test_unknown_format_has_actionable_error() -> None:
    with pytest.raises(ExportError, match="Unknown export format: absent"):
        get_exporter("absent")
