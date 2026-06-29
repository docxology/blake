"""
Tests for Blake Archive Scraper Module.
"""

import asyncio
import time

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from blake.downloader.blake_archive_scraper import (
    BlakeArchiveScraper,
    BlakeArchiveWork,
    BlakeArchiveCopy,
    BlakeArchiveObject,
    scrape_blake_archive,
)
from blake.metadata.database import MetadataDatabase
from blake.models import BlakeMetadata, BlakeWork, LicenseType, WorkType, SourceType


class FakeResponse:
    def __init__(self, status=200, text="", json_payload=None, headers=None, body=b""):
        self.status = status
        self._text = text
        self._json_payload = json_payload
        self.headers = headers or {}
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def text(self, *args, **kwargs):
        return self._text

    async def json(self):
        return self._json_payload

    async def read(self):
        return self._body


class FakeBlakeArchiveSession:
    def __init__(self):
        self.urls = []
        self.inventory = """<collection>
            <resource filename="b-los.a.xml" />
            <resource filename="b-los.b.xml" />
            <resource filename="BB206.1.xml" />
            <resource filename="homer.b.xml" />
            <resource filename="songsie.a.xml" />
        </collection>"""

    def get(self, url):
        self.urls.append(url)
        if url.endswith("/works/__contents__.xml"):
            return FakeResponse(status=200, text=self.inventory)
        if "/api/work/" in url:
            work_id = url.rsplit("/", 1)[-1]
            related = []
            if work_id == "b-los":
                related = [
                    {"title": {"link": "b-los.c", "type": "copy", "text": "Copy C"}}
                ]
            return FakeResponse(
                status=200,
                json_payload={
                    "bad_id": work_id,
                    "title": f"Archive title {work_id}",
                    "medium": "illbk" if work_id not in {"bb206"} else "spb",
                    "composition_date_string": "1795",
                    "image": f"{work_id}.a.p1.100.jpg",
                    "related_works": related,
                    "info": f"<p>{work_id}</p>",
                },
            )
        if "/api/copy/" in url:
            copy_id = url.rsplit("/", 1)[-1]
            return FakeResponse(
                status=200,
                json_payload={
                    "copy_id": copy_id,
                    "image": f"{copy_id}.p1.100.jpg",
                    "number_of_objects": 3,
                },
            )
        return FakeResponse(status=404, text="")


