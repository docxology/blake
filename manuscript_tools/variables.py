"""Manuscript variable producer for the blake corpus paper.

Single source of truth for every quantitative value cited in the manuscript.
Corpus-run values are **computed from the JSON artifacts under
``analysis_output/``** (produced by ``run_all.py --quick``). Legal-duration and
rights-layer values are loaded from ``docs/manuscript/legal_claim_ledger.yaml``. The
manuscript markdown cites these values exclusively through ``{{UPPERCASE_TOKEN}}``
markers, which ``infrastructure.rendering.manuscript_injection`` substitutes at
render time. Re-running the pipeline and re-rendering therefore updates every
prose number automatically.

Token contract: the keys returned by :func:`generate_variables` are the *only*
tokens the manuscript may use. Any ``{{TOKEN}}`` in the markdown not present here
renders literally (a visible defect) and is rejected by the build-time check that
every used token is produced. Producing a token the markdown does not use is
harmless (it never renders) and therefore permitted — a few such reserve tokens
(e.g. per-work word counts available for inline citation) are emitted by design.

All values are returned as strings (the injector substitutes text verbatim).
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from manuscript_tools.method_types import local_image_count
from manuscript_tools.core_architecture import architecture_tokens
from manuscript_tools.nlp_diagnostics import build_nlp_diagnostics, validate_membership
from manuscript_tools.paths import manuscript_roots
from manuscript_tools.publication import publication_tokens

# Human-readable labels for the registered source providers. Used only to
# render provider *names*; the *count* is always derived from the JSON.
_SOURCE_LABELS: dict[str, str] = {
    "blake_archive": "the William Blake Archive",
    "project_gutenberg": "Project Gutenberg",
    "internet_archive": "the Internet Archive",
    "wikimedia": "Wikisource",
}


class AnalysisOutputsMissing(RuntimeError):
    """Raised when a required ``analysis_output/`` artifact is absent.

    The pipeline must fail loudly rather than silently substitute ``N/A`` —
    a manuscript number that cannot be computed is a defect, not a default.
    """


def _read_json(path: Path, *, required: bool) -> Any:
    if not path.exists():
        if required:
            raise AnalysisOutputsMissing(
                f"Required analysis artifact missing: {path}. "
                "Run `run_all.py --quick` before generating manuscript variables."
            )
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _read_legal_claim_tokens(path: Path) -> dict[str, str]:
    """Read the simple legal claim ledger into manuscript tokens.

    The ledger intentionally uses a tiny, append-only YAML subset so the
    manuscript can keep legal numbers source-owned without adding a runtime YAML
    dependency to the package.
    """
    if not path.exists():
        return {}

    tokens: dict[str, str] = {}
    claim_id: str | None = None
    value: str | None = None

    def flush() -> None:
        nonlocal claim_id, value
        if claim_id and value is not None:
            tokens[claim_id.upper()] = value
        claim_id = None
        value = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("- claim_id:"):
            flush()
            claim_id = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("claim_id:"):
            claim_id = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("value:"):
            value = line.split(":", 1)[1].strip().strip('"')
    flush()
    return tokens


def _fmt_pct(numerator: float, denominator: float) -> str:
    """Percentage to one decimal place; '0.0' when denominator is zero."""
    if denominator == 0:
        return "0.0"
    return f"{(numerator / denominator) * 100:.1f}"


def _fmt_ratio_pct(ratio: float) -> str:
    return f"{ratio * 100:.1f}"


def _year(iso: str) -> str:
    return iso.split("-", 1)[0]


def generate_variables(
    project_root: Path | str,
    *,
    require_analysis_outputs: bool = True,
    evidence_root: Path | str | None = None,
) -> dict[str, str]:
    """Compute the manuscript token table from ``analysis_output/`` artifacts.

    Args:
        project_root: Root of the blake project (contains ``analysis_output/``).
        require_analysis_outputs: When True (pipeline mode), raise
            :class:`AnalysisOutputsMissing` if any required artifact is absent.
            When False (draft mode), missing optional artifacts are skipped.
        evidence_root: Explicit read root for saved analysis and source custody.
            Defaults to project_root; never falls back to authoring artifacts.

    Returns:
        Mapping ``{TOKEN: value_string}`` covering every quantitative claim in
        the manuscript.
    """
    roots = manuscript_roots(project_root, evidence_root)
    root = roots.authoring
    ao = roots.analysis

    statistics = (
        _read_json(
            ao / "reports" / "statistics.json", required=require_analysis_outputs
        )
        or {}
    )
    completeness = (
        _read_json(
            ao / "reports" / "completeness_report.json",
            required=require_analysis_outputs,
        )
        or {}
    )
    manifest = (
        _read_json(ao / "corpus_manifest.json", required=require_analysis_outputs) or {}
    )
    source_cov = (
        _read_json(
            ao / "reports" / "source_coverage.json", required=require_analysis_outputs
        )
        or {}
    )
    text_metrics = (
        _read_json(
            ao / "visualizations" / "text_metrics.json",
            required=require_analysis_outputs,
        )
        or []
    )
    lexical_signature = (
        _read_json(
            ao / "visualizations" / "lexical_signature.json",
            required=require_analysis_outputs,
        )
        or {}
    )
    network = (
        _read_json(
            ao / "visualizations" / "theme_entity_network.json",
            required=require_analysis_outputs,
        )
        or {}
    )
    linkage = (
        _read_json(
            ao / "visualizations" / "text_image_linkage.json",
            required=require_analysis_outputs,
        )
        or []
    )
    image_depth = (
        _read_json(ao / "visualizations" / "image_depth.json", required=False) or []
    )
    authority_tiers = (
        _read_json(
            ao / "visualizations" / "source_authority_tiers.json", required=False
        )
        or []
    )
    chronology = (
        _read_json(
            ao / "visualizations" / "chronology.json", required=require_analysis_outputs
        )
        or []
    )
    pipeline = (
        _read_json(ao / "pipeline_summary.json", required=require_analysis_outputs)
        or {}
    )
    analysis_summary = (
        _read_json(ao / "analysis" / "analysis_summary.json", required=False) or {}
    )
    analysis_diagnostics = (
        _read_json(ao / "analysis" / "analysis_diagnostics.json", required=False) or {}
    )
    viz_summary = (
        _read_json(ao / "visualizations" / "visualization_summary.json", required=False)
        or {}
    )
    source_audit = _read_json(ao / "data" / "source_audit.json", required=False) or {}
    acquisition_review = (
        _read_json(ao / "data" / "evidence_acquisition_review.json", required=False)
        or {}
    )
    source_discovery = (
        _read_json(ao / "data" / "source_discovery.json", required=False) or []
    )
    nlp_diagnostics = build_nlp_diagnostics(roots.evidence)
    nlp_membership = validate_membership(
        nlp_diagnostics,
        publication=require_analysis_outputs,
        coverage_count=(
            int(completeness.get("with_text", 0)) if require_analysis_outputs else None
        ),
    )

    v: dict[str, str] = {}
    v.update(architecture_tokens())
    v.update(
        publication_tokens(
            roots.evidence,
            required=require_analysis_outputs
            and (root / "docs/manuscript/14_supplement_recoverability.md").exists(),
        )
    )
    v.update(
        _read_legal_claim_tokens(
            root / "docs" / "manuscript" / "legal_claim_ledger.yaml"
        )
    )

    # ---- Corpus inventory (statistics.json) ----
    total_works = int(statistics.get("total_works", 0))
    total_images = int(statistics.get("total_images", 0))
    work_types: dict[str, int] = statistics.get("work_types", {})
    v["WORKS_PRESENT"] = str(total_works)
    v["TOTAL_IMAGES"] = str(total_images)
    v["ILLUMINATED_BOOKS"] = str(int(work_types.get("illuminated_book", 0)))
    v["LETTERS_COUNT"] = str(int(work_types.get("letter", 0)))
    v["WORK_TYPE_COUNT"] = str(len(work_types))

    date_range = statistics.get("date_range", {})
    earliest = (
        _year(date_range.get("earliest", "")) if date_range.get("earliest") else ""
    )
    latest = _year(date_range.get("latest", "")) if date_range.get("latest") else ""
    v["DATE_EARLIEST"] = earliest
    v["DATE_LATEST"] = latest
    if earliest and latest:
        v["DATE_SPAN_YEARS"] = str(int(latest) - int(earliest))

    # ---- Target ledger / coverage (completeness + manifest + source_coverage) ----
    coverage_counts = (
        completeness.get("coverage_counts")
        or manifest.get("coverage_counts")
        or source_cov.get("coverage_counts")
        or {}
    )
    target_total = int(
        completeness.get("target_total")
        or coverage_counts.get("total")
        or source_cov.get("coverage_counts", {}).get("total", 0)
    )
    present = int(coverage_counts.get("present", total_works))
    missing = int(coverage_counts.get("missing", 0))
    partial = int(coverage_counts.get("partial", 0))
    v["TARGET_TOTAL"] = str(target_total)
    v["TARGETS_PRESENT"] = str(present)
    v["WORKS_MISSING"] = str(missing)
    v["WORKS_PARTIAL"] = str(partial)
    v["COVERAGE_PCT"] = _fmt_pct(present, target_total)
    represented = max(
        target_total - missing - int(coverage_counts.get("unverified", 0)), 0
    )
    v["TARGETS_REPRESENTED"] = str(represented)
    v["REPRESENTATION_PCT"] = _fmt_pct(represented, target_total)
    v["TARGET_PROFILE"] = str(
        completeness.get("target_profile")
        or source_cov.get("target_profile")
        or "canonical"
    )
    v["TARGET_VERSION"] = str(
        completeness.get("target_version") or source_cov.get("target_version") or ""
    )
    v["COVERAGE_STATUS"] = str(
        completeness.get("coverage_status")
        or source_cov.get("coverage_status")
        or "partial"
    )

    # Coverage metrics (fractions in the completeness report)
    v["TEXT_COVERAGE_PCT"] = _fmt_ratio_pct(
        float(completeness.get("text_coverage", 0.0))
    )
    v["IMAGE_COVERAGE_PCT"] = _fmt_ratio_pct(
        float(completeness.get("image_coverage", 0.0))
    )
    v["PROCESSING_COVERAGE_PCT"] = _fmt_ratio_pct(
        float(completeness.get("processing_coverage", 0.0))
    )
    works_with_text = int(completeness.get("with_text", 0))
    works_with_images = int(completeness.get("with_images", 0))
    link_by_id = {r.get("work_id"): int(r.get("image_count", 0)) for r in linkage}
    text_by_id = {r.get("work_id"): bool(r.get("has_text")) for r in text_metrics}
    works_with_both = sum(
        1
        for work_id, has_text in text_by_id.items()
        if has_text and link_by_id.get(work_id, 0) > 0
    )
    v["WORKS_WITH_TEXT"] = str(works_with_text)
    v["WORKS_WITH_IMAGES"] = str(works_with_images)
    v["WORKS_WITH_BOTH"] = str(works_with_both)
    v["TEXTLESS_WORKS"] = str(max(total_works - works_with_text, 0))
    v["IMAGELESS_WORKS"] = str(max(total_works - works_with_images, 0))

    # ---- Source providers ----
    registered = source_cov.get("registered_sources") or {}
    if isinstance(registered, dict):
        registered_keys = list(registered.keys())
    else:
        registered_keys = list(registered)
    v["SOURCE_REGISTRY_COUNT"] = str(len(registered_keys))
    present_sources = statistics.get("sources", {})
    v["SOURCE_PRESENT_COUNT"] = str(len(present_sources))
    # Provider names, human-readable, in registry order.
    provider_names = [
        _SOURCE_LABELS.get(k, k.replace("_", " ").title()) for k in registered_keys
    ]
    v["SOURCE_PROVIDERS_CSV"] = _english_join(provider_names)
    # The single source backing the present works.
    present_source_keys = list(present_sources.keys())
    if present_source_keys:
        v["PRESENT_SOURCE_NAME"] = _SOURCE_LABELS.get(
            present_source_keys[0], present_source_keys[0].replace("_", " ").title()
        )
    discovered_by_source = Counter(
        str(row.get("source_type", "")) for row in source_discovery
    )
    v["SOURCE_RECORDS_DISCOVERED"] = str(
        int(
            source_audit.get("records_discovered") or sum(discovered_by_source.values())
        )
    )
    source_matched = int(source_audit.get("matched_target_count") or 0)
    source_unmatched_ids = list(source_audit.get("unmatched_target_ids") or [])
    source_unmatched = int(
        source_audit.get("unmatched_target_count") or len(source_unmatched_ids)
    )
    v["SOURCE_MATCHED_TARGETS"] = str(source_matched)
    v["SOURCE_MATCHED_PCT"] = _fmt_pct(source_matched, target_total)
    v["SOURCE_UNMATCHED_TARGETS"] = str(source_unmatched)
    v["SOURCE_UNMATCHED_IDS_CSV"] = _english_join(source_unmatched_ids)
    v["DUPLICATE_ALIAS_COUNT"] = str(
        int(source_audit.get("duplicate_alias_count") or 0)
    )
    live = source_audit.get("live") or {}
    checked_urls = live.get("checked_urls") or []
    ok_urls = sum(1 for row in checked_urls if row.get("ok"))
    v["SOURCE_URL_CHECKED"] = str(len(checked_urls))
    v["SOURCE_URL_OK"] = str(ok_urls)
    v["SOURCE_URL_NONOK"] = str(max(len(checked_urls) - ok_urls, 0))
    provider_discovery = source_audit.get("provider_discovery") or {}
    provider_rows = provider_discovery.get("providers") or []
    provider_failures = [
        row for row in provider_rows if str(row.get("status") or "") != "completed"
    ]
    v["PROVIDER_DISCOVERY_COUNT"] = str(
        int(provider_discovery.get("provider_count") or len(provider_rows))
    )
    v["PROVIDER_DISCOVERY_FAILURES"] = str(
        int(provider_discovery.get("failure_count") or len(provider_failures))
    )
    v["PROVIDER_DISCOVERY_RECORDS"] = str(
        int(provider_discovery.get("record_count") or 0)
    )
    v["PROVIDER_DISCOVERY_TABLE_ROWS"] = _provider_discovery_table_rows(provider_rows)
    for token, key in [
        ("GITHUB_WORK_XML_COUNT", "github_work_xml_count"),
        ("GITHUB_WORK_PREFIX_COUNT", "github_work_prefix_count"),
        ("GITHUB_CONTENTS_RESOURCE_COUNT", "github_contents_resource_count"),
    ]:
        if live.get(key) is not None:
            v[token] = str(live[key])
    archive_sample = live.get("archive_api_sample") or []
    if archive_sample:
        v["ARCHIVE_API_SAMPLE_LIMIT"] = str(len(archive_sample))
        v["ARCHIVE_API_SAMPLE_COUNT"] = str(len(archive_sample))
        v["ARCHIVE_API_SAMPLE_OK"] = str(
            sum(1 for row in archive_sample if row.get("ok"))
        )
    archive_metadata = (
        source_audit.get("metadata_enrichment_report")
        or live.get("archive_metadata_enrichment")
        or {}
    )
    v["ARCHIVE_METADATA_STATUS"] = str(archive_metadata.get("status") or "unrecorded")
    v["ARCHIVE_METADATA_ATTEMPTED"] = str(int(archive_metadata.get("attempted") or 0))
    v["ARCHIVE_METADATA_SUCCEEDED"] = str(int(archive_metadata.get("succeeded") or 0))
    v["ARCHIVE_METADATA_FAILED"] = str(int(archive_metadata.get("failed") or 0))
    v["ARCHIVE_METADATA_SKIPPED"] = str(
        int(archive_metadata.get("skipped_after_budget") or 0)
    )
    v["ARCHIVE_METADATA_TIMEOUTS"] = str(
        int(archive_metadata.get("timeout_count") or 0)
    )
    v["ARCHIVE_METADATA_DISABLED_REASON"] = str(
        archive_metadata.get("disabled_reason") or "none"
    )
    v["ARCHIVE_METADATA_FALLBACK_SOURCE"] = str(
        archive_metadata.get("fallback_source_used")
        or "target ledger + GitHub XML inventory"
    )
    if discovered_by_source:
        for source_key, count in discovered_by_source.items():
            token = "DISCOVERY_RECORDS_" + source_key.upper().replace("-", "_")
            v[token] = str(count)
    missing_evidence = source_audit.get("missing_evidence") or []
    missing_summary = source_audit.get("missing_evidence_summary") or {}
    missing_by_type = missing_summary.get("by_evidence_type") or {}
    v["MISSING_EVIDENCE_CANDIDATES"] = str(
        int(missing_summary.get("candidate_count") or len(missing_evidence))
    )
    v["MISSING_EVIDENCE_TARGETS"] = str(
        int(
            missing_summary.get("target_count")
            or len({row.get("target_id") for row in missing_evidence})
        )
    )
    v["MISSING_EVIDENCE_TEXT"] = str(int(missing_by_type.get("text") or 0))
    v["MISSING_EVIDENCE_IMAGE"] = str(int(missing_by_type.get("image") or 0))
    v["MISSING_EVIDENCE_SOURCE_MATCH"] = str(
        int(missing_by_type.get("source_match") or 0)
    )
    target_reviews = acquisition_review.get("target_reviews") or []
    review_candidates = [
        candidate
        for target_review in target_reviews
        for candidate in target_review.get("candidates", [])
    ]
    manual_review_candidates = [
        row
        for row in review_candidates
        if str(row.get("lead_status") or "") == "manual_review"
        or str(row.get("action_taken") or "").startswith("manual_review:")
        or str(row.get("status") or "") == "manual_review"
    ]
    v["ACQUISITION_REVIEW_SCHEMA_VERSION"] = str(
        acquisition_review.get("schema_version") or "unavailable"
    )
    v["ACQUISITION_REVIEW_TARGETS"] = str(
        int(acquisition_review.get("target_count") or len(target_reviews))
    )
    v["ACQUISITION_REVIEW_UNRESOLVED_TARGETS"] = str(
        int(acquisition_review.get("unresolved_target_count") or 0)
    )
    v["ACQUISITION_REVIEW_CANDIDATES"] = str(
        int(acquisition_review.get("candidate_count") or len(review_candidates))
    )
    v["ACQUISITION_REVIEW_MANUAL_CANDIDATES"] = str(len(manual_review_candidates))

    # ---- Text metrics (per-work word counts, vocabulary richness) ----
    by_id = {row.get("work_id", row.get("id", "")): row for row in text_metrics}
    text_metric_rows = [
        r for r in text_metrics if r.get("has_text") and int(r.get("word_count", 0)) > 0
    ]
    word_counts = [int(r.get("word_count", 0)) for r in text_metric_rows]
    unique_words = [int(r.get("unique_words", 0)) for r in text_metric_rows]
    richness = [float(r.get("vocabulary_richness", 0.0)) for r in text_metric_rows]
    v["WORDS_TOTAL"] = str(sum(word_counts))
    v["UNIQUE_WORDS_TOTAL"] = str(sum(unique_words))
    if richness:
        v["VOCAB_RICHNESS_MEAN"] = f"{sum(richness) / len(richness):.3f}"
        v["VOCAB_RICHNESS_MIN"] = f"{min(richness):.3f}"
        v["VOCAB_RICHNESS_MAX"] = f"{max(richness):.3f}"
    if word_counts:
        v["WORDS_MIN"] = str(min(word_counts))
        v["WORDS_MAX"] = str(max(word_counts))
    lexical_terms = lexical_signature.get("top_terms") or []
    lexical_bigrams = lexical_signature.get("top_bigrams") or []
    lexical_works = lexical_signature.get("works") or []
    v["LEXICAL_SIGNATURE_METHOD"] = str(lexical_signature.get("method") or "")
    v["LEXICAL_TEXT_WORKS"] = str(int(lexical_signature.get("text_work_count") or 0))
    v["LEXICAL_TOKEN_COUNT"] = str(
        int(lexical_signature.get("lexical_token_count") or 0)
    )
    v["LEXICAL_DISTINCT_TERMS"] = str(int(lexical_signature.get("distinct_terms") or 0))
    v["LEXICAL_DENSITY_MEAN"] = (
        f"{float(lexical_signature.get('mean_lexical_density') or 0.0):.3f}"
    )
    v["LEXICAL_TOP_TERMS_CSV"] = _english_join(
        [str(row.get("term")) for row in lexical_terms[:8]]
    )
    v["LEXICAL_TOP_BIGRAMS_CSV"] = _english_join(
        [str(row.get("phrase")) for row in lexical_bigrams[:6]]
    )
    if lexical_works:
        densest = max(
            lexical_works,
            key=lambda row: (
                float(row.get("lexical_density") or 0.0),
                int(row.get("lexical_token_count") or 0),
            ),
        )
        v["LEXICAL_DENSEST_WORK"] = str(densest.get("title") or densest.get("work_id"))
    v["LEXICAL_SIGNATURE_TABLE_ROWS"] = _lexical_signature_table_rows(lexical_signature)
    # Per-fixture word counts, keyed by stable work_id.
    _id_token = {
        "fixture-letters": "WORDS_LETTERS",
        "fixture-songsie": "WORDS_SONGSIE",
        "fixture-mhh": "WORDS_MHH",
    }
    for wid, token in _id_token.items():
        if wid in by_id:
            v[token] = str(int(by_id[wid].get("word_count", 0)))

    embedding = nlp_diagnostics.get("embedding", {})
    entity_diag = nlp_diagnostics.get("entities", {})
    text_diag = nlp_diagnostics.get("text_analysis", {})
    sentiment_counts = text_diag.get("sentiment_counts") or {}
    label_counts = entity_diag.get("label_counts") or {}
    top_entities = entity_diag.get("top_entities") or []
    v["NLP_SAVED_TEXT_WORKS"] = str(nlp_membership["saved"])
    v["NLP_DIAGNOSTIC_PRODUCER_VERSION"] = nlp_diagnostics["producer"][
        "software_version"
    ]
    v["NLP_DIAGNOSTIC_SOURCE_SHA256"] = nlp_diagnostics["producer"]["source_sha256"]
    v["NLP_MISSING_TEXT_WORKS"] = str(nlp_membership["missing"])
    v["NLP_FILTERED_TEXT_WORKS"] = str(nlp_membership["filtered"])
    v["NLP_EXCLUDED_CACHE_WORKS"] = str(nlp_membership["excluded"])
    v["NLP_MEMBERSHIP_SHA256"] = (
        nlp_diagnostics["membership"].get("source_sha256") or "unavailable"
    )
    v["NLP_EMBEDDING_METHOD"] = (
        "row-normalized, centered TF-IDF covariance principal-component projection"
    )
    v["NLP_EMBEDDING_WORKS"] = str(int(embedding.get("work_count") or 0))
    v["NLP_EMBEDDING_FEATURES"] = str(int(embedding.get("feature_count") or 0))
    v["NLP_PCA_PC1_PCT"] = _fmt_ratio_pct(float(embedding.get("variance_pc1") or 0.0))
    v["NLP_PCA_PC2_PCT"] = _fmt_ratio_pct(float(embedding.get("variance_pc2") or 0.0))
    v["NLP_PCA_TOTAL_PCT"] = _fmt_ratio_pct(
        float(embedding.get("variance_pc1") or 0.0)
        + float(embedding.get("variance_pc2") or 0.0)
    )
    v["NLP_EMBEDDING_TOP_TERMS_PC1"] = _english_join(
        list(embedding.get("top_terms_pc1") or [])
    )
    v["NLP_EMBEDDING_TOP_TERMS_PC2"] = _english_join(
        list(embedding.get("top_terms_pc2") or [])
    )
    v["TEXT_ANALYSIS_ARTIFACTS"] = str(int(text_diag.get("artifact_count") or 0))
    v["SENTIMENT_POSITIVE_WORKS"] = str(int(sentiment_counts.get("positive") or 0))
    v["SENTIMENT_NEUTRAL_WORKS"] = str(int(sentiment_counts.get("neutral") or 0))
    v["SENTIMENT_NEGATIVE_WORKS"] = str(int(sentiment_counts.get("negative") or 0))
    v["READABILITY_FLESCH_MEAN"] = (
        f"{float(text_diag.get('mean_flesch_reading_ease') or 0.0):.1f}"
    )
    v["TOPIC_MODEL_COMPONENTS"] = str(int(text_diag.get("topic_model_count") or 0))
    v["ENTITY_ANALYSIS_ARTIFACTS"] = str(int(entity_diag.get("artifact_count") or 0))
    v["ENTITY_WORKS_WITH_ENTITIES"] = str(
        int(entity_diag.get("works_with_entities") or 0)
    )
    v["ENTITY_MENTION_COUNT"] = str(int(entity_diag.get("mention_count") or 0))
    v["ENTITY_DISTINCT_COUNT"] = str(int(entity_diag.get("distinct_entity_count") or 0))
    v["ENTITY_TYPE_COUNT"] = str(len(label_counts))
    v["ENTITY_LABELS_CSV"] = _english_join(
        [str(label).lower() for label in label_counts]
    )
    v["ENTITY_TOP_CSV"] = _english_join(
        [str(row.get("text")) for row in top_entities[:8]]
    )

    # ---- Theme / entity network ----
    nodes = network.get("nodes", [])
    edges = network.get("edges", [])
    theme_nodes = [n for n in nodes if n.get("type") == "theme"]
    work_nodes = [n for n in nodes if n.get("type") == "work"]
    v["NETWORK_NODES"] = str(len(nodes))
    v["NETWORK_EDGES"] = str(len(edges))
    v["THEME_COUNT"] = str(len(theme_nodes))
    v["NETWORK_ENTITY_COUNT"] = str(sum(node.get("type") == "entity" for node in nodes))
    v["WORK_NODE_COUNT"] = str(len(work_nodes))
    v["THEMES_CSV"] = _english_join([n.get("label", "") for n in theme_nodes])

    # ---- Text-image linkage ----
    linked_total = sum(int(r.get("image_count", 0)) for r in linkage)
    linked_works = sum(1 for r in linkage if int(r.get("image_count", 0)) > 0)
    v["LINKED_IMAGES_TOTAL"] = str(linked_total)
    v["LINKED_WORKS"] = str(linked_works)

    depth_rows = [
        row
        for row in image_depth
        if int(row.get("resolved_object_count") or 0) > 0
        or int(row.get("downloaded_image_count") or row.get("local_image_count") or 0)
        > 0
    ]

    v["IMAGE_DEPTH_WORKS"] = str(len(depth_rows))
    v["IMAGE_DEPTH_RESOLVED_OBJECTS"] = str(
        sum(int(row.get("resolved_object_count") or 0) for row in depth_rows)
    )
    v["IMAGE_DEPTH_DOWNLOADED_IMAGES"] = str(
        sum(local_image_count(row) for row in depth_rows)
    )
    v["IMAGE_DEPTH_COMPLETE_WORKS"] = str(
        sum(1 for row in depth_rows if row.get("image_depth_status") == "complete")
    )
    v["IMAGE_DEPTH_PARTIAL_WORKS"] = str(
        sum(1 for row in depth_rows if row.get("image_depth_status") == "partial")
    )
    authority_counts = {
        str(row.get("authority_tier") or "unrecorded"): int(row.get("work_count") or 0)
        for row in authority_tiers
    }
    if not authority_counts and manifest.get("work_records"):
        authority_counts = Counter(
            str(record.get("source_authority_tier") or "unrecorded")
            for record in manifest.get("work_records") or []
        )
    v["SOURCE_AUTHORITY_TIER_COUNT"] = str(len(authority_counts))
    v["ARCHIVE_PRIMARY_WORKS"] = str(int(authority_counts.get("archive_primary") or 0))
    v["FALLBACK_TEXT_VALIDATED_WORKS"] = str(
        int(authority_counts.get("fallback_text_validated") or 0)
    )
    v["CORROBORATING_SOURCE_WORKS"] = str(
        int(authority_counts.get("corroborating_or_legacy") or 0)
    )

    # ---- Pipeline ----
    phases = pipeline.get("phases", [])
    v["PHASE_COUNT"] = str(len(phases))
    v["RUN_STATUS"] = str(pipeline.get("status", ""))
    completed_phases = [p for p in phases if p.get("status") == "completed"]
    v["PHASES_COMPLETED"] = str(len(completed_phases))
    # Visualization profile
    v["VIZ_GENERATED"] = str(
        int(viz_summary.get("visualizations_generated", 0))
        or len(viz_summary.get("datasets", []))
    )
    v["VIZ_AVAILABLE"] = str(len(viz_summary.get("available_visualizations", [])) or 0)

    analysis_diag_summary = analysis_diagnostics.get("summary") or {}
    analysis_errors = analysis_summary.get("errors") or []
    diagnostic_errors = (analysis_diagnostics.get("errors") or {}).get("error_count")
    summary_errors = analysis_diag_summary.get("error_count")
    summary_per_analysis = analysis_diag_summary.get("per_analysis") or {}
    skipped_works = sum(
        int(row.get("skipped_works") or 0)
        for row in summary_per_analysis.values()
        if isinstance(row, dict)
    )
    diagnostic_sections = [
        key
        for key in analysis_diagnostics
        if key
        not in {
            "schema_version",
            "generated_at",
            "requested_analysis_types",
            "status",
        }
    ]
    v["ANALYSIS_STATUS"] = str(analysis_summary.get("status") or "unknown")
    v["ANALYSIS_RESULTS_CURRENT"] = (
        "yes" if analysis_summary.get("analysis_results_current") else "no"
    )
    analyzed_value = (
        analysis_diag_summary.get("works_with_results")
        if analysis_diag_summary
        else analysis_summary.get("works_analyzed")
    )
    total_value = (
        analysis_diag_summary.get("works_total")
        if analysis_diag_summary
        else analysis_summary.get("works_total")
    )
    v["ANALYSIS_WORKS_ANALYZED"] = str(int(analyzed_value or 0))
    v["ANALYSIS_WORKS_TOTAL"] = str(int(total_value or 0))
    v["ANALYSIS_SKIPPED_WORKS"] = str(skipped_works)
    v["ANALYSIS_ERROR_COUNT"] = str(
        int(
            summary_errors
            if summary_errors is not None
            else (
                diagnostic_errors
                if diagnostic_errors is not None
                else len(analysis_errors)
            )
        )
    )
    v["ANALYSIS_ERROR_CATEGORIES"] = (
        _english_join(
            [
                str(key).replace("_", " ")
                for key, value in sorted(
                    (analysis_diag_summary.get("error_categories") or {}).items()
                )
                if int(value or 0) > 0
            ]
        )
        or "none"
    )
    v["ANALYSIS_TYPES_CSV"] = _english_join(
        [
            str(value).replace("_", " ")
            for value in analysis_summary.get("analysis_types") or []
        ]
    )
    v["ANALYSIS_DIAGNOSTIC_SECTIONS"] = _english_join(
        [str(value).replace("_", " ") for value in sorted(diagnostic_sections)]
    )

    # ---- Injected table rows (markdown) ----
    v["WORKS_TABLE_ROWS"] = _works_table_rows(chronology, by_id, linkage)
    v["COVERAGE_TABLE_ROWS"] = _coverage_table_rows(coverage_counts)
    target_records = (
        source_cov.get("target_records") or manifest.get("target_records") or []
    )
    v["WORK_TYPE_TABLE_ROWS"] = _work_type_table_rows(work_types, total_works)
    v["CATEGORY_COVERAGE_TABLE_ROWS"] = _category_coverage_table_rows(target_records)
    v["EVIDENCE_GAP_TABLE_ROWS"] = _evidence_gap_table_rows(target_records)
    v["SOURCE_AUDIT_TABLE_ROWS"] = _source_audit_table_rows(source_audit)
    v["SOURCE_DISCOVERY_TABLE_ROWS"] = _source_discovery_table_rows(
        discovered_by_source
    )
    v["MISSING_EVIDENCE_TABLE_ROWS"] = _missing_evidence_table_rows(missing_evidence)
    v["TOP_TEXT_TABLE_ROWS"] = _top_text_table_rows(text_metrics, linkage)
    v["TOP_IMAGE_TABLE_ROWS"] = _top_image_table_rows(linkage)

    # Drop empty-string optional tokens so they surface as unresolved if used.
    return {k: val for k, val in v.items() if val != ""}


def _english_join(items: list[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _cell(value: object) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ")


def _work_type_table_rows(work_types: dict[str, int], total_works: int) -> str:
    rows: list[str] = []
    total = total_works or 1
    for work_type, count in sorted(
        work_types.items(), key=lambda item: (-int(item[1]), item[0])
    ):
        label = str(work_type).replace("_", " ")
        rows.append(
            f"| {_cell(label)} | {int(count)} | {_fmt_pct(int(count), total)} |"
        )
    return "\n".join(rows)


def _category_coverage_table_rows(target_records: list[dict[str, Any]]) -> str:
    by_category: dict[str, Counter[str]] = defaultdict(Counter)
    for record in target_records:
        by_category[str(record.get("category") or "uncategorized")][
            str(record.get("status") or "")
        ] += 1

    rows: list[str] = []
    for category, counts in sorted(by_category.items()):
        total = sum(counts.values())
        rows.append(
            "| "
            + " | ".join(
                [
                    _cell(category.replace("_", " ")),
                    str(counts.get("present", 0)),
                    str(counts.get("partial", 0)),
                    str(counts.get("missing", 0)),
                    str(total),
                    _fmt_pct(counts.get("present", 0), total or 1),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def _evidence_gap_table_rows(target_records: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for record in target_records:
        if record.get("status") == "present":
            continue
        notes = record.get("notes") or []
        if not notes and record.get("status") == "missing":
            notes = [
                "No matching local work or source record in the current discovery set."
            ]
        rows.append(
            "| "
            + " | ".join(
                [
                    _cell(record.get("target_id")),
                    _cell(record.get("title")),
                    _cell(record.get("category", "").replace("_", " ")),
                    _cell(record.get("status")),
                    _cell("; ".join(str(note) for note in notes)),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def _source_audit_table_rows(source_audit: dict[str, Any]) -> str:
    live = source_audit.get("live") or {}
    rows: list[str] = []
    for item in live.get("checked_urls") or []:
        status = item.get("status")
        status_text = str(status) if status is not None else "unavailable"
        rows.append(
            "| "
            + " | ".join(
                [
                    _cell(item.get("label")),
                    status_text,
                    "yes" if item.get("ok") else "no",
                    _cell(item.get("content_type")),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def _source_discovery_table_rows(discovered_by_source: Counter[str]) -> str:
    rows: list[str] = []
    for source_key, count in sorted(
        discovered_by_source.items(), key=lambda item: (-item[1], item[0])
    ):
        label = _SOURCE_LABELS.get(source_key, source_key.replace("_", " ").title())
        rows.append(f"| {_cell(label)} | {count} |")
    return "\n".join(rows)


def _provider_discovery_table_rows(provider_rows: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for row in provider_rows:
        rows.append(
            "| "
            + " | ".join(
                [
                    _cell(row.get("provider")),
                    _cell(row.get("source_type")),
                    _cell(row.get("status")),
                    str(int(row.get("record_count") or 0)),
                    _cell(row.get("error") or ""),
                ]
            )
            + " |"
        )
    if not rows:
        rows.append("| none | none | skipped | 0 | no live provider discovery |")
    return "\n".join(rows)


def _missing_evidence_table_rows(
    missing_evidence: list[dict[str, Any]],
    *,
    limit: int | None = None,
) -> str:
    def display(value: Any, *, identifier: bool = False) -> str:
        text = _cell(value)
        if not identifier:
            text = text.replace("_", " ")
        separator = "\u200b" if identifier else "\u00ad"
        return re.sub(
            r"\w{9,}",
            lambda match: separator.join(
                match.group()[start : start + 8]
                for start in range(0, len(match.group()), 8)
            ),
            text,
        )

    rows: list[str] = []
    ordered = sorted(
        missing_evidence,
        key=lambda row: (
            str(row.get("target_id") or ""),
            str(row.get("evidence_type") or ""),
            -float(row.get("match_confidence") or 0.0),
        ),
    )
    for row in ordered[:limit] if limit is not None else ordered:
        status = row.get("http_status")
        rows.append(
            "| "
            + " | ".join(
                [
                    display(row.get("target_id"), identifier=True),
                    display(row.get("title")),
                    display(row.get("evidence_type")),
                    display(row.get("candidate_source")),
                    str(status) if status is not None else "not checked",
                    f"{float(row.get('match_confidence') or 0.0):.2f}",
                    display(row.get("action_taken")),
                ]
            )
            + " |"
        )
    if not rows:
        rows.append("| none | no missing evidence | n/a | n/a | n/a | n/a | n/a |")
    return "\n".join(rows)


def _top_text_table_rows(
    text_metrics: list[dict[str, Any]],
    linkage: list[dict[str, Any]],
    *,
    limit: int = 12,
) -> str:
    image_by_id = {
        row.get("work_id"): int(row.get("image_count", 0)) for row in linkage
    }
    rows: list[str] = []
    text_rows = [
        row
        for row in text_metrics
        if row.get("has_text") and int(row.get("word_count", 0)) > 0
    ]
    for row in sorted(
        text_rows, key=lambda item: int(item.get("word_count", 0)), reverse=True
    )[:limit]:
        richness = float(row.get("vocabulary_richness", 0.0))
        rows.append(
            "| "
            + " | ".join(
                [
                    _cell(row.get("title", row.get("work_id"))),
                    str(int(row.get("word_count", 0))),
                    str(int(row.get("unique_words", 0))),
                    f"{richness:.3f}",
                    str(image_by_id.get(row.get("work_id"), 0)),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def _lexical_signature_table_rows(
    lexical_signature: dict[str, Any],
    *,
    limit: int = 12,
) -> str:
    rows: list[str] = []
    for row in (lexical_signature.get("top_terms") or [])[:limit]:
        rows.append(
            "| "
            + " | ".join(
                [
                    _cell(row.get("term")),
                    str(int(row.get("count", 0))),
                    str(int(row.get("document_frequency", 0))),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def _top_image_table_rows(
    linkage: list[dict[str, Any]],
    *,
    limit: int = 12,
) -> str:
    rows: list[str] = []
    image_rows = [row for row in linkage if int(row.get("image_count", 0)) > 0]
    for row in sorted(
        image_rows, key=lambda item: int(item.get("image_count", 0)), reverse=True
    )[:limit]:
        rows.append(
            "| "
            + " | ".join(
                [
                    _cell(row.get("title", row.get("work_id"))),
                    str(int(row.get("image_count", 0))),
                    "yes" if row.get("has_text") else "no",
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def _works_table_rows(
    chronology: list[dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    linkage: list[dict[str, Any]],
) -> str:
    """Markdown table body: one row per present work, ordered chronologically."""
    link_by_id = {r.get("work_id"): int(r.get("image_count", 0)) for r in linkage}
    rows: list[str] = []
    for entry in chronology:
        wid = entry.get("id", "")
        metrics = by_id.get(wid, {})
        title = entry.get("title", metrics.get("title", wid))
        year = _year(entry.get("date", "")) if entry.get("date") else ""
        wtype = str(entry.get("work_type", "")).replace("_", " ")
        words = metrics.get("word_count", "")
        richness = metrics.get("vocabulary_richness", "")
        richness_str = f"{float(richness):.3f}" if richness != "" else ""
        images = link_by_id.get(wid, 0)
        rows.append(
            f"| {_cell(title)} | {year} | {_cell(wtype)} | {words} | {richness_str} | {images} |"
        )
    return "\n".join(rows)


def _coverage_table_rows(coverage_counts: dict[str, Any]) -> str:
    """Markdown table body for the coverage-status breakdown."""
    order = ["present", "partial", "missing", "duplicate", "unverified"]
    total = int(coverage_counts.get("total", 0)) or 1
    rows: list[str] = []
    for status in order:
        count = int(coverage_counts.get(status, 0))
        pct = _fmt_pct(count, total)
        rows.append(f"| {status} | {count} | {pct} |")
    return "\n".join(rows)


def save_variables(variables: dict[str, str], out_path: Path | str) -> Path:
    """Write the token table to ``out_path`` as pretty JSON (sorted keys)."""
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(variables, indent=2, sort_keys=True), encoding="utf-8")
    return path
