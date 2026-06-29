import json
import hashlib
from pathlib import Path

import pytest

from blake.corpus import (
    BlakeCorpus,
    CorpusConfig,
    CorpusCoverageRecord,
    CorpusManifest,
    CorpusTarget,
    CorpusTargetEntry,
    SourceRecord,
    SourceRegistry,
    load_corpus_target,
)
from blake.corpus.evidence_acquisition import (
    acquire_from_audit,
    apply_validated_fallback_marker,
    load_validated_fallback_marker,
    _validate_text,
)
from blake.corpus.release_preflight import write_private_release_preflight
from blake.corpus.source_audit import _check_url, build_source_audit, provider_reason_code
from blake.corpus.targets import build_fixture_works, build_target_coverage
from blake.metadata import MetadataManager
from blake.models import (
    BlakeImage,
    BlakeMetadata,
    BlakeWork,
    LicenseType,
    SourceType,
    WorkType,
)


class StaticProvider:
    source_type = SourceType.PROJECT_GUTENBERG
    name = "static"

    def __init__(self, records, works=None):
        self.records = records
        self.works = works or {}

    async def discover(self):
        return self.records

    async def fetch(
        self,
        record,
        *,
        force=False,
        image_mode="representative",
        image_dpi=100,
        max_images_per_work=1,
    ):
        return self.works.get(record.source_id)


class ArchiveStaticProvider(StaticProvider):
    source_type = SourceType.BLAKE_ARCHIVE


class FailingProvider:
    source_type = SourceType.INTERNET_ARCHIVE
    name = "failing provider"

    async def discover(self):
        raise RuntimeError("simulated discovery outage")

    async def fetch(
        self,
        record,
        *,
        force=False,
        image_mode="representative",
        image_dpi=100,
        max_images_per_work=1,
    ):
        return None


def test_corpus_config_defaults_to_archive_all_validation_profile():
    config = CorpusConfig()

    assert config.archive_scope == "archive-inventory"
    assert config.image_mode == "archive-all"
    assert config.image_dpi == 300
    assert config.max_images_per_work is None


def test_source_registry_deduplicates_stable_and_canonical_records():
    registry = SourceRegistry()
    first = SourceRecord(
        source_type=SourceType.PROJECT_GUTENBERG,
        source_id="1",
        title="Songs of Innocence",
        work_type=WorkType.POEM,
        license_type=LicenseType.PUBLIC_DOMAIN,
    )
    duplicate_id = SourceRecord(
        source_type=SourceType.PROJECT_GUTENBERG,
        source_id="1",
        title="Different Title",
        work_type=WorkType.POEM,
    )
    duplicate_title = SourceRecord(
        source_type=SourceType.BLAKE_ARCHIVE,
        source_id="archive-1",
        title=" songs   of innocence ",
        work_type=WorkType.POEM,
    )
    unique = SourceRecord(
        source_type=SourceType.BLAKE_ARCHIVE,
        source_id="archive-2",
        title="The Tyger",
        work_type=WorkType.POEM,
    )

    deduped = registry.dedupe_records([first, duplicate_id, duplicate_title, unique])

    assert [record.source_id for record in deduped] == ["1", "archive-2"]


@pytest.mark.asyncio
async def test_registry_discovery_uses_registered_provider():
    registry = SourceRegistry()
    record = SourceRecord(
        source_type=SourceType.PROJECT_GUTENBERG,
        source_id="pg-1",
        title="A Blake Poem",
        work_type=WorkType.POEM,
    )
    registry.register(StaticProvider([record]))

    discovered = await registry.discover_all()

    assert discovered == [record]


@pytest.mark.asyncio
async def test_registry_discovery_records_provider_failures():
    registry = SourceRegistry()
    record = SourceRecord(
        source_type=SourceType.PROJECT_GUTENBERG,
        source_id="pg-1",
        title="A Blake Poem",
        work_type=WorkType.POEM,
    )
    registry.register(StaticProvider([record]))
    registry.register(FailingProvider())

    discovered = await registry.discover_all()

    assert discovered == [record]
    health = {row["provider"]: row for row in registry.discovery_health()}
    assert health["static"]["status"] == "completed"
    assert health["static"]["record_count"] == 1
    assert health["failing provider"]["status"] == "error"
    assert "simulated discovery outage" in health["failing provider"]["error"]


