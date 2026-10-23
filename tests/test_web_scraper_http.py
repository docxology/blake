"""HTTP transfer and log custody with real loopback requests."""

import hashlib
import json
from pathlib import Path

import pytest

from blake.downloader.scraper import WebScraper
from blake.exceptions import DownloadError
from tests import http_fixtures

local_responses = http_fixtures.local_responses


@pytest.mark.asyncio
async def test_download_bytes_cache_force_and_hash(
    tmp_path: Path, local_responses
) -> None:
    scraper = WebScraper(tmp_path, timeout=1, retry_attempts=1)
    target = tmp_path / "saved/file.bin"
    url = local_responses.base + "/binary"
    assert await scraper.download_file(url, target, headers={"X-Test": "transfer"})
    assert target.read_bytes() == b"complete payload"
    assert local_responses.headers[-1]["X-Test"] == "transfer"
    saved = json.loads(scraper.download_log.read_text())[url]
    assert saved["success"] is True and saved["size"] == 16
    assert (
        scraper.generate_file_hash(target)
        == hashlib.sha256(b"complete payload").hexdigest()
    )
    reloaded = WebScraper(tmp_path, timeout=1, retry_attempts=1)
    assert await reloaded.download_file(url, target)
    assert local_responses.calls["/binary"] == 1
    assert await reloaded.download_file(url, target, force=True)
    assert local_responses.calls["/binary"] == 2
    target.write_bytes(b"damaged")
    assert await reloaded.download_file(url, target)
    assert target.read_bytes() == b"complete payload"
    assert local_responses.calls["/binary"] == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ["/bad", "/empty", "/truncated", "/slow"])
async def test_failed_transfer_preserves_prior_bytes(
    tmp_path: Path, local_responses, endpoint: str
) -> None:
    scraper = WebScraper(tmp_path, timeout=0.03, retry_attempts=1)
    target = tmp_path / "saved.bin"
    target.write_bytes(b"valuable prior bytes")
    url = local_responses.base + endpoint
    assert not await scraper.download_file(url, target, force=True)
    assert target.read_bytes() == b"valuable prior bytes"
    assert scraper.downloaded_files[url]["success"] is False
    assert not scraper._is_file_downloaded(url, target)
    assert not list(tmp_path.glob("*.part"))


@pytest.mark.asyncio
async def test_real_retry_then_success_retains_only_complete_bytes(
    tmp_path: Path, local_responses
) -> None:
    scraper = WebScraper(tmp_path, timeout=1, retry_attempts=2)
    target = tmp_path / "retry.bin"
    assert await scraper.download_file(local_responses.base + "/flaky", target)
    assert target.read_bytes() == b"complete payload"
    assert local_responses.calls["/flaky"] == 2


@pytest.mark.asyncio
async def test_scrape_headers_status_and_timeout(
    tmp_path: Path, local_responses
) -> None:
    scraper = WebScraper(tmp_path, timeout=0.03, retry_attempts=1)
    page = await scraper.scrape_page(
        local_responses.base + "/html", {"X-Test": "scrape"}
    )
    assert page.select_one("main").get_text(" ", strip=True) == "A & B Second."
    assert local_responses.headers[-1]["X-Test"] == "scrape"
    with pytest.raises(DownloadError, match="Failed to scrape"):
        await scraper.scrape_page(local_responses.base + "/bad")
    with pytest.raises(DownloadError, match="Failed to scrape"):
        await scraper.scrape_page(local_responses.base + "/slow")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "html,selectors,expected",
    [
        ("<main><p>First</p><p>Second</p></main>", ["missing", "p"], "First\n\nSecond"),
        ("<body>Body</body>", ["missing"], "Body"),
        ("Standalone", ["missing"], "Standalone"),
    ],
)
async def test_html_extraction_uses_first_available_selector(
    tmp_path: Path, html: str, selectors: list[str], expected: str
) -> None:
    assert (
        await WebScraper(tmp_path).extract_text_from_html(html, selectors) == expected
    )


def test_broken_log_warns_and_preserves_original_file(tmp_path: Path, caplog) -> None:
    log = tmp_path / "download_log.json"
    log.write_text("{broken")
    scraper = WebScraper(tmp_path)
    assert scraper.downloaded_files == {}
    assert log.read_text() == "{broken"
    assert "Error loading download log" in caplog.text
