#!/usr/bin/env python3
"""Thin orchestrator: re-download Project Gutenberg corpus texts.

The Gutenberg ID list, URL fallback chain, validation heuristic, and
corrupted-EPUB removal live in ``blake.downloader.gutenberg_redownload``.
This script only routes paths and delegates. Network-touching: run
deliberately.
"""

import argparse
from pathlib import Path

from bootstrap import project_root

PROJECT_ROOT = project_root()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-download Gutenberg corpus texts, replacing corrupted EPUB-mislabeled files."
    )
    parser.add_argument(
        '--output-dir',
        default=str(PROJECT_ROOT / 'data' / 'blake' / 'texts'),
        help='Directory to write the downloaded .txt files (default: <repo>/data/blake/texts)'
    )
    args = parser.parse_args()

    from blake.downloader.gutenberg_redownload import redownload_texts

    redownload_texts(Path(args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
