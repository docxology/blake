#!/usr/bin/env python3
"""Export aggregate membership evidence from an explicitly selected saved run."""

import argparse
import json
from pathlib import Path

try:
    from .bootstrap import project_root
except ImportError:
    from bootstrap import project_root


def main(argv: list[str] | None = None) -> int:
    root = project_root()
    from blake.methods.runs import write_new
    from manuscript_tools.run_membership import build_membership_audit

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, default=root)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    raw = (
        json.dumps(build_membership_audit(args.evidence_root), indent=2) + "\n"
    ).encode()
    if args.output:
        write_new(args.output, raw)
    else:
        print(raw.decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
