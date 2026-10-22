from __future__ import annotations

import logging
from time import monotonic
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Protocol

from ..downloader.blake_archive_scraper import BlakeArchiveScraper, BlakeArchiveWork
from ..models import BlakeWork, LicenseType, SourceType, WorkType
from .models import SourceRecord

logger = logging.getLogger(__name__)


class SourceProvider(Protocol):
    source_type: SourceType
    name: str

    async def discover(self) -> List[SourceRecord]: ...

    async def fetch(
        self,
        record: SourceRecord,
        *,
        force: bool = False,
        image_mode: str = "representative",
        image_dpi: int = 100,
        max_images_per_work: Optional[int] = 1,
    ) -> Optional[BlakeWork]: ...


class AdapterSourceProvider:
    def __init__(self, source_type: SourceType, adapter: Any):
        self.source_type = source_type
        self.adapter = adapter
        self.name = getattr(adapter, "name", source_type.value)

    async def discover(self) -> List[SourceRecord]:
        if not hasattr(self.adapter, "get_work_list"):
            return []

        raw_records = await self.adapter.get_work_list()
        records: List[SourceRecord] = []
        for raw in raw_records:
            if not isinstance(raw, dict):
                continue
            records.append(self._normalize_record(raw))
        return records

    async def fetch(
        self,
        record: SourceRecord,
        *,
        force: bool = False,
        image_mode: str = "representative",
        image_dpi: int = 100,
        max_images_per_work: Optional[int] = 1,
    ) -> Optional[BlakeWork]:
        if not hasattr(self.adapter, "download_work"):
            return None
        payload = dict(record.metadata)
        payload.setdefault("id", record.source_id)
        payload.setdefault("title", record.title)
        payload.setdefault("url", record.source_url)
        return await self.adapter.download_work(payload)

    def _normalize_record(self, raw: Dict[str, Any]) -> SourceRecord:
        source_id = str(
            raw.get("id")
            or raw.get("source_id")
            or raw.get("identifier")
            or raw.get("url")
            or ""
        )
        title = str(raw.get("title") or source_id or "Untitled")
        work_type = raw.get("work_type") or raw.get("type") or WorkType.POEM
        try:
            normalized_type = (
                work_type
                if isinstance(work_type, WorkType)
                else WorkType(str(work_type))
            )
        except ValueError:
            normalized_type = WorkType.POEM

        license_type = (
            raw.get("license_type") or raw.get("license") or LicenseType.UNKNOWN
        )
        try:
            normalized_license = (
                license_type
                if isinstance(license_type, LicenseType)
                else LicenseType(str(license_type))
            )
        except ValueError:
            normalized_license = LicenseType.UNKNOWN

        return SourceRecord(
            source_type=self.source_type,
            source_id=source_id,
            title=title,
            work_type=normalized_type,
            source_url=raw.get("source_url") or raw.get("url"),
            license_type=normalized_license,
            metadata=raw,
        )


class BlakeArchiveScraperProvider:
    source_type = SourceType.BLAKE_ARCHIVE
    name = "blake_archive_api_github"

    def __init__(self, data_dir: Path, archive_scope: str = "target-ledger"):
        self.data_dir = Path(data_dir)
        self.archive_scope = archive_scope
        self.last_metadata_enrichment: Dict[str, Any] = {}

    async def discover(self) -> List[SourceRecord]:
        async with BlakeArchiveScraper(self.data_dir, rate_limit=0.0) as scraper:
            catalog = await scraper.fetch_works_catalog(scope=self.archive_scope)
            self.last_metadata_enrichment = dict(
                getattr(scraper, "archive_metadata_enrichment", {}) or {}
            )
            records: List[SourceRecord] = []
            for work in catalog:
                archive_id = work.archive_id or work.work_id
                work_type = scraper._determine_work_type(work)
                creation_date = scraper._parse_date(work.composition_date)
                records.append(
                    SourceRecord(
                        source_type=self.source_type,
                        source_id=work.work_id,
                        title=work.title,
                        work_type=work_type,
                        source_url=f"{scraper.ARCHIVE_BASE_URL}/work/{archive_id}",
                        license_type=LicenseType.UNKNOWN,
                        creation_date=creation_date,
                        metadata={
                            "target_id": work.work_id,
                            "work_id": archive_id,
                            "medium": work.medium,
                            "category": work.category,
                            "copies": list(work.copies),
                            "description": work.description,
                            "expected_images": (
                                1 if work.category not in {"lt", "ms"} else 0
                            ),
                        },
                    )
                )
            return records

    async def fetch(
        self,
        record: SourceRecord,
        *,
        force: bool = False,
        image_mode: str = "representative",
        image_dpi: int = 100,
        max_images_per_work: Optional[int] = 1,
    ) -> Optional[BlakeWork]:
        async with BlakeArchiveScraper(self.data_dir, rate_limit=0.0) as scraper:
            archive_work = BlakeArchiveWork(
                work_id=record.source_id,
                title=record.title,
                archive_id=record.metadata.get("work_id") or record.source_id,
                composition_date=(
                    record.creation_date.isoformat() if record.creation_date else None
                ),
                medium=record.metadata.get("medium"),
                category=record.metadata.get("category"),
                copies=list(record.metadata.get("copies") or []),
                description=record.metadata.get("description"),
            )
            include_images = int(record.metadata.get("expected_images") or 0) > 0
            max_images = max_images_per_work if image_mode == "archive-all" else 1
            return await scraper._download_single_work(
                archive_work,
                include_images=include_images,
                image_dpi=image_dpi,
                image_mode=image_mode,
                max_images=max_images,
                force=force,
            )


