#!/usr/bin/env python3
"""Verify retained recovery and seal the saved publication-analysis evidence."""

import argparse
from pathlib import Path

from bootstrap import project_root


def main() -> int:
    root = project_root()
    from manuscript_tools.publication import seal_publication_evidence

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-receipt", type=Path, required=True)
    args = parser.parse_args()
    print(seal_publication_evidence(root, args.analysis_receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