@pytest.mark.asyncio
async def test_quick_corpus_run_writes_required_artifacts(tmp_path):
    data_dir = tmp_path / "blake_data"
    output_dir = tmp_path / "analysis_output"
    corpus = BlakeCorpus(data_dir, output_dir=output_dir)
    config = CorpusConfig(data_dir=data_dir, output_dir=output_dir, quick=True)

    summary = await corpus.run(config)

    assert summary.status == "completed"
    expected = [
        output_dir / "pipeline_summary.json",
        output_dir / "corpus_manifest.json",
        output_dir / "data" / "source_audit.json",
        output_dir / "data" / "source_discovery_health.json",
        output_dir / "analysis" / "analysis_summary.json",
        output_dir / "analysis" / "analysis_diagnostics.json",
        output_dir / "analysis" / "analysis_results.json",
        output_dir / "exports" / "export_summary.json",
        output_dir / "reports" / "completeness_report.json",
        output_dir / "reports" / "source_coverage.json",
        output_dir / "reports" / "provenance_manifest.json",
        output_dir / "reports" / "chronology.json",
        output_dir / "reports" / "theme_entity_network.json",
        output_dir / "reports" / "text_image_linkage.json",
        output_dir / "reports" / "corpus_report.md",
        output_dir / "visualizations" / "visualization_summary.json",
        output_dir / "visualizations" / "target_coverage_matrix.json",
        output_dir / "visualizations" / "lexical_signature.json",
        output_dir / "visualizations" / "image_depth.json",
        output_dir / "visualizations" / "dataset_statistics.json",
        output_dir / "visualizations" / "source_authority_tiers.json",
        output_dir / "visualizations" / "target_coverage_matrix.png",
        output_dir / "visualizations" / "corpus_workbench.html",
    ]
    assert all(path.exists() for path in expected)

    pipeline_summary = json.loads((output_dir / "pipeline_summary.json").read_text())
    manifest = json.loads((output_dir / "corpus_manifest.json").read_text())
    analysis_summary = json.loads(
        (output_dir / "analysis" / "analysis_summary.json").read_text()
    )
    analysis_diagnostics = json.loads(
        (output_dir / "analysis" / "analysis_diagnostics.json").read_text()
    )
    visualization_summary = json.loads(
        (output_dir / "visualizations" / "visualization_summary.json").read_text()
    )
    assert pipeline_summary["status"] == "completed"
    assert pipeline_summary["phases"][0]["status"] == "skipped"
    analysis_phase = next(
        phase for phase in pipeline_summary["phases"] if phase["name"] == "analysis"
    )
    assert analysis_phase["status"] == "completed"
    assert "analysis_diagnostics" in analysis_phase["artifacts"]
    assert manifest["fixture_mode"] is True
    assert manifest["total_works"] > 0
    assert manifest["target_total"] > manifest["total_works"]
    assert manifest["coverage_status"] == "partial"
    assert manifest["coverage_counts"]["present"] > 0
    assert manifest["coverage_counts"]["missing"] > 0
    assert analysis_summary["schema_version"] >= "1.0"
    assert analysis_summary["status"] == "completed"
    assert analysis_summary["analysis_results_current"] is True
    assert analysis_summary["works_total"] == manifest["total_works"]
    assert analysis_summary["works_analyzed"] > 0
    assert analysis_summary["artifact_paths"]["analysis_diagnostics"].endswith(
        "analysis_diagnostics.json"
    )
    assert {"text", "visual", "cross", "ontology"} <= set(
        analysis_summary["per_analysis"]
    )
    assert analysis_diagnostics["status"] == "completed"
    assert {
        "summary",
        "completion",
        "text",
        "visual",
        "cross_modal",
        "ontology",
        "errors",
    } <= set(analysis_diagnostics)
    assert analysis_diagnostics["summary"]["works_total"] == manifest["total_works"]
    assert analysis_diagnostics["summary"]["works_with_results"] > 0
    assert "text" in analysis_diagnostics["summary"]["per_analysis"]
    assert "error_categories" in analysis_diagnostics["summary"]
    assert analysis_diagnostics["completion"]["works_with_results"] > 0
    assert visualization_summary["status"] == "completed"
    assert "theme_entity_network" in visualization_summary["datasets"]
    assert "lexical_signature" in visualization_summary["datasets"]
    assert "image_depth" in visualization_summary["datasets"]
    assert "dataset_statistics" in visualization_summary["datasets"]
    assert "source_health" in visualization_summary["datasets"]
    assert "source_authority_tiers" in visualization_summary["datasets"]
    dataset_statistics = json.loads(
        (output_dir / "visualizations" / "dataset_statistics.json").read_text()
    )
    assert (
        visualization_summary["dataset_statistics"]["coverage"]["target_total"]
        == manifest["target_total"]
    )
    assert dataset_statistics["coverage"]["unresolved"] > 0
    assert "downloaded_vs_resolved_pct" in dataset_statistics["image_depth"]
    assert "failure_total" in dataset_statistics["image_depth"]
    assert "zero_image_works" in dataset_statistics["missingness"]
    assert "source_health" in dataset_statistics
    assert "analysis_status" in dataset_statistics["source_health"]
    assert "analysis_results_current" in dataset_statistics["source_health"]
    assert "manual_review_candidate_count" in dataset_statistics["source_health"]
    workbench = (output_dir / "visualizations" / "corpus_workbench.html").read_text()
    assert "Dataset Statistics" in workbench
    assert "Descriptive local-run statistics" in workbench
    assert "dataset_statistics" in workbench
    assert "Source Discovery Health" in workbench
    assert "Analysis current" in workbench
    assert "Review candidates" in workbench
    assert "--green:#009E73" in workbench
    assert "--gold:#E69F00" in workbench
    assert "--red:#D55E00" in workbench
    lexical_signature = json.loads(
        (output_dir / "visualizations" / "lexical_signature.json").read_text()
    )
    text_metrics = json.loads(
        (output_dir / "visualizations" / "text_metrics.json").read_text()
    )
    assert lexical_signature["text_work_count"] > 0
    assert lexical_signature["lexical_token_count"] > 0
    assert lexical_signature["top_terms"]
    assert lexical_signature["top_bigrams"]
    assert all("lexical_density" in row for row in text_metrics)
    assert all("top_terms" in row for row in text_metrics)

    second_summary = await corpus.run(config)
    second_manifest = json.loads((output_dir / "corpus_manifest.json").read_text())
    assert second_summary.status == "completed"
    assert second_manifest["fixture_mode"] is True
    assert sorted(second_manifest["fixture_work_ids"]) == [
        "fixture-letters",
        "fixture-mhh",
        "fixture-songsie",
    ]


@pytest.mark.asyncio
async def test_skip_analysis_marks_existing_results_stale(tmp_path):
    data_dir = tmp_path / "blake_data"
    output_dir = tmp_path / "analysis_output"
    stale_results = output_dir / "analysis" / "analysis_results.json"
    stale_results.parent.mkdir(parents=True)
    stale_results.write_text('[{"work_id": "old"}]', encoding="utf-8")
    corpus = BlakeCorpus(data_dir, output_dir=output_dir)

    await corpus.run(
        CorpusConfig(
            data_dir=data_dir,
            output_dir=output_dir,
            quick=True,
            skip_analysis=True,
            skip_visualizations=True,
            skip_export=True,
            skip_reports=True,
        )
    )

    summary = json.loads((output_dir / "analysis" / "analysis_summary.json").read_text())
    diagnostics = json.loads(
        (output_dir / "analysis" / "analysis_diagnostics.json").read_text()
    )

    assert summary["status"] == "skipped"
    assert summary["analysis_results_current"] is False
    assert summary["works_analyzed"] == 0
    assert summary["stale_analysis_results"].endswith("analysis_results.json")
    assert json.loads(stale_results.read_text()) == [{"work_id": "old"}]
    assert diagnostics["status"] == "skipped"
    assert diagnostics["analysis_results_current"] is False