class TestBlakeArchiveScraper:
    """Tests for BlakeArchiveScraper class."""

    @pytest.fixture
    def scraper(self, tmp_path):
        """Create scraper instance."""
        return BlakeArchiveScraper(tmp_path)

    @pytest.fixture
    def mock_session(self):
        """Create mock aiohttp session."""
        session = MagicMock()
        session.get = MagicMock()
        return session

    def test_scraper_initialization(self, scraper, tmp_path):
        """Scraper initializes with correct directories."""
        assert scraper.data_dir == tmp_path
        assert scraper.texts_dir.exists()
        assert scraper.images_dir.exists()
        assert scraper.metadata_dir.exists()
        assert scraper.xml_dir.exists()

    def test_scraper_statistics_initial(self, scraper):
        """Initial statistics are zero."""
        stats = scraper.get_statistics()
        assert stats["works_found"] == 0
        assert stats["works_downloaded"] == 0
        assert stats["images_downloaded"] == 0
        assert stats["texts_extracted"] == 0
        assert stats["errors"] == 0

    def test_determine_work_type_illuminated_book(self, scraper):
        """Correctly identifies illuminated books."""
        work = BlakeArchiveWork(
            work_id="songsie",
            title="Songs of Innocence and of Experience",
            category="illbk",
        )
        assert scraper._determine_work_type(work) == WorkType.POEM

    def test_determine_work_type_prophecy(self, scraper):
        """Correctly identifies prophetic works."""
        work = BlakeArchiveWork(
            work_id="america", title="America a Prophecy", category="illbk"
        )
        assert scraper._determine_work_type(work) == WorkType.PROPHECY

    def test_determine_work_type_letter(self, scraper):
        """Correctly identifies letters."""
        work = BlakeArchiveWork(work_id="lt", title="Letters", category="lt")
        assert scraper._determine_work_type(work) == WorkType.LETTER

    def test_determine_work_type_manuscript(self, scraper):
        """Correctly identifies manuscripts."""
        work = BlakeArchiveWork(
            work_id="fz", title="The Four Zoas (Vala)", category="ms"
        )
        assert scraper._determine_work_type(work) == WorkType.MANUSCRIPT

    def test_parse_date_single_year(self, scraper):
        """Parses single year correctly."""
        date = scraper._parse_date("1789")
        assert date is not None
        assert date.year == 1789

    def test_parse_date_range(self, scraper):
        """Parses date range, using first year."""
        date = scraper._parse_date("1789-1794")
        assert date is not None
        assert date.year == 1789

    def test_parse_date_invalid(self, scraper):
        """Returns None for invalid date."""
        date = scraper._parse_date("unknown")
        assert date is None

    def test_parse_date_none(self, scraper):
        """Returns None for None input."""
        date = scraper._parse_date(None)
        assert date is None

    @pytest.mark.asyncio
    async def test_fetch_works_catalog_uses_inventory_and_api_not_dead_csv(
        self, scraper
    ):
        scraper.session = FakeBlakeArchiveSession()

        works = await scraper.fetch_works_catalog()
        by_id = {work.work_id: work for work in works}

        assert len(works) > 38
        assert {"homer", "bb206", "abel", "b-los"}.issubset(by_id)
        assert by_id["b-los"].archive_id == "b-los"
        assert by_id["b-los"].copies == ["b-los.a", "b-los.b", "b-los.c"]
        assert by_id["songs-experience"].archive_id == "songsie"
        assert not any("csv/works.csv" in url for url in scraper.session.urls)

    @pytest.mark.asyncio
    async def test_archive_inventory_scope_discovers_inventory_prefixes(self, scraper):
        scraper.session = FakeBlakeArchiveSession()

        works = await scraper.fetch_works_catalog(scope="archive-inventory")
        by_id = {work.work_id: work for work in works}

        assert {"b-los", "bb206", "homer", "songsie"}.issubset(by_id)
        assert "songs-experience" not in by_id
        assert by_id["b-los"].copies == ["b-los.a", "b-los.b", "b-los.c"]
        assert len(works) > 100

    @pytest.mark.asyncio
    async def test_archive_inventory_scope_does_not_stall_on_slow_metadata(
        self, scraper, monkeypatch
    ):
        async def file_names():
            return ["b-los.a.xml", "bb206.1.xml", "songsie.a.xml"]

        calls = 0

        async def slow_metadata(work_id):
            nonlocal calls
            calls += 1
            await asyncio.sleep(1)
            return {"title": f"late {work_id}"}

        monkeypatch.setattr(scraper, "_fetch_work_file_names", file_names)
        monkeypatch.setattr(scraper, "_fetch_work_api_metadata", slow_metadata)
        scraper.ARCHIVE_METADATA_TIMEOUT_SECONDS = 0.01
        scraper.ARCHIVE_METADATA_TOTAL_BUDGET_SECONDS = 0.1
        scraper.ARCHIVE_METADATA_TIMEOUT_LIMIT = 1

        started = time.monotonic()
        works = await scraper.fetch_works_catalog(scope="archive-inventory")
        elapsed = time.monotonic() - started
        by_id = {work.work_id: work for work in works}

        assert elapsed < 0.5
        assert calls == 1
        assert {"b-los", "bb206", "songsie"}.issubset(by_id)
        assert by_id["b-los"].copies == ["b-los.a"]
        assert scraper.archive_metadata_enrichment["status"] == "degraded"
        assert scraper.archive_metadata_enrichment["timeout_count"] == 1
        assert scraper.archive_metadata_enrichment["skipped_after_budget"] >= 1

    @pytest.mark.asyncio
    async def test_archive_metadata_fast_failures_stop_after_degradation_limit(
        self, scraper, monkeypatch
    ):
        async def file_names():
            return [
                "b-los.a.xml",
                "bb206.1.xml",
                "songsie.a.xml",
                "milton.a.xml",
                "urizen.a.xml",
            ]

        calls = 0

        async def failed_metadata(work_id):
            nonlocal calls
            calls += 1
            return None

        monkeypatch.setattr(scraper, "_fetch_work_file_names", file_names)
        monkeypatch.setattr(scraper, "_fetch_work_api_metadata", failed_metadata)
        scraper.ARCHIVE_METADATA_FAILURE_LIMIT = 2

        works = await scraper.fetch_works_catalog(scope="archive-inventory")

        assert len(works) >= 5
        assert calls == 2
        report = scraper.archive_metadata_enrichment
        assert report["status"] == "degraded"
        assert report["attempted"] == 2
        assert report["failed"] == 2
        assert report["skipped_after_budget"] >= 1
        assert report["disabled"] is True

    @pytest.mark.asyncio
    async def test_fetch_work_file_names_falls_back_to_github_api(self, scraper):
        class ApiFallbackSession:
            def __init__(self):
                self.urls = []

            def get(self, url):
                self.urls.append(url)
                if url.endswith("/works/__contents__.xml"):
                    return FakeResponse(status=404, text="")
                if "api.github.com/repos/blakearchive/data/contents/works" in url:
                    return FakeResponse(
                        status=200,
                        json_payload=[
                            {"type": "file", "name": "america.a.xml"},
                            {"type": "file", "name": "__contents__.xml"},
                            {"type": "dir", "name": "not-a-file.xml"},
                        ],
                    )
                return FakeResponse(status=404, text="")

        scraper.session = ApiFallbackSession()

        assert await scraper._fetch_work_file_names() == ["america.a.xml"]

    @pytest.mark.asyncio
    async def test_tei_candidates_start_with_inventory_matches(self, scraper):
        scraper.session = FakeBlakeArchiveSession()

        urls = await scraper._tei_candidate_urls("bb206")

        assert urls[0].endswith("/works/BB206.1.xml")
        assert any(url.endswith("/works/bb206.a.xml") for url in urls)
        assert not any(url.endswith(".xml.xml") for url in urls)

    def test_object_ids_from_payload_extracts_image_and_object_lists(self, scraper):
        payload = {
            "image": "songsie.a.p1.100.jpg",
            "objects": [
                {"image_url": "https://blakearchive.org/images/songsie.a.p2.300.jpg"},
                {"object_id": "songsie.a.p3"},
            ],
        }

        assert scraper._object_ids_from_payload(payload) == [
            "songsie.a.p1",
            "songsie.a.p2",
            "songsie.a.p3",
        ]

    def test_work_payload_scoping_filters_related_object_links(self, scraper):
        payload = {
            "related_works": [
                {"title": {"link": "songsie.a", "type": "copy", "text": "Copy A"}},
                {
                    "title": {
                        "link": "/object?descId=songsie.a.p2",
                        "type": "object",
                        "text": "Songs plate",
                    }
                },
                {
                    "title": {
                        "link": "/object?descId=bb122.1.ms.103",
                        "type": "object",
                        "text": "Related manuscript object",
                    }
                },
            ]
        }

        copy_ids, object_ids = scraper._copy_and_object_ids_from_work_payload(
            payload, work_id="songsie"
        )

        assert copy_ids == ["songsie.a"]
        assert object_ids == ["songsie.a.p2"]

    def test_work_scoping_allows_compact_letter_copy_ids(self, scraper):
        assert scraper._work_scoped_copy_ids("lt", ["lt1", "lt2", "bb122"]) == [
            "lt1",
            "lt2",
        ]
        assert scraper._work_scoped_object_ids("lt", ["lt1", "lt2.p1", "bb122"]) == [
            "lt1",
            "lt2.p1",
        ]

    def test_image_candidate_urls_include_dpi_and_wayback_variants(self, scraper):
        urls = scraper._image_candidate_urls("songsie.a.p1", 100)

        assert "https://blakearchive.org/images/songsie.a.p1.100.jpg" in urls
        assert "https://blakearchive.org/images/songsie.a.p1.300.jpg" in urls
        assert any(url.startswith(scraper.WAYBACK_PREFIX) for url in urls)

    def test_image_candidate_urls_prefer_300dpi_then_requested_then_100dpi(
        self, scraper
    ):
        urls = scraper._image_candidate_urls("songsie.a.p1", 150)

        assert urls[:3] == [
            "https://blakearchive.org/images/songsie.a.p1.300.jpg",
            "https://blakearchive.org/images/songsie.a.p1.150.jpg",
            "https://blakearchive.org/images/songsie.a.p1.100.jpg",
        ]

    @pytest.mark.asyncio
    async def test_copy_number_of_objects_expands_to_object_ids(self, scraper):
        scraper.session = FakeBlakeArchiveSession()

        objects, expected = await scraper._objects_for_copy("songsie.b")

        assert expected == 3
        assert objects == ["songsie.b.p1", "songsie.b.p2", "songsie.b.p3"]

    @pytest.mark.asyncio
    async def test_archive_all_mode_resolves_related_copy_objects(self, scraper):
        scraper.session = FakeBlakeArchiveSession()

        objects, expected = await scraper._get_work_objects(
            "b-los", image_mode="archive-all"
        )

        assert expected >= 3
        assert {"b-los.c.p1", "b-los.c.p2", "b-los.c.p3"}.issubset(objects)

    @pytest.mark.asyncio
    async def test_archive_all_mode_expands_explicit_copy_ids(self, scraper):
        scraper.session = FakeBlakeArchiveSession()

        objects, expected = await scraper._get_work_objects(
            "orphan", image_mode="archive-all", copy_ids=["orphan.a"]
        )

        assert expected == 3
        assert objects == ["orphan.a.p1", "orphan.a.p2", "orphan.a.p3"]

    @pytest.mark.asyncio
    async def test_download_preserves_validated_fallback_text_tier(self, scraper):
        text_path = scraper.texts_dir / "bb203.txt"
        fallback_text = "Tiriel " + "validated fallback words " * 120
        text_path.write_text(fallback_text, encoding="utf-8")
        metadata = BlakeMetadata(
            id="bb203",
            title="Tiriel",
            work_type=WorkType.POEM,
            source=SourceType.WIKIMEDIA,
            source_url="https://en.wikisource.org/wiki/Tiriel",
            source_id="Tiriel",
            license_type=LicenseType.PUBLIC_DOMAIN,
            file_path=text_path,
            file_size=text_path.stat().st_size,
            mime_type="text/plain",
            checksum="sha256:test",
        )
        metadata.analysis_results = {
            "source_authority_tier": "fallback_text_validated",
            "validated_fallback_text": {
                "source": "Wikisource author page",
                "source_url": "https://en.wikisource.org/wiki/Tiriel",
                "words": 361,
                "checksum": "sha256:test",
            },
        }
        MetadataDatabase(scraper.metadata_dir / "metadata.db").save_work(
            BlakeWork(id="bb203", metadata=metadata, text_content=fallback_text)
        )

        work = await scraper._download_single_work(
            BlakeArchiveWork(work_id="bb203", title="Tiriel"),
            include_images=False,
        )

        assert work is not None
        assert work.text_content == fallback_text
        assert (
            work.metadata.analysis_results["source_authority_tier"]
            == "fallback_text_validated"
        )
        assert "validated_fallback_text" in work.metadata.analysis_results
        assert work.metadata.checksum == "sha256:test"


