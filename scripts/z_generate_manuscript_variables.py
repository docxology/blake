#!/usr/bin/env python3
"""Thin orchestrator: generate and inject manuscript variables for blake.

Reads ``analysis_output/`` artifacts, writes
``output/data/manuscript_variables.json``, and substitutes ``{{TOKEN}}`` markers
in ``manuscript/*.md`` into ``output/manuscript/`` for PDF rendering.

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


def _find_repo_root() -> Path | None:
    """Locate the template repo root (the dir containing ``infrastructure/``).

    ``blake`` lives under ``projects/working/`` as a symlink to an external
    repo, so ``Path(__file__).resolve()`` escapes the template tree and the
    relative climb to the repo root breaks. Resolution order:

    1. ``TEMPLATE_REPO_ROOT`` env var — set by the render pipeline when it
       invokes this hydration script as a subprocess (the intended hook).
    2. Search upward from the current working directory and the unresolved
       script path for the marker module (covers standalone ``uv run`` use).
    """
    marker = Path("infrastructure") / "rendering" / "manuscript_injection.py"
    env_root = os.environ.get("TEMPLATE_REPO_ROOT")
    if env_root and (Path(env_root) / marker).exists():
        return Path(env_root)
    starts = [Path.cwd(), Path(__file__).absolute().parent]
    for base in starts:
        p = base
        for _ in range(12):
            if (p / marker).exists():
                return p
            if p.parent == p:
                break
            p = p.parent
    return None


_REPO_ROOT = _find_repo_root()
if _REPO_ROOT is not None:
    sys.path.insert(0, str(_REPO_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate manuscript variables for blake")
    parser.add_argument(
        "--allow-draft",
        action="store_true",
        help="Allow missing optional analysis outputs (non-pipeline draft mode)",
    )
    args = parser.parse_args()

    from infrastructure.rendering.manuscript_injection import write_resolved_manuscript_tree
    from manuscript_tools.variables import generate_variables, save_variables

    variables = generate_variables(
        _PROJECT_ROOT,
        require_analysis_outputs=not args.allow_draft,
    )
    out_path = _PROJECT_ROOT / "output" / "data" / "manuscript_variables.json"
    save_variables(variables, out_path)
    write_resolved_manuscript_tree(_PROJECT_ROOT, variables)
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
