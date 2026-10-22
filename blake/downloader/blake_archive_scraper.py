"""
Blake Archive Comprehensive Scraper Module.

This module provides comprehensive scraping capabilities for the William Blake Archive
(blakearchive.org), including:
- Work catalog from GitHub data repository
- Text transcriptions (TEI XML)
- High-resolution images
- Metadata for all illuminated books, drawings, and manuscripts

The module follows the archive's structure:
- Works -> Copies -> Objects/Plates

Primary data sources:
- GitHub: https://github.com/blakearchive/data (work XML inventory and BAD/TEI XML)
- Archive: https://blakearchive.org (per-work API metadata, images, interactive content)
"""

import asyncio
import aiohttp
import aiofiles
import logging
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
from time import monotonic
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field

from ..models import (
    BlakeWork,
    BlakeMetadata,
    BlakeImage,
    WorkType,
    SourceType,
    LicenseType,
)
from ..exceptions import DownloadError
from ..corpus.targets import load_corpus_target
from ..metadata.database import MetadataDatabase

logger = logging.getLogger(__name__)


def _object_sort_key(object_id: str) -> Tuple[str, int, str]:
    match = re.match(r"^(?P<prefix>.*?\.p)(?P<number>\d+)(?P<suffix>.*)$", object_id)
    if not match:
        return (object_id.lower(), 0, "")
    return (
        match.group("prefix").lower(),
        int(match.group("number")),
        match.group("suffix").lower(),
    )


@dataclass
class BlakeArchiveWork:
    """Represents a work from the Blake Archive."""

    work_id: str
    title: str
    composition_date: Optional[str] = None
    medium: Optional[str] = None
    category: Optional[str] = None
    copies: List[str] = field(default_factory=list)
    description: Optional[str] = None
    archive_id: Optional[str] = None


@dataclass
class BlakeArchiveCopy:
    """Represents a specific copy of a work."""

    copy_id: str
    work_id: str
    title: str
    institution: Optional[str] = None
    print_date: Optional[str] = None
    objects: List[str] = field(default_factory=list)


@dataclass
class BlakeArchiveObject:
    """Represents an individual object/plate."""

    object_id: str
    copy_id: str
    work_id: str
    title: Optional[str] = None
    image_url: Optional[str] = None
    transcription: Optional[str] = None
    dpi: int = 100


@dataclass
class _ArchiveMetadataBudget:
    timeout_seconds: float
    total_budget_seconds: float
    timeout_limit: int
    failure_limit: int
    started_at: float = field(default_factory=monotonic)
    attempted: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped_after_budget: int = 0
    timeout_count: int = 0
    consecutive_failure_count: int = 0
    disabled: bool = False
    disabled_reason: Optional[str] = None
    fallback_source_used: str = "target ledger + GitHub XML inventory"

    @property
    def can_attempt(self) -> bool:
        if self.disabled:
            return False
        if monotonic() - self.started_at >= self.total_budget_seconds:
            self.disabled = True
            self.disabled_reason = "metadata time budget exhausted"
        return not self.disabled

    def begin_attempt(self) -> None:
        self.attempted += 1

    def record_success(self) -> None:
        self.succeeded += 1
        self.timeout_count = 0
        self.consecutive_failure_count = 0

    def record_failure(self, reason: str = "metadata request returned no payload") -> None:
        self.failed += 1
        self.consecutive_failure_count += 1
        if self.consecutive_failure_count >= self.failure_limit:
            self.disabled = True
            self.disabled_reason = f"metadata failure limit reached: {reason}"

    def record_timeout(self) -> None:
        self.failed += 1
        self.timeout_count += 1
        self.consecutive_failure_count += 1
        if self.timeout_count >= self.timeout_limit:
            self.disabled = True
            self.disabled_reason = "metadata timeout limit reached"
        elif self.consecutive_failure_count >= self.failure_limit:
            self.disabled = True
            self.disabled_reason = "metadata failure limit reached"

    def record_skip(self) -> None:
        self.skipped_after_budget += 1

    def to_report(self, *, total_candidates: int, scope: str) -> Dict[str, Any]:
        elapsed = round(monotonic() - self.started_at, 3)
        if self.disabled and not self.disabled_reason:
            self.disabled_reason = "metadata enrichment disabled"
        status = (
            "degraded"
            if self.disabled or self.failed or self.skipped_after_budget
            else "complete"
        )
        if self.attempted == 0 and total_candidates:
            status = "skipped"
        return {
            "scope": scope,
            "status": status,
            "total_candidates": int(total_candidates),
            "attempted": int(self.attempted),
            "succeeded": int(self.succeeded),
            "failed": int(self.failed),
            "skipped_after_budget": int(self.skipped_after_budget),
            "timeout_count": int(self.timeout_count),
            "failure_count": int(self.failed),
            "disabled": bool(self.disabled),
            "disabled_reason": self.disabled_reason,
            "duration_seconds": elapsed,
            "timeout_seconds": self.timeout_seconds,
            "total_budget_seconds": self.total_budget_seconds,
            "timeout_limit": self.timeout_limit,
            "failure_limit": self.failure_limit,
            "fallback_source_used": self.fallback_source_used,
        }


