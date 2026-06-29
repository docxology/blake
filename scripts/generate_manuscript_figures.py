#!/usr/bin/env python3
"""Thin orchestrator: generate manuscript figures for blake.

Draws every manuscript figure from ``analysis_output/`` JSON into
``output/figures/``. All plotting logic lives in ``manuscript_tools.figures``.
Run after ``blake corpus run`` has refreshed ``analysis_output/`` and before PDF
rendering.

Exit codes:
    0   all figures written
    1   unexpected error (e.g. analysis_output/ missing)
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


def main() -> int:
    from manuscript_tools.cover import generate_cover
    from manuscript_tools.figures import generate_all_figures

    cover_paths = generate_cover(_PROJECT_ROOT)
    written = generate_all_figures(_PROJECT_ROOT)
    for path in cover_paths.values():
        print(str(path))
    for path in written:
        print(str(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
