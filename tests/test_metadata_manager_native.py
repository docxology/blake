"""Metadata coordination through real SQLite and file-backed text."""

from datetime import datetime
import hashlib

import pytest

from blake.exceptions import MetadataError
from blake.metadata.manager import MetadataManager
from tests.export_fixtures import export_work


def manager_work(tmp_path):
    manager = MetadataManager(tmp_path / "data")
    work = export_work(tmp_path / "input")
    text = tmp_path / "data/texts/original.txt"
    text.parent.mkdir()
    text.write_text(work.text_content)
    work.metadata.file_path = text
    return manager, work


@pytest.mark.asyncio
async def test_manager_save_search_statistics_and_delete(tmp_path):
    manager, work = manager_work(tmp_path)
    await manager.save_work(work)
    assert (
        await manager.load_work(work.id)
    ).metadata.source_url == work.metadata.source_url
    assert await manager.load_work("absent") is None
    assert [item.id for item in await manager.load_all_works()] == [work.id]
    assert [item.id for item in await manager.search_works("states")] == [work.id]
    assert await manager.search_works("unfindable-token") == []
    assert (await manager.get_work_statistics())["total_works"] == 1
    assert await manager.get_search_suggestions("sta")
    assert (await manager.get_facet_counts())["work_types"] == {"poem": 1}
    assert await manager.get_related_works(work.id) == []
    assert await manager.get_related_works("absent") == []
    image_path = work.images[0].file_path
    image_before = image_path.read_bytes()
    assert await manager.delete_work(work.id) is True
    assert await manager.delete_work(work.id) is False
    assert await manager.load_all_works() == []
    assert image_path.read_bytes() == image_before
    assert work.metadata.file_path.read_text() == work.text_content


@pytest.mark.asyncio
async def test_manager_updates_and_tags_are_persisted_once(tmp_path):
    manager, work = manager_work(tmp_path)
    await manager.save_work(work)
    before = datetime.now()
    updated = await manager.update_work_metadata(
        work.id, {"description": "Revised", "unknown": 1}
    )
    assert updated.metadata.description == "Revised"
    assert updated.metadata.updated_at >= before
    assert not hasattr(updated.metadata, "unknown")
    assert (await manager.load_work(work.id)).metadata.description == "Revised"
    assert await manager.add_work_tag(work.id, "recovered")
    assert await manager.add_work_tag(work.id, "recovered")
    assert (await manager.load_work(work.id)).metadata.tags.count("recovered") == 1
    assert await manager.remove_work_tag(work.id, "recovered")
    assert await manager.remove_work_tag(work.id, "recovered")
    assert "recovered" not in (await manager.load_work(work.id)).metadata.tags
    assert await manager.update_work_metadata("absent", {}) is None
    assert not await manager.add_work_tag("absent", "x")
    assert not await manager.remove_work_tag("absent", "x")


@pytest.mark.asyncio
async def test_manager_process_and_analysis_history(tmp_path):
    manager, work = manager_work(tmp_path)
    work.images = []
    work.text_content = "Imagination   and nature with angels"
    work.metadata.file_path.write_text(work.text_content)
    before = work.metadata.file_path.read_bytes()
    processed = await manager.process_work(work)
    assert processed.metadata.processed
    assert processed.text_content == "Imagination and nature with angels"
    assert (
        "imagination" in processed.metadata.themes
        and "angels" in processed.metadata.subjects
    )
    assert processed.metadata.checksum == hashlib.sha256(before).hexdigest()
    assert work.metadata.file_path.read_bytes() == before
    await manager.save_analysis_result(
        work.id, "text", {"revision": 1}, 0.75, {"source": "fixture"}
    )
    await manager.save_analysis_result(work.id, "text", {"revision": 2})
    assert (await manager.load_work(work.id)).text_analysis == {"revision": 2}
    records = await manager.load_analysis_results(work.id, "text")
    assert len(records) == 2 and records[-1]["confidence"] == 0.75
    assert records[-1]["metadata"] == {"source": "fixture"}
    assert await manager.load_analysis_results(work.id, "visual") == []


@pytest.mark.parametrize(
    "operation",
    [
        "save_work",
        "delete_work",
        "load_all_works",
        "search_works",
        "get_work_statistics",
        "save_analysis_result",
        "process_work",
    ],
)
@pytest.mark.asyncio
async def test_manager_real_database_failures_raise(tmp_path, operation):
    manager, work = manager_work(tmp_path)
    manager.database.db_path = tmp_path / "absent/metadata.db"
    arguments = {
        "save_work": (work,),
        "delete_work": (work.id,),
        "load_all_works": (),
        "search_works": ("state",),
        "get_work_statistics": (),
        "save_analysis_result": (work.id, "text", {"retained": True}),
        "process_work": (work,),
    }
    work.images = []
    with pytest.raises(MetadataError):
        await getattr(manager, operation)(*arguments[operation])
    assert not manager.database.db_path.exists()


@pytest.mark.asyncio
async def test_existing_optional_read_failures_have_explicit_empty_results(tmp_path):
    manager, work = manager_work(tmp_path)
    await manager.save_work(work)
    # This is an actual inaccessible SQLite path, not a replacement database API.
    manager.database.db_path = tmp_path / "absent/metadata.db"
    assert await manager.load_work(work.id) is None
    assert await manager.get_search_suggestions("state") == []
    assert await manager.get_facet_counts() == {}
    assert await manager.get_related_works(work.id) == []
    assert await manager.load_analysis_results(work.id) == []
