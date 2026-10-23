#!/usr/bin/env python3
"""Restore persisted results and regenerate derived reports from a qualified epoch."""

from bootstrap import project_root


def main() -> int:
    from manuscript_tools.refresh import refresh_saved_epoch

    print(refresh_saved_epoch(project_root()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
