"""Source authority stays identical across manifest and analytical consumers."""

from pathlib import Path

from blake.corpus.models import CorpusWorkRecord
from blake.corpus.visualizations import CorpusVisualizationBuilder
from blake.models import BlakeWork, SourceType
from blake.provenance import source_authority_tier, work_provenance


def test_authority_is_shared_without_promoting_source_evidence(
    tmp_path: Path, sample_work: BlakeWork
) -> None:
    builder = CorpusVisualizationBuilder(tmp_path)
    cases = (
        (SourceType.BLAKE_ARCHIVE, {}, "archive_primary"),
        (SourceType.PROJECT_GUTENBERG, {}, "corroborating_or_legacy"),
        (
            SourceType.INTERNET_ARCHIVE,
            {"validated_fallback_text": {"checksum": "a" * 64}},
            "fallback_text_validated",
        ),
        (SourceType.TATE, {"source_authority_tier": "catalogue_review"}, "catalogue_review"),
    )
    for source, analysis, expected in cases:
        metadata = sample_work.metadata.model_copy(
            update={"source": source, "analysis_results": analysis}
        )
        work = sample_work.model_copy(update={"metadata": metadata})
        assert source_authority_tier(work) == expected
        assert work_provenance(work)["source_authority_tier"] == expected
        assert CorpusWorkRecord.from_work(work).source_authority_tier == expected
        assert builder._source_authority_tiers([work]) == [
            {"authority_tier": expected, "work_count": 1}
        ]
