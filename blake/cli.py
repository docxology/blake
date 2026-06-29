"""
Command-line interface for Blake package.
"""

import asyncio
import click
from pathlib import Path
import logging
import json

from . import __version__
from .corpus import BlakeCorpus, CorpusConfig
from .corpus.evidence_acquisition import acquire_from_audit
from .corpus.public_release import (
    write_public_release_package,
    write_public_release_preflight,
)
from .corpus.release_preflight import write_private_release_preflight
from .corpus.source_audit import provider_reason_code
from .models import ExportConfig, SourceType

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _run_async(coro):
    try:
        return asyncio.run(coro)
    finally:
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())


def _parse_max_images(_ctx, _param, value):
    if value is None:
        return 1
    text = str(value).strip().lower()
    if text in {"none", "all", "unlimited"}:
        return None
    try:
        parsed = int(text)
    except ValueError as exc:
        raise click.BadParameter("use a positive integer or 'none'") from exc
    if parsed < 1:
        raise click.BadParameter("use a positive integer or 'none'")
    return parsed


@click.group()
@click.version_option(__version__)
@click.option(
    "--data-dir",
    type=click.Path(),
    default="blake_data",
    help="Directory to store Blake data",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default="analysis_output",
    help="Directory for corpus pipeline outputs",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def main(ctx, data_dir, output_dir, verbose):
    """Blake: target-aware corpus workflow for William Blake research."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    ctx.ensure_object(dict)
    ctx.obj["data_dir"] = Path(data_dir)
    ctx.obj["output_dir"] = Path(output_dir)
    ctx.obj["blake"] = BlakeCorpus(Path(data_dir), output_dir=Path(output_dir))


@main.group(
    help=(
        "Run and inspect the source-governed Blake corpus workflow; "
        "coverage and release claims come from generated artifacts."
    )
)
@click.pass_context
def corpus(ctx):
    pass


@corpus.command(
    "run",
    help=(
        "Regenerate the corpus artifact contract: discovery, local evidence, "
        "metadata, analysis, visualizations, exports, and reports."
    ),
)
@click.option(
    "--quick",
    is_flag=True,
    help="Run offline against local cache or deterministic fixtures; no live acquisition.",
)
@click.option(
    "--force", is_flag=True, help="Force acquisition when downloads are enabled"
)
@click.option("--output-dir", type=click.Path(), help="Directory for pipeline outputs")
@click.option(
    "--data-dir", type=click.Path(), help="Directory for raw and cached Blake data"
)
@click.option(
    "--skip-download",
    is_flag=True,
    help="Reuse existing local evidence instead of acquiring remote source assets.",
)
@click.option(
    "--skip-analysis",
    is_flag=True,
    help="Skip analysis and mark saved analysis results as not current",
)
@click.option("--skip-viz", is_flag=True, help="Skip visualization inventory/rendering")
@click.option("--skip-export", is_flag=True, help="Skip exports")
@click.option("--skip-reports", is_flag=True, help="Skip reports")
@click.option(
    "--target-profile",
    default="canonical",
    show_default=True,
    help="Corpus target ledger profile",
)
@click.option(
    "--fixture-mode",
    default="auto",
    show_default=True,
    type=click.Choice(["auto", "always", "never"]),
    help="Quick-mode fixture behavior",
)
@click.option(
    "--viz-profile",
    default="core",
    show_default=True,
    type=click.Choice(["inventory", "core", "full"]),
    help="Visualization artifact profile",
)
@click.option(
    "--archive-scope",
    default="archive-inventory",
    show_default=True,
    type=click.Choice(["target-ledger", "archive-inventory"]),
    help="Blake Archive discovery scope",
)
@click.option(
    "--image-mode",
    default="archive-all",
    show_default=True,
    type=click.Choice(["representative", "archive-all"]),
    help="Local Blake Archive image evidence depth; not redistribution permission.",
)
@click.option(
    "--image-dpi",
    default=300,
    show_default=True,
    type=int,
    help="Preferred image DPI for Archive image acquisition",
)
@click.option(
    "--max-images-per-work",
    default="none",
    show_default=True,
    callback=_parse_max_images,
    help="Maximum Archive images per work; use 'none' for all discoverable objects",
)
@click.option(
    "--format",
    "export_formats",
    multiple=True,
    type=click.Choice(["json", "csv", "pdf", "html", "markdown", "md", "parquet"]),
    help="Export format; can be repeated",
)
@click.pass_context
def corpus_run(
    ctx,
    quick,
    force,
    output_dir,
    data_dir,
    skip_download,
    skip_analysis,
    skip_viz,
    skip_export,
    skip_reports,
    target_profile,
    fixture_mode,
    viz_profile,
    archive_scope,
    image_mode,
    image_dpi,
    max_images_per_work,
    export_formats,
):
    blake = ctx.obj["blake"]
    data_path = Path(data_dir) if data_dir else ctx.obj["data_dir"]
    output_path = Path(output_dir) if output_dir else ctx.obj["output_dir"]
    if data_path != blake.data_dir or output_path != blake.output_dir:
        blake = BlakeCorpus(data_path, output_dir=output_path)
        ctx.obj["blake"] = blake

    config = CorpusConfig(
        data_dir=data_path,
        output_dir=output_path,
        quick=quick,
        force=force,
        skip_download=skip_download,
        skip_analysis=skip_analysis,
        skip_visualizations=skip_viz,
        skip_export=skip_export,
        skip_reports=skip_reports,
        target_profile=target_profile,
        fixture_mode=fixture_mode,
        viz_profile=viz_profile,
        archive_scope=archive_scope,
        image_mode=image_mode,
        image_dpi=image_dpi,
        max_images_per_work=max_images_per_work,
        export_formats=list(export_formats) or ["json"],
    )
    try:
        summary = _run_async(blake.run(config))
        click.echo(f"Corpus run {summary.status}: {summary.output_dir}")
        click.echo(f"Manifest: {summary.manifest_path}")
    except Exception as e:
        click.echo(f"Error running corpus pipeline: {e}", err=True)
        raise click.Abort()


@corpus.command("status", help="Inspect local corpus status and target coverage.")
@click.option(
    "--coverage", "show_coverage", is_flag=True, help="Print target coverage records"
)
@click.pass_context
def corpus_status(ctx, show_coverage):
    blake = ctx.obj["blake"]
    try:
        if show_coverage:
            payload = _run_async(blake.coverage())
        else:
            payload = _run_async(blake.status())
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    except Exception as e:
        click.echo(f"Error reading corpus status: {e}", err=True)
        raise click.Abort()


@corpus.command(
    "visualize",
    help=(
        "Generate local corpus visualization artifacts from manifest-backed "
        "evidence and diagnostics."
    ),
)
@click.option(
    "--profile",
    default="core",
    show_default=True,
    type=click.Choice(["core", "full"]),
    help="Visualization profile to render",
)
@click.option(
    "--output-dir", type=click.Path(), help="Directory for visualization outputs"
)
@click.option(
    "--data-dir", type=click.Path(), help="Directory for raw and cached Blake data"
)
@click.pass_context
def corpus_visualize(ctx, profile, output_dir, data_dir):
    blake = ctx.obj["blake"]
    data_path = Path(data_dir) if data_dir else ctx.obj["data_dir"]
    output_path = Path(output_dir) if output_dir else ctx.obj["output_dir"]
    if data_path != blake.data_dir or output_path != blake.output_dir:
        blake = BlakeCorpus(data_path, output_dir=output_path)
        ctx.obj["blake"] = blake
    blake.config.viz_profile = profile
    try:
        summary = _run_async(blake.visualize(profile))
        click.echo(f"Visualization profile {summary['profile']}: {summary['status']}")
        click.echo(f"Summary: {summary['artifacts'].get('visualization_summary')}")
    except Exception as e:
        click.echo(f"Error generating corpus visualizations: {e}", err=True)
        raise click.Abort()


@corpus.command(
    "audit-sources",
    help=(
        "Write a source audit with provider health, URL checks, and "
        "manual-review evidence candidates."
    ),
)
@click.option("--output-dir", type=click.Path(), help="Directory for audit outputs")
@click.option(
    "--data-dir", type=click.Path(), help="Directory for raw and cached Blake data"
)
@click.option(
    "--limit",
    default=12,
    show_default=True,
    help="Number of Archive API target records to sample",
)
@click.option(
    "--archive-scope",
    default="archive-inventory",
    show_default=True,
    type=click.Choice(["target-ledger", "archive-inventory"]),
    help="Blake Archive discovery scope",
)
@click.option(
    "--no-live", is_flag=True, help="Skip live URL checks and source discovery"
)
@click.pass_context
def corpus_audit_sources(ctx, output_dir, data_dir, limit, archive_scope, no_live):
    blake = ctx.obj["blake"]
    data_path = Path(data_dir) if data_dir else ctx.obj["data_dir"]
    output_path = Path(output_dir) if output_dir else ctx.obj["output_dir"]
    if data_path != blake.data_dir or output_path != blake.output_dir:
        blake = BlakeCorpus(data_path, output_dir=output_path)
        ctx.obj["blake"] = blake
    blake.config.archive_scope = archive_scope
    try:
        payload = _run_async(blake.audit_sources(include_live=not no_live, limit=limit))
        click.echo(f"Source audit written: {payload['path']}")
        click.echo(
            f"Targets matched: {payload.get('matched_target_count', 0)}/{payload.get('target_total', 0)}"
        )
        missing = payload.get("missing_evidence_summary") or {}
        click.echo(f"Missing-evidence candidates: {missing.get('candidate_count', 0)}")
        provider_discovery = payload.get("provider_discovery") or {}
        provider_failures = [
            row
            for row in provider_discovery.get("providers", [])
            if str(row.get("status") or "") != "completed"
        ]
        if provider_failures:
            click.echo(f"Provider warnings: {len(provider_failures)}")
            for row in provider_failures:
                click.echo(
                    "  - "
                    f"{row.get('provider')}: {row.get('status')} "
                    f"[{row.get('reason_code') or provider_reason_code(row)}] "
                    f"({row.get('error') or 'no error detail'})"
                )
        archive_metadata = (payload.get("live") or {}).get(
            "archive_metadata_enrichment"
        ) or {}
        if archive_metadata:
            click.echo(
                "Archive metadata enrichment: "
                f"{archive_metadata.get('status')} "
                f"({archive_metadata.get('succeeded', 0)}/"
                f"{archive_metadata.get('attempted', 0)} succeeded; "
                f"{archive_metadata.get('skipped_after_budget', 0)} skipped)"
            )
    except Exception as e:
        click.echo(f"Error auditing corpus sources: {e}", err=True)
        raise click.Abort()


@corpus.command(
    "acquire-evidence",
    help=(
        "Acquire only validated fallback text from source-audit candidates; "
        "manual source leads remain review-only."
    ),
)
@click.option(
    "--from-audit",
    "audit_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to analysis_output/data/source_audit.json.",
)
@click.option(
    "--data-dir", type=click.Path(), help="Directory for raw and cached Blake data"
)
@click.option(
    "--min-confidence",
    default=0.68,
    show_default=True,
    type=float,
    help="Minimum candidate confidence for automatic fallback acquisition.",
)
@click.option("--dry-run", is_flag=True, help="Fetch and validate without saving works")
@click.pass_context
def corpus_acquire_evidence(ctx, audit_path, data_dir, min_confidence, dry_run):
    data_path = Path(data_dir) if data_dir else ctx.obj["data_dir"]
    try:
        payload = acquire_from_audit(
            Path(audit_path),
            data_path,
            min_confidence=min_confidence,
            dry_run=dry_run,
        )
        click.echo(
            "Evidence acquisition: "
            f"{payload['accepted']} accepted, "
            f"{payload['rejected']} rejected, "
            f"{payload['skipped']} skipped"
        )
        if payload.get("path"):
            click.echo(f"Report: {payload['path']}")
        if payload.get("review_path"):
            click.echo(f"Review: {payload['review_path']}")
        for row in payload["results"]:
            if row["status"] == "accepted":
                click.echo(
                    f"accepted {row['target_id']}: {row['candidate_source']} "
                    f"({row['words']} words)"
                )
    except Exception as e:
        click.echo(f"Error acquiring evidence: {e}", err=True)
        raise click.Abort()


@corpus.command(
    "private-release-preflight",
    help=(
        "Write local-only private release and rights-gate reports; "
        "no publish, tag, deposit, or redistribution action is performed."
    ),
)
@click.option("--output-dir", type=click.Path(), help="Directory for report outputs")
@click.option(
    "--data-dir", type=click.Path(), help="Directory for raw and cached Blake data"
)
@click.option(
    "--target",
    default="private-github",
    show_default=True,
    help="Local preflight target label; no publish action is performed.",
)
@click.pass_context
def corpus_private_release_preflight(ctx, output_dir, data_dir, target):
    output_path = Path(output_dir) if output_dir else ctx.obj["output_dir"]
    data_path = Path(data_dir) if data_dir else ctx.obj["data_dir"]
    try:
        payload = write_private_release_preflight(
            output_dir=output_path,
            data_dir=data_path,
            target=target,
        )
        click.echo(f"Private release preflight: {payload['path']}")
        click.echo(f"Rights gate report: {payload['rights_gate_path']}")
        click.echo(f"Publish action: {payload['publish_action']}")
    except Exception as e:
        click.echo(f"Error writing private release preflight: {e}", err=True)
        raise click.Abort()


@corpus.command(
    "public-release-preflight",
    help=(
        "Write a non-publishing preflight for the GitHub/Zenodo public bundle "
        "and its rights-gated exclusions."
    ),
)
@click.option("--output-dir", type=click.Path(), help="Directory for report outputs")
@click.option(
    "--data-dir", type=click.Path(), help="Directory for raw and cached Blake data"
)
@click.option(
    "--release-dir",
    type=click.Path(),
    help="Directory for the public release bundle and metadata",
)
@click.option(
    "--destination",
    default="github+zenodo",
    show_default=True,
    type=click.Choice(["github+zenodo", "github", "zenodo"]),
    help="Release destination the bundle is being prepared for",
)
@click.pass_context
def corpus_public_release_preflight(
    ctx, output_dir, data_dir, release_dir, destination
):
    output_path = Path(output_dir) if output_dir else ctx.obj["output_dir"]
    data_path = Path(data_dir) if data_dir else ctx.obj["data_dir"]
    release_path = Path(release_dir) if release_dir else None
    try:
        payload = write_public_release_preflight(
            output_dir=output_path,
            data_dir=data_path,
            release_dir=release_path,
            destination=destination,
        )
        click.echo(f"Public release preflight: {payload['path']}")
        click.echo(f"Status: {payload['status']}")
        click.echo(f"Release dir: {payload['release_dir']}")
        click.echo(f"Included assets: {payload['included_asset_count']}")
        click.echo(f"Excluded assets: {payload['excluded_asset_count']}")
        click.echo(
            "Fallback corroboration targets: "
            f"{payload['corroborated_fallback_target_count']}"
        )
        if payload["blocked_reasons"]:
            click.echo("Blocked reasons:")
            for reason in payload["blocked_reasons"]:
                click.echo(f"  - {reason}")
    except Exception as e:
        click.echo(f"Error writing public release preflight: {e}", err=True)
        raise click.Abort()


@corpus.command(
    "public-release-package",
    help=(
        "Stage the GitHub/Zenodo public bundle metadata and checksums locally; "
        "does not publish or deposit."
    ),
)
@click.option("--output-dir", type=click.Path(), help="Directory for report outputs")
@click.option(
    "--data-dir", type=click.Path(), help="Directory for raw and cached Blake data"
)
@click.option(
    "--release-dir",
    type=click.Path(),
    help="Directory for the public release bundle and metadata",
)
@click.option(
    "--destination",
    default="github+zenodo",
    show_default=True,
    type=click.Choice(["github+zenodo", "github", "zenodo"]),
    help="Release destination the bundle is being prepared for",
)
@click.pass_context
def corpus_public_release_package(
    ctx, output_dir, data_dir, release_dir, destination
):
    output_path = Path(output_dir) if output_dir else ctx.obj["output_dir"]
    data_path = Path(data_dir) if data_dir else ctx.obj["data_dir"]
    release_path = Path(release_dir) if release_dir else None
    try:
        payload = write_public_release_package(
            output_dir=output_path,
            data_dir=data_path,
            release_dir=release_path,
            destination=destination,
        )
        if payload["status"] != "ready":
            click.echo(f"Public release package blocked: {payload['blocked_reasons']}")
            raise click.Abort()
        click.echo(f"Public release package: {payload['release_dir']}")
        click.echo(f"Bundle archive: {payload['archive_path']}")
        click.echo(f"Manifest: {payload['manifest_path']}")
        click.echo(f"GitHub notes: {payload['github_release_notes_path']}")
        click.echo(f"Zenodo metadata: {payload['zenodo_metadata_path']}")
        click.echo(f"Checksums: {payload['checksums_path']}")
        click.echo(
            "Fallback corroboration targets: "
            f"{payload['corroborated_fallback_target_count']}"
        )
    except click.Abort:
        raise
    except Exception as e:
        click.echo(f"Error writing public release package: {e}", err=True)
        raise click.Abort()


@main.command(
    help=(
        "Compatibility provider-fetch shortcut. Prefer `blake corpus run` for "
        "source audit, coverage, and release validation."
    )
)
@click.option(
    "--all",
    "download_all",
    is_flag=True,
    help="Fetch currently discoverable provider records",
)
@click.option("--work-id", help="Download specific work by ID")
@click.option(
    "--source",
    type=click.Choice(["blake_archive", "project_gutenberg", "internet_archive"]),
    help="Download from specific source",
)
@click.option("--force", is_flag=True, help="Force re-download even if works exist")
@click.pass_context
def download(ctx, download_all, work_id, source, force):
    """Download Blake works from various sources."""
    blake = ctx.obj["blake"]

    try:
        if download_all:
            click.echo("Fetching currently discoverable provider records...")
            works = _run_async(blake.download_all(force=force))
            click.echo(f"Downloaded {len(works)} works")

        elif work_id:
            click.echo(f"Downloading work: {work_id}")
            work = _run_async(blake.download_work(work_id, force=force))
            if work:
                click.echo(f"Downloaded: {work.metadata.title}")
            else:
                click.echo(f"Work {work_id} not found")

        elif source:
            click.echo(f"Downloading from {source}...")
            source_type = SourceType(source)
            works = _run_async(
                blake.downloader.download_from_source(source_type, force=force)
            )
            click.echo(f"Downloaded {len(works)} works from {source}")

        else:
            click.echo("Please specify --all, --work-id, or --source")

    except Exception as e:
        click.echo(f"Error downloading works: {e}", err=True)
        raise click.Abort()


@main.command(
    help=(
        "Compatibility local-analysis shortcut. Prefer `blake corpus run` so "
        "analysis summaries and diagnostics are regenerated together."
    )
)
@click.option("--work-id", help="Analyze specific work by ID")
@click.option("--all", "analyze_all", is_flag=True, help="Analyze all local works")
@click.option("--text", is_flag=True, help="Perform text analysis")
@click.option("--visual", is_flag=True, help="Perform visual analysis")
@click.option("--cross", is_flag=True, help="Perform cross analysis")
@click.pass_context
def analyze(ctx, work_id, analyze_all, text, visual, cross):
    """Analyze Blake works."""
    blake = ctx.obj["blake"]

    # Determine analysis types
    analysis_types = []
    if text:
        analysis_types.append("text")
    if visual:
        analysis_types.append("visual")
    if cross:
        analysis_types.append("cross")

    if not analysis_types:
        analysis_types = None  # All analyses

    try:
        if work_id:
            click.echo(f"Analyzing work: {work_id}")
            results = _run_async(blake.analyze_work(work_id, analysis_types))
            click.echo("Analysis completed")

            # Display basic results
            if "text_analysis" in results:
                basic_stats = results["text_analysis"].get("basic_stats", {})
                click.echo(f"Word count: {basic_stats.get('word_count', 0)}")
                click.echo(
                    f"Sentiment: {results['text_analysis'].get('sentiment', {}).get('sentiment', 'Unknown')}"
                )

        elif analyze_all:
            click.echo("Analyzing all local works...")
            results = _run_async(blake.analyze_all(analysis_types))
            click.echo(f"Analysis completed for {len(results)} works")

        else:
            click.echo("Please specify --work-id or --all")

    except Exception as e:
        click.echo(f"Error analyzing works: {e}", err=True)
        raise click.Abort()


@main.command()
@click.option("--host", default="localhost", help="Host to run GUI on")
@click.option("--port", default=8501, help="Port to run GUI on")
@click.pass_context
def explore(ctx, host, port):
    """Start interactive exploration GUI."""
    blake = ctx.obj["blake"]

    click.echo(f"Starting GUI on {host}:{port}")
    click.echo("Open your browser to view the interface")

    try:
        blake.explore(host=host, port=port)
    except Exception as e:
        click.echo(f"Error starting GUI: {e}", err=True)
        raise click.Abort()


@main.command(
    help=(
        "Compatibility export shortcut. Prefer corpus exports when provenance, "
        "manifest, and release checks must travel together."
    )
)
@click.option(
    "--format",
    "export_format",
    type=click.Choice(["json", "csv", "pdf", "html", "markdown", "md", "parquet"]),
    default="json",
    help="Export format (json, csv, pdf, html, markdown, parquet)",
)
@click.option("--output-dir", type=click.Path(), help="Output directory")
@click.option("--work-ids", help="Comma-separated list of work IDs to export")
@click.option("--include-images", is_flag=True, help="Include images in export")
@click.option("--include-analysis", is_flag=True, help="Include analysis results")
@click.option("--compress", is_flag=True, help="Compress output")
@click.pass_context
def export(
    ctx, export_format, output_dir, work_ids, include_images, include_analysis, compress
):
    """Export Blake works data."""
    blake = ctx.obj["blake"]

    # Set output directory
    if not output_dir:
        output_dir = Path("./exports")
    else:
        output_dir = Path(output_dir)

    # Parse work IDs
    filter_works = None
    if work_ids:
        filter_works = [id.strip() for id in work_ids.split(",")]

    # Create export config
    config = ExportConfig(
        format=export_format,
        output_dir=output_dir,
        include_images=include_images,
        include_analysis=include_analysis,
        compress=compress,
        filter_works=filter_works,
    )

    try:
        click.echo(f"Exporting works in {export_format} format...")
        output_path = _run_async(blake.export_works(config))
        click.echo(f"Export completed: {output_path}")

    except Exception as e:
        click.echo(f"Error exporting works: {e}", err=True)
        raise click.Abort()


@main.command()
@click.option("--query", help="Search query")
@click.option("--work-type", help="Filter by work type")
@click.option("--source", help="Filter by source")
@click.option("--has-images", is_flag=True, help="Filter works with images")
@click.option("--has-text", is_flag=True, help="Filter works with text")
@click.option("--limit", default=10, help="Maximum number of results")
@click.pass_context
def search(ctx, query, work_type, source, has_images, has_text, limit):
    """Search Blake works."""
    blake = ctx.obj["blake"]

    # Build filters
    filters = {}
    if work_type:
        filters["work_type"] = work_type
    if source:
        filters["source"] = source
    if has_images:
        filters["has_images"] = True
    if has_text:
        filters["has_text"] = True

    try:
        click.echo("Searching works...")
        results = _run_async(blake.search_works(query or "", filters))

        # Limit results
        results = results[:limit]

        if not results:
            click.echo("No works found")
            return

        click.echo(f"Found {len(results)} works:")
        for work in results:
            click.echo(f"- {work.metadata.title} ({work.metadata.work_type})")
            if work.metadata.creation_date:
                click.echo(
                    f"  Date: {work.metadata.creation_date.strftime('%Y-%m-%d')}"
                )
            click.echo(f"  Source: {work.metadata.source}")
            click.echo()

    except Exception as e:
        click.echo(f"Error searching works: {e}", err=True)
        raise click.Abort()


@main.command(
    help="Compatibility statistics shortcut over local corpus metadata."
)
@click.pass_context
def stats(ctx):
    """Show collection statistics."""
    blake = ctx.obj["blake"]

    try:
        click.echo("Loading collection statistics...")
        stats = _run_async(blake.get_statistics())

        click.echo("\n=== Collection Statistics ===")
        click.echo(f"Total works: {stats['total_works']}")
        click.echo(f"Total images: {stats['total_images']}")
        click.echo(f"Processed works: {stats['processed_works']}")

        if stats["work_types"]:
            click.echo("\nWork types:")
            for work_type, count in stats["work_types"].items():
                click.echo(f"  {work_type}: {count}")

        if stats["sources"]:
            click.echo("\nSources:")
            for source, count in stats["sources"].items():
                click.echo(f"  {source}: {count}")

        if stats["date_range"]:
            click.echo(
                f"\nDate range: {stats['date_range']['earliest']} - {stats['date_range']['latest']}"
            )

    except Exception as e:
        click.echo(f"Error loading statistics: {e}", err=True)
        raise click.Abort()


@main.command()
@click.option("--work-id", help="Show details for specific work")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
@click.pass_context
def info(ctx, work_id, output_json):
    """Show information about works."""
    blake = ctx.obj["blake"]

    try:
        if work_id:
            work = _run_async(blake.get_work(work_id))
            if not work:
                click.echo(f"Work {work_id} not found")
                return

            if output_json:
                work_dict = {
                    "id": work.id,
                    "metadata": work.metadata.model_dump(mode="json"),
                    "has_text": work.text_content is not None,
                    "num_images": len(work.images),
                    "is_processed": work.fully_processed,
                }
                click.echo(json.dumps(work_dict, indent=2, default=str))
            else:
                click.echo(f"Work: {work.metadata.title}")
                click.echo(f"Type: {work.metadata.work_type}")
                click.echo(f"Date: {work.metadata.creation_date or 'Unknown'}")
                click.echo(f"Source: {work.metadata.source}")
                if work.metadata.description:
                    click.echo(f"Description: {work.metadata.description}")
                click.echo(f"Text content: {'Yes' if work.text_content else 'No'}")
                click.echo(f"Images: {len(work.images)}")
                click.echo(f"Processed: {'Yes' if work.fully_processed else 'No'}")

        else:
            # Show all works
            works = _run_async(blake.get_all_works())

            if output_json:
                works_list = []
                for work in works:
                    works_list.append(
                        {
                            "id": work.id,
                            "title": work.metadata.title,
                            "work_type": work.metadata.work_type,
                            "creation_date": (
                                work.metadata.creation_date.isoformat()
                                if work.metadata.creation_date
                                else None
                            ),
                            "source": work.metadata.source,
                        }
                    )
                click.echo(json.dumps(works_list, indent=2, default=str))
            else:
                click.echo(f"Found {len(works)} works:")
                for work in works:
                    click.echo(f"- {work.metadata.title} ({work.metadata.work_type})")

    except Exception as e:
        click.echo(f"Error loading work information: {e}", err=True)
        raise click.Abort()


@main.command()
@click.option("--data-dir", type=click.Path(), help="Data directory path")
def interactive(data_dir):
    """Launch the interactive terminal orchestrator."""
    try:
        from .interactive_orchestrator import InteractiveOrchestrator

        orchestrator = InteractiveOrchestrator(data_dir or "./blake_data")
        _run_async(orchestrator.run())

    except ImportError as e:
        click.echo(f"❌ Failed to import interactive orchestrator: {e}")
        click.echo("Make sure all dependencies are installed: pip install rich")
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Interactive orchestrator failed: {e}")
        logger.exception("Interactive orchestrator failed")
        raise click.Abort()


@main.command("scrape-archive")
@click.option(
    "--include-images/--no-images", default=True, help="Download images (default: yes)"
)
@click.option(
    "--dpi",
    type=click.Choice(["100", "150", "200", "300"]),
    default="100",
    help="Image resolution in DPI",
)
@click.option(
    "--max-images", type=int, default=5, help="Maximum images per work (0 for all)"
)
@click.option(
    "--category",
    multiple=True,
    type=click.Choice(["illbk", "comb", "spb", "wc", "pt", "pdes", "pen", "ms", "lt"]),
    help="Filter by category (illuminated books, drawings, letters, etc.)",
)
@click.option("--force", is_flag=True, help="Force re-download even if exists")
@click.pass_context
def scrape_archive(ctx, include_images, dpi, max_images, category, force):
    """
    Scrape all works from the William Blake Archive.

    This command downloads texts, images, and metadata from blakearchive.org.
    Data sources include GitHub repository (structured data) and archive site.

    Categories:
      illbk - Illuminated Books
      comb  - Commercial Book Illustrations
      spb   - Separate Prints
      wc    - Watercolor Drawings
      pt    - Paintings
      pdes  - Pencil Drawings
      pen   - Pen and Ink Drawings
      ms    - Manuscripts
      lt    - Letters
    """
    from .downloader.blake_archive_scraper import BlakeArchiveScraper

    data_dir = ctx.obj["data_dir"]
    categories = list(category) if category else None
    max_imgs = max_images if max_images > 0 else None

    async def run_scraper():
        async with BlakeArchiveScraper(data_dir) as scraper:
            click.echo("Starting Blake Archive source-aware scrape...")
            click.echo(f"   Data directory: {data_dir}")
            click.echo(f"   Include images: {include_images}")
            click.echo(f"   Image DPI: {dpi}")
            click.echo(f"   Categories: {categories or 'all'}")
            click.echo()

            works = await scraper.download_all_works(
                include_images=include_images,
                image_dpi=int(dpi),
                max_images_per_work=max_imgs,
                categories=categories,
                force=force,
            )

            # Display results
            stats = scraper.get_statistics()
            click.echo()
            click.echo("✅ Scrape complete!")
            click.echo(f"   Works found: {stats['works_found']}")
            click.echo(f"   Works downloaded: {stats['works_downloaded']}")
            click.echo(f"   Texts extracted: {stats['texts_extracted']}")
            click.echo(f"   Images downloaded: {stats['images_downloaded']}")
            if stats["errors"] > 0:
                click.echo(f"   Errors: {stats['errors']}")

            return works

    try:
        works = _run_async(run_scraper())
        click.echo(f"\n📚 Successfully processed {len(works)} Blake works")
    except Exception as e:
        click.echo(f"❌ Error scraping archive: {e}", err=True)
        logger.exception("Archive scrape failed")
        raise click.Abort()


if __name__ == "__main__":
    main()