class TestBlakeArchiveWorkDataClass:
    """Tests for BlakeArchiveWork dataclass."""

    def test_work_creation(self):
        """Work dataclass creates correctly."""
        work = BlakeArchiveWork(
            work_id="mhh",
            title="The Marriage of Heaven and Hell",
            composition_date="1790",
            medium="illbk",
            category="Illuminated Books",
        )
        assert work.work_id == "mhh"
        assert work.title == "The Marriage of Heaven and Hell"
        assert work.composition_date == "1790"
        assert work.copies == []

    def test_work_with_copies(self):
        """Work can have copies."""
        work = BlakeArchiveWork(
            work_id="mhh",
            title="The Marriage of Heaven and Hell",
            copies=["mhh.a", "mhh.b", "mhh.c"],
        )
        assert len(work.copies) == 3


class TestBlakeArchiveCopyDataClass:
    """Tests for BlakeArchiveCopy dataclass."""

    def test_copy_creation(self):
        """Copy dataclass creates correctly."""
        copy = BlakeArchiveCopy(
            copy_id="mhh.a",
            work_id="mhh",
            title="The Marriage of Heaven and Hell, Copy A",
            institution="British Museum",
        )
        assert copy.copy_id == "mhh.a"
        assert copy.work_id == "mhh"
        assert copy.objects == []


