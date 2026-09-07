#!/usr/bin/env python3
"""Thin orchestrator: target-aware Blake corpus download.

Downloads target-ledger Blake corpus candidates from Project Gutenberg and
the Blake Archive. The work registries, HTTP fetching, and TEI/XML text
extraction live in ``blake.downloader.target_corpus``. This script only
routes paths, configures logging, and delegates. Network-touching: run
deliberately.
"""

import argparse
import asyncio
import logging
from pathlib import Path

from bootstrap import project_root

PROJECT_ROOT = project_root()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download the target Blake corpus from Gutenberg and the Blake Archive."
    )
    parser.add_argument(
        '--data-dir',
        default=str(PROJECT_ROOT / 'data' / 'blake' / 'texts'),
        help='Directory to write downloaded texts and MANIFEST.json (default: <repo>/data/blake/texts)'
    )
    args = parser.parse_args()

    from blake.downloader.target_corpus import download_target_corpus

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    asyncio.run(download_target_corpus(Path(args.data_dir)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
