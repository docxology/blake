from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..analysis import BlakeAnalyzer
from ..downloader import BlakeDownloader
from ..exceptions import BlakeError
from ..export import BlakeExporter
from ..metadata import MetadataManager
from ..models import AnalysisResult, BlakeWork, ExportConfig, SourceType
from .models import (
    CorpusConfig,
    CorpusCoverageRecord,
    CorpusManifest,
    CorpusRunSummary,
    CorpusTarget,
    PhaseResult,
    SourceRecord,
)
from .evidence_acquisition import (
    FALLBACK_VALIDATION_DIR,
    apply_validated_fallback_marker,
)
from .source_audit import (
    attach_missing_evidence,
    build_source_audit,
    classify_provider_rows,
)
from .sources import SourceRegistry, build_default_source_registry
from .targets import build_fixture_works, build_target_coverage, load_corpus_target
from .visualizations import CorpusVisualizationBuilder

logger = logging.getLogger(__name__)


class BlakeCorpus:
    def __init__(
        self,
        data_dir: Optional[Path] = None,
        *,
        output_dir: Optional[Path] = None,
        config: Optional[CorpusConfig] = None,
        source_registry: Optional[SourceRegistry] = None,
    ):
        self.config = config or CorpusConfig()
        if data_dir is not None:
            self.config.data_dir = Path(data_dir)
        if output_dir is not None:
            self.config.output_dir = Path(output_dir)

        self.data_dir = Path(self.config.data_dir)
        self.output_dir = Path(self.config.output_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.downloader = BlakeDownloader(self.data_dir)
        self.metadata_manager = MetadataManager(self.data_dir)
        self.analyzer = BlakeAnalyzer(self.data_dir)
        self.exporter = BlakeExporter(self.data_dir)
        self.source_registry = source_registry or build_default_source_registry(
            self.data_dir,
            sources=getattr(self.downloader, "sources", None),
            archive_scope=self.config.archive_scope,
        )

        self._works_cache: Dict[str, BlakeWork] = {}
        self._gui = None
        self._visualization = None
        self._initialized = False

        logger.info("Initialized BlakeCorpus with data directory %s", self.data_dir)

    @property
    def gui(self):
        if self._gui is None:
            from ..gui import BlakeGUI

            self._gui = BlakeGUI(self.data_dir, output_dir=self.output_dir)
        return self._gui

    @property
    def visualization(self):
        if self._visualization is None:
            from ..viz.integrations.blake_viz_integration import BlakeVizIntegration

            self._visualization = BlakeVizIntegration(self)
        return self._visualization

    def plan(self, config: Optional[CorpusConfig] = None) -> List[str]:
        cfg = config or self.config
        phases = [
            "discovery",
            "acquisition",
            "metadata",
            "analysis",
            "visualizations",
            "export",
            "reports",
        ]
        if cfg.quick or cfg.skip_download:
            phases[1] = "acquisition:skipped"
        if cfg.skip_analysis:
            phases[3] = "analysis:skipped"
        if cfg.skip_visualizations:
            phases[4] = "visualizations:skipped"
        if cfg.skip_export:
            phases[5] = "export:skipped"
        if cfg.skip_reports:
            phases[6] = "reports:skipped"
        return phases

    async def status(self) -> Dict[str, Any]:
        works = await self.get_all_works()
        target = load_corpus_target(self.config.target_profile)
        manifest = self._build_manifest(works, target, [], None, {}, False)
        return {
            "data_dir": str(self.data_dir),
            "output_dir": str(self.output_dir),
            "total_works": manifest.total_works,
            "total_images": manifest.total_images,
            "source_coverage": manifest.source_coverage,
            "target_profile": manifest.target_profile,
            "coverage_status": manifest.coverage_status,
            "coverage_counts": manifest.coverage_counts,
        }

    async def coverage(self) -> Dict[str, Any]:
        works = await self.get_all_works()
        target = load_corpus_target(self.config.target_profile)
        manifest = self._build_manifest(works, target, [], None, {}, False)
        return {
            "target_profile": manifest.target_profile,
            "target_version": manifest.target_version,
            "coverage_status": manifest.coverage_status,
            "coverage_counts": manifest.coverage_counts,
            "target_records": [
                record.model_dump(mode="json") for record in manifest.target_records
            ],
        }

    async def run(self, config: Optional[CorpusConfig] = None) -> CorpusRunSummary:
        cfg = config or self.config
        self.config = cfg
        self.data_dir = Path(cfg.data_dir)
        self.output_dir = Path(cfg.output_dir)
        self._prepare_output_dirs(self.output_dir)
        target = load_corpus_target(cfg.target_profile)
        archive_provider = self.source_registry.get(SourceType.BLAKE_ARCHIVE)
        if archive_provider and hasattr(archive_provider, "archive_scope"):
            setattr(archive_provider, "archive_scope", cfg.archive_scope)

        run_id = uuid4().hex
        started_at = datetime.now()
        phases: List[PhaseResult] = []
        artifacts: Dict[str, str] = {}
        records: List[SourceRecord] = []
        fixture_seeded = False

        discovery = PhaseResult(name="discovery")
        try:
            discovery_path = self.output_dir / "data" / "source_discovery.json"
            discovery_health_path = (
                self.output_dir / "data" / "source_discovery_health.json"
            )
            audit_path = self.output_dir / "data" / "source_audit.json"
            if cfg.quick:
                self._write_json(discovery_path, [])
                discovery_health = self._source_discovery_health_payload([])
                self._write_json(discovery_health_path, discovery_health)
                audit_payload = await build_source_audit(
                    target,
                    [],
                    include_live=False,
                    provider_discovery=[],
                    source_leads=self._source_leads(),
                )
                self._write_json(audit_path, audit_payload)
                artifacts["source_discovery"] = str(discovery_path)
                artifacts["source_discovery_health"] = str(discovery_health_path)
                artifacts["source_audit"] = str(audit_path)
                discovery.finish(
                    status="skipped",
                    message="Quick mode: live source discovery skipped",
                    items_processed=0,
                    artifacts={
                        "source_discovery": str(discovery_path),
                        "source_discovery_health": str(discovery_health_path),
                        "source_audit": str(audit_path),
                    },
                )
                phases.append(discovery)
            else:
                records = await self.source_registry.discover_all()
                discovery_health = self._source_discovery_health_payload(
                    self.source_registry.discovery_health()
                )
                self._write_json(
                    discovery_path,
                    [record.model_dump(mode="json") for record in records],
                )
                self._write_json(discovery_health_path, discovery_health)
                audit_payload = await self._build_source_audit_with_errors(
                    target,
                    records,
                    include_live=True,
                    provider_discovery=discovery_health["providers"],
                    archive_metadata_enrichment=(
                        self.source_registry.archive_metadata_enrichment()
                    ),
                    source_leads=self._source_leads(),
                )
                self._write_json(audit_path, audit_payload)
                artifacts["source_discovery"] = str(discovery_path)
                artifacts["source_discovery_health"] = str(discovery_health_path)
                artifacts["source_audit"] = str(audit_path)
                discovery.finish(
                    status="completed",
                    message=f"Discovered {len(records)} normalized source records",
                    items_processed=len(records),
                    artifacts={
                        "source_discovery": str(discovery_path),
                        "source_discovery_health": str(discovery_health_path),
                        "source_audit": str(audit_path),
                    },
                )
                phases.append(discovery)
        except Exception as exc:
            discovery.finish(status="error", message=str(exc), errors=[str(exc)])
            phases.append(discovery)

        acquisition = PhaseResult(name="acquisition")
        try:
            if cfg.quick:
                works, fixture_seeded = await self._ensure_quick_corpus(cfg)
                acquisition.finish(
                    status="completed" if fixture_seeded else "skipped",
                    message=(
                        "Quick mode: seeded deterministic fixture corpus"
                        if fixture_seeded
                        else "Quick mode: using existing local corpus"
                    ),
                    items_processed=len(works),
                    artifacts={"fixture_mode": str(fixture_seeded)},
                )
            elif cfg.skip_download:
                works = await self.get_all_works()
                acquisition.finish(
                    status="skipped",
                    message="Acquisition skipped: using existing local corpus",
                    items_processed=len(works),
                )
            else:
                report = await self._acquire_from_source_records(records, cfg)
                report_path = self.output_dir / "data" / "download_report.json"
                self._write_json(report_path, report)
                works = await self.get_all_works()
                acquisition.finish(
                    status="completed",
                    message="Acquisition completed",
                    items_processed=len(works),
                    artifacts={"download_report": str(report_path)},
                )
                artifacts["download_report"] = str(report_path)
        except Exception as exc:
            acquisition.finish(status="error", message=str(exc), errors=[str(exc)])
        phases.append(acquisition)

        metadata = PhaseResult(name="metadata")
        works = await self.get_all_works()
        manifest = self._build_manifest(
            works, target, records, run_id, artifacts, fixture_seeded
        )
        manifest_path = manifest.write_json(self.output_dir / "corpus_manifest.json")
        artifacts["corpus_manifest"] = str(manifest_path)
        metadata.finish(
            status="completed",
            message="Corpus manifest written",
            items_processed=len(works),
            artifacts={"corpus_manifest": str(manifest_path)},
        )
        phases.append(metadata)

        phases.append(await self._run_analysis_phase(cfg, works))
        works = await self.get_all_works()
        manifest = self._build_manifest(
            works, target, records, run_id, artifacts, fixture_seeded
        )
        manifest_path = manifest.write_json(self.output_dir / "corpus_manifest.json")
        phases.append(await self._run_visualization_phase(cfg, works, manifest))
        phases.append(await self._run_export_phase(cfg, works))
        phases.append(await self._run_report_phase(cfg, works, manifest))
        self._refresh_source_audit_missing_evidence(target, records, manifest)

        ended_at = datetime.now()
        status = (
            "error" if any(phase.status == "error" for phase in phases) else "completed"
        )
        summary = CorpusRunSummary(
            run_id=run_id,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=(ended_at - started_at).total_seconds(),
            phases=phases,
            manifest_path=manifest_path,
            output_dir=self.output_dir,
        )
        self._write_json(
            self.output_dir / "pipeline_summary.json", summary.model_dump(mode="json")
        )
        return summary

    async def audit_sources(
        self, *, include_live: bool = True, limit: int = 12
    ) -> Dict[str, Any]:
        self._prepare_output_dirs(self.output_dir)
        target = load_corpus_target(self.config.target_profile)
        archive_provider = self.source_registry.get(SourceType.BLAKE_ARCHIVE)
        if archive_provider and hasattr(archive_provider, "archive_scope"):
            setattr(archive_provider, "archive_scope", self.config.archive_scope)
        records = await self.source_registry.discover_all() if include_live else []
        discovery_path = self.output_dir / "data" / "source_discovery.json"
        discovery_health_path = self.output_dir / "data" / "source_discovery_health.json"
        discovery_health = self._source_discovery_health_payload(
            self.source_registry.discovery_health() if include_live else []
        )
        self._write_json(
            discovery_path, [record.model_dump(mode="json") for record in records]
        )
        self._write_json(discovery_health_path, discovery_health)
        works = await self.get_all_works()
        coverage_records, _, _ = build_target_coverage(target, works, records)
        payload = await self._build_source_audit_with_errors(
            target,
            records,
            include_live=include_live,
            limit=limit,
            coverage_records=coverage_records,
            provider_discovery=discovery_health["providers"],
            archive_metadata_enrichment=(
                self.source_registry.archive_metadata_enrichment()
            ),
            source_leads=self._source_leads(),
        )
        path = self.output_dir / "data" / "source_audit.json"
        self._write_json(path, payload)
        payload["path"] = str(path)
        payload["source_discovery_path"] = str(discovery_path)
        payload["source_discovery_health_path"] = str(discovery_health_path)
        return payload

    async def analyze(
        self, analysis_types: Optional[List[str]] = None
    ) -> List[AnalysisResult]:
        works = await self.get_all_works()
        records: List[AnalysisResult] = []
        for work in works:
            try:
                result = await self.analyze_work(work.id, analysis_types)
            except Exception as exc:
                logger.exception("Analysis failed for work %s", work.id)
                work.processing_errors.append(str(exc))
                result = {"error": str(exc)}
            records.append(
                AnalysisResult(
                    work_id=work.id,
                    analysis_type="corpus",
                    results=result,
                    metadata={"title": work.metadata.title},
                )
            )
        return records

    async def export(self, formats: Optional[List[str]] = None) -> Dict[str, str]:
        works = await self.get_all_works()
        exported: Dict[str, str] = {}
        for export_format in formats or self.config.export_formats:
            config = ExportConfig(
                format=export_format,
                output_dir=self.output_dir / "exports" / export_format,
                include_images=True,
                include_metadata=True,
                include_analysis=True,
            )
            path = await self.exporter.export_works(works, config)
            exported[export_format] = str(path)
        return exported

    async def initialize(self) -> None:
        self._initialized = True

    async def clear_cache(self) -> None:
        self._works_cache = {}

    async def _ensure_quick_corpus(
        self, cfg: CorpusConfig
    ) -> tuple[List[BlakeWork], bool]:
        works = await self.get_all_works()
        should_seed = cfg.fixture_mode == "always" or (
            cfg.fixture_mode == "auto" and not works
        )
        if not should_seed or cfg.fixture_mode == "never":
            return works, False

        fixture_works = build_fixture_works(self.data_dir)
        existing_ids = {work.id for work in works}
        for work in fixture_works:
            if work.id not in existing_ids:
                await self._save_corpus_work(work)
        await self.clear_cache()
        return await self.get_all_works(), True

    async def _acquire_from_source_records(
        self,
        records: List[SourceRecord],
        cfg: CorpusConfig,
    ) -> Dict[str, Any]:
        report: Dict[str, Any] = {
            "records_discovered": len(records),
            "records_fetched": 0,
            "works_saved": 0,
            "stale_works_pruned": [],
            "records_unfetched": [],
            "errors": [],
        }
        report["stale_works_pruned"] = await self._prune_stale_local_works(records)

        for record in records:
            try:
                source_type = (
                    record.source_type
                    if isinstance(record.source_type, SourceType)
                    else SourceType(str(record.source_type))
                )
            except ValueError:
                report["records_unfetched"].append(
                    {
                        "stable_id": record.stable_id,
                        "reason": f"Unknown source type {record.source_type}",
                    }
                )
                continue
            provider = self.source_registry.get(source_type)
            if not provider:
                report["records_unfetched"].append(
                    {"stable_id": record.stable_id, "reason": "No provider registered"}
                )
                continue
            try:
                work = await provider.fetch(
                    record,
                    force=cfg.force,
                    image_mode=cfg.image_mode,
                    image_dpi=cfg.image_dpi,
                    max_images_per_work=cfg.max_images_per_work,
                )
            except Exception as exc:
                report["errors"].append(
                    {"stable_id": record.stable_id, "error": str(exc)}
                )
                continue

            report["records_fetched"] += 1
            if not work:
                report["records_unfetched"].append(
                    {
                        "stable_id": record.stable_id,
                        "reason": "Provider returned no work",
                    }
                )
                continue

            if not work.metadata.source_id:
                work.metadata.source_id = record.source_id
            if not work.metadata.source_url:
                work.metadata.source_url = record.source_url
            await self._save_corpus_work(work, process=True)
            report["works_saved"] += 1

        await self.clear_cache()
        return report

    async def _prune_stale_local_works(
        self, records: List[SourceRecord]
    ) -> List[str]:
        keep_ids = {
            str(record.source_id)
            for record in records
            if str(record.source_id or "").strip()
        }
        keep_ids.update(
            str(record.metadata.get("target_id"))
            for record in records
            if str(record.metadata.get("target_id") or "").strip()
        )
        marker_dir = self.data_dir / "metadata" / FALLBACK_VALIDATION_DIR
        if marker_dir.exists():
            keep_ids.update(path.stem for path in marker_dir.glob("*.json"))
        if not keep_ids:
            return []

        pruned: List[str] = []
        for work in await self.metadata_manager.load_all_works():
            if work.id in keep_ids:
                continue
            if await self.metadata_manager.delete_work(work.id):
                self._works_cache.pop(work.id, None)
                pruned.append(work.id)
        return sorted(pruned)

    async def _build_source_audit_with_errors(
        self,
        target: CorpusTarget,
        records: List[SourceRecord],
        *,
        include_live: bool,
        limit: int = 12,
        coverage_records: Optional[List[CorpusCoverageRecord]] = None,
        provider_discovery: Optional[List[Dict[str, Any]]] = None,
        archive_metadata_enrichment: Optional[Dict[str, Any]] = None,
        source_leads: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        try:
            return await build_source_audit(
                target,
                records,
                include_live=include_live,
                limit=limit,
                coverage_records=coverage_records or (),
                provider_discovery=provider_discovery or [],
                archive_metadata_enrichment=archive_metadata_enrichment or {},
                source_leads=source_leads or [],
            )
        except Exception as exc:
            return {
                "generated_at": datetime.now().isoformat(),
                "target_profile": target.profile,
                "target_version": target.version,
                "target_total": target.total,
                "records_discovered": len(records),
                "status": "error",
                "errors": [str(exc)],
            }

    def _refresh_source_audit_missing_evidence(
        self,
        target: CorpusTarget,
        records: List[SourceRecord],
        manifest: CorpusManifest,
    ) -> None:
        path = self.output_dir / "data" / "source_audit.json"
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        attach_missing_evidence(
            payload,
            target,
            records,
            manifest.target_records,
            source_leads=self._source_leads(),
        )
        self._write_json(path, payload)

    async def _save_corpus_work(
        self, work: BlakeWork, *, process: bool = False
    ) -> BlakeWork:
        apply_validated_fallback_marker(self.data_dir, work)
        if work.text_content:
            texts_dir = self.data_dir / "texts"
            texts_dir.mkdir(parents=True, exist_ok=True)
            (texts_dir / f"{work.id}.txt").write_text(
                work.text_content, encoding="utf-8"
            )

        saved = await self.metadata_manager.process_work(work) if process else work
        if not process:
            await self.metadata_manager.save_work(saved)
        marker_applied = apply_validated_fallback_marker(self.data_dir, saved)
        if process and marker_applied:
            await self.metadata_manager.save_work(saved)
        self._works_cache[saved.id] = saved
        return saved

    def _build_manifest(
        self,
        works: List[BlakeWork],
        target: CorpusTarget,
        source_records: List[SourceRecord],
        run_id: Optional[str],
        artifacts: Dict[str, str],
        fixture_mode: bool,
    ) -> CorpusManifest:
        for work in works:
            apply_validated_fallback_marker(self.data_dir, work)
        target_records, coverage_counts, coverage_status = build_target_coverage(
            target,
            works,
            source_records,
        )
        fixture_work_ids = [
            work.id
            for work in works
            if getattr(work.metadata, "api_source", None) == "fixture"
            or work.id.startswith("fixture-")
        ]
        return CorpusManifest.from_works(
            works,
            data_dir=self.data_dir,
            output_dir=self.output_dir,
            run_id=run_id,
            artifacts=artifacts,
            target_profile=target.profile,
            target_version=target.version,
            target_records=target_records,
            coverage_status=coverage_status,
            coverage_counts=coverage_counts,
            fixture_mode=fixture_mode or bool(fixture_work_ids),
            fixture_work_ids=fixture_work_ids,
        )

    async def download_all(self, force: bool = False) -> List[BlakeWork]:
        works = await self.downloader.download_all(force=force)
        for work in works:
            await self._save_corpus_work(work, process=True)
            self._works_cache[work.id] = work
        return works

    async def download_work(
        self, work_id: str, force: bool = False
    ) -> Optional[BlakeWork]:
        work = await self.downloader.download_work(work_id, force=force)
        if work:
            await self._save_corpus_work(work, process=True)
            self._works_cache[work.id] = work
        return work

    async def analyze_work(
        self, work_id: str, analysis_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        work = await self.get_work(work_id)
        if not work:
            raise BlakeError(f"Work {work_id} not found")

        results = await self.analyzer.analyze_work(work, analysis_types)
        work.text_analysis.update(results.get("text_analysis", {}))
        work.visual_analysis.update(results.get("visual_analysis", {}))
        work.cross_analysis.update(results.get("cross_analysis", {}))
        work.fully_processed = True
        work.metadata.processed = True
        await self.metadata_manager.save_work(work)
        self._works_cache[work.id] = work
        return results

    async def analyze_all(
        self, analysis_types: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        results: Dict[str, Dict[str, Any]] = {}
        for work in await self.get_all_works():
            results[work.id] = await self.analyze_work(work.id, analysis_types)
        return results

    async def get_work(self, work_id: str) -> Optional[BlakeWork]:
        if work_id in self._works_cache:
            return self._works_cache[work_id]
        work = await self.metadata_manager.load_work(work_id)
        if work:
            apply_validated_fallback_marker(self.data_dir, work)
            self._works_cache[work_id] = work
        return work

    async def get_all_works(self) -> List[BlakeWork]:
        works = await self.metadata_manager.load_all_works()
        for work in works:
            apply_validated_fallback_marker(self.data_dir, work)
            self._works_cache[work.id] = work
        return works

    async def search_works(
        self, query: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[BlakeWork]:
        return await self.metadata_manager.search_works(query, filters)

    def explore(self, host: str = "localhost", port: int = 8501) -> None:
        self.gui.run(host=host, port=port)

    async def export_works(self, *args: Any, **kwargs: Any) -> Path:
        if args and isinstance(args[0], list):
            works = args[0]
            config = args[1] if len(args) > 1 else kwargs.get("config")
        else:
            works = await self.get_all_works()
            config = args[0] if args else kwargs.get("config")

        if config is None:
            config = ExportConfig(format="json", output_dir=self.output_dir / "exports")
        if config.filter_works:
            works = [work for work in works if work.id in config.filter_works]
        return await self.exporter.export_works(works, config)

    async def get_statistics(self) -> Dict[str, Any]:
        works = await self.get_all_works()
        stats: Dict[str, Any] = {
            "total_works": len(works),
            "work_types": {},
            "sources": {},
            "date_range": {},
            "total_images": 0,
            "processed_works": 0,
        }
        dates = []
        for work in works:
            work_type = str(work.metadata.work_type)
            source = str(work.metadata.source)
            stats["work_types"][work_type] = stats["work_types"].get(work_type, 0) + 1
            stats["sources"][source] = stats["sources"].get(source, 0) + 1
            stats["total_images"] += len(work.images)
            if work.fully_processed or work.metadata.processed:
                stats["processed_works"] += 1
            if work.metadata.creation_date:
                dates.append(work.metadata.creation_date)
        if dates:
            stats["date_range"] = {
                "earliest": min(dates).isoformat(),
                "latest": max(dates).isoformat(),
            }
        return stats

    async def create_visualization(
        self,
        viz_type: str,
        data_type: str = "all",
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return await self.visualization.create_visualization(
            viz_type, data_type, config
        )

    async def visualize(
        self,
        profile: Optional[str] = None,
        *,
        works: Optional[List[BlakeWork]] = None,
        manifest: Optional[CorpusManifest] = None,
    ) -> Dict[str, Any]:
        works = works if works is not None else await self.get_all_works()
        if manifest is None:
            target = load_corpus_target(self.config.target_profile)
            manifest = self._build_manifest(works, target, [], None, {}, False)
        try:
            available = await self.get_available_visualizations()
        except Exception as exc:
            available = []
            logger.warning("Unable to enumerate visualizations: %s", exc)
        builder = CorpusVisualizationBuilder(self.output_dir)
        return builder.generate(
            works,
            manifest,
            profile=profile or self.config.viz_profile,
            available_visualizations=available,
        )

    async def create_research_dashboard(self) -> Dict[str, Any]:
        return await self.visualization.create_research_dashboard()

    async def create_educational_dashboard(self) -> Dict[str, Any]:
        return await self.visualization.create_educational_dashboard()

    async def create_public_dashboard(self) -> Dict[str, Any]:
        return await self.visualization.create_public_dashboard()

    async def generate_research_report(
        self, focus: str = "comprehensive"
    ) -> Dict[str, Any]:
        return await self.visualization.generate_research_report(focus)

    async def generate_educational_report(
        self, level: str = "intermediate"
    ) -> Dict[str, Any]:
        return await self.visualization.generate_educational_report(level)

    async def generate_public_report(self) -> Dict[str, Any]:
        return await self.visualization.generate_public_report()

    async def get_available_visualizations(self) -> List[Dict[str, Any]]:
        return await self.visualization.get_available_visualizations()

    async def get_dashboard_summary(self) -> Dict[str, Any]:
        return await self.visualization.get_dashboard_summary()

    async def get_visualization_statistics(self) -> Dict[str, Any]:
        return await self.visualization.get_visualization_statistics()

    def _prepare_output_dirs(self, output_dir: Path) -> None:
        for name in [
            "data",
            "analysis",
            "visualizations",
            "exports",
            "reports",
            "logs",
        ]:
            (output_dir / name).mkdir(parents=True, exist_ok=True)

    def _analysis_types_for_summary(
        self, analysis_types: Optional[List[str]]
    ) -> List[str]:
        return list(analysis_types or ["text", "visual", "cross", "ontology"])

    def _analysis_eligibility(self, works: List[BlakeWork]) -> Dict[str, int]:
        return {
            "text": sum(1 for work in works if bool(work.text_content)),
            "visual": sum(1 for work in works if bool(work.images)),
            "cross": sum(1 for work in works if bool(work.text_content and work.images)),
            "ontology": len(works),
        }

    def _analysis_result_status(
        self, records: List[AnalysisResult]
    ) -> tuple[Dict[str, Counter[str]], list[Dict[str, str]], Counter[str]]:
        key_to_type = {
            "text_analysis": "text",
            "visual_analysis": "visual",
            "cross_analysis": "cross",
            "ontological_analysis": "ontology",
        }
        status: Dict[str, Counter[str]] = defaultdict(Counter)
        result_type_counts: Counter[str] = Counter()
        errors: list[Dict[str, str]] = []
        for record in records:
            title = str(record.metadata.get("title") or "")
            results = record.results or {}
            if "error" in results:
                status["work"]["errors"] += 1
                errors.append(
                    {
                        "work_id": record.work_id,
                        "title": title,
                        "analysis_type": "work",
                        "error": str(results.get("error"))[:500],
                    }
                )
                continue
            for result_key, result_value in results.items():
                analysis_type = key_to_type.get(result_key, result_key)
                result_type_counts[analysis_type] += 1
                if isinstance(result_value, dict) and result_value.get("error"):
                    status[analysis_type]["errors"] += 1
                    errors.append(
                        {
                            "work_id": record.work_id,
                            "title": title,
                            "analysis_type": analysis_type,
                            "error": str(result_value.get("error"))[:500],
                        }
                    )
                else:
                    status[analysis_type]["completed"] += 1
        return status, errors, result_type_counts

    def _analysis_summary_payload(
        self,
        *,
        status: str,
        works: List[BlakeWork],
        records: List[AnalysisResult],
        requested_types: List[str],
        results_path: Path,
        diagnostics_path: Path,
        notes: list[str],
        current: bool,
    ) -> Dict[str, Any]:
        eligibility = self._analysis_eligibility(works)
        result_status, errors, result_type_counts = self._analysis_result_status(records)
        per_analysis = {}
        for analysis_type in requested_types:
            eligible = int(eligibility.get(analysis_type, 0))
            completed = int(result_status[analysis_type].get("completed", 0))
            error_count = int(result_status[analysis_type].get("errors", 0))
            per_analysis[analysis_type] = {
                "eligible": eligible,
                "completed": completed,
                "errors": error_count,
                "not_applicable": max(len(works) - eligible, 0),
                "not_completed": max(eligible - completed - error_count, 0),
            }
        artifacts = {"analysis_summary": str(self.output_dir / "analysis" / "analysis_summary.json")}
        if results_path.exists() or current:
            artifacts["analysis_results"] = str(results_path)
        if diagnostics_path.exists() or current:
            artifacts["analysis_diagnostics"] = str(diagnostics_path)
        return {
            "schema_version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "status": status,
            "analysis_results_current": current,
            "works_total": len(works),
            "works_analyzed": len(records) if current else 0,
            "requested_analysis_types": requested_types,
            "analysis_types": requested_types,
            "analysis_type_counts": dict(sorted(result_type_counts.items())),
            "per_analysis": per_analysis,
            "error_count": len(errors),
            "error_ledger": errors,
            "artifact_paths": artifacts,
            "analysis_results": str(results_path) if current else None,
            "stale_analysis_results": str(results_path) if not current and results_path.exists() else None,
            "notes": notes,
        }

    def _numeric_summary(self, values: List[float]) -> Dict[str, Any]:
        cleaned = sorted(float(value) for value in values if value is not None)
        if not cleaned:
            return {"count": 0, "min": 0, "median": 0, "mean": 0, "max": 0, "iqr": 0}
        count = len(cleaned)

        def percentile(pct: float) -> float:
            if count == 1:
                return cleaned[0]
            pos = (count - 1) * pct
            lower = int(pos)
            upper = min(lower + 1, count - 1)
            weight = pos - lower
            return cleaned[lower] * (1 - weight) + cleaned[upper] * weight

        q1 = percentile(0.25)
        q2 = percentile(0.5)
        q3 = percentile(0.75)
        return {
            "count": count,
            "min": round(cleaned[0], 4),
            "median": round(q2, 4),
            "mean": round(sum(cleaned) / count, 4),
            "max": round(cleaned[-1], 4),
            "iqr": round(q3 - q1, 4),
        }

    def _as_float(self, value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _analysis_error_categories(
        self, errors: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        categories: Counter[str] = Counter()
        for row in errors:
            detail = str(row.get("error") or "").lower()
            if "timeout" in detail or "timed out" in detail:
                categories["timeout"] += 1
            elif "memory" in detail:
                categories["resource"] += 1
            elif "missing" in detail or "not found" in detail:
                categories["missing_input"] += 1
            elif "parse" in detail or "decode" in detail:
                categories["parse_failure"] += 1
            elif detail:
                categories["analysis_error"] += 1
            else:
                categories["unknown"] += 1
        return dict(sorted(categories.items()))

    def _analysis_diagnostics_summary(
        self,
        works: List[BlakeWork],
        records: List[AnalysisResult],
        requested_types: List[str],
        result_status: Dict[str, Counter[str]],
        errors: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        eligibility = self._analysis_eligibility(works)
        per_analysis: Dict[str, Dict[str, int]] = {}
        for analysis_type in requested_types:
            eligible = int(eligibility.get(analysis_type, 0))
            completed = int(result_status[analysis_type].get("completed", 0))
            error_count = int(result_status[analysis_type].get("errors", 0))
            per_analysis[analysis_type] = {
                "eligible_works": eligible,
                "analyzed_works": completed,
                "error_count": error_count,
                "skipped_works": max(eligible - completed - error_count, 0),
                "not_applicable_works": max(len(works) - eligible, 0),
            }
        return {
            "works_total": len(works),
            "works_with_results": len(records),
            "fully_processed_works": sum(1 for work in works if work.fully_processed),
            "requested_analysis_types": requested_types,
            "per_analysis": per_analysis,
            "error_count": len(errors),
            "error_categories": self._analysis_error_categories(errors),
        }

    def _build_analysis_diagnostics(
        self,
        works: List[BlakeWork],
        records: List[AnalysisResult],
        requested_types: List[str],
    ) -> Dict[str, Any]:
        result_by_id = {record.work_id: record.results or {} for record in records}
        result_status, errors, _type_counts = self._analysis_result_status(records)
        word_counts: list[float] = []
        ttr_values: list[float] = []
        flesch_values: list[float] = []
        sentence_lengths: list[float] = []
        theme_counts: Counter[str] = Counter()
        theme_docs: Counter[str] = Counter()
        text_outliers = []
        image_counts = [len(work.images) for work in works]
        missing_image_paths = 0
        brightness_values: list[float] = []
        contrast_values: list[float] = []
        texture_values: list[float] = []
        symmetry_values: list[float] = []
        contour_values: list[float] = []
        visual_work_rows = []
        jaccard_values: list[float] = []
        harmony_values: list[float] = []
        entity_counts: Counter[str] = Counter()
        concept_counts: Counter[str] = Counter()
        graph_densities: list[float] = []
        ontology_empty = 0
        relationship_total = 0

        for work in works:
            results = result_by_id.get(work.id, {})
            text_result = results.get("text_analysis") or {}
            if work.text_content:
                fallback_words = len(str(work.text_content).split())
                basic_stats = text_result.get("basic_stats") if isinstance(text_result, dict) else {}
                word_count = int(basic_stats.get("word_count") or fallback_words)
                word_counts.append(float(word_count))
                lexical = text_result.get("lexical_diversity") if isinstance(text_result, dict) else {}
                ttr = self._as_float(lexical.get("ttr") if isinstance(lexical, dict) else None)
                if ttr is None:
                    ttr = self._as_float(basic_stats.get("vocabulary_richness"))
                if ttr is not None:
                    ttr_values.append(ttr)
                readability = text_result.get("readability") if isinstance(text_result, dict) else {}
                flesch = self._as_float(readability.get("flesch_reading_ease") if isinstance(readability, dict) else None)
                if flesch is not None:
                    flesch_values.append(flesch)
                sent_len = self._as_float(
                    (readability or basic_stats).get("avg_sentence_length")
                    if isinstance(readability or basic_stats, dict)
                    else None
                )
                if sent_len is not None:
                    sentence_lengths.append(sent_len)
                themes = text_result.get("themes") if isinstance(text_result, dict) else {}
                seen_themes = set()
                for item in themes.get("themes", []) if isinstance(themes, dict) else []:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        theme = str(item[0])
                        count = int(item[1] or 0)
                        theme_counts[theme] += count
                        seen_themes.add(theme)
                theme_docs.update(seen_themes)
                text_outliers.append(
                    {
                        "work_id": work.id,
                        "title": work.metadata.title,
                        "word_count": word_count,
                        "image_count": len(work.images),
                    }
                )
            for image in work.images:
                if not image.file_path or not Path(image.file_path).exists():
                    missing_image_paths += 1
            visual_result = results.get("visual_analysis") or {}
            analyzed_images = 0
            if isinstance(visual_result, dict):
                for image_result in visual_result.values():
                    if not isinstance(image_result, dict) or image_result.get("error"):
                        continue
                    analyzed_images += 1
                    style = image_result.get("style") or {}
                    composition = image_result.get("composition") or {}
                    texture = image_result.get("texture") or {}
                    shapes = image_result.get("shapes") or {}
                    for target, key, values in [
                        (style, "brightness", brightness_values),
                        (style, "contrast", contrast_values),
                        (texture, "texture_energy", texture_values),
                        (composition, "symmetry_score", symmetry_values),
                        (shapes, "num_contours", contour_values),
                    ]:
                        value = self._as_float(target.get(key) if isinstance(target, dict) else None)
                        if value is not None:
                            values.append(value)
            if work.images:
                visual_work_rows.append(
                    {
                        "work_id": work.id,
                        "title": work.metadata.title,
                        "image_count": len(work.images),
                        "analyzed_images": analyzed_images,
                    }
                )
            cross_result = results.get("cross_analysis") or {}
            if isinstance(cross_result, dict):
                correlation = cross_result.get("text_image_correlation") or {}
                harmony = cross_result.get("visual_textual_harmony") or {}
                jaccard = self._as_float(correlation.get("jaccard_similarity") if isinstance(correlation, dict) else None)
                if jaccard is not None:
                    jaccard_values.append(jaccard)
                harmony_score = self._as_float(harmony.get("harmony_score") if isinstance(harmony, dict) else None)
                if harmony_score is not None:
                    harmony_values.append(harmony_score)
            ontology = results.get("ontological_analysis") or {}
            if isinstance(ontology, dict):
                entities = ontology.get("entities") or []
                concepts = ontology.get("concepts") or []
                relationships = ontology.get("relationships") or []
                if not entities and not concepts and not relationships:
                    ontology_empty += 1
                for entity in entities:
                    if isinstance(entity, dict):
                        entity_counts[str(entity.get("text") or "")] += int(entity.get("mention_count") or 1)
                for concept in concepts:
                    if isinstance(concept, dict):
                        concept_counts[str(concept.get("name") or concept.get("text") or "")] += int(concept.get("count") or 1)
                    else:
                        concept_counts[str(concept)] += 1
                relationship_total += len(relationships)
                density = self._as_float((ontology.get("graph_stats") or {}).get("density"))
                if density is not None:
                    graph_densities.append(density)

        text_total_words = int(sum(word_counts))
        top_themes = [
            {
                "theme": theme,
                "count": int(count),
                "document_frequency": int(theme_docs.get(theme, 0)),
                "hits_per_1000_words": round((count / text_total_words) * 1000, 4)
                if text_total_words
                else 0,
            }
            for theme, count in theme_counts.most_common(20)
        ]
        text_outliers = sorted(
            text_outliers, key=lambda row: row["word_count"], reverse=True
        )[:12]
        visual_work_rows = sorted(
            visual_work_rows, key=lambda row: row["image_count"], reverse=True
        )[:12]
        text_work_count = sum(1 for work in works if work.text_content)
        image_work_count = sum(1 for work in works if work.images)
        cross_eligible = sum(1 for work in works if work.text_content and work.images)
        zero_image_text_works = sum(1 for work in works if work.text_content and not work.images)
        image_rich_text_works = sum(1 for work in works if work.text_content and len(work.images) >= 10)
        fully_processed = sum(1 for work in works if work.fully_processed)
        return {
            "schema_version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "requested_analysis_types": requested_types,
            "summary": self._analysis_diagnostics_summary(
                works, records, requested_types, result_status, errors
            ),
            "completion": {
                "works_total": len(works),
                "works_with_results": len(records),
                "fully_processed_works": fully_processed,
                "processed_pct": round((fully_processed / len(works)) * 100, 2)
                if works
                else 0,
                "by_analysis": {
                    key: dict(counter) for key, counter in sorted(result_status.items())
                },
            },
            "text": {
                "eligible_works": text_work_count,
                "analyzed_works": int(result_status["text"].get("completed", 0)),
                "total_words": text_total_words,
                "word_count_summary": self._numeric_summary(word_counts),
                "lexical_diversity_summary": self._numeric_summary(ttr_values),
                "readability_flesch_summary": self._numeric_summary(flesch_values),
                "sentence_length_summary": self._numeric_summary(sentence_lengths),
                "top_themes": top_themes,
                "largest_text_works": text_outliers,
            },
            "visual": {
                "eligible_works": image_work_count,
                "works_with_visual_results": int(result_status["visual"].get("completed", 0)),
                "total_images": int(sum(image_counts)),
                "missing_image_paths": missing_image_paths,
                "image_count_summary": self._numeric_summary([float(value) for value in image_counts]),
                "brightness_summary": self._numeric_summary(brightness_values),
                "contrast_summary": self._numeric_summary(contrast_values),
                "texture_energy_summary": self._numeric_summary(texture_values),
                "symmetry_summary": self._numeric_summary(symmetry_values),
                "contour_count_summary": self._numeric_summary(contour_values),
                "image_rich_works": visual_work_rows,
            },
            "cross_modal": {
                "eligible_works": cross_eligible,
                "analyzed_works": int(result_status["cross"].get("completed", 0)),
                "zero_image_text_works": zero_image_text_works,
                "image_rich_text_works_10_plus_images": image_rich_text_works,
                "jaccard_similarity_summary": self._numeric_summary(jaccard_values),
                "harmony_score_summary": self._numeric_summary(harmony_values),
            },
            "ontology": {
                "eligible_works": len(works),
                "analyzed_works": int(result_status["ontology"].get("completed", 0)),
                "empty_ontology_works": ontology_empty,
                "entity_total": int(sum(entity_counts.values())),
                "relationship_total": relationship_total,
                "top_entities": [
                    {"entity": entity, "count": int(count)}
                    for entity, count in entity_counts.most_common(20)
                    if entity
                ],
                "top_concepts": [
                    {"concept": concept, "count": int(count)}
                    for concept, count in concept_counts.most_common(20)
                    if concept
                ],
                "graph_density_summary": self._numeric_summary(graph_densities),
            },
            "errors": {
                "error_count": len(errors),
                "error_ledger": errors,
            },
        }

    async def _run_analysis_phase(
        self, cfg: CorpusConfig, works: List[BlakeWork]
    ) -> PhaseResult:
        phase = PhaseResult(name="analysis")
        summary_path = self.output_dir / "analysis" / "analysis_summary.json"
        results_path = self.output_dir / "analysis" / "analysis_results.json"
        diagnostics_path = self.output_dir / "analysis" / "analysis_diagnostics.json"
        requested_types = self._analysis_types_for_summary(cfg.analysis_types)

        if cfg.skip_analysis:
            summary = self._analysis_summary_payload(
                status="skipped",
                works=works,
                records=[],
                requested_types=requested_types,
                results_path=results_path,
                diagnostics_path=diagnostics_path,
                notes=[
                    "Analysis was skipped for this run.",
                    "Any existing analysis_results.json is stale relative to this pipeline summary.",
                ],
                current=False,
            )
            diagnostics = {
                "schema_version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "status": "skipped",
                "analysis_results_current": False,
                "works_total": len(works),
                "summary": self._analysis_diagnostics_summary(
                    works,
                    [],
                    requested_types,
                    self._analysis_result_status([])[0],
                    [],
                ),
                "notes": summary["notes"],
            }
            self._write_json(summary_path, summary)
            self._write_json(diagnostics_path, diagnostics)
            return phase.finish(
                status="skipped",
                message="Analysis skipped",
                artifacts={
                    "analysis_summary": str(summary_path),
                    "analysis_diagnostics": str(diagnostics_path),
                },
            )

        if not works:
            records: List[AnalysisResult] = []
            diagnostics = self._build_analysis_diagnostics(
                works, records, requested_types
            )
            diagnostics["status"] = "skipped"
            summary = self._analysis_summary_payload(
                status="skipped",
                works=works,
                records=records,
                requested_types=requested_types,
                results_path=results_path,
                diagnostics_path=diagnostics_path,
                notes=["No works were available for analysis."],
                current=True,
            )
            self._write_json(summary_path, summary)
            self._write_json(results_path, [])
            self._write_json(diagnostics_path, diagnostics)
            return phase.finish(
                status="skipped",
                message="No works to analyze",
                artifacts={
                    "analysis_summary": str(summary_path),
                    "analysis_results": str(results_path),
                    "analysis_diagnostics": str(diagnostics_path),
                },
            )

        records = await self.analyze(cfg.analysis_types)
        record_payloads = [record.model_dump(mode="json") for record in records]
        self._write_json(results_path, record_payloads)
        refreshed_works = await self.get_all_works()
        diagnostics = self._build_analysis_diagnostics(
            refreshed_works, records, requested_types
        )
        diagnostics["status"] = "completed"
        summary = self._analysis_summary_payload(
            status="completed",
            works=refreshed_works,
            records=records,
            requested_types=requested_types,
            results_path=results_path,
            diagnostics_path=diagnostics_path,
            notes=[
                "Local-only analysis completed over the saved corpus.",
                "Downloads were not required for this analysis phase.",
            ],
            current=True,
        )
        self._write_json(summary_path, summary)
        self._write_json(diagnostics_path, diagnostics)
        return phase.finish(
            status="completed",
            message=f"Analyzed {len(records)} works",
            items_processed=len(records),
            artifacts={
                "analysis_summary": str(summary_path),
                "analysis_results": str(results_path),
                "analysis_diagnostics": str(diagnostics_path),
            },
        )

    async def _run_visualization_phase(
        self,
        cfg: CorpusConfig,
        works: List[BlakeWork],
        manifest: CorpusManifest,
    ) -> PhaseResult:
        phase = PhaseResult(name="visualizations")
        summary_path = self.output_dir / "visualizations" / "visualization_summary.json"

        if cfg.skip_visualizations:
            summary = {
                "status": "skipped",
                "message": "Visualization rendering skipped",
                "works_available": len(works),
            }
            self._write_json(summary_path, summary)
            return phase.finish(
                status="skipped",
                message=summary["message"],
                artifacts={"visualization_summary": str(summary_path)},
            )

        summary = await self.visualize(cfg.viz_profile, works=works, manifest=manifest)
        return phase.finish(
            status="completed",
            message=f"Generated {summary['profile']} corpus visualization artifacts",
            items_processed=summary.get("visualizations_generated", 0),
            artifacts=summary.get(
                "artifacts", {"visualization_summary": str(summary_path)}
            ),
        )

    async def _run_export_phase(
        self, cfg: CorpusConfig, works: List[BlakeWork]
    ) -> PhaseResult:
        phase = PhaseResult(name="export")
        summary_path = self.output_dir / "exports" / "export_summary.json"

        if cfg.skip_export:
            self._write_json(summary_path, {"status": "skipped", "formats": []})
            return phase.finish(
                status="skipped",
                message="Export skipped",
                artifacts={"export_summary": str(summary_path)},
            )

        exported: Dict[str, str] = {}
        errors: List[str] = []
        for export_format in cfg.export_formats:
            try:
                config = ExportConfig(
                    format=export_format,
                    output_dir=self.output_dir / "exports" / export_format,
                    include_images=True,
                    include_metadata=True,
                    include_analysis=True,
                )
                exported[export_format] = str(
                    await self.exporter.export_works(works, config)
                )
            except Exception as exc:
                message = f"{export_format}: {exc}"
                errors.append(message)
                logger.warning("Export failed for %s: %s", export_format, exc)

        summary = {
            "status": "completed" if not errors else "partial",
            "formats": list(exported.keys()),
            "exports": exported,
            "errors": errors,
        }
        self._write_json(summary_path, summary)
        return phase.finish(
            status="completed" if not errors else "error",
            message=(
                "Export phase completed" if not errors else "One or more exports failed"
            ),
            items_processed=len(exported),
            artifacts={"export_summary": str(summary_path), **exported},
            errors=errors,
        )

    async def _run_report_phase(
        self,
        cfg: CorpusConfig,
        works: List[BlakeWork],
        manifest: CorpusManifest,
    ) -> PhaseResult:
        phase = PhaseResult(name="reports")
        if cfg.skip_reports:
            return phase.finish(status="skipped", message="Reports skipped")

        reports_dir = self.output_dir / "reports"
        stats_path = reports_dir / "statistics.json"
        completeness_path = reports_dir / "completeness_report.json"
        coverage_path = reports_dir / "source_coverage.json"
        provenance_path = reports_dir / "provenance_manifest.json"
        chronology_path = reports_dir / "chronology.json"
        network_path = reports_dir / "theme_entity_network.json"
        linkage_path = reports_dir / "text_image_linkage.json"
        report_md_path = reports_dir / "corpus_report.md"

        stats = await self.get_statistics()
        completeness = self._build_completeness_report(works, manifest)
        coverage = {
            "target_profile": manifest.target_profile,
            "target_version": manifest.target_version,
            "coverage_status": manifest.coverage_status,
            "coverage_counts": manifest.coverage_counts,
            "target_records": [
                record.model_dump(mode="json") for record in manifest.target_records
            ],
            "source_coverage": manifest.source_coverage,
            "registered_sources": self.source_registry.coverage(),
        }
        provenance = self._build_provenance_manifest(works)
        chronology = self._build_chronology(works)
        network = self._build_theme_entity_network(works)
        linkage = self._build_text_image_linkage(works)

        self._write_json(stats_path, stats)
        self._write_json(completeness_path, completeness)
        self._write_json(coverage_path, coverage)
        self._write_json(provenance_path, provenance)
        self._write_json(chronology_path, chronology)
        self._write_json(network_path, network)
        self._write_json(linkage_path, linkage)
        report_md_path.write_text(
            self._build_markdown_report(manifest, stats, completeness), encoding="utf-8"
        )

        artifacts = {
            "statistics": str(stats_path),
            "completeness_report": str(completeness_path),
            "source_coverage": str(coverage_path),
            "provenance_manifest": str(provenance_path),
            "chronology": str(chronology_path),
            "theme_entity_network": str(network_path),
            "text_image_linkage": str(linkage_path),
            "corpus_report": str(report_md_path),
        }
        return phase.finish(
            status="completed",
            message="Corpus reports written",
            items_processed=len(artifacts),
            artifacts=artifacts,
        )

    def _build_completeness_report(
        self, works: List[BlakeWork], manifest: CorpusManifest
    ) -> Dict[str, Any]:
        total = len(works)
        with_text = sum(1 for work in works if work.text_content)
        with_images = sum(1 for work in works if work.images)
        processed = sum(
            1 for work in works if work.fully_processed or work.metadata.processed
        )
        return {
            "target_profile": manifest.target_profile,
            "target_version": manifest.target_version,
            "target_total": manifest.target_total,
            "coverage_status": manifest.coverage_status,
            "coverage_counts": manifest.coverage_counts,
            "fixture_mode": manifest.fixture_mode,
            "total_works": total,
            "with_text": with_text,
            "with_images": with_images,
            "processed": processed,
            "text_coverage": with_text / total if total else 0.0,
            "image_coverage": with_images / total if total else 0.0,
            "processing_coverage": processed / total if total else 0.0,
        }

    def _build_provenance_manifest(
        self, works: List[BlakeWork]
    ) -> List[Dict[str, Any]]:
        return [
            {
                "id": work.id,
                "title": work.metadata.title,
                "source": str(work.metadata.source),
                "source_id": work.metadata.source_id,
                "source_url": work.metadata.source_url,
                "license_type": str(work.metadata.license_type),
                "attribution": work.metadata.attribution,
                "image_sources": [
                    image.original_url for image in work.images if image.original_url
                ],
            }
            for work in works
        ]

    def _build_chronology(self, works: List[BlakeWork]) -> List[Dict[str, Any]]:
        rows = []
        for work in works:
            date_value = work.metadata.creation_date or work.metadata.publication_date
            rows.append(
                {
                    "id": work.id,
                    "title": work.metadata.title,
                    "date": date_value.isoformat() if date_value else None,
                    "work_type": str(work.metadata.work_type),
                    "source": str(work.metadata.source),
                }
            )
        return sorted(rows, key=lambda row: row["date"] or "9999")

    def _build_theme_entity_network(self, works: List[BlakeWork]) -> Dict[str, Any]:
        nodes: Dict[str, Dict[str, Any]] = {}
        edges: List[Dict[str, Any]] = []
        for work in works:
            work_node = f"work:{work.id}"
            nodes[work_node] = {
                "id": work_node,
                "label": work.metadata.title,
                "type": "work",
            }
            for theme in work.metadata.themes:
                theme_node = f"theme:{theme}"
                nodes.setdefault(
                    theme_node, {"id": theme_node, "label": theme, "type": "theme"}
                )
                edges.append(
                    {
                        "source": work_node,
                        "target": theme_node,
                        "relationship": "has_theme",
                    }
                )
            entities = (
                work.text_analysis.get("entities", [])
                if isinstance(work.text_analysis, dict)
                else []
            )
            for entity in entities:
                label = entity.get("text") if isinstance(entity, dict) else str(entity)
                entity_node = f"entity:{label}"
                nodes.setdefault(
                    entity_node, {"id": entity_node, "label": label, "type": "entity"}
                )
                edges.append(
                    {
                        "source": work_node,
                        "target": entity_node,
                        "relationship": "mentions",
                    }
                )
        return {"nodes": list(nodes.values()), "edges": edges}

    def _build_text_image_linkage(self, works: List[BlakeWork]) -> List[Dict[str, Any]]:
        return [
            {
                "work_id": work.id,
                "title": work.metadata.title,
                "has_text": bool(work.text_content),
                "image_count": len(work.images),
                "linked_images": [
                    {
                        "image_id": image.id,
                        "title": image.title,
                        "related_text_id": image.related_text_id,
                        "plate_number": image.plate_number,
                    }
                    for image in work.images
                ],
            }
            for work in works
        ]

    def _build_markdown_report(
        self,
        manifest: CorpusManifest,
        stats: Dict[str, Any],
        completeness: Dict[str, Any],
    ) -> str:
        return "\n".join(
            [
                "# Blake Corpus Report",
                "",
                f"Run ID: `{manifest.run_id}`",
                f"Target: {manifest.target_profile} ({manifest.target_version})",
                f"Coverage status: {manifest.coverage_status}",
                f"Works: {manifest.total_works}",
                f"Target entries: {manifest.target_total}",
                f"Images: {manifest.total_images}",
                f"Processed works: {stats.get('processed_works', 0)}",
                f"Fixture mode: {str(manifest.fixture_mode).lower()}",
                "",
                "## Completeness",
                "",
                f"- Text coverage: {completeness['text_coverage']:.2%}",
                f"- Image coverage: {completeness['image_coverage']:.2%}",
                f"- Processing coverage: {completeness['processing_coverage']:.2%}",
                f"- Target coverage counts: {manifest.coverage_counts}",
                "",
            ]
        )

    def _source_discovery_health_payload(
        self, providers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        provider_rows = classify_provider_rows(providers)
        failures = [
            row for row in provider_rows if str(row.get("status") or "") != "completed"
        ]
        return {
            "schema_version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "providers": provider_rows,
            "provider_count": len(provider_rows),
            "failure_count": len(failures),
            "record_count": sum(
                int(row.get("record_count") or 0) for row in provider_rows
            ),
            "records_used": sum(
                int(row.get("record_count") or 0)
                for row in provider_rows
                if row.get("records_used")
            ),
        }

    def _source_leads(self) -> List[Dict[str, Any]]:
        path = Path(__file__).resolve().parents[2] / "docs" / "source-leads.json"
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Could not read source-lead registry at %s", path)
            return []
        leads = payload.get("leads") if isinstance(payload, dict) else payload
        if not isinstance(leads, list):
            return []
        return [dict(lead) for lead in leads if isinstance(lead, dict)]

    def _write_json(self, path: Path, data: Any) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return path
