"""Provider adapter behavior against finite owned HTTP pages only."""

import asyncio
import socket
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from blake.downloader.sources import (
    BlakeArchiveSource,
    InternetArchiveSource,
    ProjectGutenbergSource,
)
from blake.exceptions import DownloadError
from tests import source_http_fixtures
from tests.source_http_fixtures import BODY

adapter_pages = source_http_fixtures.adapter_pages


def source_for(cls, tmp_path, pages, search):
    class LocalSource(cls):
        BASE_URL = pages.base
        SEARCH_URL = pages.base + search

    source = LocalSource(tmp_path)
    source.scraper.timeout = 1
    source.scraper.retry_attempts = 1
    return source


def assert_owned_network(pages):
    endpoint = urlsplit(pages.base)
    assert pages.denied == []
    assert pages.connects
    assert set(pages.connects) == {(endpoint.hostname, endpoint.port)}
    assert set(pages.hosts) == {endpoint.netloc}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cls,search,ids",
    [
        (BlakeArchiveSource, "/archive-search", {"archive", "object", "item"}),
        (ProjectGutenbergSource, "/pg-search", {"701"}),
        (InternetArchiveSource, "/ia-search", {"test"}),
    ],
)
async def test_work_lists_use_owned_endpoints_and_reject_irrelevant_links(
    tmp_path: Path, adapter_pages, cls, search: str, ids: set[str]
) -> None:
    source = source_for(cls, tmp_path, adapter_pages, search)
    works = await source.get_work_list()
    assert {work["id"] for work in works} == ids
    assert len(works) == len(ids)
    assert all(work["url"].startswith(adapter_pages.base + "/") for work in works)
    if cls is BlakeArchiveSource:
        assert adapter_pages.calls["/browse"] == 1
        assert adapter_pages.calls["/works/prophecies"] == 1
    assert_owned_network(adapter_pages)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cls", [BlakeArchiveSource, ProjectGutenbergSource, InternetArchiveSource]
)
async def test_unavailable_search_is_an_explicit_error(
    tmp_path: Path, adapter_pages, cls
) -> None:
    source = source_for(cls, tmp_path, adapter_pages, "/bad")
    with pytest.raises(DownloadError, match="Failed"):
        await source.get_work_list()
    assert_owned_network(adapter_pages)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cls,identifier,path,expected",
    [
        (BlakeArchiveSource, "archive", "/works/archive", "First Second"),
        (ProjectGutenbergSource, "701", "/ebooks/701", "Synthetic states and time."),
        (ProjectGutenbergSource, "702", "/ebooks/702", "HTML states."),
        (InternetArchiveSource, "test", "/details/test", "Synthetic IA text."),
    ],
)
async def test_source_download_retains_text_identity_and_images(
    tmp_path: Path, adapter_pages, cls, identifier: str, path: str, expected: str
) -> None:
    source = source_for(cls, tmp_path, adapter_pages, "/bad")
    info = {
        "id": identifier,
        "title": "Synthetic title",
        "url": adapter_pages.base + path,
    }
    before = info.copy()
    work = await source.download_work(info)
    assert work is not None and work.id == identifier
    assert work.text_content == expected
    assert work.metadata.source_url == info["url"]
    if cls is not ProjectGutenbergSource:
        assert len(work.images) == 1
        assert work.images[0].metadata_id == identifier
        assert work.primary_image == work.images[0]
    else:
        assert work.metadata.file_path.is_file()
    assert info == before
    assert_owned_network(adapter_pages)


@pytest.mark.asyncio
@pytest.mark.parametrize("identifier", ["704", "705"])
async def test_direct_plain_and_html_fallbacks_stay_owned(
    tmp_path: Path, adapter_pages, identifier: str
) -> None:
    source = source_for(ProjectGutenbergSource, tmp_path, adapter_pages, "/bad")
    work = await source.download_work(
        {
            "id": identifier,
            "title": "Synthetic",
            "url": adapter_pages.base + "/ebooks/" + identifier,
        }
    )
    assert work is not None
    assert work.text_content.count("Synthetic states.") == 80
    assert "Project Gutenberg" not in work.text_content
    assert work.metadata.file_path.is_file()
    assert_owned_network(adapter_pages)


@pytest.mark.asyncio
async def test_cache_prefix_collision_cannot_supply_another_work(
    tmp_path: Path, adapter_pages
) -> None:
    source = source_for(ProjectGutenbergSource, tmp_path, adapter_pages, "/bad")
    unrelated = source.scraper.texts_dir / "7030_other.txt"
    unrelated.write_text(BODY)
    work = await source.download_work(
        {"id": "703", "title": "Uncached", "url": adapter_pages.base + "/ebooks/703"}
    )
    assert work is None
    assert unrelated.read_text() == BODY
    assert adapter_pages.calls["/files/703/703-0.txt"] == 1
    assert_owned_network(adapter_pages)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cls", [BlakeArchiveSource, ProjectGutenbergSource, InternetArchiveSource]
)
async def test_unavailable_work_has_no_fabricated_content(
    tmp_path: Path, adapter_pages, cls
) -> None:
    source = source_for(cls, tmp_path, adapter_pages, "/bad")
    assert (
        await source.download_work(
            {"id": "missing", "title": "Missing", "url": adapter_pages.base + "/bad"}
        )
        is None
    )
    assert list(source.scraper.texts_dir.iterdir()) == []
    assert_owned_network(adapter_pages)


@pytest.mark.asyncio
async def test_network_control_rejects_an_unowned_loopback_port(adapter_pages) -> None:
    with pytest.raises(RuntimeError, match="Non-owned HTTP endpoint"):
        socket.create_connection(("127.0.0.1", 0), timeout=0.01)
    assert adapter_pages.denied == ["('127.0.0.1', 0)"]
    assert adapter_pages.connects == []


@pytest.mark.asyncio
async def test_wrapper_only_download_is_not_a_recovered_text(
    tmp_path: Path, adapter_pages
) -> None:
    source = source_for(ProjectGutenbergSource, tmp_path, adapter_pages, "/bad")
    work = await source.download_work(
        {"id": "706", "title": "Wrapper", "url": adapter_pages.base + "/ebooks/706"}
    )
    assert work is None
    assert_owned_network(adapter_pages)


@pytest.mark.asyncio
async def test_direct_fallback_timeout_uses_scraper_budget(
    tmp_path: Path, adapter_pages
) -> None:
    source = source_for(ProjectGutenbergSource, tmp_path, adapter_pages, "/bad")
    source.scraper.timeout = 0.01
    result = await asyncio.wait_for(source._try_direct_file_access("slow"), timeout=0.3)
    assert result is None
    assert sum(adapter_pages.calls.values()) == 5
    assert_owned_network(adapter_pages)
