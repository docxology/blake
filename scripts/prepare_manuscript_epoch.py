#!/usr/bin/env python3
"""Prepare a new, private analysis epoch from retained source evidence."""

import argparse
from bootstrap import project_root

PROJECT_ROOT = project_root()


def main() -> None:
    from manuscript_tools.epoch import prepare_analysis_epoch

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    print(prepare_analysis_epoch(PROJECT_ROOT, args.destination))


if __name__ == "__main__":
    main()
