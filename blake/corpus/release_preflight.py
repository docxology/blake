from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


RIGHTS_GATE_CLASSES: tuple[dict[str, Any], ...] = (
    {
        "artifact_class": "Project code, tests, scripts, and project-authored documentation",
        "rights_matrix_key": "Project code, tests, scripts, and project-authored documentation",
        "default_public_release_rule": "include under repository license",
        "release_disposition": "include",
        "public_bundle_allowed": True,
        "evidence_required": "repository license, authorship, version",
        "checked_paths": ["LICENSE", "README.md", "docs"],
    },
    {
        "artifact_class": "Aggregate counts, provenance tables, and non-image charts",
        "rights_matrix_key": "Aggregate counts, coverage tables, checksums, source URLs, authority tiers, and non-image charts",
        "default_public_release_rule": "include with citations and provenance",
        "release_disposition": "include",
        "public_bundle_allowed": True,
        "evidence_required": "source URL, checksum where applicable, authority tier, generation command",
        "checked_paths": [
            "analysis_output/corpus_manifest.json",
            "analysis_output/visualizations/dataset_statistics.json",
            "output/figures/figure_registry.json",
        ],
    },
    {
        "artifact_class": "Validated Project Gutenberg fallback text",
        "rights_matrix_key": "Project Gutenberg fallback text",
        "default_public_release_rule": "conditional source-specific inclusion",
        "release_disposition": "conditional",
        "public_bundle_allowed": False,
        "evidence_required": "source URL, checksum, validation note, license/trademark handling",
        "checked_paths": ["blake_data/metadata/fallback_text_validations"],
    },
    {
        "artifact_class": "Validated Wikisource fallback text",
        "rights_matrix_key": "Wikisource fallback text",
        "default_public_release_rule": "conditional attribution and license continuity",
        "release_disposition": "conditional",
        "public_bundle_allowed": False,
        "evidence_required": "page URL, retrieval note, attribution, license metadata, checksum",
        "checked_paths": ["blake_data/metadata/fallback_text_validations"],
    },
    {
        "artifact_class": "William Blake Archive TEI, transcriptions, object images, and bulk mirrors",
        "rights_matrix_key": "William Blake Archive TEI, transcriptions, object images, and bulk mirrors",
        "default_public_release_rule": "exclude raw files and mirrors from the public repository",
        "release_disposition": "exclude",
        "public_bundle_allowed": False,
        "evidence_required": "source URL, object/work id, checksum, local-cache path excluded from release",
        "checked_paths": ["blake_data", "analysis_output/data"],
    },
    {
        "artifact_class": "Image mosaics and visual supplements made from local source files",
        "rights_matrix_key": "Image mosaics and visual supplements made from local source files",
        "default_public_release_rule": "local review only unless cleared for the exact venue",
        "release_disposition": "local-only",
        "public_bundle_allowed": False,
        "evidence_required": "input file list, source URLs, resolution, caption caveat, permission or fair-use memo",
        "checked_paths": ["output/figures", "analysis_output/visualizations"],
    },
    {
        "artifact_class": "Generated cover and project-authored diagrams",
        "rights_matrix_key": "Generated cover and project-authored diagrams",
        "default_public_release_rule": "include with provenance and non-evidence label",
        "release_disposition": "include",
        "public_bundle_allowed": True,
        "evidence_required": "prompt/provenance record, generation command, manuscript role",
        "checked_paths": ["output/cover", "output/figures"],
    },
)


EXCLUDED_PUBLIC_PATTERNS: tuple[str, ...] = (
    "blake_data/**",
    "analysis_output/**/raw*/**",
    "analysis_output/**/*.tei",
    "analysis_output/**/*.xml",
    "analysis_output/**/*mosaic*.png",
    "output/figures/*mosaic*.png",
    "output/figures/work_area_image_mosaics.png",
    "output/figures/all_acquired_images_mosaic.png",
)


def write_private_release_preflight(
    project_root: Path | str | None = None,
    *,
    output_dir: Path | str = "analysis_output",
    data_dir: Path | str = "blake_data",
    target: str = "private-github",
) -> dict[str, Any]:
    root = Path(project_root) if project_root is not None else _project_root()
    output_path = Path(output_dir)
    data_path = Path(data_dir)
    reports_dir = output_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    rights_gate = build_rights_gate_report(
        root,
        output_dir=output_path,
        data_dir=data_path,
    )
    rights_gate_path = reports_dir / "rights_gate_report.json"
    rights_gate_md_path = reports_dir / "rights_gate_report.md"
    rights_gate_path.write_text(json.dumps(rights_gate, indent=2), encoding="utf-8")
    rights_gate_md_path.write_text(
        _rights_gate_markdown(rights_gate), encoding="utf-8"
    )

    preflight = build_private_release_preflight(
        root,
        output_dir=output_path,
        data_dir=data_path,
        target=target,
        rights_gate_path=rights_gate_path,
        rights_gate=rights_gate,
    )
    preflight_path = reports_dir / "private_release_preflight.json"
    preflight_md_path = reports_dir / "private_release_preflight.md"
    preflight_path.write_text(json.dumps(preflight, indent=2), encoding="utf-8")
    preflight_md_path.write_text(
        _private_preflight_markdown(preflight), encoding="utf-8"
    )
    preflight["path"] = str(preflight_path)
    preflight["markdown_path"] = str(preflight_md_path)
    preflight["rights_gate_path"] = str(rights_gate_path)
    preflight["rights_gate_markdown_path"] = str(rights_gate_md_path)
    preflight_path.write_text(json.dumps(preflight, indent=2), encoding="utf-8")
    return preflight