class TestBlakeArchiveObjectDataClass:
    """Tests for BlakeArchiveObject dataclass."""

    def test_object_creation(self):
        """Object dataclass creates correctly."""
        obj = BlakeArchiveObject(
            object_id="mhh.a.illbk.01",
            copy_id="mhh.a",
            work_id="mhh",
            title="Plate 1",
            dpi=100,
        )
        assert obj.object_id == "mhh.a.illbk.01"
        assert obj.dpi == 100


class TestFallbackCatalog:
    """Tests for fallback canonical works catalog."""

    @pytest.fixture
    def scraper(self, tmp_path):
        """Create scraper instance."""
        return BlakeArchiveScraper(tmp_path)

    @pytest.mark.asyncio
    async def test_fallback_catalog_returns_works(self, scraper):
        """Fallback catalog returns canonical works."""
        works = await scraper._fetch_works_fallback()

        assert len(works) > 0
        assert any(w.work_id == "songsie" for w in works)
        assert any(w.work_id == "mhh" for w in works)
        assert any(w.work_id == "jerusalem" for w in works)

    @pytest.mark.asyncio
    async def test_fallback_catalog_populates_cache(self, scraper):
        """Fallback catalog populates work cache."""
        await scraper._fetch_works_fallback()

        assert "songsie" in scraper._works_cache
        assert "mhh" in scraper._works_cache