class BlakeArchiveScraper:
    """
    Comprehensive scraper for the William Blake Archive.

    This scraper uses multiple data sources:
    1. GitHub repository for structured data (works.csv, TEI XML)
    2. Direct archive access for images and interactive content
    3. Wayback Machine as fallback when archive is unavailable
    """

    # Primary URLs
    ARCHIVE_BASE_URL = "https://blakearchive.org"
    GITHUB_BASE_URL = "https://raw.githubusercontent.com/blakearchive/data/master"
    GITHUB_REPO_URL = "https://api.github.com/repos/blakearchive/data"
    ERDMAN_URL = "https://erdman.blakearchive.org"
    WAYBACK_PREFIX = "https://web.archive.org/web/20240101000000"

    # Data URLs
    WORKS_CONTENTS_URL = f"{GITHUB_BASE_URL}/works/__contents__.xml"
    WORKS_API_CONTENTS_URL = f"{GITHUB_REPO_URL}/contents/works?ref=master"
    WORK_API_URL = f"{ARCHIVE_BASE_URL}/api/work"

    WORKS_CSV_URL = f"{GITHUB_BASE_URL}/csv/works.csv"
    COPIES_CSV_URL = f"{GITHUB_BASE_URL}/csv/copies.csv"
    OBJECTS_CSV_URL = f"{GITHUB_BASE_URL}/csv/objects.csv"
    ARCHIVE_METADATA_TIMEOUT_SECONDS = 3.0
    ARCHIVE_METADATA_TOTAL_BUDGET_SECONDS = 15.0
    ARCHIVE_METADATA_TIMEOUT_LIMIT = 3
    ARCHIVE_METADATA_FAILURE_LIMIT = 8

    # Work categories
    CATEGORIES = {
        "illbk": "Illuminated Books",
        "comb": "Commercial Book Illustrations",
        "spb": "Separate Prints and Prints in Series",
        "pdes": "Pencil Drawings",
        "wc": "Watercolor Drawings",
        "pt": "Paintings",
        "pen": "Pen and Ink Drawings",
        "ms": "Manuscripts and Typographic Works",
        "lt": "Letters",
        "te": "Engraved Technical Works",
    }

    def __init__(self, data_dir: Path, rate_limit: float = 0.5):
        """
        Initialize Blake Archive scraper.

        Args:
            data_dir: Directory to store downloaded data
            rate_limit: Seconds between requests to avoid rate limiting
        """
        self.data_dir = Path(data_dir)
        self.rate_limit = rate_limit
        self.session: Optional[aiohttp.ClientSession] = None

        # Create subdirectories
        self.texts_dir = self.data_dir / "texts" / "blake_archive"
        self.images_dir = self.data_dir / "images" / "blake_archive"
        self.metadata_dir = self.data_dir / "metadata" / "blake_archive"
        self.xml_dir = self.data_dir / "xml" / "blake_archive"

        for dir_path in [
            self.texts_dir,
            self.images_dir,
            self.metadata_dir,
            self.xml_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Cache for downloaded data
        self._works_cache: Dict[str, BlakeArchiveWork] = {}
        self._copies_cache: Dict[str, BlakeArchiveCopy] = {}
        self.image_depth_reports: Dict[str, Dict[str, Any]] = {}
        self.archive_metadata_enrichment: Dict[str, Any] = {}

        # Statistics tracking
        self.stats = {
            "works_found": 0,
            "works_downloaded": 0,
            "images_downloaded": 0,
            "texts_extracted": 0,
            "errors": 0,
        }

        logger.info(f"Initialized BlakeArchiveScraper with data_dir: {self.data_dir}")

    async def __aenter__(self):
        """Async context manager entry."""
        headers = {
            "User-Agent": "BlakeAnalysisPlatform/1.0 (Academic Research)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        timeout = aiohttp.ClientTimeout(total=30, sock_connect=8, sock_read=20)
        self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    # =========================================================================
    # CATALOG FETCHING
    # =========================================================================

    async def fetch_works_catalog(
        self, scope: str = "target-ledger"
    ) -> List[BlakeArchiveWork]:
        """
        Fetch the complete work-level catalog from the canonical target ledger,
        GitHub XML inventory, and Archive API metadata.

        Returns:
            List of BlakeArchiveWork objects
        """
        logger.info(
            "Fetching works catalog from Blake Archive API and GitHub XML inventory"
        )

        try:
            if scope == "archive-inventory":
                return await self._fetch_archive_inventory_catalog()

            target = load_corpus_target("canonical")
            file_names = await self._fetch_work_file_names()
            copy_index = self._copy_index_from_file_names(file_names)
            works: List[BlakeArchiveWork] = []
            metadata_guard = _ArchiveMetadataBudget(
                timeout_seconds=self.ARCHIVE_METADATA_TIMEOUT_SECONDS,
                total_budget_seconds=self.ARCHIVE_METADATA_TOTAL_BUDGET_SECONDS,
                timeout_limit=self.ARCHIVE_METADATA_TIMEOUT_LIMIT,
                failure_limit=self.ARCHIVE_METADATA_FAILURE_LIMIT,
            )

            candidate_count = sum(
                1
                for entry in target.entries
                if entry.source_hints.get(SourceType.BLAKE_ARCHIVE.value)
            )
            for entry in target.entries:
                archive_ids = entry.source_hints.get(SourceType.BLAKE_ARCHIVE.value, [])
                if not archive_ids:
                    continue
                work_id = str(archive_ids[0])
                api_data = await self._fetch_work_api_metadata_with_budget(
                    work_id, metadata_guard
                )
                title = (
                    str(api_data.get("title") or entry.title)
                    if api_data
                    else entry.title
                )
                date = (
                    api_data.get("composition_date_string")
                    or api_data.get("composition_date")
                    or entry.date_label
                    if api_data
                    else entry.date_label
                )
                medium = (
                    str(
                        api_data.get("medium")
                        or self._medium_for_category(entry.category)
                    )
                    if api_data
                    else self._medium_for_category(entry.category)
                )
                copies = copy_index.get(work_id.lower(), [])
                copies.extend(self._copy_ids_from_api(api_data))
                copies = sorted(set(copies), key=str.lower)
                work = BlakeArchiveWork(
                    work_id=entry.target_id,
                    title=title,
                    archive_id=work_id,
                    composition_date=str(date) if date else None,
                    medium=medium,
                    category=medium,
                    copies=copies,
                    description=(
                        str(api_data.get("info"))
                        if api_data and api_data.get("info")
                        else entry.notes
                    ),
                )
                works.append(work)
                self._works_cache[work.work_id] = work

            self.archive_metadata_enrichment = metadata_guard.to_report(
                total_candidates=candidate_count, scope=scope
            )
            self.stats["works_found"] = len(works)
            logger.info(
                f"Found {len(works)} work-level targets in Blake Archive catalog"
            )
            return works

        except Exception as e:
            logger.error(f"Error fetching works catalog: {e}")
            return await self._fetch_works_fallback()

    async def _fetch_archive_inventory_catalog(self) -> List[BlakeArchiveWork]:
        file_names = await self._fetch_work_file_names()
        copy_index = self._copy_index_from_file_names(file_names)
        target = load_corpus_target("canonical")
        target_by_archive_id = {}
        for entry in target.entries:
            for archive_id in entry.source_hints.get(
                SourceType.BLAKE_ARCHIVE.value, []
            ):
                target_by_archive_id.setdefault(str(archive_id).lower(), entry)

        inventory_ids = set(copy_index)
        inventory_ids.update(target_by_archive_id)
        works: List[BlakeArchiveWork] = []
        metadata_guard = _ArchiveMetadataBudget(
            timeout_seconds=self.ARCHIVE_METADATA_TIMEOUT_SECONDS,
            total_budget_seconds=self.ARCHIVE_METADATA_TOTAL_BUDGET_SECONDS,
            timeout_limit=self.ARCHIVE_METADATA_TIMEOUT_LIMIT,
            failure_limit=self.ARCHIVE_METADATA_FAILURE_LIMIT,
        )
        for work_id in sorted(inventory_ids, key=str.lower):
            api_data = await self._fetch_work_api_metadata_with_budget(
                work_id, metadata_guard
            )
            entry = target_by_archive_id.get(work_id.lower())
            title = (
                str(api_data.get("title"))
                if api_data and api_data.get("title")
                else entry.title if entry else work_id
            )
            date = (
                api_data.get("composition_date_string")
                or api_data.get("composition_date")
                if api_data
                else None
            )
            if not date and entry:
                date = entry.date_label
            medium = (
                str(api_data.get("medium"))
                if api_data and api_data.get("medium")
                else self._medium_for_category(entry.category) if entry else "ms"
            )
            copies = list(copy_index.get(work_id.lower(), []))
            copies.extend(self._copy_ids_from_api(api_data))
            work = BlakeArchiveWork(
                work_id=work_id,
                title=title,
                archive_id=work_id,
                composition_date=str(date) if date else None,
                medium=medium,
                category=medium,
                copies=sorted(set(copies), key=str.lower),
                description=(
                    str(api_data.get("info"))
                    if api_data and api_data.get("info")
                    else entry.notes if entry else None
                ),
            )
            works.append(work)
            self._works_cache[work.work_id] = work

        self.archive_metadata_enrichment = metadata_guard.to_report(
            total_candidates=len(inventory_ids), scope="archive-inventory"
        )
        self.stats["works_found"] = len(works)
        logger.info(
            "Found %s Archive inventory work prefixes from %s XML records",
            len(works),
            len(file_names),
        )
        return works

    async def _fetch_work_file_names(self) -> List[str]:
        if not self.session:
            return []

        try:
            async with self.session.get(self.WORKS_CONTENTS_URL) as response:
                if response.status == 200:
                    content = await response.text()
                    root = ET.fromstring(content)
                    names = []
                    for elem in root.iter():
                        name = elem.attrib.get("filename") or elem.attrib.get("name")
                        if (
                            name
                            and name.endswith(".xml")
                            and name != "__contents__.xml"
                        ):
                            names.append(name)
                    if names:
                        return sorted(set(names), key=str.lower)
        except Exception as e:
            logger.debug(f"Failed to fetch work XML inventory: {e}")

        try:
            async with self.session.get(self.WORKS_API_CONTENTS_URL) as response:
                if response.status == 200:
                    payload = await response.json()
                    return sorted(
                        {
                            item.get("name", "")
                            for item in payload
                            if isinstance(item, dict)
                            and item.get("type") == "file"
                            and str(item.get("name", "")).endswith(".xml")
                            and item.get("name") != "__contents__.xml"
                        },
                        key=str.lower,
                    )
        except Exception as e:
            logger.debug(f"Failed to fetch GitHub API work inventory: {e}")

        return []

    def _copy_index_from_file_names(
        self, file_names: List[str]
    ) -> Dict[str, List[str]]:
        index: Dict[str, List[str]] = {}
        for name in file_names:
            stem = name[:-4] if name.endswith(".xml") else name
            if not stem:
                continue
            work_id = stem.split(".", 1)[0].lower()
            index.setdefault(work_id, []).append(stem)
        return {
            key: sorted(set(values), key=str.lower) for key, values in index.items()
        }

    async def _fetch_work_api_metadata(self, work_id: str) -> Optional[Dict[str, Any]]:
        if not self.session:
            return None
        await asyncio.sleep(self.rate_limit)
        try:
            async with self.session.get(f"{self.WORK_API_URL}/{work_id}") as response:
                if response.status == 200:
                    payload = await response.json()
                    return payload if isinstance(payload, dict) else None
        except Exception as e:
            logger.debug(f"Failed to fetch Archive API metadata for {work_id}: {e}")
        return None

    async def _fetch_work_api_metadata_with_budget(
        self, work_id: str, budget: "_ArchiveMetadataBudget"
    ) -> Optional[Dict[str, Any]]:
        if not budget.can_attempt:
            budget.record_skip()
            return None
        budget.begin_attempt()
        try:
            payload = await asyncio.wait_for(
                self._fetch_work_api_metadata(work_id),
                timeout=budget.timeout_seconds,
            )
            if payload:
                budget.record_success()
            else:
                budget.record_failure()
            return payload
        except asyncio.TimeoutError:
            budget.record_timeout()
            return None

    def _copy_ids_from_api(self, api_data: Optional[Dict[str, Any]]) -> List[str]:
        if not api_data:
            return []
        copy_ids: List[str] = []
        for related in api_data.get("related_works") or []:
            if not isinstance(related, dict):
                continue
            title = related.get("title")
            link = title.get("link") if isinstance(title, dict) else None
            if link and re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*", str(link)):
                copy_ids.append(str(link))
        return copy_ids

    def _medium_for_category(self, category: str) -> str:
        category_to_medium = {
            "illuminated_books": "illbk",
            "commercial_illustrations": "comb",
            "separate_prints": "spb",
            "drawings": "pdes",
            "watercolors_drawings": "wc",
            "paintings": "pt",
            "manuscripts": "ms",
            "typographic_works": "ms",
            "letters": "lt",
            "engravings": "spb",
            "color_prints": "spb",
            "poems": "ms",
        }
        return category_to_medium.get(category, "ms")

    async def _fetch_works_fallback(self) -> List[BlakeArchiveWork]:
        """Fallback method using hardcoded canonical Blake works."""
        logger.info("Using fallback canonical works list")

        canonical_works = [
            BlakeArchiveWork(
                "songsie",
                "Songs of Innocence and of Experience",
                "1789-1794",
                "illbk",
                "Illuminated Books",
            ),
            BlakeArchiveWork(
                "thel", "The Book of Thel", "1789", "illbk", "Illuminated Books"
            ),
            BlakeArchiveWork(
                "mhh",
                "The Marriage of Heaven and Hell",
                "1790",
                "illbk",
                "Illuminated Books",
            ),
            BlakeArchiveWork(
                "vda",
                "Visions of the Daughters of Albion",
                "1793",
                "illbk",
                "Illuminated Books",
            ),
            BlakeArchiveWork(
                "america", "America a Prophecy", "1793", "illbk", "Illuminated Books"
            ),
            BlakeArchiveWork(
                "urizen", "The Book of Urizen", "1794", "illbk", "Illuminated Books"
            ),
            BlakeArchiveWork(
                "europe", "Europe a Prophecy", "1794", "illbk", "Illuminated Books"
            ),
            BlakeArchiveWork(
                "ahania", "The Book of Ahania", "1795", "illbk", "Illuminated Books"
            ),
            BlakeArchiveWork(
                "b-los", "The Book of Los", "1795", "illbk", "Illuminated Books"
            ),
            BlakeArchiveWork(
                "s-los", "The Song of Los", "1795", "illbk", "Illuminated Books"
            ),
            BlakeArchiveWork(
                "milton", "Milton a Poem", "1804-1811", "illbk", "Illuminated Books"
            ),
            BlakeArchiveWork(
                "jerusalem",
                "Jerusalem The Emanation of The Giant Albion",
                "1804-1820",
                "illbk",
                "Illuminated Books",
            ),
            BlakeArchiveWork(
                "gates-child",
                "For Children: The Gates of Paradise",
                "1793",
                "illbk",
                "Illuminated Books",
            ),
            BlakeArchiveWork(
                "gates-sexes",
                "For the Sexes: The Gates of Paradise",
                "1818",
                "illbk",
                "Illuminated Books",
            ),
            BlakeArchiveWork(
                "aro", "All Religions are One", "1788", "illbk", "Illuminated Books"
            ),
            BlakeArchiveWork(
                "nnr",
                "There is No Natural Religion",
                "1788",
                "illbk",
                "Illuminated Books",
            ),
            BlakeArchiveWork(
                "abel", "The Ghost of Abel", "1822", "illbk", "Illuminated Books"
            ),
            BlakeArchiveWork(
                "homer",
                "On Homers Poetry [and] On Virgil",
                "1821",
                "illbk",
                "Illuminated Books",
            ),
            BlakeArchiveWork(
                "bb206",
                "Laocoön",
                "1826",
                "spb",
                "Separate Prints and Prints in Series",
            ),
            BlakeArchiveWork(
                "fz", "The Four Zoas (Vala)", "1797-1807", "ms", "Manuscripts"
            ),
            BlakeArchiveWork(
                "bb421",
                "Illustrations of the Book of Job",
                "1823-1826",
                "spb",
                "Separate Prints and Prints in Series",
            ),
            BlakeArchiveWork(
                "but812",
                "Illustrations to Dante's Divine Comedy",
                "1824-1827",
                "wc",
                "Watercolor Drawings",
            ),
            BlakeArchiveWork("lt", "Letters", "1780-1827", "lt", "Letters"),
        ]

        for work in canonical_works:
            self._works_cache[work.work_id] = work

        self.stats["works_found"] = len(canonical_works)
        return canonical_works

    # =========================================================================
    # TEXT EXTRACTION
    # =========================================================================

    async def fetch_tei_content(
        self, work_id: str, copy_ids: Optional[List[str]] = None
    ) -> Optional[str]:
        logger.debug(f"Fetching TEI content for {work_id}")

        tei_patterns = await self._tei_candidate_urls(work_id, copy_ids)
        seen_patterns = []
        for url in tei_patterns:
            if url in seen_patterns:
                continue
            seen_patterns.append(url)
            try:
                await asyncio.sleep(self.rate_limit)
                async with self.session.get(url) as response:
                    if response.status == 200:
                        xml_content = await response.text()

                        # Verify we got XML, not error page
                        if (
                            "<?xml" not in xml_content[:100]
                            and "<bad" not in xml_content[:100]
                        ):
                            continue

                        # Save raw XML
                        xml_path = self.xml_dir / f"{Path(url).name}"
                        async with aiofiles.open(xml_path, "w", encoding="utf-8") as f:
                            await f.write(xml_content)

                        # Extract text from TEI XML
                        text = self._extract_text_from_tei(xml_content)
                        if text:
                            logger.info(
                                f"Extracted {len(text)} chars of text for {work_id}"
                            )
                            return text
            except Exception as e:
                logger.debug(f"Failed to fetch TEI from {url}: {e}")
                continue

        return None

    async def _tei_candidate_urls(
        self, work_id: str, copy_ids: Optional[List[str]] = None
    ) -> List[str]:
        stems: List[str] = []
        for copy_id in copy_ids or []:
            stems.append(self._normalise_tei_stem(copy_id))

        inventory_names = await self._fetch_work_file_names()
        copy_index = self._copy_index_from_file_names(inventory_names)
        stems.extend(copy_index.get(work_id.lower(), []))

        copy_letters = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "k"]
        for letter in copy_letters:
            stems.append(f"{work_id}.{letter}")
            stems.append(f"{work_id}.{letter.upper()}")
        stems.append(work_id)

        urls: List[str] = []
        seen: Set[str] = set()
        for stem in stems:
            if not stem or stem in seen:
                continue
            seen.add(stem)
            urls.append(f"{self.GITHUB_BASE_URL}/works/{stem}.xml")
        urls.append(f"{self.GITHUB_BASE_URL}/teicontent/{work_id}.xml")
        return urls

    def _normalise_tei_stem(self, value: str) -> str:
        stem = str(value).strip()
        if stem.endswith(".xml"):
            stem = stem[:-4]
        return stem

    def _extract_text_from_tei(self, xml_content: str) -> Optional[str]:
        """
        Extract text content from TEI XML.

        Args:
            xml_content: Raw XML string

        Returns:
            Extracted text or None
        """
        try:
            from ..transcription import extract_primary_text

            return extract_primary_text(xml_content)

        except ET.ParseError as e:
            logger.debug(f"TEI parse error: {e}")
        except Exception as e:
            logger.debug(f"TEI extraction error: {e}")

        return None

    async def fetch_erdman_text(self, work_id: str) -> Optional[str]:
        """
        Fetch text from Erdman edition (Complete Poetry and Prose).

        Args:
            work_id: Work identifier

        Returns:
            Text content or None
        """
        logger.debug(f"Fetching Erdman text for {work_id}")

        # Erdman edition anchors
        erdman_anchors = {
            "songsie": "b1.1",
            "mhh": "b1.7",
            "thel": "b1.3",
            "vda": "b1.8",
            "america": "b1.9",
            "europe": "b1.10",
            "urizen": "b1.11",
            "los": "b1.12",
            "ahania": "b1.13",
            "s-los": "b1.14",
            "milton": "b1.15",
            "jerusalem": "b1.16",
        }

        anchor = erdman_anchors.get(work_id)
        if not anchor:
            return None

        try:
            # Use Wayback Machine for reliability
            url = f"{self.WAYBACK_PREFIX}/{self.ERDMAN_URL}/#{anchor}"

            await asyncio.sleep(self.rate_limit)
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    # Extract text from HTML
                    return self._extract_text_from_html(html, anchor)
        except Exception as e:
            logger.debug(f"Failed to fetch Erdman text: {e}")

        return None

    def _extract_text_from_html(self, html: str, anchor: str) -> Optional[str]:
        """Extract text from HTML content."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Remove scripts and styles
            for tag in soup(["script", "style", "nav", "header", "footer"]):
                tag.decompose()

            # Find main content area
            main_content = (
                soup.find("main")
                or soup.find("article")
                or soup.find("div", class_="content")
            )

            if main_content:
                text = main_content.get_text(separator="\n", strip=True)
                return text if len(text) > 100 else None

        except Exception as e:
            logger.debug(f"HTML extraction error: {e}")

        return None

    # =========================================================================
    # IMAGE DOWNLOADING
    # =========================================================================

    async def download_work_images(
        self,
        work_id: str,
        dpi: int = 100,
        max_images: Optional[int] = None,
        image_mode: str = "representative",
        copy_ids: Optional[List[str]] = None,
    ) -> List[BlakeImage]:
        """
        Download all images for a work.

        Args:
            work_id: Work identifier
            dpi: Image resolution (100, 150, 200, 300)
            max_images: Maximum number of images to download (None for all)

        Returns:
            List of BlakeImage objects
        """
        logger.info(f"Downloading images for work {work_id}")

        images = []
        work_images_dir = self.images_dir / work_id
        work_images_dir.mkdir(parents=True, exist_ok=True)

        # Get list of objects/plates for this work
        objects, expected_count = await self._get_work_objects(
            work_id, image_mode=image_mode, copy_ids=copy_ids
        )

        if max_images:
            objects = objects[:max_images]

        semaphore = asyncio.Semaphore(8)

        async def fetch_object(obj_id: str) -> Tuple[str, Optional[BlakeImage], str]:
            async with semaphore:
                try:
                    image = await self._download_object_image(
                        work_id, obj_id, dpi, work_images_dir
                    )
                    if image:
                        return obj_id, image, ""
                    return obj_id, None, "no candidate image URL returned an image"
                except Exception as e:
                    return obj_id, None, str(e)

        failures: List[Dict[str, str]] = []
        results = await asyncio.gather(
            *(fetch_object(obj_id) for obj_id in objects),
            return_exceptions=False,
        )
        for obj_id, image, error in results:
            if image:
                images.append(image)
                self.stats["images_downloaded"] += 1
            elif error:
                failures.append({"object_id": obj_id, "reason": error})
                self.stats["errors"] += 1

        status = (
            "complete"
            if objects and len(images) == len(objects)
            else "partial" if images else "missing"
        )
        self.image_depth_reports[work_id] = {
            "image_mode": image_mode,
            "preferred_dpi": dpi,
            "expected_object_count": expected_count,
            "resolved_object_count": len(objects),
            "downloaded_image_count": len(images),
            "image_depth_status": status,
            "failures": failures,
        }
        logger.info(f"Downloaded {len(images)} images for {work_id}")
        return images

    async def _get_work_objects(
        self,
        work_id: str,
        *,
        image_mode: str = "representative",
        copy_ids: Optional[List[str]] = None,
    ) -> Tuple[List[str], Optional[int]]:
        """Get list of object IDs for a work."""
        objects: List[str] = []
        payload_objects: List[str] = []
        payload: Dict[str, Any] = {}
        try:
            async with self.session.get(f"{self.WORK_API_URL}/{work_id}") as response:
                if response.status == 200:
                    raw_payload = await response.json()
                    if isinstance(raw_payload, dict):
                        payload = raw_payload
                        payload_objects = self._object_ids_from_payload(payload)
        except Exception as e:
            logger.debug(f"Failed to fetch objects list: {e}")

        if image_mode == "archive-all" and (payload or copy_ids):
            objects.extend(
                self._work_scoped_object_ids(
                    work_id,
                    payload_objects,
                    copy_ids=copy_ids,
                )
            )
            payload_copy_ids, direct_objects = (
                self._copy_and_object_ids_from_work_payload(payload, work_id=work_id)
                if payload
                else ([], [])
            )
            copy_id_set = set(payload_copy_ids)
            copy_id_set.update(self._work_scoped_copy_ids(work_id, copy_ids or []))
            objects.extend(direct_objects)
            expected_total = len(direct_objects)
            for copy_id in sorted(copy_id_set, key=str.lower):
                copy_objects, copy_expected = await self._objects_for_copy(copy_id)
                copy_objects = self._work_scoped_object_ids(
                    work_id,
                    copy_objects,
                    copy_ids=[copy_id],
                )
                expected_total += copy_expected or len(copy_objects)
                objects.extend(copy_objects)
            resolved = sorted(set(objects), key=_object_sort_key)
            return resolved, expected_total or len(resolved)

        scoped_payload_objects = self._work_scoped_object_ids(
            work_id, payload_objects, copy_ids=copy_ids
        )
        objects.extend(scoped_payload_objects or payload_objects)
        if objects:
            resolved = sorted(set(objects), key=_object_sort_key)
            return resolved, len(resolved)

        cached = self._works_cache.get(work_id)
        if cached and cached.copies:
            return [cached.copies[0]], 1
        return [], 0

    def _copy_and_object_ids_from_work_payload(
        self, payload: Dict[str, Any], work_id: Optional[str] = None
    ) -> Tuple[List[str], List[str]]:
        copy_ids: List[str] = []
        object_ids: List[str] = []
        for related in payload.get("related_works") or []:
            if not isinstance(related, dict):
                continue
            title = related.get("title")
            title_type = title.get("type") if isinstance(title, dict) else None
            link = title.get("link") if isinstance(title, dict) else None
            if title_type == "copy" and link:
                normalised = str(link).strip()
                if re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*", normalised):
                    copy_ids.append(normalised)
            elif title_type == "object" and link:
                parsed = urlparse(str(link))
                desc_match = re.search(r"(?:^|[?&])descId=([^&]+)", parsed.query)
                if desc_match:
                    object_ids.append(self._normalise_object_id(desc_match.group(1)))
        if work_id:
            copy_ids = self._work_scoped_copy_ids(work_id, copy_ids)
            object_ids = self._work_scoped_object_ids(
                work_id,
                object_ids,
                copy_ids=copy_ids,
            )
        return (
            sorted(set(copy_ids), key=str.lower),
            sorted({item for item in object_ids if item}, key=_object_sort_key),
        )

    def _work_scoped_copy_ids(
        self, work_id: str, copy_ids: List[str]
    ) -> List[str]:
        return [
            str(copy_id).strip()
            for copy_id in copy_ids
            if self._id_belongs_to_prefix(work_id, copy_id)
        ]

    def _work_scoped_object_ids(
        self,
        work_id: str,
        object_ids: List[str],
        *,
        copy_ids: Optional[List[str]] = None,
    ) -> List[str]:
        prefixes = [work_id]
        prefixes.extend(str(copy_id).strip() for copy_id in copy_ids or [] if copy_id)
        return [
            object_id
            for object_id in object_ids
            if any(
                self._id_belongs_to_prefix(prefix, object_id) for prefix in prefixes
            )
        ]

    def _id_belongs_to_prefix(self, prefix: str, candidate: Any) -> bool:
        prefix_text = str(prefix or "").strip().lower()
        candidate_text = self._normalise_object_id(candidate).lower()
        if not prefix_text or not candidate_text:
            return False
        if (
            candidate_text == prefix_text
            or candidate_text.startswith(f"{prefix_text}.")
            or candidate_text.startswith(f"{prefix_text}-")
        ):
            return True
        if prefix_text.isalpha() and len(prefix_text) <= 3:
            suffix = candidate_text[len(prefix_text) :]
            return bool(
                candidate_text.startswith(prefix_text)
                and suffix
                and suffix[0].isdigit()
            )
        return False

    async def _objects_for_copy(self, copy_id: str) -> Tuple[List[str], Optional[int]]:
        try:
            await asyncio.sleep(self.rate_limit)
            async with self.session.get(
                f"{self.ARCHIVE_BASE_URL}/api/copy/{copy_id}"
            ) as response:
                if response.status != 200:
                    return [], None
                payload = await response.json()
        except Exception as e:
            logger.debug(f"Failed to fetch Archive copy metadata for {copy_id}: {e}")
            return [], None

        if not isinstance(payload, dict):
            return [], None
        number = payload.get("number_of_objects")
        try:
            number_of_objects = int(number) if number is not None else None
        except (TypeError, ValueError):
            number_of_objects = None
        lead = self._normalise_object_id(payload.get("image"))
        if number_of_objects and lead:
            match = re.match(r"(?P<prefix>.+\.p)\d+[A-Za-z]?$", lead)
            if match:
                prefix = match.group("prefix")
                return (
                    [f"{prefix}{index}" for index in range(1, number_of_objects + 1)],
                    number_of_objects,
                )
        objects = self._object_ids_from_payload(payload)
        return sorted(set(objects), key=_object_sort_key), number_of_objects

    def _object_ids_from_payload(self, payload: Dict[str, Any]) -> List[str]:
        ids: List[str] = []

        def add(value: Any) -> None:
            normalised = self._normalise_object_id(value)
            if normalised:
                ids.append(normalised)

        for key in ("image", "image_url", "object_id", "objectid"):
            add(payload.get(key))

        for collection_key in ("objects", "object_list", "plates", "related_objects"):
            collection = payload.get(collection_key) or []
            if not isinstance(collection, list):
                continue
            for item in collection:
                if isinstance(item, dict):
                    for key in (
                        "image",
                        "image_url",
                        "object_id",
                        "objectid",
                        "id",
                        "bad_id",
                    ):
                        add(item.get(key))
                else:
                    add(item)

        return ids

    def _normalise_object_id(self, value: Any) -> str:
        if not value:
            return ""
        text = str(value).strip()
        text = text.rsplit("/", 1)[-1]
        text = re.sub(r"\.(?:100|150|200|300|600)\.jpg$", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\.jpg$", "", text, flags=re.IGNORECASE)
        return text

    async def _download_object_image(
        self, work_id: str, object_id: str, dpi: int, output_dir: Path
    ) -> Optional[BlakeImage]:
        """Download a single object image."""
        object_id = self._normalise_object_id(object_id)
        image_patterns = self._image_candidate_urls(object_id, dpi)
        request_timeout = aiohttp.ClientTimeout(total=18, sock_connect=5, sock_read=12)

        for url in image_patterns:
            actual_dpi = self._dpi_from_image_url(url, dpi)
            filename = f"{object_id}_{actual_dpi}dpi.jpg"
            image_path = output_dir / filename
            if image_path.exists():
                return BlakeImage(
                    id=object_id,
                    metadata_id=work_id,
                    title=filename,
                    file_path=image_path,
                    original_url=url,
                    width=None,
                    height=None,
                    dpi=actual_dpi,
                    plate_number=self._plate_number_from_object_id(object_id),
                )
            try:
                await asyncio.sleep(self.rate_limit)
                async with self.session.get(url, timeout=request_timeout) as response:
                    if response.status == 200:
                        content = await response.read()

                        content_type = response.headers.get("content-type", "")
                        has_image_signature = (
                            content.startswith(b"\xff\xd8")
                            or content.startswith(b"\x89PNG\r\n\x1a\n")
                            or content.startswith(b"GIF")
                        )
                        if (
                            "image" not in content_type.lower()
                            and not has_image_signature
                        ):
                            continue

                        async with aiofiles.open(image_path, "wb") as f:
                            await f.write(content)

                        return BlakeImage(
                            id=object_id,
                            metadata_id=work_id,
                            title=filename,
                            file_path=image_path,
                            original_url=url,
                            width=None,
                            height=None,
                            dpi=actual_dpi,
                            plate_number=self._plate_number_from_object_id(object_id),
                        )
            except Exception as e:
                logger.debug(f"Failed to download from {url}: {e}")
                continue

        return None

    def _image_candidate_urls(self, object_id: str, dpi: int) -> List[str]:
        primary = [300]
        if dpi not in primary:
            primary.append(dpi)
        if 100 not in primary:
            primary.append(100)
        urls = [
            f"{self.ARCHIVE_BASE_URL}/images/{object_id}.{candidate_dpi}.jpg"
            for candidate_dpi in primary
        ]
        urls.extend(
            [
                f"{self.WAYBACK_PREFIX}/{self.ARCHIVE_BASE_URL}/images/{object_id}.{candidate_dpi}.jpg"
                for candidate_dpi in primary
            ]
        )
        return list(dict.fromkeys(urls))

    def _dpi_from_image_url(self, url: str, fallback: int) -> int:
        match = re.search(r"\.(100|150|200|300|600)\.jpg$", url, re.IGNORECASE)
        if match:
            return int(match.group(1))
        match = re.search(r"/(100|150|200|300|600)dpi/", url, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return fallback

    def _plate_number_from_object_id(self, object_id: str) -> Optional[int]:
        match = re.search(r"\.p(\d+)", object_id)
        return int(match.group(1)) if match else None

    # =========================================================================
    # COMPREHENSIVE DOWNLOAD
    # =========================================================================

    async def download_all_works(
        self,
        include_images: bool = True,
        image_dpi: int = 100,
        max_images_per_work: Optional[int] = 5,
        categories: Optional[List[str]] = None,
        image_mode: str = "representative",
        archive_scope: str = "target-ledger",
        force: bool = False,
    ) -> List[BlakeWork]:
        """
        Download works from the selected Blake Archive catalog scope.

        Args:
            include_images: Whether to download images
            image_dpi: Image resolution to download
            max_images_per_work: Maximum images per work (None for all)
            categories: Filter by category (None for all)
            force: Force re-download even if exists

        Returns:
            List of BlakeWork objects
        """
        logger.info("Starting Blake Archive catalog-scope download")

        # Fetch catalog
        catalog = await self.fetch_works_catalog(scope=archive_scope)

        # Filter by category if specified
        if categories:
            catalog = [w for w in catalog if w.category in categories]

        downloaded_works = []

        for i, archive_work in enumerate(catalog):
            logger.info(f"Processing work {i+1}/{len(catalog)}: {archive_work.title}")

            try:
                work = await self._download_single_work(
                    archive_work,
                    include_images=include_images,
                    image_dpi=image_dpi,
                    max_images=max_images_per_work,
                    image_mode=image_mode,
                    force=force,
                )

                if work:
                    downloaded_works.append(work)
                    self.stats["works_downloaded"] += 1

            except Exception as e:
                logger.error(f"Failed to download work {archive_work.work_id}: {e}")
                self.stats["errors"] += 1

        # Save download report
        await self._save_download_report()

        logger.info(f"Download complete. Stats: {self.stats}")
        return downloaded_works

    async def _download_single_work(
        self,
        archive_work: BlakeArchiveWork,
        include_images: bool = True,
        image_dpi: int = 100,
        max_images: Optional[int] = None,
        image_mode: str = "representative",
        force: bool = False,
    ) -> Optional[BlakeWork]:
        """Download a single work with all its content."""
        work_id = archive_work.work_id
        archive_id = archive_work.archive_id or work_id
        existing_work = self._load_existing_work(work_id)
        existing_analysis = (
            existing_work.metadata.analysis_results if existing_work else {}
        )
        fallback_validation = existing_analysis.get("validated_fallback_text")
        uses_validated_fallback_text = False

        # Check if already downloaded
        text_path = self.texts_dir / f"{work_id}.txt"
        if text_path.exists() and not force:
            logger.debug(f"Work {work_id} already exists, skipping")
            # Load existing
            async with aiofiles.open(text_path, "r", encoding="utf-8") as f:
                text_content = await f.read()
            uses_validated_fallback_text = bool(fallback_validation and text_content)
        else:
            # Fetch text content
            text_content = await self.fetch_tei_content(archive_id, archive_work.copies)

            if not text_content:
                text_content = await self.fetch_erdman_text(work_id)

            if not text_content and fallback_validation and existing_work:
                text_content = existing_work.text_content
                uses_validated_fallback_text = bool(text_content)

            if text_content:
                # Save text
                async with aiofiles.open(text_path, "w", encoding="utf-8") as f:
                    await f.write(text_content)
                self.stats["texts_extracted"] += 1

        # Download images
        images = []
        if include_images:
            images = await self.download_work_images(
                archive_id,
                dpi=image_dpi,
                max_images=max_images,
                image_mode=image_mode,
                copy_ids=archive_work.copies,
            )
            for image in images:
                image.metadata_id = work_id
        else:
            self.image_depth_reports[archive_id] = {
                "image_mode": image_mode,
                "preferred_dpi": image_dpi,
                "expected_object_count": 0,
                "resolved_object_count": 0,
                "downloaded_image_count": 0,
                "image_depth_status": "not_requested",
                "failures": [],
            }

        # Determine work type
        work_type = self._determine_work_type(archive_work)

        # Create metadata
        metadata = BlakeMetadata(
            id=work_id,
            title=archive_work.title,
            work_type=work_type,
            source=SourceType.BLAKE_ARCHIVE,
            source_url=f"{self.ARCHIVE_BASE_URL}/work/{archive_id}",
            source_id=archive_id,
            api_source="blake_archive_api_github",
            license_type=LicenseType.UNKNOWN,
            usage_terms="Archive provider files require source-specific rights review; public-domain underlying Blake works do not grant redistribution of this edition or its images.",
            creation_date=self._parse_date(archive_work.composition_date),
            medium=archive_work.medium,
            description=archive_work.description,
            file_path=text_path if text_content else None,
        )
        if uses_validated_fallback_text and existing_work:
            metadata.file_path = existing_work.metadata.file_path or metadata.file_path
            metadata.file_size = existing_work.metadata.file_size
            metadata.mime_type = existing_work.metadata.mime_type
            metadata.checksum = existing_work.metadata.checksum

        metadata.analysis_results = {
            "source_authority_tier": (
                "fallback_text_validated"
                if uses_validated_fallback_text
                else "archive_primary"
            ),
            "image_depth": self.image_depth_reports.get(archive_id, {}),
        }
        if uses_validated_fallback_text and fallback_validation:
            metadata.analysis_results["validated_fallback_text"] = fallback_validation

        # Save metadata
        metadata_path = self.metadata_dir / f"{work_id}.json"
        async with aiofiles.open(metadata_path, "w", encoding="utf-8") as f:
            await f.write(
                json.dumps(metadata.model_dump(mode="json"), default=str, indent=2)
            )

        # Create BlakeWork
        return BlakeWork(
            id=work_id,
            metadata=metadata,
            text_content=text_content,
            images=images,
            fully_processed=bool(text_content),
        )

    def _load_existing_work(self, work_id: str) -> Optional[BlakeWork]:
        db_path = self.metadata_dir / "metadata.db"
        if not db_path.exists():
            return None
        try:
            return MetadataDatabase(db_path).load_work(work_id)
        except Exception as exc:
            logger.warning("Could not load existing work %s: %s", work_id, exc)
            return None

    def _determine_work_type(self, archive_work: BlakeArchiveWork) -> WorkType:
        """Determine work type from archive category."""
        category = archive_work.category or ""
        title = (archive_work.title or "").lower()

        if category == "illbk" or "illuminated" in category.lower():
            if "song" in title:
                return WorkType.POEM
            elif "prophecy" in title or any(
                p in title
                for p in [
                    "america",
                    "europe",
                    "urizen",
                    "los",
                    "ahania",
                    "milton",
                    "jerusalem",
                ]
            ):
                return WorkType.PROPHECY
            return WorkType.ILLUMINATED_BOOK
        elif category == "lt" or "letter" in category.lower():
            return WorkType.LETTER
        elif category == "ms" or "manuscript" in category.lower():
            return WorkType.MANUSCRIPT
        elif category in ["wc", "pt", "pdes"] or any(
            w in category.lower() for w in ["drawing", "painting", "watercolor"]
        ):
            return WorkType.DRAWING
        elif category == "comb" or "illustration" in category.lower():
            return WorkType.ILLUSTRATION
        else:
            return WorkType.POEM  # Default

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime."""
        if not date_str:
            return None

        try:
            # Handle ranges like "1789-1794"
            if "-" in date_str and len(date_str) > 5:
                date_str = date_str.split("-")[0]

            year = int(re.search(r"\d{4}", date_str).group())
            return datetime(year, 1, 1)
        except (ValueError, AttributeError):
            return None

    async def _save_download_report(self):
        """Save download statistics report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "statistics": self.stats,
            "data_directory": str(self.data_dir),
        }

        report_path = self.data_dir / "blake_archive_download_report.json"
        async with aiofiles.open(report_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(report, indent=2))

        logger.info(f"Download report saved to {report_path}")

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    async def get_work_info(self, work_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific work."""
        if work_id in self._works_cache:
            work = self._works_cache[work_id]
            return {
                "id": work.work_id,
                "title": work.title,
                "date": work.composition_date,
                "category": work.category,
                "url": f"{self.ARCHIVE_BASE_URL}/work/{work_id}",
            }
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get current download statistics."""
        return {
            **self.stats,
            "data_directory": str(self.data_dir),
            "texts_directory": str(self.texts_dir),
            "images_directory": str(self.images_dir),
        }

    async def verify_downloads(self) -> Dict[str, Any]:
        """Verify downloaded content integrity."""
        verification = {
            "texts": {"count": 0, "valid": 0, "errors": []},
            "images": {"count": 0, "valid": 0, "errors": []},
            "metadata": {"count": 0, "valid": 0, "errors": []},
        }

        # Verify texts
        for text_file in self.texts_dir.glob("*.txt"):
            verification["texts"]["count"] += 1
            try:
                async with aiofiles.open(text_file, "r", encoding="utf-8") as f:
                    content = await f.read()
                if len(content) > 100:
                    verification["texts"]["valid"] += 1
                else:
                    verification["texts"]["errors"].append(
                        f"Too short: {text_file.name}"
                    )
            except Exception as e:
                verification["texts"]["errors"].append(
                    f"Read error {text_file.name}: {e}"
                )

        # Verify images
        for image_file in self.images_dir.rglob("*.jpg"):
            verification["images"]["count"] += 1
            if image_file.stat().st_size > 1000:
                verification["images"]["valid"] += 1
            else:
                verification["images"]["errors"].append(f"Too small: {image_file.name}")

        # Verify metadata
        for meta_file in self.metadata_dir.glob("*.json"):
            verification["metadata"]["count"] += 1
            try:
                async with aiofiles.open(meta_file, "r", encoding="utf-8") as f:
                    content = await f.read()
                json.loads(content)
                verification["metadata"]["valid"] += 1
            except Exception as e:
                verification["metadata"]["errors"].append(
                    f"Parse error {meta_file.name}: {e}"
                )

        return verification


# Convenience function for quick scraping
async def scrape_blake_archive(
    data_dir: Path,
    include_images: bool = True,
    max_images_per_work: int = 5,
    categories: Optional[List[str]] = None,
    image_mode: str = "representative",
    archive_scope: str = "target-ledger",
) -> List[BlakeWork]:
    """
    Convenience function to scrape the Blake Archive.

    Args:
        data_dir: Directory to store downloaded data
        include_images: Whether to download images
        max_images_per_work: Maximum images per work
        categories: Filter by category (None for all)

    Returns:
        List of downloaded BlakeWork objects
    """
    async with BlakeArchiveScraper(data_dir) as scraper:
        return await scraper.download_all_works(
            include_images=include_images,
            max_images_per_work=max_images_per_work,
            categories=categories,
            image_mode=image_mode,
            archive_scope=archive_scope,
        )