@pytest.mark.asyncio
async def test_fresh_corpus_run_prunes_stale_works_but_keeps_fallback_markers(
    tmp_path,
):
    data_dir = tmp_path / "blake_data"
    output_dir = tmp_path / "analysis_output"
    current_record = SourceRecord(
        source_type=SourceType.PROJECT_GUTENBERG,
        source_id="current-work",
        title="Current Work",
        work_type=WorkType.POEM,
        license_type=LicenseType.PUBLIC_DOMAIN,
    )
    current_work = BlakeWork(
        id="current-work",
        metadata=BlakeMetadata(
            id="current-work",
            title="Current Work",
            work_type=WorkType.POEM,
            source=SourceType.PROJECT_GUTENBERG,
            source_id="current-work",
            license_type=LicenseType.PUBLIC_DOMAIN,
        ),
        text_content="Current Work text",
    )
    stale_work = BlakeWork(
        id="stale-work",
        metadata=BlakeMetadata(
            id="stale-work",
            title="Stale Work",
            work_type=WorkType.POEM,
            source=SourceType.BLAKE_ARCHIVE,
            source_id="stale-work",
            license_type=LicenseType.PUBLIC_DOMAIN,
        ),
        text_content="Stale Work text",
    )
    fallback_text = "Fallback Work " + "validated " * 120
    fallback_checksum = hashlib.sha256(fallback_text.encode("utf-8")).hexdigest()
    fallback_work = BlakeWork(
        id="fallback-work",
        metadata=BlakeMetadata(
            id="fallback-work",
            title="Fallback Work",
            work_type=WorkType.POEM,
            source=SourceType.WIKIMEDIA,
            source_id="fallback-work",
            license_type=LicenseType.PUBLIC_DOMAIN,
            analysis_results={
                "source_authority_tier": "fallback_text_validated",
                "validated_fallback_text": {
                    "target_id": "fallback-work",
                    "title": "Fallback Work",
                    "authority_tier": "fallback_text_validated",
                    "source": "Wikisource author page",
                    "source_url": "https://en.wikisource.org/wiki/Fallback_Work",
                    "checksum": fallback_checksum,
                    "words": len(fallback_text.split()),
                },
            },
        ),
        text_content=fallback_text,
    )
    manager = MetadataManager(data_dir)
    await manager.save_work(stale_work)
    await manager.save_work(fallback_work)
    fallback_text_path = data_dir / "texts" / "fallback-work.txt"
    fallback_text_path.parent.mkdir(parents=True, exist_ok=True)
    fallback_text_path.write_text(fallback_text, encoding="utf-8")
    marker_path = (
        data_dir / "metadata" / "fallback_text_validations" / "fallback-work.json"
    )
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(
        json.dumps(fallback_work.metadata.analysis_results["validated_fallback_text"]),
        encoding="utf-8",
    )
    registry = SourceRegistry()
    registry.register(StaticProvider([current_record], {"current-work": current_work}))
    corpus = BlakeCorpus(data_dir, output_dir=output_dir, source_registry=registry)

    await corpus.run(
        CorpusConfig(
            data_dir=data_dir,
            output_dir=output_dir,
            fixture_mode="never",
            skip_analysis=True,
            skip_visualizations=True,
            skip_export=True,
            skip_reports=True,
        )
    )

    ids = {work.id for work in await corpus.get_all_works()}
    report = json.loads((output_dir / "data" / "download_report.json").read_text())
    assert ids == {"current-work", "fallback-work"}
    assert report["stale_works_pruned"] == ["stale-work"]


def test_corpus_manifest_serializes_fixture_work(tmp_path):
    work = BlakeWork(
        id="work-1",
        metadata=BlakeMetadata(
            id="work-1",
            title="The Tyger",
            work_type=WorkType.POEM,
            source=SourceType.PROJECT_GUTENBERG,
            source_id="pg-1",
            license_type=LicenseType.CC_BY_NC_ND,
            themes=["experience"],
        ),
        text_content="Tyger Tyger, burning bright",
    )

    manifest = CorpusManifest.from_works(
        [work],
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "out",
    )
    payload = manifest.model_dump(mode="json")

    assert payload["total_works"] == 1
    assert payload["source_coverage"] == {"project_gutenberg": 1}
    assert payload["work_records"][0]["provenance"]["license_type"] == "cc_by_nc_nd"
    assert (
        payload["work_records"][0]["source_authority_tier"] == "corroborating_or_legacy"
    )


def test_corpus_manifest_serializes_image_depth_and_authority_tier(tmp_path):
    work = BlakeWork(
        id="songsie",
        metadata=BlakeMetadata(
            id="songsie",
            title="Songs of Innocence and of Experience",
            work_type=WorkType.ILLUMINATED_BOOK,
            source=SourceType.BLAKE_ARCHIVE,
            license_type=LicenseType.PUBLIC_DOMAIN,
            analysis_results={
                "source_authority_tier": "archive_primary",
                "image_depth": {
                    "expected_object_count": 54,
                    "resolved_object_count": 54,
                    "downloaded_image_count": 53,
                    "image_depth_status": "partial",
                    "failures": [{"object_id": "songsie.a.p54", "reason": "404"}],
                },
            },
        ),
        text_content="Songs of Innocence and of Experience",
    )

    manifest = CorpusManifest.from_works(
        [work],
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "out",
    )
    record = manifest.model_dump(mode="json")["work_records"][0]

    assert record["source_authority_tier"] == "archive_primary"
    assert record["expected_object_count"] == 54
    assert record["resolved_object_count"] == 54
    assert record["downloaded_image_count"] == 53
    assert record["image_depth_status"] == "partial"
    assert record["image_depth_failures"] == [
        {"object_id": "songsie.a.p54", "reason": "404"}
    ]


def test_canonical_target_loads_modality_categories():
    target = load_corpus_target()

    categories = {entry.category for entry in target.entries}

    assert target.profile == "canonical"
    assert target.total > 38
    assert "illuminated_books" in categories
    assert "letters" in categories
    assert "commercial_illustrations" in categories
    assert "watercolors_drawings" in categories
    assert "separate_prints" in categories
    assert "typographic_works" in categories
    assert "drawings" in categories
    assert "engravings" in categories


def test_canonical_target_includes_archive_only_gap_ids():
    target = load_corpus_target()
    entries = {entry.target_id: entry for entry in target.entries}

    assert {"homer", "bb206", "abel", "b-los"}.issubset(entries)
    assert entries["homer"].source_hints[SourceType.BLAKE_ARCHIVE.value] == ["homer"]
    assert entries["bb206"].category == "typographic_works"
    assert entries["abel"].expected_images == 1
    assert entries["b-los"].source_hints[SourceType.BLAKE_ARCHIVE.value] == ["b-los"]


def test_target_coverage_does_not_claim_complete_for_fixture_subset(tmp_path):
    target = load_corpus_target()
    works = build_fixture_works(tmp_path / "data")

    records, counts, status = build_target_coverage(target, works)

    assert status == "partial"
    assert counts["present"] > 0
    assert counts["missing"] > 0
    assert len(records) == target.total


