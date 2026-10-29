from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from ..models import BlakeWork, LicenseType, SourceType, WorkType
from ..provenance import source_authority_tier


class CorpusConfig(BaseModel):
    data_dir: Path = Field(default_factory=lambda: Path("blake_data"))
    output_dir: Path = Field(default_factory=lambda: Path("analysis_output"))
    quick: bool = False
    force: bool = False
    skip_download: bool = False
    skip_analysis: bool = False
    skip_visualizations: bool = False
    skip_export: bool = False
    skip_reports: bool = False
    analysis_types: Optional[List[str]] = None
    export_formats: List[str] = Field(default_factory=lambda: ["json"])
    target_profile: str = "canonical"
    fixture_mode: Literal["auto", "always", "never"] = "auto"
    viz_profile: Literal["inventory", "core", "full"] = "core"
    archive_scope: Literal["target-ledger", "archive-inventory"] = "archive-inventory"
    image_mode: Literal["representative", "archive-all"] = "archive-all"
    image_dpi: int = 300
    max_images_per_work: Optional[int] = None
    max_workers: int = 4

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_serializer("data_dir", "output_dir")
    @classmethod
    def serialize_path(cls, value: Path) -> str:
        return str(value)


class SourceRecord(BaseModel):
    source_type: SourceType
    source_id: str
    title: str
    work_type: WorkType
    source_url: Optional[str] = None
    license_type: LicenseType = LicenseType.UNKNOWN
    creation_date: Optional[datetime] = None
    publication_date: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)

    @property
    def stable_id(self) -> str:
        return f"{self.source_type}:{self.source_id}"

    @property
    def canonical_key(self) -> str:
        title = " ".join(self.title.lower().strip().split())
        date_value = self.creation_date or self.publication_date
        date_key = date_value.date().isoformat() if date_value else ""
        return f"{title}|{date_key}|{self.work_type}"

    @field_serializer("creation_date", "publication_date")
    @classmethod
    def serialize_datetime(cls, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class CorpusTargetEntry(BaseModel):
    target_id: str
    title: str
    work_type: WorkType
    category: str
    date_label: Optional[str] = None
    creation_date: Optional[datetime] = None
    expected_text: bool = False
    expected_images: int = 0
    expected_copies: Optional[int] = None
    aliases: List[str] = Field(default_factory=list)
    source_hints: Dict[str, List[str]] = Field(default_factory=dict)
    notes: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("creation_date")
    @classmethod
    def serialize_datetime(cls, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class CorpusTarget(BaseModel):
    profile: str = "canonical"
    version: str
    description: str
    entries: List[CorpusTargetEntry] = Field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.entries)


class CorpusCoverageRecord(BaseModel):
    target_id: str
    title: str
    category: str
    work_type: str
    expected_text: bool = False
    expected_images: int = 0
    expected_copies: Optional[int] = None
    matched_work_ids: List[str] = Field(default_factory=list)
    matched_source_ids: List[str] = Field(default_factory=list)
    status: Literal["present", "partial", "missing", "duplicate", "unverified"]
    notes: List[str] = Field(default_factory=list)


class CorpusWorkRecord(BaseModel):
    id: str
    target_id: Optional[str] = None
    title: str
    work_type: str
    source: str
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    creation_date: Optional[datetime] = None
    publication_date: Optional[datetime] = None
    has_text: bool = False
    text_versions: int = 0
    has_images: bool = False
    image_count: int = 0
    expected_object_count: Optional[int] = None
    resolved_object_count: Optional[int] = None
    downloaded_image_count: Optional[int] = None
    image_depth_status: Optional[str] = None
    image_depth_failures: List[Dict[str, Any]] = Field(default_factory=list)
    source_authority_tier: Optional[str] = None
    processed: bool = False
    themes: List[str] = Field(default_factory=list)
    subjects: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_work(
        cls, work: BlakeWork, *, target_id: Optional[str] = None
    ) -> "CorpusWorkRecord":
        metadata = work.metadata
        analysis = metadata.analysis_results or {}
        image_depth = analysis.get("image_depth") or {}
        authority_tier = source_authority_tier(work)
        return cls(
            id=work.id,
            target_id=target_id,
            title=metadata.title,
            work_type=str(metadata.work_type),
            source=str(metadata.source),
            source_id=metadata.source_id,
            source_url=metadata.source_url,
            creation_date=metadata.creation_date,
            publication_date=metadata.publication_date,
            has_text=bool(work.text_content),
            text_versions=len(work.text_versions),
            has_images=bool(work.images),
            image_count=len(work.images),
            expected_object_count=image_depth.get("expected_object_count"),
            resolved_object_count=image_depth.get("resolved_object_count"),
            downloaded_image_count=image_depth.get("downloaded_image_count"),
            image_depth_status=image_depth.get("image_depth_status"),
            image_depth_failures=list(image_depth.get("failures") or []),
            source_authority_tier=authority_tier,
            processed=work.fully_processed or metadata.processed,
            themes=list(metadata.themes),
            subjects=list(metadata.subjects),
            provenance={
                "license_type": str(metadata.license_type),
                "attribution": metadata.attribution,
                "usage_terms": metadata.usage_terms,
                "api_source": metadata.api_source,
                "source_authority_tier": authority_tier,
                "image_depth": image_depth,
            },
        )

    @field_serializer("creation_date", "publication_date")
    @classmethod
    def serialize_datetime(cls, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class CorpusManifest(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid4().hex)
    generated_at: datetime = Field(default_factory=datetime.now)
    data_dir: Path
    output_dir: Path
    target_profile: str = "canonical"
    target_version: Optional[str] = None
    target_total: int = 0
    coverage_status: str = "unscoped"
    coverage_counts: Dict[str, int] = Field(default_factory=dict)
    target_records: List[CorpusCoverageRecord] = Field(default_factory=list)
    fixture_mode: bool = False
    fixture_work_ids: List[str] = Field(default_factory=list)
    total_works: int = 0
    total_images: int = 0
    work_records: List[CorpusWorkRecord] = Field(default_factory=list)
    source_coverage: Dict[str, int] = Field(default_factory=dict)
    artifacts: Dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def from_works(
        cls,
        works: List[BlakeWork],
        *,
        data_dir: Path,
        output_dir: Path,
        run_id: Optional[str] = None,
        artifacts: Optional[Dict[str, str]] = None,
        target_profile: str = "canonical",
        target_version: Optional[str] = None,
        target_records: Optional[List[CorpusCoverageRecord]] = None,
        coverage_status: str = "unscoped",
        coverage_counts: Optional[Dict[str, int]] = None,
        fixture_mode: bool = False,
        fixture_work_ids: Optional[List[str]] = None,
    ) -> "CorpusManifest":
        target_records = target_records or []
        target_by_work: Dict[str, str] = {}
        for target_record in target_records:
            for work_id in target_record.matched_work_ids:
                target_by_work[work_id] = target_record.target_id

        records = [
            CorpusWorkRecord.from_work(work, target_id=target_by_work.get(work.id))
            for work in works
        ]
        coverage: Dict[str, int] = {}
        for record in records:
            coverage[record.source] = coverage.get(record.source, 0) + 1
        return cls(
            run_id=run_id or uuid4().hex,
            data_dir=data_dir,
            output_dir=output_dir,
            target_profile=target_profile,
            target_version=target_version,
            target_total=len(target_records),
            coverage_status=coverage_status,
            coverage_counts=coverage_counts or {},
            target_records=target_records,
            fixture_mode=fixture_mode,
            fixture_work_ids=fixture_work_ids or [],
            total_works=len(records),
            total_images=sum(record.image_count for record in records),
            work_records=records,
            source_coverage=coverage,
            artifacts=artifacts or {},
        )

    def write_json(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return path

    @field_serializer("generated_at")
    @classmethod
    def serialize_generated_at(cls, value: datetime) -> str:
        return value.isoformat()

    @field_serializer("data_dir", "output_dir")
    @classmethod
    def serialize_path(cls, value: Path) -> str:
        return str(value)


class PhaseResult(BaseModel):
    name: str
    status: str = "pending"
    message: Optional[str] = None
    items_processed: int = 0
    errors: List[str] = Field(default_factory=list)
    artifacts: Dict[str, str] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    def finish(
        self,
        *,
        status: str,
        message: Optional[str] = None,
        items_processed: Optional[int] = None,
        artifacts: Optional[Dict[str, str]] = None,
        errors: Optional[List[str]] = None,
    ) -> "PhaseResult":
        ended_at = datetime.now()
        self.status = status
        self.message = message
        if items_processed is not None:
            self.items_processed = items_processed
        if artifacts:
            self.artifacts.update(artifacts)
        if errors:
            self.errors.extend(errors)
        self.ended_at = ended_at
        self.duration_seconds = (ended_at - self.started_at).total_seconds()
        return self

    @field_serializer("started_at", "ended_at")
    @classmethod
    def serialize_datetime(cls, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class CorpusRunSummary(BaseModel):
    run_id: str
    status: str
    started_at: datetime
    ended_at: datetime
    duration_seconds: float
    phases: List[PhaseResult]
    manifest_path: Path
    output_dir: Path

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_serializer("started_at", "ended_at")
    @classmethod
    def serialize_datetime(cls, value: datetime) -> str:
        return value.isoformat()

    @field_serializer("manifest_path", "output_dir")
    @classmethod
    def serialize_path(cls, value: Path) -> str:
        return str(value)