class SourceRegistry:
    def __init__(self):
        self._providers: Dict[SourceType, SourceProvider] = {}
        self.last_discovery_health: List[Dict[str, Any]] = []

    def register(self, provider: SourceProvider) -> None:
        self._providers[provider.source_type] = provider

    def get(self, source_type: SourceType) -> Optional[SourceProvider]:
        return self._providers.get(source_type)

    def providers(self) -> List[SourceProvider]:
        return list(self._providers.values())

    async def discover_all(self) -> List[SourceRecord]:
        records: List[SourceRecord] = []
        health: List[Dict[str, Any]] = []
        for provider in self.providers():
            started = monotonic()
            provider_records: List[SourceRecord] = []
            error: str | None = None
            status = "completed"
            try:
                provider_records = await provider.discover()
                records.extend(provider_records)
            except Exception as exc:
                status = "error"
                error = str(exc)
                logger.warning("Source discovery failed for %s: %s", provider.name, exc)
            health.append(
                {
                    "provider": provider.name,
                    "source_type": getattr(provider.source_type, "value", provider.source_type),
                    "status": status,
                    "record_count": len(provider_records),
                    "error": error,
                    "duration_seconds": round(monotonic() - started, 3),
                    "records_used": bool(provider_records) and status == "completed",
                }
            )
        self.last_discovery_health = health
        return self.dedupe_records(records)

    def discovery_health(self) -> List[Dict[str, Any]]:
        return [dict(row) for row in self.last_discovery_health]

    def archive_metadata_enrichment(self) -> Dict[str, Any]:
        provider = self.get(SourceType.BLAKE_ARCHIVE)
        if provider is None:
            return {}
        return dict(getattr(provider, "last_metadata_enrichment", {}) or {})

    def dedupe_records(self, records: Iterable[SourceRecord]) -> List[SourceRecord]:
        seen_stable: set[str] = set()
        seen_canonical: set[str] = set()
        deduped: List[SourceRecord] = []

        for record in records:
            stable = record.stable_id
            canonical = record.canonical_key
            has_explicit_target = bool(record.metadata.get("target_id"))
            if stable in seen_stable or (
                canonical in seen_canonical and not has_explicit_target
            ):
                continue
            seen_stable.add(stable)
            seen_canonical.add(canonical)
            deduped.append(record)
        return deduped

    def coverage(self) -> Dict[str, str]:
        return {
            source_type.value: provider.name
            for source_type, provider in self._providers.items()
        }


def build_default_source_registry(
    data_dir: Path,
    *,
    sources: Optional[Dict[SourceType, Any]] = None,
    archive_scope: str = "target-ledger",
) -> SourceRegistry:
    registry = SourceRegistry()

    if sources is None:
        from ..downloader.sources import (
            BlakeArchiveSource,
            InternetArchiveSource,
            ProjectGutenbergSource,
        )

        sources = {
            SourceType.BLAKE_ARCHIVE: BlakeArchiveScraperProvider(
                data_dir, archive_scope=archive_scope
            ),
            SourceType.PROJECT_GUTENBERG: ProjectGutenbergSource(data_dir),
            SourceType.INTERNET_ARCHIVE: InternetArchiveSource(data_dir),
        }

    for source_type, adapter in sources.items():
        if source_type == SourceType.BLAKE_ARCHIVE:
            if isinstance(adapter, BlakeArchiveScraperProvider):
                adapter.archive_scope = archive_scope
                registry.register(adapter)
            else:
                registry.register(
                    BlakeArchiveScraperProvider(data_dir, archive_scope=archive_scope)
                )
        else:
            registry.register(AdapterSourceProvider(source_type, adapter))

    return registry
