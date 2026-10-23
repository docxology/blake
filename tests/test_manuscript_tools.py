import asyncio
import json
import re
import shutil
from pathlib import Path

import pytest


from manuscript_tools.figures import (
    BRIEF_FIELDS,
    FIGURE_BRIEFS,
    FIGURES,
    STATISTICAL_FIELDS,
    _pipeline_strip_label,
    compute_figure_statistics,
)
from manuscript_tools.variables import AnalysisOutputsMissing, generate_variables
from manuscript_tools.nlp_diagnostics import build_nlp_diagnostics
from scripts.acquire_missing_texts import TARGETS, clean_raw_wikitext


def test_missing_evidence_table_wraps_long_identifiers_without_changing_identity():
    from manuscript_tools.variables import _missing_evidence_table_rows

    rendered = _missing_evidence_table_rows(
        [
            {
                "target_id": "biblicaltemperas",
                "title": "Illustrations",
                "evidence_type": "source_match",
                "candidate_source": "Archive",
                "action_taken": "manual_review",
            }
        ]
    )
    cells = [cell.strip() for cell in rendered.strip("|").split("|")]
    assert "\u200b" in cells[0]
    assert cells[0].replace("\u200b", "") == "biblicaltemperas"
    assert "\u00ad" in cells[1]
    assert cells[1].replace("\u00ad", "") == "Illustrations"
    assert cells[2] == "source match"
    assert cells[-1] == "manual review"


@pytest.fixture(scope="module")
def manuscript_fixture_root(tmp_path_factory):
    """Offline synthetic corpus for projection tests, never publication evidence."""
    from blake.corpus import BlakeCorpus, CorpusConfig, SourceRegistry

    root = tmp_path_factory.mktemp("manuscript-fixture")
    data_dir = root / "blake_data"
    output_dir = root / "analysis_output"
    corpus = BlakeCorpus(
        data_dir, output_dir=output_dir, source_registry=SourceRegistry()
    )
    config = CorpusConfig(
        data_dir=data_dir, output_dir=output_dir, quick=True, fixture_mode="always"
    )
    summary = asyncio.run(corpus.run(config))
    assert summary.status == "completed"
    manifest = json.loads((output_dir / "corpus_manifest.json").read_text())
    assert manifest["fixture_mode"] is True
    audit_path = output_dir / "data" / "source_audit.json"
    audit = json.loads(audit_path.read_text())
    # Synthetic observations exercise token projection without contacting endpoints.
    audit["test_fixture"] = True
    audit["live"]["archive_api_sample"] = [{"ok": True}, {"ok": False}]
    assert audit["live"]["enabled"] is False
    audit_path.write_text(json.dumps(audit))
    # Legal claims are source-owned; they are independent of corpus measurements.
    legal_dir = root / "docs" / "manuscript"
    legal_dir.mkdir(parents=True)
    shutil.copyfile(
        Path(__file__).resolve().parents[1]
        / "docs"
        / "manuscript"
        / "legal_claim_ledger.yaml",
        legal_dir / "legal_claim_ledger.yaml",
    )
    return root


