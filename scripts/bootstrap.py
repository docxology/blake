"""Shared path bootstrap for thin-orchestrator scripts.

Puts the repository root on ``sys.path`` so the ``blake`` and
``manuscript_tools`` packages resolve when a script is executed outside the
project virtualenv, and returns the root so scripts can route data/output
paths (scripts must never depend on the caller's cwd).
"""
from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    """Repository root (parent of scripts/), inserted into sys.path."""
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root