def test_target_coverage_allows_shared_source_hint_matches():
    target = CorpusTarget(
        version="test",
        description="test target",
        entries=[
            CorpusTargetEntry(
                target_id="songs-experience",
                title="Songs of Experience",
                work_type=WorkType.ILLUMINATED_BOOK,
                category="illuminated_books",
                expected_text=True,
                expected_images=1,
                source_hints={SourceType.BLAKE_ARCHIVE.value: ["songsie"]},
            ),
            CorpusTargetEntry(
                target_id="songsie",
                title="Songs of Innocence and of Experience",
                work_type=WorkType.ILLUMINATED_BOOK,
                category="illuminated_books",
                expected_text=True,
                expected_images=1,
                source_hints={SourceType.BLAKE_ARCHIVE.value: ["songsie"]},
            ),
        ],
    )
    work = BlakeWork(
        id="songsie",
        metadata=BlakeMetadata(
            id="songsie",
            title="Songs of Innocence and of Experience",
            work_type=WorkType.ILLUMINATED_BOOK,
            source=SourceType.BLAKE_ARCHIVE,
            source_id="songsie",
            license_type=LicenseType.PUBLIC_DOMAIN,
        ),
        text_content="Songs text",
        images=[
            BlakeImage(
                id="songsie.a.p1",
                metadata_id="songsie",
                title="songsie.a.p1",
                file_path=Path("songsie.a.p1.jpg"),
            )
        ],
    )

    records, counts, status = build_target_coverage(target, [work])
    by_id = {record.target_id: record for record in records}

    assert status == "complete"
    assert counts["present"] == 2
    assert by_id["songs-experience"].matched_work_ids == ["songsie"]
    assert by_id["songsie"].matched_work_ids == ["songsie"]


def test_target_coverage_does_not_duplicate_from_broad_title_aliases():
    target = CorpusTarget(
        version="test",
        description="test target",
        entries=[
            CorpusTargetEntry(
                target_id="songsie",
                title="Songs of Innocence and of Experience",
                aliases=["Songs of Innocence", "Songs of Experience"],
                work_type=WorkType.ILLUMINATED_BOOK,
                category="illuminated_books",
                expected_text=True,
                expected_images=1,
                source_hints={SourceType.BLAKE_ARCHIVE.value: ["songsie"]},
            ),
            CorpusTargetEntry(
                target_id="bb421",
                title="Illustrations of the Book of Job",
                aliases=["Illustrations to the Book of Job"],
                work_type=WorkType.ILLUSTRATION,
                category="commercial_illustrations",
                expected_text=False,
                expected_images=1,
                source_hints={SourceType.BLAKE_ARCHIVE.value: ["bb421"]},
            ),
        ],
    )
    works = [
        BlakeWork(
            id="songsie",
            metadata=BlakeMetadata(
                id="songsie",
                title="Songs of Innocence and of Experience",
                work_type=WorkType.ILLUMINATED_BOOK,
                source=SourceType.BLAKE_ARCHIVE,
                source_id="songsie",
                license_type=LicenseType.PUBLIC_DOMAIN,
            ),
            text_content="Songs text",
            images=[
                BlakeImage(
                    id="songsie.a.p1",
                    metadata_id="songsie",
                    title="songsie.a.p1",
                    file_path=Path("songsie.a.p1.jpg"),
                )
            ],
        ),
        BlakeWork(
            id="s-inn",
            metadata=BlakeMetadata(
                id="s-inn",
                title="Songs of Innocence",
                work_type=WorkType.ILLUMINATED_BOOK,
                source=SourceType.BLAKE_ARCHIVE,
                source_id="s-inn",
                license_type=LicenseType.PUBLIC_DOMAIN,
            ),
            text_content="Songs of Innocence text",
            images=[
                BlakeImage(
                    id="s-inn.a.p1",
                    metadata_id="s-inn",
                    title="s-inn.a.p1",
                    file_path=Path("s-inn.a.p1.jpg"),
                )
            ],
        ),
        BlakeWork(
            id="bb421",
            metadata=BlakeMetadata(
                id="bb421",
                title="Illustrations of the Book of Job",
                work_type=WorkType.ILLUSTRATION,
                source=SourceType.BLAKE_ARCHIVE,
                source_id="bb421",
                license_type=LicenseType.PUBLIC_DOMAIN,
            ),
            images=[
                BlakeImage(
                    id="bb421.1.1.ps",
                    metadata_id="bb421",
                    title="bb421.1.1.ps",
                    file_path=Path("bb421.1.1.ps.jpg"),
                )
            ],
        ),
        BlakeWork(
            id="esv",
            metadata=BlakeMetadata(
                id="esv",
                title="Illustrations to the Book of Job",
                work_type=WorkType.ILLUSTRATION,
                source=SourceType.BLAKE_ARCHIVE,
                source_id="esv",
                license_type=LicenseType.PUBLIC_DOMAIN,
            ),
            images=[
                BlakeImage(
                    id="esv.1.1.sp",
                    metadata_id="esv",
                    title="esv.1.1.sp",
                    file_path=Path("esv.1.1.sp.jpg"),
                )
            ],
        ),
    ]

    records, counts, status = build_target_coverage(target, works)
    by_id = {record.target_id: record for record in records}

    assert status == "complete"
    assert counts["duplicate"] == 0
    assert by_id["songsie"].matched_work_ids == ["songsie"]
    assert by_id["bb421"].matched_work_ids == ["bb421"]


@pytest.mark.asyncio
async def test_source_audit_reports_missing_evidence_candidates():
    target = CorpusTarget(
        version="test",
        description="test target",
        entries=[
            CorpusTargetEntry(
                target_id="songs-experience",
                title="Songs of Experience",
                work_type=WorkType.ILLUMINATED_BOOK,
                category="illuminated_books",
                expected_text=True,
                expected_images=1,
                source_hints={SourceType.BLAKE_ARCHIVE.value: ["songsie"]},
            )
        ],
    )
    coverage_records = [
        CorpusCoverageRecord(
            target_id="songs-experience",
            title="Songs of Experience",
            category="illuminated_books",
            work_type="illuminated_book",
            expected_text=True,
            expected_images=1,
            status="partial",
            notes=[
                "Expected text is not available locally.",
                "Expected image evidence is not available locally.",
            ],
        )
    ]

    payload = await build_source_audit(
        target,
        [],
        include_live=False,
        coverage_records=coverage_records,
        provider_discovery=[
            {
                "provider": "bad",
                "source_type": "internet_archive",
                "status": "error",
                "record_count": 0,
                "error": "timeout",
                "duration_seconds": 0.01,
                "records_used": False,
            }
        ],
        archive_metadata_enrichment={
            "status": "degraded",
            "attempted": 2,
            "succeeded": 0,
            "failed": 2,
            "skipped_after_budget": 3,
            "fallback_source_used": "target ledger + GitHub XML inventory",
        },
    )

    evidence_types = {row["evidence_type"] for row in payload["missing_evidence"]}
    sources = {row["candidate_source"] for row in payload["missing_evidence"]}
    assert {"text", "image"}.issubset(evidence_types)
    assert "William Blake Archive work API" in sources
    assert "Project Gutenberg author page" in sources
    assert "British Museum collection search" in sources
    assert payload["missing_evidence_summary"]["target_count"] == 1
    assert payload["provider_discovery"]["failure_count"] == 1
    assert payload["provider_discovery"]["providers"][0]["reason_code"] == "timeout"
    assert payload["live"]["archive_metadata_enrichment"]["status"] == "degraded"


