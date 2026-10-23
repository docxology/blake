"""Export service selection and archive custody on real files."""

import json
import zipfile
from pathlib import Path

import pytest

from blake.exceptions import ExportError
from blake.export import BlakeExporter
from blake.export.formats import get_exporter
from blake.models import ExportConfig
from tests.export_fixtures import export_work


@pytest.mark.asyncio
@pytest.mark.parametrize("compressed", [True, False])
@pytest.mark.parametrize("images", [True, False])
async def test_service_filters_and_packages_only_selected_inputs(
    tmp_path: Path, compressed: bool, images: bool
) -> None:
    rich = export_work(tmp_path / "input")
    empty = export_work(tmp_path / "empty", rich=False)
    originals = {
        p: p.read_bytes()
        for p in (rich.images[0].file_path, rich.images[0].thumbnail_path)
    }
    before = rich.model_dump(mode="json")
    service = BlakeExporter(tmp_path / "storage")
    output = await service.export_works(
        [rich, empty],
        ExportConfig(
            output_dir=tmp_path / "output",
            format="json",
            filter_works=["rich"],
            include_images=images,
            compress=compressed,
        ),
    )
    if compressed:
        assert output.suffix == ".zip"
        assert not output.with_suffix("").exists()
        with zipfile.ZipFile(output) as archive:
            members = archive.namelist()
            payloads = {Path(n).name: archive.read(n) for n in members}
            assert all(
                not Path(n).is_absolute() and ".." not in Path(n).parts for n in members
            )
    else:
        assert output.is_dir()
        payloads = {p.name: p.read_bytes() for p in output.rglob("*") if p.is_file()}
    rows = json.loads(payloads["blake_works.json"])
    assert [row["id"] for row in rows] == ["rich"]
    metadata = json.loads(payloads["export_metadata.json"])
    assert metadata["export_info"]["total_works"] == 1
    assert metadata["export_info"]["include_images"] is images
    assert metadata["works_summary"][0]["provenance"]["checksum"] == "a" * 64
    assert ("rich_plate.png" in payloads) is images
    if images:
        assert payloads["rich_plate.png"] == originals[rich.images[0].file_path]
        assert (
            payloads["rich_plate_thumb.png"] == originals[rich.images[0].thumbnail_path]
        )
    assert rich.model_dump(mode="json") == before
    assert all(p.read_bytes() == value for p, value in originals.items())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method", ["export_work", "export_works", "export_analysis_results"]
)
async def test_unsupported_service_formats_preserve_sources(
    tmp_path: Path, method: str
) -> None:
    work = export_work(tmp_path / "input")
    before = work.model_dump(mode="json")
    service = BlakeExporter(tmp_path / "storage")
    args = (
        ([work], ExportConfig(output_dir=tmp_path / "output", format="absent"))
        if method == "export_works"
        else (
            work if method == "export_work" else [work],
            tmp_path / "untouched",
            "absent",
        )
    )
    with pytest.raises(ExportError, match="Unsupported export format"):
        await getattr(service, method)(*args)
    assert not (tmp_path / "untouched").exists()
    assert work.model_dump(mode="json") == before
    assert set(service.get_export_info()["supported_formats"]) == set(
        service.get_supported_formats()
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("format_name", ["json", "csv", "html", "markdown", "parquet"])
@pytest.mark.parametrize(
    "method", ["export_work", "export_works", "export_analysis_results"]
)
async def test_real_filesystem_error_does_not_modify_inputs(
    tmp_path: Path, format_name: str, method: str
) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_bytes(b"preserve")
    work = export_work(tmp_path / "input")
    before = work.model_dump(mode="json")
    exporter = get_exporter(format_name)
    args = (
        ([work], blocker, ExportConfig(output_dir=blocker))
        if method == "export_works"
        else (work if method == "export_work" else [work], blocker / "report")
    )
    with pytest.raises(OSError):
        await getattr(exporter, method)(*args)
    assert blocker.read_bytes() == b"preserve"
    assert work.model_dump(mode="json") == before
