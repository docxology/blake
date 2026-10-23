from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from packaging.version import Version

from .. import __affiliation__, __author__, __email__, __orcid__, __version__
from .evidence_acquisition import (
    FALLBACK_VALIDATION_DIR,
    load_validated_fallback_marker,
)
from .release_preflight import EXCLUDED_PUBLIC_PATTERNS, build_rights_gate_report

PUBLIC_RELEASE_SCHEMES = {"github+zenodo", "github", "zenodo"}

SOURCE_ROOTS: tuple[str, ...] = (
    "blake",
    "manuscript_tools",
    "scripts",
    "tests",
)

TOP_LEVEL_FILES: tuple[str, ...] = (
    "LICENSE",
    "README.md",
    "CITATION.cff",
    "codemeta.json",
    ".zenodo.json",
    "requirements.txt",
    "blake_viewer.py",
    "pyproject.toml",
    "run_all.py",
)

GENERATED_ROOTS: tuple[str, ...] = (
    "analysis_output",
    "output",
)

SOURCE_SUFFIXES: set[str] = {
    "",
    ".cff",
    ".csv",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

GENERATED_SUFFIXES: set[str] = {
    "",
    ".cff",
    ".csv",
    ".json",
    ".png",
    ".txt",
    ".yaml",
    ".yml",
}

EXCLUDED_EXACT_PATHS: set[str] = {
    "blake/AGENTS.md",
    "docs/AGENTS.md",
    "docs/manuscript/AGENTS.md",
    "tests/AGENTS.md",
    "blake/analysis/AGENTS.md",
    "blake/downloader/AGENTS.md",
    "blake/export/AGENTS.md",
    "blake/gui/AGENTS.md",
    "blake/metadata/AGENTS.md",
    "blake/utils/AGENTS.md",
    "blake/viz/AGENTS.md",
    "ISA.md",
    "TODO.md",
    "docs/online-scholarship-gap-review.md",
    "docs/source-leads.json",
    "docs/visualization-publication-brief.md",
    "docs/manuscript/",
    "blake_data/",
}

# Directory subtrees that hold corpus payloads or local-pipeline artifacts and must
# never enter a public bundle. These are the rights-encumbered / process-only zones.
EXCLUDED_DIR_PREFIXES: tuple[str, ...] = (
    "analysis_output/exports/",
    "analysis_output/data/",
    "analysis_output/releases/",
    "output/reports/",
    "output/pdf/",
    "output/manuscript/",
    "output/web/",
    "output/qa_previews/",
)

# Specific generated reports that embed the absolute project_root (home-path leak)
# and are process metadata, not release deliverables.
EXCLUDED_REPORT_BASENAMES: frozenset[str] = frozenset(
    {
        "public_release_preflight.json",
        "public_release_preflight.md",
        "private_release_preflight.json",
        "private_release_preflight.md",
        "rights_gate_report.json",
        "rights_gate_report.md",
    }
)

# Content-leak detection thresholds and patterns. These are the structural guarantee:
# even if a path-based rule has a gap, a bundled artifact carrying full source text or
# an absolute local path is rejected from the bundle.
MAX_BUNDLED_TEXT_FIELD_CHARS = 20_000
# Aggregate (sum of all string lengths) guard catches a full work chunked into many
# short lines/stanzas, which the single-field guard would miss.
MAX_BUNDLED_TEXT_TOTAL_CHARS = 200_000
# Assembled from fragments so this module's own source never contains a literal
# "/Users/<seg>/" that would make the scanner exclude the packager itself.
_ABS_HOME_DIRS = ("Users", "home", "root")
ABSOLUTE_PATH_RE = re.compile(
    r"(?:/(?:" + "|".join(_ABS_HOME_DIRS) + r")/[A-Za-z0-9._-]+/)"
    r"|(?:[A-Za-z]:[\\/](?:" + "|".join(_ABS_HOME_DIRS) + r")[\\/][A-Za-z0-9._-]+)"
)
# Text suffixes whose embedded-payload size is bounded (transcription/full-text guard).
SIZE_SCAN_SUFFIXES: frozenset[str] = frozenset({".json", ".csv", ".txt"})
# Images may only ship from project-authored chart directories. Any image elsewhere
# (e.g. rasterized manuscript pages under output/qa_previews) is rights-gated by default.
IMAGE_SUFFIXES: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff", ".bmp", ".svg"}
)
ALLOWED_IMAGE_DIR_PREFIXES: tuple[str, ...] = (
    "output/figures/",
    "output/cover/",
    "analysis_output/visualizations/",
)
# Rights-gated territories: any included asset whose path lands here is a hard
# release blocker (the rights gate wired into the go/no-go decision).
RIGHTS_GATED_PREFIXES: dict[str, str] = {
    "blake_data/": "local evidence cache",
    "docs/manuscript/": "local manuscript pipeline",
    "analysis_output/exports/": "corpus export payload",
    "analysis_output/data/": "corpus source/provenance payload",
    "analysis_output/releases/": "prior release staging",
}


@dataclass(frozen=True)
class PublicReleaseAsset:
    source_path: str
    bundle_path: str
    kind: str
    category: str
    size_bytes: int
    sha256: str
    notes: str = ""
    decision_reason: str = "included by public release allowlist"


