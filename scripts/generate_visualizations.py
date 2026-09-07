#!/usr/bin/env python3
"""Thin orchestrator: comprehensive corpus visualizations.

All corpus loading, lexical statistics, and matplotlib rendering live in
``blake.viz.generate_visualizations``. This script only routes paths and
delegates.
"""

import argparse
from pathlib import Path

from bootstrap import project_root

PROJECT_ROOT = project_root()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate comprehensive text/temporal/network/comparative/image visualizations."
    )
    parser.add_argument(
        '--texts-dir',
        default=str(PROJECT_ROOT / 'data' / 'blake' / 'texts'),
        help='Directory containing the .txt corpus files (default: <repo>/data/blake/texts)'
    )
    parser.add_argument(
        '--output-dir',
        default=str(PROJECT_ROOT / 'analysis_output' / 'visualizations'),
        help='Visualization output base directory (default: <repo>/analysis_output/visualizations)'
    )
    args = parser.parse_args()

    from blake.viz.generate_visualizations import generate_all_visualizations

    generate_all_visualizations(Path(args.texts_dir), Path(args.output_dir))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
