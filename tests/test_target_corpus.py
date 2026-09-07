"""Tests for blake.downloader.target_corpus (moved from scripts/download_complete_corpus.py)."""

import asyncio

import pytest

from blake.downloader.target_corpus import (
    download_blake_archive,
    download_gutenberg,
    extract_text_from_tei,
    GUTENBERG_WORKS,
)


class _FakeResponse:
    def __init__(self, text, status=200):
        self._text = text
        self.status = status

    async def text(self):
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False


class _FakeSession:
    """Minimal aiohttp.ClientSession stand-in serving one canned body."""

    def __init__(self, text):
        self._text = text

    def get(self, url, **kwargs):
        return _FakeResponse(self._text)


def test_extract_text_from_tei_emits_header_and_stripped_lines():
    xml = (
        '<?xml version="1.0"?><TEI xmlns="http://www.tei-c.org/ns/1.0">'
        "<text><body><head>The Argument</head>"
        "<l>How   do I know</l><l>but from the dawn</l></body></text></TEI>"
    )

    text = extract_text_from_tei(xml, "America a Prophecy", "1793")

    assert text.startswith("AMERICA A PROPHECY\n(1793)")
    assert "The Argument" in text
    assert "How do I know" in text
    assert "but from the dawn" in text


def test_extract_text_from_tei_invalid_xml_returns_empty():
    assert extract_text_from_tei("this is not xml", "Title", "1800") == ""


@pytest.mark.asyncio
async def test_download_gutenberg_writes_all_registered_works(tmp_path):
    results = await download_gutenberg(_FakeSession("body text"), tmp_path)

    assert len(results) == len(GUTENBERG_WORKS)
    for filename, info in results.items():
        assert info["status"] == "complete"
        assert info["chars"] == len("body text")
        assert (tmp_path / filename).read_text(encoding="utf-8") == "body text"


@pytest.mark.asyncio
async def test_download_blake_archive_without_tei_payload_is_partial(tmp_path, monkeypatch):
    async def _nosleep(_seconds):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)

    results = await download_blake_archive(_FakeSession("<html>no tei here</html>"), tmp_path)

    assert len(results) == 20
    assert all(info["status"] == "partial" for info in results.values())
    assert not list(tmp_path.glob("*.txt"))