@dataclass(frozen=True)
class PublicReleaseExclusion:
    source_path: str
    category: str
    reason: str
    matched_rule: str


@dataclass(frozen=True)
class FallbackCorroborationRecord:
    target_id: str
    title: str
    validated_source: dict[str, Any]
    corroborating_sources: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ready"
    note: str = ""


def write_public_release_preflight(
    project_root: Path | str | None = None,
    *,
    output_dir: Path | str = "analysis_output",
    data_dir: Path | str = "blake_data",
    release_dir: Path | str | None = None,
    destination: str = "github+zenodo",
) -> dict[str, Any]:
    root = Path(project_root) if project_root is not None else _project_root()
    output_path = Path(output_dir)
    data_path = Path(data_dir)
    release_path = _release_dir(output_path, release_dir)
    reports_dir = output_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    report = build_public_release_report(
        root,
        output_dir=output_path,
        data_dir=data_path,
        release_dir=release_path,
        destination=destination,
    )

    preflight_path = reports_dir / "public_release_preflight.json"
    preflight_md_path = reports_dir / "public_release_preflight.md"
    preflight_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    preflight_md_path.write_text(_public_preflight_markdown(report), encoding="utf-8")
    report["path"] = str(preflight_path)
    report["markdown_path"] = str(preflight_md_path)
    preflight_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def write_public_release_package(
    project_root: Path | str | None = None,
    *,
    output_dir: Path | str = "analysis_output",
    data_dir: Path | str = "blake_data",
    release_dir: Path | str | None = None,
    destination: str = "github+zenodo",
) -> dict[str, Any]:
    root = Path(project_root) if project_root is not None else _project_root()
    output_path = Path(output_dir)
    data_path = Path(data_dir)
    release_path = _release_dir(output_path, release_dir)
    if release_path.exists():
        shutil.rmtree(release_path)
    release_path.mkdir(parents=True, exist_ok=True)

    report = build_public_release_report(
        root,
        output_dir=output_path,
        data_dir=data_path,
        release_dir=release_path,
        destination=destination,
    )
    preflight_path = output_path / "reports" / "public_release_preflight.json"
    preflight_path.parent.mkdir(parents=True, exist_ok=True)
    preflight_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    manifest_path = release_path / "public_release_manifest.json"
    bundle_dir = release_path / "bundle"
    archive_path = release_path / "public_release_bundle.zip"
    notes_path = release_path / "github_release.md"
    github_json_path = release_path / "github_release.json"
    zenodo_path = release_path / "zenodo_metadata.json"
    citation_path = release_path / "CITATION.cff"
    package_summary_path = release_path / "public_release_package.json"
    checksums_path = release_path / "checksums.sha256"
    corroboration_path = release_path / "fallback_corroboration.json"

    if report["status"] != "ready":
        package_summary = {
            "schema_version": "1.0",
            "artifact": "public_release_package",
            "generated_at": report["generated_at"],
            "status": "blocked",
            "release_dir": str(release_path),
            "preflight_path": str(preflight_path),
            "package_summary_path": str(package_summary_path),
            "blocked_reasons": report["blocked_reasons"],
            "package_manifest_path": str(manifest_path),
        }
        package_summary_path.write_text(
            json.dumps(package_summary, indent=2), encoding="utf-8"
        )
        return package_summary

    manifest = report["manifest"]
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    bundle_dir.mkdir(parents=True, exist_ok=True)
    _materialize_bundle(root, bundle_dir, manifest["included_assets"])

    checksums = _build_checksum_ledger(bundle_dir, manifest["included_assets"])
    _write_checksum_ledger(checksums_path, checksums)

    github_release = _build_github_release_payload(manifest, checksums)
    notes_path.write_text(github_release["body"], encoding="utf-8")
    github_json_path.write_text(json.dumps(github_release, indent=2), encoding="utf-8")

    zenodo_metadata = _build_zenodo_metadata(manifest, github_release)
    zenodo_path.write_text(json.dumps(zenodo_metadata, indent=2), encoding="utf-8")

    citation_text = _build_citation_cff(manifest)
    citation_path.write_text(citation_text, encoding="utf-8")

    corroboration = manifest["corroboration"]
    corroboration_path.write_text(json.dumps(corroboration, indent=2), encoding="utf-8")

    _write_zip_archive(bundle_dir, archive_path)

    package_summary = {
        "schema_version": "1.0",
        "artifact": "public_release_package",
        "generated_at": report["generated_at"],
        "status": "ready",
        "release_dir": str(release_path),
        "preflight_path": str(preflight_path),
        "manifest_path": str(manifest_path),
        "bundle_dir": str(bundle_dir),
        "archive_path": str(archive_path),
        "package_summary_path": str(package_summary_path),
        "github_release_path": str(github_json_path),
        "github_release_notes_path": str(notes_path),
        "zenodo_metadata_path": str(zenodo_path),
        "citation_path": str(citation_path),
        "checksums_path": str(checksums_path),
        "corroboration_path": str(corroboration_path),
        "included_asset_count": len(manifest["included_assets"]),
        "excluded_asset_count": len(manifest["excluded_assets"]),
        "corroborated_fallback_target_count": len(corroboration["validated_targets"]),
    }
    package_summary_path.write_text(
        json.dumps(package_summary, indent=2), encoding="utf-8"
    )
    return package_summary