def build_rights_gate_report(
    project_root: Path,
    *,
    output_dir: Path,
    data_dir: Path,
) -> dict[str, Any]:
    rights_matrix_path = project_root / "manuscript" / "13_supplement_rights_matrix.md"
    rights_matrix_text = (
        rights_matrix_path.read_text(encoding="utf-8")
        if rights_matrix_path.exists()
        else ""
    )
    rows = []
    for artifact in RIGHTS_GATE_CLASSES:
        checked_paths = [
            {
                "path": path,
                "exists": (project_root / path).exists()
                if not path.startswith("analysis_output")
                else (output_dir / path.removeprefix("analysis_output/")).exists(),
            }
            for path in artifact["checked_paths"]
        ]
        rows.append(
            {
                **artifact,
                "rights_matrix_row_found": artifact["rights_matrix_key"]
                in rights_matrix_text,
                "checked_paths": checked_paths,
            }
        )

    blocked = [
        row
        for row in rows
        if row["release_disposition"] in {"exclude", "local-only", "conditional"}
        and not row["public_bundle_allowed"]
    ]
    return {
        "schema_version": "1.0",
        "artifact": "rights_gate_report",
        "generated_at": datetime.now().isoformat(),
        "rights_matrix_path": str(rights_matrix_path),
        "output_dir": str(output_dir),
        "data_dir": str(data_dir),
        "artifact_classes": rows,
        "public_bundle_allowed_count": sum(
            1 for row in rows if row["public_bundle_allowed"]
        ),
        "public_bundle_blocked_count": len(blocked),
        "excluded_public_patterns": list(EXCLUDED_PUBLIC_PATTERNS),
        "status": "blocked_for_public_redistribution"
        if blocked
        else "public_bundle_clear",
    }


def build_private_release_preflight(
    project_root: Path,
    *,
    output_dir: Path,
    data_dir: Path,
    target: str,
    rights_gate_path: Path,
    rights_gate: dict[str, Any],
) -> dict[str, Any]:
    manifest = _read_json(output_dir / "corpus_manifest.json", {})
    figure_registry = _read_json(project_root / "output" / "figures" / "figure_registry.json", {})
    dataset_statistics = _read_json(
        output_dir / "visualizations" / "dataset_statistics.json", {}
    )
    excluded = [
        row
        for row in rights_gate["artifact_classes"]
        if row["release_disposition"] in {"exclude", "local-only", "conditional"}
        and not row["public_bundle_allowed"]
    ]
    return {
        "schema_version": "1.0",
        "artifact": "private_release_preflight",
        "generated_at": datetime.now().isoformat(),
        "target": target,
        "publish_action": "none",
        "no_public_release_performed": True,
        "output_dir": str(output_dir),
        "data_dir": str(data_dir),
        "candidate_private_bundle": [
            "project code, tests, scripts, and project-authored documentation",
            "manuscript source and generated PDF/web outputs",
            "aggregate diagnostics, source URLs, checksums, and non-image charts",
        ],
        "public_exclusions": list(EXCLUDED_PUBLIC_PATTERNS),
        "rights_gate_report": str(rights_gate_path),
        "public_redistribution_status": rights_gate["status"],
        "blocked_artifact_classes": [
            {
                "artifact_class": row["artifact_class"],
                "release_disposition": row["release_disposition"],
                "evidence_required": row["evidence_required"],
            }
            for row in excluded
        ],
        "manifest_summary": {
            "coverage_status": manifest.get("coverage_status"),
            "coverage_counts": manifest.get("coverage_counts", {}),
            "total_works": manifest.get("total_works", 0),
            "total_images": manifest.get("total_images", 0),
        },
        "figure_registry_summary": {
            "schema_version": figure_registry.get("schema_version"),
            "figure_count": len(figure_registry.get("figures", [])),
            "has_statistical_briefs": all(
                figure.get("statistics")
                and figure.get("statistical_question")
                and figure.get("missingness_or_scope")
                for figure in figure_registry.get("figures", [])
            ),
        },
        "dataset_statistics_summary": {
            "schema_version": dataset_statistics.get("schema_version"),
            "coverage": dataset_statistics.get("coverage", {}),
            "missingness": dataset_statistics.get("missingness", {}),
        },
    }


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _rights_gate_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Rights Gate Report",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Rights matrix: `{report['rights_matrix_path']}`",
        "",
        "| Artifact class | Disposition | Public bundle allowed | Matrix row |",
        "| --- | --- | --- | --- |",
    ]
    for row in report["artifact_classes"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["artifact_class"],
                    row["release_disposition"],
                    "yes" if row["public_bundle_allowed"] else "no",
                    "yes" if row["rights_matrix_row_found"] else "no",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Excluded public patterns:",
            *[f"- `{pattern}`" for pattern in report["excluded_public_patterns"]],
            "",
        ]
    )
    return "\n".join(lines)


def _private_preflight_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Private Release Preflight",
        "",
        f"- Target: `{report['target']}`",
        f"- Publish action: `{report['publish_action']}`",
        f"- Public redistribution status: `{report['public_redistribution_status']}`",
        f"- Rights gate report: `{report['rights_gate_report']}`",
        "",
        "Candidate private bundle:",
        *[f"- {item}" for item in report["candidate_private_bundle"]],
        "",
        "Blocked public artifact classes:",
    ]
    lines.extend(
        f"- {row['artifact_class']} ({row['release_disposition']}): {row['evidence_required']}"
        for row in report["blocked_artifact_classes"]
    )
    lines.extend(
        [
            "",
            "Public exclusions:",
            *[f"- `{pattern}`" for pattern in report["public_exclusions"]],
            "",
        ]
    )
    return "\n".join(lines)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]
