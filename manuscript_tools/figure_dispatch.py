"""Figure-registry orchestration; analysis stays with its source owner."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pydantic import JsonValue, TypeAdapter

from manuscript_tools.paths import manuscript_roots


def generate_all_figures(
    project_root: Path | str,
    *,
    public_only: bool = False,
    evidence_root: Path | str | None = None,
) -> list[Path]:
    """Keep explicit roots and public exclusions when dispatching builders."""
    from manuscript_tools import figures as source

    roots = manuscript_roots(project_root, evidence_root)
    ao = roots.analysis
    if not ao.exists():
        raise FileNotFoundError(
            f"analysis_output/ not found at {ao}. Run `run_all.py --quick` first."
        )
    source._configure()
    out_dir = roots.output / "figures"
    written: list[Path] = []
    for name, builder in source.FIGURES:
        if public_only and name in source.PUBLICATION_OMISSIONS:
            continue
        written.append(builder(ao, out_dir))
    registry: JsonValue = TypeAdapter(JsonValue).validate_python(
        {
            "schema_version": "1.5",
            "scope": "public" if public_only else "local",
            "generated_at": datetime.now().isoformat(),
            "figures": [
                {
                    "label": f"fig:{path.stem}",
                    "filename": path.name,
                    "path": path.name,
                    "alt_text": source.FIGURE_BRIEFS[path.stem][
                        "accessibility_summary"
                    ],
                    "generated_by": "manuscript_tools.figures",
                    "bytes": path.stat().st_size,
                    "statistics": source.compute_figure_statistics(ao, path.stem),
                    **source.FIGURE_BRIEFS[path.stem],
                }
                for path in written
            ],
        }
    )
    (out_dir / "figure_registry.json").write_text(
        json.dumps(registry, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return written
