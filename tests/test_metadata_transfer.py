"""Metadata transfers retain all saved analysis planes and reject invalid inputs."""

import json
import hashlib

import pytest

from blake.exceptions import MetadataError
from blake.metadata.manager import MetadataManager
from tests.test_metadata_manager_native import manager_work


@pytest.mark.asyncio
async def test_export_import_restores_each_analysis_plane(tmp_path):
    source, work = manager_work(tmp_path)
    work.metadata.processed = True
    work.ontological_analysis = {"concepts": ["synthetic-state"]}
    await source.save_work(work)
    for kind, field in (
        ("text", "text_analysis"),
        ("visual", "visual_analysis"),
        ("cross", "cross_analysis"),
        ("ontology", "ontological_analysis"),
    ):
        await source.save_analysis_result(work.id, kind, getattr(work, field))
    export = tmp_path / "metadata.json"
    await source.export_metadata(export)
    raw = json.loads(export.read_text())
    assert raw[0]["ontological_analysis"] == work.ontological_analysis
    assert raw[0]["fully_processed"] is True
    assert raw[0]["metadata"]["source_url"] == str(work.metadata.source_url)
    assert raw[0]["metadata"]["usage_terms"] == "Synthetic test record"
    destination = MetadataManager(tmp_path / "restored")
    imported = await destination.import_metadata(export)
    assert len(imported) == 1
    restored = await destination.load_work(work.id)
    for field in (
        "text_content",
        "text_analysis",
        "visual_analysis",
        "cross_analysis",
        "ontological_analysis",
        "fully_processed",
    ):
        assert getattr(restored, field) == getattr(work, field)
    assert restored.metadata.source_id == work.metadata.source_id
    assert (
        restored.images[0].file_path.read_bytes()
        == work.images[0].file_path.read_bytes()
    )
    subset = tmp_path / "empty.json"
    await source.export_metadata(subset, works=[])
    assert json.loads(subset.read_text()) == []
    assert await destination.import_metadata(subset) == []


@pytest.mark.parametrize("contents", ["{", "{}", '[{"id":"invalid"}]'])
@pytest.mark.asyncio
async def test_invalid_metadata_does_not_change_existing_records(tmp_path, contents):
    manager, work = manager_work(tmp_path)
    await manager.save_work(work)
    before = manager.database.db_path.read_bytes()
    transfer = tmp_path / "invalid.json"
    transfer.write_text(contents)
    with pytest.raises(MetadataError):
        await manager.import_metadata(transfer)
    assert manager.database.db_path.read_bytes() == before
    assert transfer.read_text() == contents


@pytest.mark.asyncio
async def test_invalid_later_record_is_validated_before_any_save(tmp_path):
    manager, work = manager_work(tmp_path)
    transfer = tmp_path / "mixed.json"
    transfer.write_text(json.dumps([work.model_dump(mode="json"), {"id": "invalid"}]))
    before = manager.database.db_path.read_bytes()
    with pytest.raises(MetadataError):
        await manager.import_metadata(transfer)
    assert manager.database.db_path.read_bytes() == before
    assert await manager.load_all_works() == []


@pytest.mark.asyncio
async def test_transfer_io_failure_is_reported(tmp_path):
    manager, work = manager_work(tmp_path)
    with pytest.raises(MetadataError, match="import"):
        await manager.import_metadata(tmp_path / "missing.json")
    with pytest.raises(MetadataError, match="export"):
        await manager.export_metadata(tmp_path / "absent/output.json", [work])
    assert not (tmp_path / "absent").exists()


@pytest.mark.asyncio
async def test_imported_text_refuses_symlink_storage(tmp_path):
    manager, work = manager_work(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_text("retain")
    destination = MetadataManager(tmp_path / "restored")
    (destination.data_dir / "texts").symlink_to(outside, target_is_directory=True)
    transfer = tmp_path / "transfer.json"
    await manager.export_metadata(transfer, [work])
    before = destination.database.db_path.read_bytes()
    with pytest.raises(MetadataError, match="symlink"):
        await destination.import_metadata(transfer)
    assert destination.database.db_path.read_bytes() == before
    assert [path.name for path in outside.iterdir()] == ["sentinel.txt"]
    assert sentinel.read_text() == "retain"


@pytest.mark.asyncio
async def test_imported_text_uses_owned_content_path_not_work_id(tmp_path):
    manager, work = manager_work(tmp_path)
    work.id = work.metadata.id = "../../escape"
    work.images = []
    transfer = tmp_path / "transfer.json"
    await manager.export_metadata(transfer, [work])
    destination = MetadataManager(tmp_path / "restored")
    imported = await destination.import_metadata(transfer)
    path = imported[0].metadata.file_path
    assert path.resolve().is_relative_to(destination.data_dir.resolve())
    assert path.read_text() == work.text_content
    assert not (tmp_path / "escape.txt").exists()


@pytest.mark.asyncio
async def test_import_reuses_exact_text_and_refuses_conflicting_or_linked_file(
    tmp_path,
):
    manager, work = manager_work(tmp_path)
    transfer = tmp_path / "transfer.json"
    await manager.export_metadata(transfer, [work])
    destination = MetadataManager(tmp_path / "restored")
    imported = await destination.import_metadata(transfer)
    path = imported[0].metadata.file_path
    before = path.stat()
    await destination.import_metadata(transfer)
    assert path.stat().st_ino == before.st_ino
    assert path.stat().st_mtime_ns == before.st_mtime_ns
    path.write_text("retained damaged copy")
    with pytest.raises(MetadataError, match="content hash"):
        await destination.import_metadata(transfer)
    assert path.read_text() == "retained damaged copy"
    # A separate destination supplies a real symlink at the exact content path.
    linked = MetadataManager(tmp_path / "linked")
    directory = linked.data_dir / "texts"
    directory.mkdir()
    filename = (
        "imported-" + hashlib.sha256(work.text_content.encode()).hexdigest() + ".txt"
    )
    (directory / filename).symlink_to(path)
    with pytest.raises(MetadataError, match="symlink"):
        await linked.import_metadata(transfer)
    assert path.read_text() == "retained damaged copy"
