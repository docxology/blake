#!/usr/bin/env python3
"""Thin orchestrator: repair text files that are actually EPUBs.

EPUB detection and HTML→text extraction live in ``blake.corpus.text_repair``.
This script only routes paths and delegates.
"""

import argparse
from pathlib import Path

from bootstrap import project_root

PROJECT_ROOT = project_root()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan data/blake/texts for EPUB files mislabeled as .txt and restore real text."
    )
    parser.add_argument(
        '--texts-dir',
        default=str(PROJECT_ROOT / 'data' / 'blake' / 'texts'),
        help='Directory containing the downloaded .txt corpus files (default: <repo>/data/blake/texts)'
    )
    args = parser.parse_args()

    from blake.corpus.text_repair import fix_text_files

    fix_text_files(Path(args.texts_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