def test_nlp_diagnostics_builds_embedding_and_entity_summary(tmp_path):
    root = tmp_path
    text_dir = root / "blake_data" / "texts"
    analysis_dir = root / "blake_data" / "analysis"
    viz_dir = root / "analysis_output" / "visualizations"
    text_dir.mkdir(parents=True)
    analysis_dir.mkdir(parents=True)
    viz_dir.mkdir(parents=True)
    (viz_dir / "text_metrics.json").write_text(
        json.dumps(
            [
                {"work_id": "a", "title": "Alpha Song"},
                {"work_id": "b", "title": "Beta Vision"},
                {"work_id": "c", "title": "Gamma Night"},
            ]
        ),
        encoding="utf-8",
    )
    (text_dir / "a.txt").write_text(
        "Los vision fire city city prophet morning flame",
        encoding="utf-8",
    )
    (text_dir / "b.txt").write_text(
        "Los Urizen iron law night night shadow city",
        encoding="utf-8",
    )
    (text_dir / "c.txt").write_text(
        "Lamb child garden morning song song delight",
        encoding="utf-8",
    )
    (analysis_dir / "a_ontological_analysis.json").write_text(
        json.dumps(
            {
                "ontological_analysis": {
                    "entities": [
                        {"text": "Los", "label": "PERSON", "mention_count": 2},
                        {"text": "London", "label": "GPE", "mention_count": 1},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    (analysis_dir / "b_ontological_analysis.json").write_text(
        json.dumps(
            {
                "ontological_analysis": {
                    "entities": [
                        {"text": "Urizen", "label": "PERSON", "mention_count": 3}
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    for stem, sentiment in [("a", "positive"), ("b", "negative"), ("c", "neutral")]:
        (analysis_dir / f"{stem}_text_analysis.json").write_text(
            json.dumps(
                {
                    "sentiment": {"sentiment": sentiment},
                    "readability": {"flesch_reading_ease": 70.0},
                    "topics": {"n_topics": 2},
                }
            ),
            encoding="utf-8",
        )

    diagnostics = build_nlp_diagnostics(root)

    assert diagnostics["embedding"]["work_count"] == 3
    assert diagnostics["embedding"]["feature_count"] > 0
    assert len(diagnostics["embedding"]["points"]) == 3
    assert diagnostics["entities"]["works_with_entities"] == 2
    assert diagnostics["entities"]["mention_count"] == 6
    assert diagnostics["text_analysis"]["sentiment_counts"] == {
        "negative": 1,
        "neutral": 1,
        "positive": 1,
    }


def test_long_evidence_tables_live_in_supplements():
    root = Path(__file__).resolve().parents[1]
    main = (root / "docs" / "manuscript" / "04_results_coverage.md").read_text(
        encoding="utf-8"
    )
    evidence_supplement = (
        root / "docs" / "manuscript" / "10_supplement_evidence_gaps.md"
    ).read_text(encoding="utf-8")
    missing_supplement = (
        root / "docs" / "manuscript" / "11_supplement_missing_evidence.md"
    ).read_text(encoding="utf-8")

    assert "{{EVIDENCE_GAP_TABLE_ROWS}}" not in main
    assert "{{MISSING_EVIDENCE_TABLE_ROWS}}" not in main
    assert "{{EVIDENCE_GAP_TABLE_ROWS}}" in evidence_supplement
    assert "{{MISSING_EVIDENCE_TABLE_ROWS}}" in missing_supplement


def test_reproducibility_uses_generated_archive_sample_limit(manuscript_fixture_root):
    root = Path(__file__).resolve().parents[1]
    reproducibility = (
        root / "docs" / "manuscript" / "08_reproducibility.md"
    ).read_text(encoding="utf-8")
    variables = generate_variables(manuscript_fixture_root)

    assert variables["ARCHIVE_API_SAMPLE_LIMIT"] == "2"
    assert variables["ARCHIVE_API_SAMPLE_OK"] == "1"
    assert "--limit 8" not in reproducibility
    assert (
        "Fresh remote acquisition can produce a different inventory" in reproducibility
    )
    assert "--data-dir blake_data/publication/reproduction" in reproducibility
    assert (
        variables["ARCHIVE_API_SAMPLE_LIMIT"] == variables["ARCHIVE_API_SAMPLE_COUNT"]
    )
    for token in [
        "PROVIDER_DISCOVERY_FAILURES",
        "PROVIDER_DISCOVERY_TABLE_ROWS",
        "ARCHIVE_METADATA_STATUS",
        "ARCHIVE_METADATA_ATTEMPTED",
        "ARCHIVE_METADATA_SUCCEEDED",
        "ARCHIVE_METADATA_FAILED",
        "ARCHIVE_METADATA_SKIPPED",
        "ARCHIVE_METADATA_FALLBACK_SOURCE",
        "ANALYSIS_STATUS",
        "ANALYSIS_RESULTS_CURRENT",
        "ANALYSIS_WORKS_ANALYZED",
        "ANALYSIS_WORKS_TOTAL",
        "ANALYSIS_SKIPPED_WORKS",
        "ANALYSIS_ERROR_COUNT",
        "ANALYSIS_ERROR_CATEGORIES",
        "ANALYSIS_DIAGNOSTIC_SECTIONS",
        "ACQUISITION_REVIEW_SCHEMA_VERSION",
        "ACQUISITION_REVIEW_UNRESOLVED_TARGETS",
        "ACQUISITION_REVIEW_MANUAL_CANDIDATES",
    ]:
        assert token in variables
        assert variables[token] != ""


def test_reproducibility_uses_existing_template_validation_command():
    root = Path(__file__).resolve().parents[1]
    reproducibility = (
        root / "docs" / "manuscript" / "08_reproducibility.md"
    ).read_text(encoding="utf-8")

    # The reproducibility doc must reference the real sibling-template validation
    # command. Assert on the documented command path rather than a machine-specific
    # absolute filesystem location (which would leak a home path and only pass on one
    # machine).
    assert "04_render_html.py" not in reproducibility
    assert "scripts/pipeline/stage_04_validate.py" in reproducibility
    assert "scripts/pipeline/stage_03_render.py" in reproducibility
    assert "projects/active/blake" in reproducibility
    assert "--project active/blake" in reproducibility
    assert "--project blake" not in reproducibility


def test_abstract_is_unnumbered_block_scoped_and_artifact_bound():
    root = Path(__file__).resolve().parents[1]
    abstract = (root / "docs" / "manuscript" / "00_abstract.md").read_text(
        encoding="utf-8"
    )
    preamble = (root / "docs" / "manuscript" / "preamble.md").read_text(
        encoding="utf-8"
    )

    assert abstract.startswith("# Abstract {#sec:abstract .unnumbered}")
    assert "\t" not in abstract
    assert "{{ANALYSIS_WORKS_ANALYZED}}/{{ANALYSIS_WORKS_TOTAL}}" in abstract
    assert "not completeness of Blake's oeuvre" in abstract
    assert "unverified authorship" in abstract
    assert "source-image mosaics remain local" in abstract
    assert r"\setlength{\parindent}{0pt}" in preamble
    assert r"\setlength{\parskip}" in preamble


def test_render_typography_uses_compact_pdf_layout():
    root = Path(__file__).resolve().parents[1]
    config = (root / "docs" / "manuscript" / "config.yaml").read_text(encoding="utf-8")
    preamble = (root / "docs" / "manuscript" / "preamble.md").read_text(
        encoding="utf-8"
    )

    assert 'geometry: "left=0.48in,right=0.48in,top=0.6in,bottom=0.65in"' in config
    assert r"\changefontsize[13.2pt]{10.5pt}" in preamble


def test_manuscript_title_and_section_titles_are_evidence_bounded():
    root = Path(__file__).resolve().parents[1]
    config = (root / "docs" / "manuscript" / "config.yaml").read_text(encoding="utf-8")
    headings = "\n".join(
        line
        for path in sorted((root / "docs" / "manuscript").glob("*.md"))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("#")
    )

    assert 'title: "Mapping William Blake’s Works"' in config
    assert (
        'subtitle: "Evidence ledgers, source provenance, text-image diagnostics, and rights-bounded release controls"'
        in config
    )
    for title in [
        "# Introduction: Making Blake Coverage Measurable {#sec:introduction}",
        "# Methods: Target Ledger, Source Custody, and Offline Analysis {#sec:methods_pipeline}",
        "# Methods: Local Text, Image, Cross-Modal, and Theme Diagnostics {#sec:methods_analysis}",
        "# Results: Target Coverage, Provenance, and Evidence Gaps {#sec:results_coverage}",
        "# Results: Text Scale, Visual Evidence, and Cross-Modal Diagnostics {#sec:results_text}",
        "# Discussion: What the Corpus Can and Cannot Claim {#sec:discussion}",
        "# Rights and Distribution Controls {#sec:legal_distribution}",
        "# Limitations: Target Scope, Source Drift, and Missing Evidence {#sec:limitations}",
        "# Conclusion: Evidence-Bounded Blake Corpus Mapping {#sec:conclusion}",
    ]:
        assert title in headings


def test_manuscript_overclaims_are_negated_or_scoped():
    root = Path(__file__).resolve().parents[1]
    manuscript_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((root / "docs" / "manuscript").glob("*.md"))
        if path.name != "AGENTS.md"
    )

    forbidden = [
        "complete Blake corpus",
        "complete corpus",
        "comprehensive Blake corpus",
        "fully analyzed Blake",
        "all Blake works",
        "latent structure",
        "exhaustively analyzed Blake's works",
    ]
    allowed_boundary_phrases = [
        "not a complete Blake corpus",
        "not a claim to have completed or exhaustively analyzed Blake's works",
        "not a claim to have completed or exhaustively analyzed Blake’s works",
    ]
    scrubbed = manuscript_text
    for phrase in allowed_boundary_phrases:
        scrubbed = scrubbed.replace(phrase, "")

    for phrase in forbidden:
        assert phrase.lower() not in scrubbed.lower(), phrase


def test_reproducibility_prepares_a_fresh_store_before_offline_analysis():
    root = Path(__file__).resolve().parents[1]
    reproducibility = (
        root / "docs" / "manuscript" / "08_reproducibility.md"
    ).read_text(encoding="utf-8")

    prepare_index = reproducibility.index("scripts/prepare_manuscript_epoch.py")
    analysis_index = reproducibility.index("scripts/reproduce_manuscript_analysis.py")
    assert prepare_index < analysis_index
    assert "--seed {{ANALYSIS_SEED}}" in reproducibility
    assert "no synthetic fixtures" in reproducibility
    assert "preserves Blake's analysis environment" in reproducibility


def test_public_docs_use_canonical_local_regeneration_command():
    root = Path(__file__).resolve().parents[1]
    docs = [
        root / "README.md",
        root / "blake" / "README.md",
        root / "docs" / "index.md",
        root / "docs" / "quickstart.md",
        root / "docs" / "user-guide.md",
        root / "docs" / "api-reference.md",
        root / "docs" / "developer-guide.md",
        root / "docs" / "guides" / "download-workflow.md",
        root / "docs" / "manuscript" / "AGENTS.md",
    ]
    canonical = "blake corpus run --skip-download --output-dir analysis_output"

    for path in docs:
        text = path.read_text(encoding="utf-8")
        assert canonical in text, path
        assert "blake corpus run --skip-download --skip-analysis" not in text, path
        assert "uv run python run_all.py --quick" not in text, path


def test_public_docs_document_corpus_cli_and_artifact_contract():
    root = Path(__file__).resolve().parents[1]
    api_reference = (root / "docs" / "api-reference.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    docs_index = (root / "docs" / "index.md").read_text(encoding="utf-8")
    combined = "\n".join([api_reference, readme, docs_index])

    for command in [
        "blake corpus run",
        "blake corpus status",
        "blake corpus visualize",
        "blake corpus audit-sources",
        "blake corpus acquire-evidence",
        "blake corpus private-release-preflight",
        "blake corpus public-release-preflight",
        "blake corpus public-release-package",
    ]:
        assert command in combined

    for artifact in [
        "source_discovery_health.json",
        "source_audit.json",
        "evidence_acquisition_review.json",
        "analysis_summary.json",
        "analysis_diagnostics.json",
        "figure_registry.json",
        "private_release_preflight",
        "rights_gate_report",
        "public_release_preflight",
        "public_release_package",
    ]:
        assert artifact in combined

    assert "publish_action: none" in api_reference


def test_todo_remains_forward_only_public_release_scope():
    root = Path(__file__).resolve().parents[1]
    todo = (root / "TODO.md").read_text(encoding="utf-8").lower()

    for required in [
        "public release decision",
        "fallback-text corroboration",
        "partial-evidence pass",
        "distribution rights gate",
    ]:
        assert required in todo

    for stale in [
        "completed visualization",
        "schema 1.4",
        "dataset_statistics",
        "private preflight implementation",
        "render pdf",
    ]:
        assert stale not in todo


def test_wikisource_fallback_script_is_scoped_to_text_only_missing_targets():
    target_ids = {target.work_id for target in TARGETS}
    assert target_ids == {"poetical-sketches", "everlasting-gospel"}
    assert all(
        target.source_url.startswith("https://en.wikisource.org/wiki/")
        for target in TARGETS
    )
    assert all(target.work_type == "poem" for target in TARGETS)


def test_raw_wikisource_cleanup_preserves_poem_text_without_templates():
    raw = (
        "{{header\n"
        " | title = The Everlasting Gospel\n"
        "}}\n"
        "__TOC__\n"
        "{{poem-on| fragment }}\n"
        "<poem>\n"
        "There is not one Moral Virtue.\n"
        "[[Author:William Blake|William Blake]]\n"
        "</poem>\n"
        "{{PD-old}}\n"
    )
    text = clean_raw_wikitext(raw)

    assert "There is not one Moral Virtue." in text
    assert "William Blake" in text
    assert "{{" not in text
    assert "<poem>" not in text


def test_public_metadata_avoids_complete_corpus_overclaims():
    root = Path(__file__).resolve().parents[1]
    surfaces = [
        root / "pyproject.toml",
        root / "README.md",
        root / "blake" / "README.md",
        root / "blake" / "cli.py",
        root / "blake" / "gui" / "gui.py",
        root / "blake" / "interactive_orchestrator.py",
        root / "blake" / "downloader" / "downloader.py",
        root / "blake_viewer.py",
        root / "scripts" / "download_complete_corpus.py",
        root / "docs" / "COMPREHENSIVE_SYSTEM_SUMMARY.md",
        root / "docs" / "api-reference.md",
        root / "docs" / "user-guide.md",
    ]
    forbidden = [
        "William Blake's complete works",
        "Comprehensive Analysis Platform for William Blake's Works",
        "comprehensive, modular platform for acquiring, analyzing, and visualizing William Blake's works",
        "fully organized with proper documentation",
        "comprehensive API-based approach",
        "Run comprehensive analysis on all works",
        "complete corpus download",
        "explore the complete works",
    ]

    for path in surfaces:
        text = path.read_text(encoding="utf-8")
        for phrase in forbidden:
            assert phrase.lower() not in text.lower(), f"{phrase!r} found in {path}"


def test_spec_preserves_source_governed_rights_bounded_scope():
    root = Path(__file__).resolve().parents[1]
    spec = (root / "docs" / "spec.md").read_text(encoding="utf-8")

    assert (
        "Key sources to audit, acquire from when permitted, or record as corroborating leads"
        in spec
    )
    assert "rights-gated" in spec
    assert (
        "Raw assets only when source terms, rights metadata, and release policy permit redistribution"
        in spec
    )
    assert "source-governed exploration and analysis" in spec
    assert "exhaustive, interactive exploration" not in spec
    assert "All raw assets (original scans, images, texts)" not in spec


def test_discussion_conclusion_avoid_then_now_framing():
    root = Path(__file__).resolve().parents[1]
    discussion = (root / "docs" / "manuscript" / "06_discussion.md").read_text(
        encoding="utf-8"
    )
    conclusion = (root / "docs" / "manuscript" / "09_conclusion.md").read_text(
        encoding="utf-8"
    )
    combined = f"{discussion}\n{conclusion}".lower()

    assert "current run acquired" not in combined
    assert "current run analyzes" not in combined
    assert "current run analyzed" not in combined
    assert "no longer" not in combined
    assert "fixture-only" not in combined
    assert "*blake* now" not in combined


def test_language_visualization_figures_are_registered_and_cited():
    root = Path(__file__).resolve().parents[1]
    figure_names = {name for name, _builder in FIGURES}
    results = (root / "docs" / "manuscript" / "05_results_text.md").read_text(
        encoding="utf-8"
    )

    assert "lexical_signature" in figure_names
    assert "text_image_density" in figure_names
    assert "{#fig:lexical_signature}" in results
    assert "{#fig:text_image_density}" in results
    assert "{{LEXICAL_SIGNATURE_TABLE_ROWS}}" in results


def test_supplemental_visual_mosaics_are_registered_and_cited():
    root = Path(__file__).resolve().parents[1]
    figure_names = {name for name, _builder in FIGURES}
    supplement = (
        root / "docs" / "manuscript" / "12_supplement_visual_mosaics.md"
    ).read_text(encoding="utf-8")

    expected = {
        "all_acquired_images_mosaic",
        "work_area_image_mosaics",
        "work_evidence_profile_grid",
        "image_depth_by_work",
        "image_depth_by_area",
        "source_authority_tiers",
    }
    assert expected <= figure_names
    private = {"all_acquired_images_mosaic", "work_area_image_mosaics"}
    for name in expected - private:
        assert f"{{#fig:{name}}}" in supplement
    for name in private:
        assert f"{name}.png" in supplement
        assert f"{{#fig:{name}}}" not in supplement
        assert f"](../output/figures/{name}.png)" not in supplement
    assert (
        "excluded from the public manuscript, HTML, and release archives" in supplement
    )


def test_figure_registry_briefs_cover_every_manuscript_figure():
    root = Path(__file__).resolve().parents[1]
    figure_names = {name for name, _builder in FIGURES}
    registry_path = root / "output" / "figures" / "figure_registry.json"

    assert figure_names == set(FIGURE_BRIEFS)
    for name, brief in FIGURE_BRIEFS.items():
        assert BRIEF_FIELDS <= brief.keys(), name
        for field in BRIEF_FIELDS:
            assert brief[field], f"{name}.{field} is empty"

    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        assert registry["schema_version"] == "1.5"
        registry_names = {
            Path(figure["filename"]).stem for figure in registry["figures"]
        }
        omitted = {
            "all_acquired_images_mosaic",
            "work_area_image_mosaics",
            "source_audit",
            "chronology",
        }
        expected = (
            figure_names - omitted
            if registry.get("scope") == "public"
            else figure_names
        )
        assert registry_names == expected
        for figure in registry["figures"]:
            assert BRIEF_FIELDS <= figure.keys(), figure["filename"]
            assert STATISTICAL_FIELDS <= figure.keys(), figure["filename"]
            assert figure["accessibility_summary"]
            assert isinstance(figure.get("statistics"), dict), figure["filename"]
            assert figure["statistics"], figure["filename"]


def test_figure_statistics_are_json_ready_and_non_empty(manuscript_fixture_root):
    analysis_output = manuscript_fixture_root / "analysis_output"

    def walk(payload):
        if isinstance(payload, dict):
            for value in payload.values():
                yield from walk(value)
        elif isinstance(payload, list):
            for value in payload:
                yield from walk(value)
        else:
            yield payload

    for name, _builder in FIGURES:
        stats = compute_figure_statistics(analysis_output, name)
        assert isinstance(stats, dict), name
        assert stats, name
        assert None not in set(walk(stats)), name
        json.dumps(stats)

    source_stats = compute_figure_statistics(analysis_output, "source_audit")
    assert source_stats["analysis_status"] in {"completed", "skipped"}
    assert "manual_review_candidate_count" in source_stats
    assert "archive_metadata_status" in source_stats

    evidence_stats = compute_figure_statistics(analysis_output, "evidence_gaps")
    assert "review_candidate_count" in evidence_stats
    assert "manual_review_candidate_count" in evidence_stats

    pipeline_stats = compute_figure_statistics(analysis_output, "pipeline_dag")
    assert pipeline_stats["phase_records"]


def test_pipeline_dag_explains_reused_phase_states(manuscript_fixture_root):
    root = Path(__file__).resolve().parents[1]
    methods = (root / "docs" / "manuscript" / "02_methods_pipeline.md").read_text(
        encoding="utf-8"
    )
    brief = FIGURE_BRIEFS["pipeline_dag"]
    stats = compute_figure_statistics(
        manuscript_fixture_root / "analysis_output", "pipeline_dag"
    )
    records = {record["name"]: record for record in stats["phase_records"]}

    assert "skipped acquisition stays visible" not in brief["claim"].lower()
    assert "skipped/acquired states" not in methods
    assert "reused the retained local evidence" in methods
    assert "Analysis and downstream reporting generated fresh artifacts" in methods
    assert records["acquisition"]["action"] in {
        "reused local corpus",
        "generated this run",
    }
    assert records["analysis"]["action"] in {
        "deep analyzer not rerun",
        "generated this run",
    }
    assert stats["phase_records"]


def test_pipeline_dag_strip_labels_follow_saved_phase_state():
    assert (
        _pipeline_strip_label(
            {
                "name": "acquisition",
                "action_class": "reused",
                "action": "reused local corpus",
            }
        )
        == "REUSED CORPUS"
    )
    assert (
        _pipeline_strip_label(
            {
                "name": "analysis",
                "action_class": "generated",
                "action": "generated this run",
            }
        )
        == "GENERATED"
    )
    assert (
        _pipeline_strip_label(
            {
                "name": "analysis",
                "action_class": "not rerun",
                "action": "deep analyzer not rerun",
            }
        )
        == "NOT RERUN"
    )


def test_registered_figures_are_cited_in_manuscript_sources():
    root = Path(__file__).resolve().parents[1]
    manuscript_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((root / "docs" / "manuscript").glob("*.md"))
    )

    registered = {name for name, _builder in FIGURES}
    embedded = set(re.findall(r"\{#fig:([a-z_]+)\}", manuscript_text))
    omitted = {
        "all_acquired_images_mosaic",
        "work_area_image_mosaics",
        "source_audit",
        "chronology",
    }
    assert embedded == registered - omitted


def test_forward_todo_has_no_resolved_missing_target_task():
    root = Path(__file__).resolve().parents[1]
    todo = (root / "TODO.md").read_text(encoding="utf-8").lower()

    assert "missing target resolution" not in todo
    assert "fallback-text corroboration" in todo


def test_legal_distribution_section_separates_code_from_source_materials(
    manuscript_fixture_root,
):
    root = Path(__file__).resolve().parents[1]
    legal = (root / "docs" / "manuscript" / "06a_legal_distribution.md").read_text(
        encoding="utf-8"
    )
    rights_matrix = (
        root / "docs" / "manuscript" / "13_supplement_rights_matrix.md"
    ).read_text(encoding="utf-8")
    claim_ledger = (root / "docs" / "manuscript" / "legal_claim_ledger.yaml").read_text(
        encoding="utf-8"
    )
    references = (root / "docs" / "manuscript" / "references.bib").read_text(
        encoding="utf-8"
    )
    readme = (root / "README.md").read_text(encoding="utf-8")
    variables = generate_variables(manuscript_fixture_root)

    assert "not legal advice" in legal
    assert "William Blake died in {{BLAKE_DEATH_YEAR}}" in legal
    assert (
        "The code can be open source; the entire local evidence cache is not" in legal
    )
    assert "Keep raw Archive files and full image mirrors out" in legal
    assert "notice and assent" in legal
    assert "CC BY-SA {{WIKIMEDIA_CC_BY_SA_VERSION}}" in legal
    assert "[@sec:supp_rights_matrix]" in legal
    assert "blake_data/" in legal
    assert "usc_pre_1978_unpublished_section" in claim_ledger
    assert "life_plus_term_years" in claim_ledger
    assert variables["BLAKE_DEATH_YEAR"] == "1827"
    assert variables["EU_DSM_PUBLIC_DOMAIN_ARTICLE"] == "14"
    assert variables["WIKIMEDIA_CC_BY_SA_VERSION"] == "4.0"
    assert "Image mosaics and visual supplements" in rights_matrix
    assert "source-compatible thumbnails" in rights_matrix
    assert "document venue-specific fair use" in rights_matrix
    for citation_key in [
        "feist_rural",
        "eudirective2019dsm",
        "specht_netscape",
        "nguyen_barnes",
        "hathitrust",
        "google_books",
        "mazzone_copyfraud",
        "petri_public_domain_museum",
        "wallace_culture_copyright",
        "candela_collections_data",
    ]:
        assert f"{{{citation_key}," in references
    assert "source-provider terms" in readme


def test_generated_manuscript_has_no_unresolved_body_tokens():
    root = Path(__file__).resolve().parents[1]
    output_dir = root / "output" / "manuscript"
    token_pattern = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")

    for path in sorted(output_dir.glob("*.md")):
        if path.name in {"README.md", "SYNTAX.md"}:
            continue
        text = path.read_text(encoding="utf-8")
        assert not token_pattern.search(text), f"unresolved token in {path}"


def test_pipeline_variables_reject_missing_analysis_outputs(tmp_path):
    with pytest.raises(AnalysisOutputsMissing, match="statistics.json"):
        generate_variables(tmp_path)


def test_cover_reads_canonical_manuscript_source(tmp_path, monkeypatch):
    from PIL import Image
    from manuscript_tools import cover

    source_path = (
        tmp_path / "docs" / "manuscript" / "assets" / "cover_blakean_source.png"
    )
    source_path.parent.mkdir(parents=True)
    Image.new("RGB", (2, 2)).save(source_path)
    observed = []

    def source_image(path):
        observed.append(path)
        return Image.new("RGB", (2, 2))

    def unexpected_fallback():
        pytest.fail("Canonical source exists; fallback must not replace it")

    monkeypatch.setattr(cover, "_cover_from_source", source_image)
    monkeypatch.setattr(cover, "_draw_cover", unexpected_fallback)
    result = cover.generate_cover(tmp_path)
    assert observed == [source_path]
    provenance = json.loads(result["provenance"].read_text())
    assert provenance["model_tool_provenance"]["source_image_path"] == str(source_path)
    assert result["cover"].exists()


def test_public_only_generation_excludes_private_mosaics_and_matches_the_paper(
    manuscript_fixture_root,
):
    from manuscript_tools.figures import generate_all_figures

    written = generate_all_figures(manuscript_fixture_root, public_only=True)
    omitted = {
        "all_acquired_images_mosaic",
        "work_area_image_mosaics",
        "source_audit",
        "chronology",
    }
    assert {path.stem for path in written} == {name for name, _ in FIGURES} - omitted
    assert all(path.is_file() and path.stat().st_size > 0 for path in written)
    for name in omitted:
        assert not (
            manuscript_fixture_root / "output/figures" / (name + ".png")
        ).exists()
    registry = json.loads(
        (manuscript_fixture_root / "output/figures/figure_registry.json").read_text()
    )
    assert registry["scope"] == "public"
    for figure in registry["figures"]:
        assert figure["filename"] == figure["path"]
        assert Path(figure["path"]).name == figure["path"]
        assert figure["alt_text"] == figure["accessibility_summary"]
