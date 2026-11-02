#!/usr/bin/env python3
"""Thin orchestrator: generate and inject manuscript variables for blake.

Reads ``analysis_output/`` artifacts, writes
``output/data/manuscript_variables.json``, and substitutes ``{{TOKEN}}`` markers
in ``docs/manuscript/*.md`` into ``output/manuscript/`` for PDF rendering.

All computation lives in ``manuscript_tools.variables``; all injection lives in
``infrastructure.rendering.manuscript_injection``. The render pipeline discovers
and runs this script automatically during hydration (the ``z_`` prefix makes it
sort last).

Exit codes:
    0   variables written and injected successfully
    1   unexpected error (e.g. missing analysis outputs in pipeline mode)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


def _find_repo_root(selected: str | None = None) -> Path:
    """Admit the explicitly selected rendering package without ancestor guesses."""
    if selected is None:
        selected = os.environ.get("TEMPLATE_REPO_ROOT")
    if not selected or not selected.strip():
        raise ValueError("template_root_required: set TEMPLATE_REPO_ROOT")
    root = Path(selected).absolute()
    if any(path.is_symlink() for path in (root, *root.parents)):
        raise ValueError("template_root_symlink: select the actual checkout")
    if not (root / "infrastructure/rendering/__init__.py").is_file():
        raise ValueError("template_root_invalid: rendering package is absent")
    return root


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate manuscript variables for blake"
    )
    parser.add_argument(
        "--template-root",
        help="Explicit framework checkout; defaults to TEMPLATE_REPO_ROOT",
    )
    parser.add_argument(
        "--evidence-root",
        type=str,
        default=os.environ.get("BLAKE_MANUSCRIPT_EVIDENCE_ROOT"),
        help="Explicit read-only saved-evidence root; defaults to this authoring tree",
    )
    parser.add_argument(
        "--allow-draft",
        action="store_true",
        help="Allow missing optional analysis outputs (non-pipeline draft mode)",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(_find_repo_root(args.template_root)))
    from infrastructure.rendering.manuscript_injection import (
        write_resolved_manuscript_tree,
    )

    from manuscript_tools.publication import validate_manuscript_tokens
    from manuscript_tools.variables import generate_variables, save_variables

    variables = generate_variables(
        _PROJECT_ROOT,
        require_analysis_outputs=not args.allow_draft,
        evidence_root=args.evidence_root,
    )
    if not args.allow_draft:
        validate_manuscript_tokens(_PROJECT_ROOT / "docs/manuscript", variables)
    out_path = _PROJECT_ROOT / "output" / "data" / "manuscript_variables.json"
    save_variables(variables, out_path)
    write_resolved_manuscript_tree(_PROJECT_ROOT, variables)
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
