#!/usr/bin/env python3
"""Run the prepared local analysis epoch through the qualified corpus API."""

import argparse

from bootstrap import project_root


def main() -> int:
    root = project_root()
    from manuscript_tools.epoch import run_analysis_epoch

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    print(run_analysis_epoch(root, args.data_dir, args.seed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