class TestTEIExtraction:
    """Tests for TEI XML text extraction."""

    @pytest.fixture
    def scraper(self, tmp_path):
        """Create scraper instance."""
        return BlakeArchiveScraper(tmp_path)

    def test_extract_text_from_tei_simple(self, scraper):
        """Extracts text from simple TEI structure."""
        xml = """<?xml version="1.0"?>
        <TEI>
            <text>
                <body>
                    <div>
                        <p>This is a test paragraph.</p>
                        <l>This is a line of poetry.</l>
                    </div>
                </body>
            </text>
        </TEI>
        """
        text = scraper._extract_text_from_tei(xml)

        assert text is not None
        assert "test paragraph" in text
        assert "line of poetry" in text

    def test_extract_text_from_tei_invalid(self, scraper):
        """Returns None for invalid XML."""
        text = scraper._extract_text_from_tei("not valid xml <<<<")
        assert text is None


class TestVerification:
    """Tests for download verification."""

    @pytest.fixture
    def scraper(self, tmp_path):
        """Create scraper with sample data."""
        scraper = BlakeArchiveScraper(tmp_path)

        # Create sample text file
        text_path = scraper.texts_dir / "test_work.txt"
        text_path.write_text(
            "This is a test work with sufficient content for verification." * 5
        )

        # Create sample metadata file
        meta_path = scraper.metadata_dir / "test_work.json"
        meta_path.write_text('{"id": "test_work", "title": "Test Work"}')

        return scraper

    @pytest.mark.asyncio
    async def test_verify_downloads(self, scraper):
        """Verification detects valid files."""
        verification = await scraper.verify_downloads()

        assert verification["texts"]["count"] == 1
        assert verification["texts"]["valid"] == 1
        assert verification["metadata"]["count"] == 1
        assert verification["metadata"]["valid"] == 1


class TestWorkInfo:
    """Tests for work info retrieval."""

    @pytest.fixture
    def scraper(self, tmp_path):
        """Create scraper with cached work."""
        scraper = BlakeArchiveScraper(tmp_path)
        scraper._works_cache["mhh"] = BlakeArchiveWork(
            work_id="mhh",
            title="The Marriage of Heaven and Hell",
            composition_date="1790",
            category="illbk",
        )
        return scraper

    @pytest.mark.asyncio
    async def test_get_work_info_exists(self, scraper):
        """Returns info for cached work."""
        info = await scraper.get_work_info("mhh")

        assert info is not None
        assert info["id"] == "mhh"
        assert info["title"] == "The Marriage of Heaven and Hell"

    @pytest.mark.asyncio
    async def test_get_work_info_not_found(self, scraper):
        """Returns None for unknown work."""
        info = await scraper.get_work_info("unknown")
        assert info is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