def test_provider_reason_code_classifies_reviewable_failures():
    rows = [
        ({"status": "completed", "record_count": 3}, "ok"),
        ({"status": "completed", "record_count": 0}, "empty_result"),
        ({"status": "error", "error": "request timeout"}, "timeout"),
        ({"status": "error", "error": "HTTP 503 from source"}, "http_failure"),
        ({"status": "error", "error": "XML parse failure"}, "parse_failure"),
        ({"status": "error", "error": "429 Too Many Requests"}, "throttled"),
        ({"status": "error", "error": "source terms forbid bulk download"}, "source_terms_review"),
    ]

    for row, expected in rows:
        assert provider_reason_code(row) == expected


def test_source_leads_registry_has_acceptance_checklist():
    payload = json.loads(Path("docs/source-leads.json").read_text(encoding="utf-8"))
    checklist = set(payload["acceptance_checklist"])

    for required in [
        "exact_title_or_alias_match",
        "source_owned_or_authority_tier_recorded",
        "stable_source_url",
        "attribution_recorded",
        "license_or_terms_recorded",
        "content_checksum_recorded",
        "rights_disposition_recorded",
        "rejection_reason_recorded_when_not_accepted",
    ]:
        assert required in checklist


@pytest.mark.asyncio
async def test_source_audit_bounded_url_samples_preserve_xml_counts():
    class FakeResponse:
        status = 200
        headers = {"content-type": "application/xml"}

        async def text(self, errors="ignore"):
            files = "".join(
                f'<resource filename="bb{i}.xml" />' for i in range(60)
            )
            return f"<root>{files}<note>{'x' * 5000}</note></root>"

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        def get(self, url):
            return FakeResponse()

    row = await _check_url(FakeSession(), "xml inventory", "https://example.test/x.xml")

    assert row["xml_resource_count"] == 60
    assert row["xml_prefix_count"] == 60
    assert row["sample_truncated"] is True
    assert "text_sample" not in row
    assert len(row["normalized_snippet"]) <= 360
    assert len(row["body_sha256"]) == 64


@pytest.mark.asyncio
async def test_manual_source_leads_are_review_candidates_not_auto_acceptance(tmp_path):
    target = CorpusTarget(
        version="test",
        description="test target",
        entries=[
            CorpusTargetEntry(
                target_id="bb126",
                title="The Pickering Manuscript",
                work_type=WorkType.MANUSCRIPT,
                category="manuscripts",
                expected_text=True,
            )
        ],
    )
    coverage_records = [
        CorpusCoverageRecord(
            target_id="bb126",
            title="The Pickering Manuscript",
            category="manuscripts",
            work_type="manuscript",
            expected_text=True,
            expected_images=0,
            status="partial",
            notes=["Expected text is not available locally."],
        )
    ]

    payload = await build_source_audit(
        target,
        [],
        include_live=False,
        coverage_records=coverage_records,
        source_leads=[
            {
                "target_id": "bb126",
                "evidence_type": "text",
                "source_owner": "Morgan Library",
                "url": "https://www.themorgan.org/collection/William-Blakes-World/163",
                "status": "manual_review",
                "rights_note": "excerpt only",
                "review_priority": "high",
                "direct_source_basis": "source-owned collection record",
                "scholarship_note": "review only",
                "match_confidence": 0.67,
            }
        ],
    )
    manual = [
        row
        for row in payload["missing_evidence"]
        if row["candidate_source"] == "Morgan Library"
    ][0]

    assert manual["candidate_url"].startswith("https://www.themorgan.org/")
    assert manual["match_confidence"] < 0.68
    assert manual["ok"] is None
    assert manual["action_taken"].startswith("manual_review:")
    assert manual["lead_status"] == "manual_review"
    assert manual["rights_note"] == "excerpt only"
    assert manual["review_priority"] == "high"
    assert manual["direct_source_basis"] == "source-owned collection record"
    assert manual["scholarship_note"] == "review only"
    assert "Manual review only" in manual["acceptance_policy"]

    audit_path = tmp_path / "source_audit.json"
    audit_path.write_text(json.dumps(payload), encoding="utf-8")
    acquisition = acquire_from_audit(audit_path, tmp_path / "data", dry_run=True)
    result = [
        row
        for row in acquisition["results"]
        if row["candidate_source"] == "Morgan Library"
    ][0]
    assert result["status"] == "skipped"
    assert result["reason"] == "manual-review source lead cannot be automatically accepted"