def build_public_release_report(
    project_root: Path,
    *,
    output_dir: Path,
    data_dir: Path,
    release_dir: Path,
    destination: str,
) -> dict[str, Any]:
    if destination not in PUBLIC_RELEASE_SCHEMES:
        raise ValueError(
            f"unsupported destination {destination!r}; expected one of {sorted(PUBLIC_RELEASE_SCHEMES)}"
        )

    rights_gate = build_rights_gate_report(
        project_root,
        output_dir=output_dir,
        data_dir=data_dir,
    )
    manifest = _build_public_release_manifest(
        project_root,
        output_dir=output_dir,
        data_dir=data_dir,
        release_dir=release_dir,
        destination=destination,
        rights_gate=rights_gate,
    )

    blocked_reasons = list(manifest["blocked_reasons"])
    status = "ready" if not blocked_reasons else "blocked"
    return {
        "schema_version": "1.0",
        "artifact": "public_release_preflight",
        "generated_at": manifest["generated_at"],
        "project_root": str(project_root),
        "output_dir": str(output_dir),
        "data_dir": str(data_dir),
        "release_dir": str(release_dir),
        "destination": destination,
        "status": status,
        "blocked_reasons": blocked_reasons,
        "included_asset_count": len(manifest["included_assets"]),
        "excluded_asset_count": len(manifest["excluded_assets"]),
        "included_bytes": sum(
            asset["size_bytes"] for asset in manifest["included_assets"]
        ),
        "excluded_bytes": sum(
            asset.get("size_bytes", 0) for asset in manifest["excluded_assets"]
        ),
        "corroboration": manifest["corroboration"],
        "corroborated_fallback_target_count": len(
            manifest["corroboration"]["validated_targets"]
        ),
        "rights_gate": rights_gate,
        "manifest": manifest,
        "public_release_allowed": not blocked_reasons,
    }