def test_source_leads_schema_records_scholarship_controls_without_auto_acceptance():
    root = Path(__file__).resolve().parents[1]
    payload = json.loads((root / "docs" / "source-leads.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "1.1"
    assert "manual-review source leads only" in payload["scope_note"].lower()

    leads = payload["leads"]
    required = {
        "target_id",
        "title",
        "evidence_type",
        "source_owner",
        "url",
        "status",
        "rights_note",
        "review_priority",
        "direct_source_basis",
        "scholarship_note",
        "match_confidence",
    }
    assert leads
    for lead in leads:
        assert required <= lead.keys(), lead
        assert lead["status"] == "manual_review"
        assert lead["rights_note"]
        assert lead["direct_source_basis"]
        assert lead["scholarship_note"]

    morgan_urls = {
        lead["url"]
        for lead in leads
        if lead["target_id"] == "bb126" and lead["source_owner"] == "Morgan Library"
    }
    assert "https://www.themorgan.org/collection/william-blake/pickering-manuscript" in morgan_urls
    assert "https://www.themorgan.org/collection/william-blake/pickering-manuscript/13" in morgan_urls

    four_zoas_controls = [
        lead
        for lead in leads
        if lead["target_id"] == "bb209"
        and lead["source_owner"] == "Blake/An Illustrated Quarterly"
    ]
    assert four_zoas_controls
    assert four_zoas_controls[0]["evidence_type"] == "source_match"
    assert "cannot supply corpus text" in four_zoas_controls[0]["rights_note"]



def test_fallback_text_validation_rejects_search_results_and_title_mismatch():
    entry = CorpusTargetEntry(
        target_id="poetical-sketches",
        title="Poetical Sketches",
        work_type=WorkType.POEM,
        category="poems",
        expected_text=True,
        aliases=["Poetical Sketches by William Blake"],
    )
    enough_words = " ".join(["line"] * 1200)

    assert _validate_text(entry, f"Poetical Sketches\n{enough_words}") is None
    assert (
        _validate_text(entry, f"Search results\nPoetical Sketches\n{enough_words}")
        == "pulled content is a search page, not a transcription"
    )
    assert (
        _validate_text(entry, f"Different Title\n{enough_words}")
        == "pulled content does not identify the target title near the start"
    )
    catalog_text = "{{Versions\n| title = Poetical Sketches\n}}\n" + " ".join(
        ["catalog"] * 1200
    )
    assert (
        _validate_text(entry, catalog_text)
        == "pulled content is a catalog or versions page, not a transcription"
    )
    short_text = "Poetical Sketches\n" + " ".join(["line"] * 125)
    assert (
        _validate_text(entry, short_text)
        == "pulled content is too short (127 words; minimum 1000)"
    )


def test_acquire_evidence_accepts_only_validated_fallback_text(tmp_path, monkeypatch):
    target_entry = next(
        entry for entry in load_corpus_target().entries if entry.expected_text
    )
    audit_path = tmp_path / "source_audit.json"
    good_text = f"{target_entry.title}\n" + " ".join(["validated"] * 140)
    audit_path.write_text(
        json.dumps(
            {
                "target_profile": "canonical",
                "missing_evidence": [
                    {
                        "target_id": target_entry.target_id,
                        "title": target_entry.title,
                        "evidence_type": "text",
                        "candidate_source": "Project Gutenberg author page",
                        "candidate_url": "https://www.gutenberg.org/ebooks/author/915",
                        "ok": True,
                        "match_confidence": 0.91,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "blake.corpus.evidence_acquisition._pull_gutenberg_text",
        lambda _session, _entry, _url: (
            "https://www.gutenberg.org/cache/epub/999/pg999.txt",
            good_text,
        ),
    )

    summary = acquire_from_audit(audit_path, tmp_path / "data", dry_run=False)

    assert summary["accepted"] == 1
    result = summary["results"][0]
    assert result["authority_tier"] == "fallback_text_validated"
    assert result["checksum"]
    work = MetadataManager(tmp_path / "data").database.load_work(target_entry.target_id)
    assert work is not None
    assert work.metadata.checksum == result["checksum"]
    assert (
        work.metadata.analysis_results["source_authority_tier"]
        == "fallback_text_validated"
    )
    assert work.metadata.analysis_results["validated_fallback_text"]["checksum"]
    marker = load_validated_fallback_marker(tmp_path / "data", target_entry.target_id)
    assert marker is not None
    assert marker["checksum"] == result["checksum"]

    archive_work = BlakeWork(
        id=target_entry.target_id,
        metadata=BlakeMetadata(
            id=target_entry.target_id,
            title=target_entry.title,
            work_type=target_entry.work_type,
            source=SourceType.BLAKE_ARCHIVE,
            source_id=target_entry.target_id,
            license_type=LicenseType.PUBLIC_DOMAIN,
        ),
        text_content=good_text,
    )
    assert apply_validated_fallback_marker(tmp_path / "data", archive_work) is True
    manifest = CorpusManifest.from_works(
        [archive_work],
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "out",
    ).model_dump(mode="json")
    record = manifest["work_records"][0]
    assert record["source"] == "blake_archive"
    assert record["source_authority_tier"] == "fallback_text_validated"


def test_acquire_evidence_skips_low_confidence_and_catalog_sources(tmp_path):
    target_entry = next(
        entry for entry in load_corpus_target().entries if entry.expected_text
    )
    audit_path = tmp_path / "source_audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "target_profile": "canonical",
                "missing_evidence": [
                    {
                        "target_id": target_entry.target_id,
                        "title": target_entry.title,
                        "evidence_type": "text",
                        "candidate_source": "Project Gutenberg author page",
                        "candidate_url": "https://www.gutenberg.org/ebooks/author/915",
                        "ok": True,
                        "match_confidence": 0.3,
                    },
                    {
                        "target_id": target_entry.target_id,
                        "title": target_entry.title,
                        "evidence_type": "text",
                        "candidate_source": "British Museum collection search",
                        "candidate_url": "https://www.britishmuseum.org/collection",
                        "ok": True,
                        "match_confidence": 0.95,
                    },
                    {
                        "target_id": target_entry.target_id,
                        "title": target_entry.title,
                        "evidence_type": "image",
                        "candidate_source": "William Blake Archive work API",
                        "candidate_url": "https://blakearchive.org/api/work/songsie",
                        "ok": True,
                        "match_confidence": 0.95,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    summary = acquire_from_audit(audit_path, tmp_path / "data", dry_run=True)

    assert summary["accepted"] == 0
    assert summary["skipped"] == 3
    reasons = {row["reason"] for row in summary["results"]}
    assert "candidate confidence below threshold" in reasons
    assert "source is corroborating/catalog-only for automatic text pull" in reasons
    assert "non-text evidence is handled by image-depth acquisition" in reasons


def test_acquire_evidence_dry_run_writes_target_review_for_zero_accepts(
    tmp_path, monkeypatch
):
    target_entry = next(
        entry for entry in load_corpus_target().entries if entry.expected_text
    )
    audit_path = tmp_path / "source_audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "target_profile": "canonical",
                "missing_evidence": [
                    {
                        "target_id": target_entry.target_id,
                        "title": target_entry.title,
                        "evidence_type": "text",
                        "candidate_source": "Project Gutenberg author page",
                        "candidate_url": "https://www.gutenberg.org/ebooks/author/915",
                        "ok": True,
                        "match_confidence": 0.91,
                    },
                    {
                        "target_id": target_entry.target_id,
                        "title": target_entry.title,
                        "evidence_type": "text",
                        "candidate_source": "Project Gutenberg author page",
                        "candidate_url": "https://www.gutenberg.org/ebooks/author/fail",
                        "ok": True,
                        "match_confidence": 0.91,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    def fake_pull(_session, _entry, url):
        if url.endswith("/fail"):
            raise RuntimeError("429 Client Error: Too Many Requests")
        return None

    monkeypatch.setattr(
        "blake.corpus.evidence_acquisition._pull_gutenberg_text",
        fake_pull,
    )

    summary = acquire_from_audit(audit_path, tmp_path / "data", dry_run=True)

    assert summary["accepted"] == 0
    review_path = Path(summary["review_path"])
    queue_path = Path(summary["review_queue_path"])
    assert review_path.exists()
    assert queue_path.exists()
    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert review["artifact"] == "evidence_acquisition_review"
    assert review["schema_version"] == "1.1"
    assert review["unresolved_target_count"] == 1
    assert review["review_queue"]
    assert "Evidence Acquisition Review Queue" in queue_path.read_text(encoding="utf-8")
    target_review = review["target_reviews"][0]
    assert target_review["target_id"] == target_entry.target_id
    assert target_review["candidate_count"] == 2
    assert "Manual source-owned review required" in target_review["recommended_action"]
    assert target_review["recommended_next_action"] == target_review["recommended_action"]
    reasons = {candidate["reason"] for candidate in target_review["candidates"]}
    assert "no exact title or alias match found" in reasons
    assert any(reason.startswith("source pull failed: 429") for reason in reasons)
    for candidate in target_review["candidates"]:
        assert candidate["candidate_source"]
        assert candidate["source"]
        assert candidate["live_ok"] is True
        assert candidate["match_confidence"] == 0.91
        assert "checksum" in candidate
        assert "http_status" in candidate
        assert "ok" in candidate
        assert "action_taken" in candidate
        assert "evidence_note" in candidate
        assert "recommended_next_action" in candidate


def test_acquire_evidence_manual_source_leads_are_review_only(tmp_path):
    target_entry = next(
        entry for entry in load_corpus_target().entries if entry.target_id == "bb126"
    )
    audit_path = tmp_path / "source_audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "target_profile": "canonical",
                "missing_evidence": [
                    {
                        "target_id": target_entry.target_id,
                        "title": target_entry.title,
                        "evidence_type": "text",
                        "candidate_source": "Morgan Library",
                        "candidate_url": "https://www.themorgan.org/collection/William-Blakes-World/163",
                        "ok": True,
                        "http_status": 200,
                        "match_confidence": 0.99,
                        "action_taken": "manual_review: source-owned lead only",
                        "evidence_note": "Lead status: manual_review.",
                        "lead_status": "manual_review",
                        "rights_note": "Corroborating manuscript evidence only.",
                        "review_priority": "high",
                        "direct_source_basis": "source-owned collection record",
                        "scholarship_note": "review only",
                        "acceptance_policy": "Exact title/source validation, attribution, checksum, rights metadata, and regenerated coverage required.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    summary = acquire_from_audit(audit_path, tmp_path / "data", dry_run=True)

    assert summary["accepted"] == 0
    assert summary["skipped"] == 1
    result = summary["results"][0]
    assert result["reason"] == "manual-review source lead cannot be automatically accepted"
    review = json.loads(Path(summary["review_path"]).read_text(encoding="utf-8"))
    candidate = review["target_reviews"][0]["candidates"][0]
    assert candidate["candidate_source"] == "Morgan Library"
    assert candidate["http_status"] == 200
    assert candidate["ok"] is True
    assert candidate["lead_status"] == "manual_review"
    assert "Corroborating manuscript evidence" in candidate["rights_note"]
    assert candidate["review_priority"] == "high"
    assert candidate["direct_source_basis"] == "source-owned collection record"
    assert candidate["scholarship_note"] == "review only"
    assert "Exact title/source validation" in candidate["acceptance_policy"]
    assert "Manual review only" in candidate["recommended_next_action"]


@pytest.mark.asyncio
async def test_source_audit_manual_leads_and_bounded_url_samples(tmp_path):
    class FakeResponse:
        def __init__(self, body, content_type):
            self.status = 200
            self.headers = {"content-type": content_type}
            self._body = body

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return False

        async def text(self, errors="ignore"):
            return self._body

    class FakeSession:
        def __init__(self, body, content_type):
            self.body = body
            self.content_type = content_type

        def get(self, _url):
            return FakeResponse(self.body, self.content_type)

    html_body = "<html><body>" + (" Blake Archive " * 200) + "</body></html>"
    html_row = await _check_url(
        FakeSession(html_body, "text/html"), "HTML", "https://example.test"
    )

    assert "text_sample" not in html_row
    assert len(html_row["normalized_snippet"]) <= 360
    assert html_row["body_sha256"] == hashlib.sha256(html_body.encode("utf-8")).hexdigest()
    assert html_row["bytes_sampled"] == len(html_body)
    assert html_row["sample_truncated"] is True

    json_body = json.dumps([{"name": "bb126.xml"}, {"name": "bb127.xml"}])
    json_row = await _check_url(
        FakeSession(json_body, "application/json"), "JSON", "https://example.test"
    )
    assert "text_sample" not in json_row
    assert json_row["json_count"] == 2
    assert json_row["json_xml_count"] == 2

    target = CorpusTarget(
        version="test",
        description="test",
        entries=[
            CorpusTargetEntry(
                target_id="bb126",
                title="The Pickering Manuscript",
                work_type=WorkType.MANUSCRIPT,
                category="manuscripts",
                expected_text=True,
            )
        ],
    )
    audit = await build_source_audit(
        target,
        [],
        include_live=False,
        coverage_records=[
            {
                "target_id": "bb126",
                "title": "The Pickering Manuscript",
                "status": "missing",
                "notes": ["Expected text is not available locally."],
            }
        ],
        archive_metadata_enrichment={
            "status": "degraded",
            "attempted": 2,
            "succeeded": 1,
            "failed": 1,
        },
        source_leads=[
            {
                "target_id": "bb126",
                "evidence_type": "text",
                "source_owner": "Morgan Library",
                "url": "https://www.themorgan.org/collection/William-Blakes-World/163",
                "status": "manual_review",
                "rights_note": "Collection record only.",
                "review_priority": "high",
                "direct_source_basis": "source-owned collection record",
                "scholarship_note": "review only",
                "match_confidence": 0.67,
            }
        ],
    )

    assert audit["metadata_enrichment_report"]["status"] == "degraded"
    manual_rows = [
        row for row in audit["missing_evidence"] if row.get("lead_status") == "manual_review"
    ]
    assert manual_rows
    assert manual_rows[0]["candidate_source"] == "Morgan Library"
    assert manual_rows[0]["rights_note"] == "Collection record only."
    assert manual_rows[0]["review_priority"] == "high"
    assert manual_rows[0]["direct_source_basis"] == "source-owned collection record"
    assert manual_rows[0]["scholarship_note"] == "review only"
    assert "Manual review only" in manual_rows[0]["acceptance_policy"]


def test_private_release_preflight_excludes_raw_cache_and_mosaics(tmp_path):
    output_dir = tmp_path / "analysis_output"
    data_dir = tmp_path / "blake_data"
    (output_dir / "visualizations").mkdir(parents=True)
    (output_dir / "reports").mkdir(parents=True)
    (tmp_path / "output" / "figures").mkdir(parents=True)
    (tmp_path / "manuscript").mkdir()
    (tmp_path / "manuscript" / "13_supplement_rights_matrix.md").write_text(
        "\n".join(
            [
                "Project code, tests, scripts, and project-authored documentation",
                "Aggregate counts, coverage tables, checksums, source URLs, authority tiers, and non-image charts",
                "Project Gutenberg fallback text",
                "Wikisource fallback text",
                "William Blake Archive TEI, transcriptions, object images, and bulk mirrors",
                "Image mosaics and visual supplements made from local source files",
                "Generated cover and project-authored diagrams",
            ]
        ),
        encoding="utf-8",
    )
    (output_dir / "corpus_manifest.json").write_text(
        json.dumps(
            {
                "coverage_status": "partial",
                "coverage_counts": {"present": 1, "total": 2},
                "total_works": 2,
                "total_images": 5,
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "visualizations" / "dataset_statistics.json").write_text(
        json.dumps({"schema_version": "1.0", "coverage": {}, "missingness": {}}),
        encoding="utf-8",
    )
    (tmp_path / "output" / "figures" / "figure_registry.json").write_text(
        json.dumps(
            {
                "schema_version": "1.4",
                "figures": [
                    {
                        "statistics": {"n": 1},
                        "statistical_question": "What is counted?",
                        "missingness_or_scope": "local test fixture",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = write_private_release_preflight(
        tmp_path, output_dir=output_dir, data_dir=data_dir
    )

    assert report["publish_action"] == "none"
    assert report["target"] == "private-github"
    assert "blake_data/**" in report["public_exclusions"]
    assert "output/figures/*mosaic*.png" in report["public_exclusions"]
    assert any(
        row["release_disposition"] == "exclude"
        and "William Blake Archive" in row["artifact_class"]
        for row in report["blocked_artifact_classes"]
    )
    rights_gate = json.loads(Path(report["rights_gate_path"]).read_text())
    assert rights_gate["status"] == "blocked_for_public_redistribution"
    assert all(row["rights_matrix_row_found"] for row in rights_gate["artifact_classes"])


def test_manuscript_config_uses_paper_cover_image_contract():
    config = Path("manuscript/config.yaml").read_text(encoding="utf-8")

    assert "paper:" in config
    assert "cover:" in config
    assert 'image: "output/cover/cover_blakean.png"' in config


def test_target_coverage_requires_required_text_and_images(tmp_path):
    target = CorpusTarget(
        version="test",
        description="test target",
        entries=[
            CorpusTargetEntry(
                target_id="visual-text",
                title="Visual Text",
                work_type=WorkType.ILLUMINATED_BOOK,
                category="illuminated_books",
                expected_text=True,
                expected_images=1,
            )
        ],
    )
    work = BlakeWork(
        id="visual-text",
        metadata=BlakeMetadata(
            id="visual-text",
            title="Visual Text",
            work_type=WorkType.ILLUMINATED_BOOK,
            source=SourceType.BLAKE_ARCHIVE,
            license_type=LicenseType.PUBLIC_DOMAIN,
        ),
    )

    records, counts, status = build_target_coverage(target, [work])
    assert status == "partial"
    assert counts["partial"] == 1
    assert records[0].notes == [
        "Expected text is not available locally.",
        "Expected image evidence is not available locally.",
    ]

    work.text_content = "Full text"
    work.images = [build_fixture_works(tmp_path / "data")[0].images[0]]
    records, counts, status = build_target_coverage(target, [work])
    assert status == "complete"
    assert counts["present"] == 1
    assert records[0].status == "present"


def test_target_coverage_reports_duplicates(tmp_path):
    target = load_corpus_target()
    first, second, *_ = build_fixture_works(tmp_path / "data")
    second.id = "fixture-songsie-copy"
    second.metadata.id = "fixture-songsie-copy"
    second.metadata.title = "Songs of Innocence and of Experience"
    second.metadata.source_id = "songsie"

    records, counts, status = build_target_coverage(target, [first, second])
    songs_record = next(record for record in records if record.target_id == "songsie")
    experience_record = next(
        record for record in records if record.target_id == "songs-experience"
    )

    assert status == "partial"
    assert counts["duplicate"] == 2
    assert songs_record.status == "duplicate"
    assert experience_record.status == "duplicate"


@pytest.mark.asyncio
async def test_source_backed_acquisition_fetches_and_saves_work(tmp_path):
    data_dir = tmp_path / "blake_data"
    output_dir = tmp_path / "analysis_output"
    record = SourceRecord(
        source_type=SourceType.PROJECT_GUTENBERG,
        source_id="songsie",
        title="Songs of Innocence and of Experience",
        work_type=WorkType.ILLUMINATED_BOOK,
        license_type=LicenseType.PUBLIC_DOMAIN,
    )
    work = build_fixture_works(data_dir)[0]
    work.metadata.source = SourceType.PROJECT_GUTENBERG
    registry = SourceRegistry()
    registry.register(StaticProvider([record], {"songsie": work}))
    corpus = BlakeCorpus(data_dir, output_dir=output_dir, source_registry=registry)
    config = CorpusConfig(
        data_dir=data_dir,
        output_dir=output_dir,
        quick=False,
        skip_analysis=True,
        skip_visualizations=True,
        skip_export=True,
    )

    summary = await corpus.run(config)
    manifest = json.loads((output_dir / "corpus_manifest.json").read_text())
    report = json.loads((output_dir / "data" / "download_report.json").read_text())

    assert summary.status == "completed"
    assert report["works_saved"] == 1
    assert manifest["total_works"] == 1
    assert manifest["coverage_counts"]["present"] >= 1
    assert (data_dir / "texts" / "fixture-songsie.txt").exists()


@pytest.mark.asyncio
async def test_cross_analysis_color_text_relationship_regression(tmp_path):
    from blake.analysis.cross_analysis import CrossAnalyzer

    work = build_fixture_works(tmp_path / "data")[0]

    result = await CrossAnalyzer().analyze_work(work)
    correlation = result["text_image_correlation"]

    assert "error" not in correlation
    assert "color_text_analysis" in correlation
    assert correlation["color_text_analysis"]["relationship_score"] >= 0