def _build_public_release_manifest(
    project_root: Path,
    *,
    output_dir: Path,
    data_dir: Path,
    release_dir: Path,
    destination: str,
    report: dict[str, Any] | None = None,
    rights_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report = report or {}
    rights_gate = rights_gate or build_rights_gate_report(
        project_root,
        output_dir=output_dir,
        data_dir=data_dir,
    )
    selected_paths = _selected_public_paths(project_root, output_dir, data_dir)
    included_assets: list[PublicReleaseAsset] = []
    excluded_assets: list[PublicReleaseExclusion] = []

    for rel_path in selected_paths:
        kind, category = _classify_path(rel_path)
        source_path = project_root / rel_path
        if _is_excluded(rel_path):
            excluded_assets.append(
                PublicReleaseExclusion(
                    source_path=rel_path.as_posix(),
                    category=category,
                    reason=_exclusion_reason(rel_path),
                    matched_rule=_matched_rule(rel_path),
                )
            )
            continue
        if not source_path.exists() or not source_path.is_file():
            continue
        if not _suffix_allowed(rel_path, kind):
            excluded_assets.append(
                PublicReleaseExclusion(
                    source_path=rel_path.as_posix(),
                    category=category,
                    reason="unsupported file type for public release package",
                    matched_rule="suffix-filter",
                )
            )
            continue
        if source_path.is_symlink():
            excluded_assets.append(
                PublicReleaseExclusion(
                    source_path=rel_path.as_posix(),
                    category=category,
                    reason="symlinks are not bundled (could resolve outside the release scope)",
                    matched_rule="symlink-skip",
                )
            )
            continue
        leak_reason = _content_leak_reason(rel_path, source_path)
        if leak_reason:
            excluded_assets.append(
                PublicReleaseExclusion(
                    source_path=rel_path.as_posix(),
                    category=category,
                    reason=leak_reason,
                    matched_rule="content-leak-scan",
                )
            )
            continue

        included_assets.append(
            PublicReleaseAsset(
                source_path=rel_path.as_posix(),
                bundle_path=rel_path.as_posix(),
                kind=kind,
                category=category,
                size_bytes=source_path.stat().st_size,
                sha256=_sha256_file(source_path),
                notes=_asset_note(rel_path),
                decision_reason=_inclusion_reason(rel_path),
            )
        )

    excluded_source_paths = {
        exclusion.source_path for exclusion in excluded_assets if exclusion.source_path
    }
    blocked_reference_candidates = _blocked_reference_candidates()
    blocked_references: list[dict[str, Any]] = []
    for asset in included_assets:
        source_path = project_root / asset.source_path
        text_blockers = _blocked_reference_hits(
            source_path,
            excluded_source_paths | blocked_reference_candidates,
        )
        if text_blockers:
            for blocker in text_blockers:
                blocked_references.append(
                    {
                        "source_path": asset.source_path,
                        "blocked_reference": blocker,
                    }
                )

    corroboration = _build_fallback_corroboration(project_root, data_dir)
    corroboration_blockers = [
        record.note
        for record in corroboration["validated_targets"]
        if record["status"] != "ready"
    ]
    # Hard fail-closed signal: any included asset that belongs to a rights-gated
    # territory blocks the release. This wires the rights gate into the go/no-go
    # decision instead of leaving it as a decorative report.
    rights_gate_violations = _rights_gate_violations(included_assets)
    content_leak_exclusions = [
        asdict(exclusion)
        for exclusion in excluded_assets
        if exclusion.matched_rule == "content-leak-scan"
    ]
    # Reference mentions of excluded paths are advisory only (a metadata file naming
    # an excluded asset is not a content leak — the content-leak scan guarantees that).
    reference_warnings = _blocked_references_text(blocked_references)
    blocked_reasons: list[str] = []
    blocked_reasons.extend(rights_gate_violations)
    blocked_reasons.extend(corroboration_blockers)

    included_payload = [asdict(asset) for asset in included_assets]
    excluded_payload = [asdict(asset) for asset in excluded_assets]
    public_release_name = f"blake-public-release-{__version__}"
    return {
        "schema_version": "1.0",
        "artifact": "public_release_manifest",
        "generated_at": datetime.now().isoformat(),
        "project_root": str(project_root),
        "output_dir": str(output_dir),
        "data_dir": str(data_dir),
        "release_dir": str(release_dir),
        "public_release_name": public_release_name,
        "version": __version__,
        "destination": destination,
        "package_policy": {
            "source_roots": list(SOURCE_ROOTS),
            "top_level_files": list(TOP_LEVEL_FILES),
            "generated_roots": list(GENERATED_ROOTS),
            "excluded_exact_paths": sorted(EXCLUDED_EXACT_PATHS),
            "excluded_public_patterns": list(EXCLUDED_PUBLIC_PATTERNS),
        },
        "package_info": _package_info(project_root),
        "rights_gate": rights_gate,
        "included_assets": included_payload,
        "excluded_assets": excluded_payload,
        "included_asset_count": len(included_payload),
        "excluded_asset_count": len(excluded_payload),
        "included_bytes": sum(asset["size_bytes"] for asset in included_payload),
        "excluded_bytes": sum(asset.get("size_bytes", 0) for asset in excluded_payload),
        "blocked_references": blocked_references,
        "reference_warnings": reference_warnings,
        "rights_gate_violations": rights_gate_violations,
        "content_leak_exclusions": content_leak_exclusions,
        "content_leak_exclusion_count": len(content_leak_exclusions),
        "blocked_reasons": blocked_reasons,
        "status": "ready" if not blocked_reasons else "blocked",
        "corroboration": corroboration,
        "github_release": _github_release_metadata(public_release_name, destination),
        "zenodo_metadata": _zenodo_metadata_template(public_release_name),
    }


def _selected_public_paths(
    project_root: Path, output_dir: Path, data_dir: Path
) -> list[Path]:
    candidates: list[Path] = []
    for filename in TOP_LEVEL_FILES:
        path = project_root / filename
        if path.exists():
            candidates.append(Path(filename))

    for root_name in SOURCE_ROOTS:
        root = project_root / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_symlink():
                continue
            if path.is_file():
                candidates.append(path.relative_to(project_root))

    for root_name in GENERATED_ROOTS:
        root = project_root / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_symlink():
                continue
            if path.is_file():
                candidates.append(path.relative_to(project_root))

    _ = data_dir
    unique: dict[str, Path] = {}
    for candidate in candidates:
        unique[candidate.as_posix()] = candidate
    return [unique[key] for key in sorted(unique)]


def _classify_path(rel_path: Path) -> tuple[str, str]:
    parts = rel_path.parts
    if not parts:
        return "unknown", "unknown"
    if parts[0] in SOURCE_ROOTS or rel_path.name in TOP_LEVEL_FILES:
        return "source", "source-code"
    if parts[0] == "output":
        if len(parts) > 1 and parts[1] == "figures":
            return "generated", "figure-output"
        if len(parts) > 1 and parts[1] == "cover":
            return "generated", "cover-art"
        if len(parts) > 1 and parts[1] == "data":
            return "generated", "rendered-data"
        return "generated", "rendered-output"
    if parts[0] == "analysis_output":
        if len(parts) > 1 and parts[1] == "analysis":
            return "generated", "analysis-json"
        if len(parts) > 1 and parts[1] == "exports":
            return "generated", "export-output"
        if len(parts) > 1 and parts[1] == "reports":
            return "generated", "report-json"
        if len(parts) > 1 and parts[1] == "visualizations":
            return "generated", "visualization-json"
        if len(parts) > 1 and parts[1] == "data":
            return "generated", "auditing-json"
        return "generated", "analysis-output"
    return "source", "source-code"


def _suffix_allowed(rel_path: Path, kind: str) -> bool:
    suffix = rel_path.suffix.lower()
    if kind == "source":
        return suffix in SOURCE_SUFFIXES
    return suffix in GENERATED_SUFFIXES


def _is_excluded(rel_path: Path) -> bool:
    rel = rel_path.as_posix()
    if rel.endswith("/"):
        rel = rel[:-1]
    if rel in EXCLUDED_EXACT_PATHS:
        return True
    if any(rel.startswith(prefix) for prefix in EXCLUDED_DIR_PREFIXES):
        return True
    if rel_path.name in EXCLUDED_REPORT_BASENAMES:
        return True
    # Dotfiles (.DS_Store, .gitignore, etc.) leak local state and are not deliverables,
    # except the explicitly allowlisted top-level metadata files.
    if rel_path.name.startswith(".") and rel_path.name not in TOP_LEVEL_FILES:
        return True
    # Images may only come from project-authored chart directories. Any image elsewhere
    # (rasterized manuscript pages, source plates) is rights-gated by default.
    if rel_path.suffix.lower() in IMAGE_SUFFIXES and not any(
        rel.startswith(prefix) for prefix in ALLOWED_IMAGE_DIR_PREFIXES
    ):
        return True
    if rel_path.name == "AGENTS.md":
        return True
    if rel_path.parts and rel_path.parts[0] == "manuscript":
        return True
    if rel_path.parts and rel_path.parts[0] == "blake_data":
        return True
    if rel_path.name == "figure_registry.json":
        return True
    if rel_path.match("output/figures/*mosaic*.png"):
        return True
    if rel_path.match("analysis_output/**/*mosaic*.png"):
        return True
    if rel_path.suffix.lower() in {".html", ".pdf", ".tei", ".xml"}:
        return True
    return False


def _exclusion_reason(rel_path: Path) -> str:
    if rel_path.name == "AGENTS.md":
        return "internal agent instructions are not part of the public release"
    if rel_path.parts and rel_path.parts[0] == "manuscript":
        return "local manuscript pipeline stays separate from the public bundle"
    if rel_path.parts and rel_path.parts[0] == "blake_data":
        return "local evidence cache and source downloads stay private"
    if rel_path.name == "figure_registry.json":
        return "figure registry can enumerate blocked local-only mosaics"
    if rel_path.match("output/figures/*mosaic*.png"):
        return "rights-gated mosaic figure excluded from the public bundle"
    if rel_path.match("analysis_output/**/*mosaic*.png"):
        return "rights-gated mosaic visualization excluded from the public bundle"
    if rel_path.suffix.lower() in {".html", ".pdf"}:
        return "rendered publication artifact stays in the local pipeline"
    if rel_path.suffix.lower() in {".tei", ".xml"}:
        return "raw source transcription or markup is not public release material"
    if rel_path.suffix.lower() == ".md":
        return "generated markdown publication artifact stays local"
    return "excluded by public release policy"


def _matched_rule(rel_path: Path) -> str:
    if rel_path.name == "AGENTS.md":
        return "internal-instructions"
    if rel_path.parts and rel_path.parts[0] == "manuscript":
        return "local-manuscript-root"
    if rel_path.parts and rel_path.parts[0] == "blake_data":
        return "local-cache-root"
    if rel_path.name == "figure_registry.json":
        return "figure-registry"
    if rel_path.match("output/figures/*mosaic*.png"):
        return "mosaic-figure"
    if rel_path.match("analysis_output/**/*mosaic*.png"):
        return "mosaic-visualization"
    if rel_path.suffix.lower() in {".html", ".pdf"}:
        return "rendered-publication-artifact"
    if rel_path.suffix.lower() in {".tei", ".xml"}:
        return "source-markup"
    if rel_path.suffix.lower() == ".md":
        return "markdown-artifact"
    return "policy-default"


def _asset_note(rel_path: Path) -> str:
    if rel_path.parts and rel_path.parts[0] == "output":
        return "project-authored output artifact"
    if rel_path.parts and rel_path.parts[0] == "analysis_output":
        return "analysis or audit artifact"
    if rel_path.name in TOP_LEVEL_FILES:
        return "top-level project file"
    return "source or test asset"


def _inclusion_reason(rel_path: Path) -> str:
    if rel_path.name in TOP_LEVEL_FILES:
        return "top-level project file selected for public source bundle"
    if rel_path.parts and rel_path.parts[0] in SOURCE_ROOTS:
        return "project source/test/script file selected by source allowlist"
    if rel_path.parts[:2] == ("analysis_output", "reports"):
        return "safe generated report selected with rights-gated assets excluded"
    if rel_path.parts[:2] == ("analysis_output", "visualizations"):
        return "safe visualization data selected without raw source files"
    if rel_path.parts and rel_path.parts[0] == "analysis_output":
        return "safe generated audit or analysis artifact selected"
    if rel_path.parts and rel_path.parts[0] == "output":
        return "project-authored generated output selected"
    return "selected by public release allowlist"


def _content_leak_reason(rel_path: Path, source_path: Path) -> str | None:
    """Structural leak guarantee. Rejects a bundled artifact that (a) carries an
    absolute local home path (PII — scanned on EVERY text file, source included),
    (b) embeds a large or chunked text payload (transcription / full work text, on
    generated data artifacts), or (c) is an undecodable binary in a generated
    directory (cannot be scanned -> fails closed). Images are handled by the
    allowlist in _is_excluded and are not content-scanned here."""
    suffix = source_path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return None
    try:
        raw = source_path.read_bytes()
    except OSError:
        return "unreadable artifact excluded from the public bundle"
    in_generated = bool(rel_path.parts) and rel_path.parts[0] in {
        "analysis_output",
        "output",
    }
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        if in_generated:
            return "non-UTF-8 generated artifact excluded (cannot be scanned for leaks)"
        return None
    if ABSOLUTE_PATH_RE.search(text):
        return "contains an absolute local filesystem path (home-directory leak)"
    if in_generated and suffix in SIZE_SCAN_SUFFIXES:
        if suffix == ".json":
            try:
                data: Any = json.loads(text)
            except json.JSONDecodeError:
                data = None
            if data is not None:
                if (
                    _max_string_len(data) > MAX_BUNDLED_TEXT_FIELD_CHARS
                    or _aggregate_string_len(data) > MAX_BUNDLED_TEXT_TOTAL_CHARS
                ):
                    return "embeds a large text payload (possible transcription or full-text leak)"
            elif len(text) > MAX_BUNDLED_TEXT_TOTAL_CHARS:
                return "embeds a large text payload (possible transcription or full-text leak)"
        elif len(text) > MAX_BUNDLED_TEXT_TOTAL_CHARS:
            return (
                "embeds a large text payload (possible transcription or full-text leak)"
            )
    return None


def _max_string_len(obj: Any) -> int:
    if isinstance(obj, str):
        return len(obj)
    if isinstance(obj, dict):
        return max((_max_string_len(value) for value in obj.values()), default=0)
    if isinstance(obj, list):
        return max((_max_string_len(value) for value in obj), default=0)
    return 0


def _aggregate_string_len(obj: Any) -> int:
    if isinstance(obj, str):
        return len(obj)
    if isinstance(obj, dict):
        return sum(_aggregate_string_len(value) for value in obj.values())
    if isinstance(obj, list):
        return sum(_aggregate_string_len(value) for value in obj)
    return 0


def _rights_gate_violations(included_assets: list[PublicReleaseAsset]) -> list[str]:
    """Hard fail-closed check: no included asset may belong to a rights-gated
    territory. This is the rights gate wired into the release go/no-go decision."""
    violations: list[str] = []
    for asset in included_assets:
        rel = asset.source_path
        for prefix, label in RIGHTS_GATED_PREFIXES.items():
            if rel.startswith(prefix):
                violations.append(
                    f"{rel} belongs to rights-gated class ({label}) and must not be in the public bundle"
                )
                break
        if ("mosaic" in rel and rel.endswith(".png")) or rel.endswith((".tei", ".xml")):
            violations.append(
                f"{rel} is a rights-gated source/mosaic artifact and must not be in the public bundle"
            )
    return violations


def _blocked_reference_hits(path: Path, excluded_assets: Iterable[str]) -> list[str]:
    if path.suffix.lower() not in {".json", ".md", ".txt", ".yaml", ".yml", ".toml"}:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    blocked: list[str] = []
    for candidate in excluded_assets:
        # Only flag references to concrete excluded FILES (with a suffix); directory
        # mentions like "docs/manuscript/" are legitimate layout documentation, not leaks.
        if not candidate or candidate.endswith("/") or not Path(candidate).suffix:
            continue
        if candidate in text:
            blocked.append(candidate)
    return blocked


def _build_fallback_corroboration(project_root: Path, data_dir: Path) -> dict[str, Any]:
    manifest = _read_json(project_root / "analysis_output" / "corpus_manifest.json", {})
    target_records = {
        str(row.get("target_id") or ""): row
        for row in manifest.get("target_records") or []
        if row.get("target_id")
    }
    validated_dir = data_dir / "metadata" / FALLBACK_VALIDATION_DIR
    validated_targets: list[FallbackCorroborationRecord] = []

    for marker_path in sorted(validated_dir.glob("*.json")):
        marker = load_validated_fallback_marker(data_dir, marker_path.stem)
        if not marker:
            continue
        target_id = str(marker.get("target_id") or marker_path.stem)
        target_record = target_records.get(target_id, {})
        text_path = data_dir / "texts" / f"{target_id}.txt"
        current_checksum = _sha256_file(text_path) if text_path.exists() else None
        checksum_matches = bool(
            current_checksum
            and marker.get("checksum")
            and current_checksum == marker.get("checksum")
        )
        corroborating_sources = []
        for source_id in target_record.get("matched_source_ids") or []:
            corroborating_sources.append(
                {
                    "source_id": source_id,
                    "source_type": source_id.split(":", 1)[0],
                    "basis": "source-owned target-coverage corroboration",
                    "evidence_role": "contextual_target_match",
                    "text_bearing": False,
                    "reviewer_note": "Corroborates target identity, not a second fallback transcription.",
                }
            )
        if not corroborating_sources:
            manual_sources = _manual_corroboration_sources(project_root, target_id)
            corroborating_sources.extend(manual_sources)

        status = (
            "ready"
            if corroborating_sources and checksum_matches
            else (
                "stale_checksum"
                if corroborating_sources and not checksum_matches
                else "needs_secondary_citation"
            )
        )
        note = (
            "Validated fallback text is corroborated by a source-owned archive id."
            if status == "ready"
            else (
                "Validated fallback text checksum no longer matches the stored marker."
                if status == "stale_checksum"
                else "Validated fallback text still needs a second editorial or source-owned citation."
            )
        )
        validated_targets.append(
            FallbackCorroborationRecord(
                target_id=target_id,
                title=str(
                    marker.get("title") or target_record.get("title") or target_id
                ),
                validated_source={
                    "label": marker.get("source"),
                    "url": marker.get("source_url"),
                    "authority_tier": marker.get("authority_tier"),
                    "license_or_terms": marker.get("license")
                    or marker.get("license_type")
                    or marker.get("rights_note")
                    or "not recorded",
                    "checksum": marker.get("checksum"),
                    "validated_at": marker.get("validated_at"),
                    "reviewer_note": marker.get("reviewer_note")
                    or marker.get("validation_note")
                    or "Validated fallback text marker.",
                    "text_bearing": True,
                    "current_checksum": current_checksum,
                    "checksum_matches": checksum_matches,
                },
                corroborating_sources=corroborating_sources,
                status=status,
                note=note,
            )
        )

    unresolved = [
        asdict(record) for record in validated_targets if record.status != "ready"
    ]
    return {
        "schema_version": "1.0",
        "artifact": "fallback_corroboration",
        "generated_at": datetime.now().isoformat(),
        "validated_target_count": len(validated_targets),
        "validated_targets": [asdict(record) for record in validated_targets],
        "unresolved_target_count": len(unresolved),
        "unresolved_targets": unresolved,
    }


def _manual_corroboration_sources(
    project_root: Path, target_id: str
) -> list[dict[str, Any]]:
    leads_path = project_root / "docs" / "source-leads.json"
    leads = _read_json(leads_path, {})
    rows = leads.get("leads") if isinstance(leads, dict) else []
    corroborating_sources: list[dict[str, Any]] = []
    for row in rows or []:
        if str(row.get("target_id") or "") != target_id:
            continue
        if str(row.get("status") or "") != "manual_review":
            continue
        corroborating_sources.append(
            {
                "source_owner": row.get("source_owner"),
                "url": row.get("url"),
                "basis": row.get("direct_source_basis"),
                "note": row.get("scholarship_note"),
                "rights_note": row.get("rights_note"),
                "evidence_role": "candidate_text_bearing_lead"
                if row.get("evidence_type") == "text"
                else "contextual_source_lead",
                "text_bearing": row.get("evidence_type") == "text",
                "reviewer_note": row.get("scholarship_note")
                or row.get("direct_source_basis")
                or "",
            }
        )
    return corroborating_sources


def _build_github_release_payload(
    manifest: dict[str, Any], checksums: dict[str, str]
) -> dict[str, Any]:
    github = manifest["github_release"]
    included_count = manifest["included_asset_count"]
    excluded_count = manifest["excluded_asset_count"]
    corroboration = manifest["corroboration"]
    body_lines = [
        f"# Blake public release bundle {manifest['version']}",
        "",
        "Public GitHub/Zenodo bundle generated from the local release manifest.",
        "",
        f"- Status: `{manifest['status']}`",
        f"- Included assets: `{included_count}`",
        f"- Excluded assets: `{excluded_count}`",
        f"- Fallback targets with secondary corroboration: `{corroboration['validated_target_count']}`",
        "",
        "Release boundary:",
        "- The public bundle contains code, safe generated outputs, and release metadata.",
        "- It excludes the local manuscript pipeline, raw source caches, and rights-gated assets by default.",
        "- MIT covers project code and project-authored aggregate outputs only; provider TEI,",
        "  transcriptions, images, and fallback source texts are excluded and keep their source terms.",
        f"- Rights-gate violations: `{len(manifest.get('rights_gate_violations', []))}`; "
        f"content-leak exclusions: `{manifest.get('content_leak_exclusion_count', 0)}`.",
        "",
        "Attach `public_release_bundle.zip` together with `CITATION.cff` and `zenodo_metadata.json`.",
        "",
        "Checksums:",
    ]
    for rel_path in sorted(checksums):
        body_lines.append(f"- `{rel_path}`")
    body = "\n".join(body_lines)
    github = dict(github)
    github.update(
        {
            "body": body,
            "asset_names": [
                "public_release_bundle.zip",
                "CITATION.cff",
                "zenodo_metadata.json",
            ],
            "included_asset_count": included_count,
            "excluded_asset_count": excluded_count,
            "corroborated_fallback_target_count": corroboration[
                "validated_target_count"
            ],
        }
    )
    return github


def _build_zenodo_metadata(
    manifest: dict[str, Any], github_release: dict[str, Any]
) -> dict[str, Any]:
    return {
        "metadata": {
            "title": f"{manifest['public_release_name']} ({manifest['version']})",
            "upload_type": "software",
            "description": github_release["body"],
            "creators": [
                {
                    "name": "Friedman, Daniel Ari",
                    "orcid": __orcid__,
                    "affiliation": __affiliation__,
                }
            ],
            "keywords": [
                "William Blake",
                "digital humanities",
                "corpus acquisition",
                "public release",
            ],
            "notes": (
                "The MIT license covers the project source code and project-authored "
                "aggregate analysis outputs only. Provider-supplied Blake Archive TEI, "
                "transcriptions, images, fallback source texts, and local evidence caches "
                "are excluded from this bundle and remain under their source-provider terms."
            ),
            "version": manifest["version"],
            "license": "MIT",
            "access_right": "open",
            "relations": [
                {
                    "relation": "isSupplementTo",
                    "identifier": "https://github.com/docxology/blake",
                    "resource_type": "software",
                }
            ],
        }
    }


def _zenodo_metadata_template(public_release_name: str) -> dict[str, Any]:
    return {
        "metadata": {
            "title": public_release_name,
            "upload_type": "software",
            "description": "Public release bundle metadata generated from the Blake corpus release manifest.",
            "creators": [{"name": __author__}],
            "keywords": ["William Blake", "digital humanities", "software"],
            "version": __version__,
            "license": "MIT",
            "access_right": "open",
        }
    }


def _build_citation_cff(manifest: dict[str, Any]) -> str:
    lines = [
        "cff-version: 1.2.0",
        'message: "If you use this release package, please cite it as below."',
        f'title: "{manifest["public_release_name"]}"',
        f'version: "{manifest["version"]}"',
        'url: "https://github.com/docxology/blake"',
        'repository-code: "https://github.com/docxology/blake"',
        'license: "MIT"',
        "authors:",
        "  - family-names: Friedman",
        "    given-names: Daniel Ari",
        f'    orcid: "https://orcid.org/{__orcid__}"',
        f'    affiliation: "{__affiliation__}"',
        f'    email: "{__email__}"',
        f'date-released: "{datetime.now().date().isoformat()}"',
    ]
    return "\n".join(lines) + "\n"


def _github_release_metadata(
    public_release_name: str, destination: str, *, version: str = __version__
) -> dict[str, Any]:
    parsed = Version(version)
    return {
        "tag_name": f"v{parsed}",
        "name": f"{public_release_name} for {destination}",
        "draft": True,
        "prerelease": parsed.is_prerelease,
    }


def _materialize_bundle(
    project_root: Path, bundle_dir: Path, included_assets: list[dict[str, Any]]
) -> None:
    for asset in included_assets:
        source_path = project_root / asset["source_path"]
        target_path = bundle_dir / asset["bundle_path"]
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def _build_checksum_ledger(
    bundle_dir: Path, included_assets: list[dict[str, Any]]
) -> dict[str, str]:
    ledger: dict[str, str] = {}
    for asset in included_assets:
        bundle_path = asset["bundle_path"]
        checksum_path = bundle_dir / bundle_path
        if checksum_path.exists():
            ledger[bundle_path] = _sha256_file(checksum_path)
    return ledger


def _write_checksum_ledger(path: Path, checksums: dict[str, str]) -> None:
    lines = [
        f"{checksum}  {rel_path}" for rel_path, checksum in sorted(checksums.items())
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_zip_archive(bundle_dir: Path, archive_path: Path) -> None:
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(bundle_dir.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(bundle_dir).as_posix())


def _public_preflight_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Public Release Preflight",
        "",
        f"- Status: `{report['status']}`",
        f"- Destination: `{report['destination']}`",
        f"- Included assets: `{report['included_asset_count']}`",
        f"- Excluded assets: `{report['excluded_asset_count']}`",
        f"- Fallback targets with corroboration: `{report['corroborated_fallback_target_count']}`",
        "",
        "Blocked reasons:",
    ]
    if report["blocked_reasons"]:
        lines.extend(f"- {reason}" for reason in report["blocked_reasons"])
    else:
        lines.append("- none")
    return "\n".join(lines)


def _release_dir(output_dir: Path, release_dir: Path | str | None) -> Path:
    return (
        Path(release_dir)
        if release_dir is not None
        else output_dir / "releases" / "public_release"
    )


def _package_info(project_root: Path) -> dict[str, Any]:
    git = _git_info(project_root)
    return {
        "project_name": "blake",
        "version": __version__,
        "authors": __author__,
        "repository_url": _project_url(project_root, "Repository")
        or "https://github.com/docxology/blake",
        "homepage_url": _project_url(project_root, "Homepage")
        or "https://github.com/docxology/blake",
        **git,
    }


def _project_url(project_root: Path, label: str) -> str | None:
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        return None
    pattern = re.compile(rf"^{re.escape(label)}\s*=\s*\"([^\"]+)\"", re.MULTILINE)
    match = pattern.search(pyproject.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def _git_info(project_root: Path) -> dict[str, Any]:
    commit = _run_git(project_root, "rev-parse", "HEAD")
    branch = _run_git(project_root, "rev-parse", "--abbrev-ref", "HEAD")
    remote = _run_git(project_root, "remote", "get-url", "origin")
    status = _run_git(project_root, "status", "--porcelain")
    return {
        "git_commit": commit,
        "git_branch": branch,
        "git_remote": remote,
        "git_dirty": bool(status),
    }


def _run_git(project_root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=project_root,
            capture_output=True,
            check=True,
            text=True,
        )
    except Exception:
        return None
    return result.stdout.strip() or None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _blocked_references_text(blocked_references: list[dict[str, Any]]) -> list[str]:
    return [
        f"{row['source_path']} references excluded asset {row['blocked_reference']}"
        for row in blocked_references
    ]


def _blocked_reference_candidates() -> set[str]:
    candidates = {
        candidate
        for candidate in EXCLUDED_EXACT_PATHS
        if candidate and not _contains_glob(candidate)
    }
    candidates.update(
        candidate
        for candidate in EXCLUDED_PUBLIC_PATTERNS
        if candidate and not _contains_glob(candidate)
    )
    return candidates


def _contains_glob(value: str) -> bool:
    return any(char in value for char in "*?[")


__all__ = [
    "FallbackCorroborationRecord",
    "PublicReleaseAsset",
    "PublicReleaseExclusion",
    "build_public_release_report",
    "write_public_release_package",
    "write_public_release_preflight",
]
