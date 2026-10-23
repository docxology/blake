#!/usr/bin/env python3
"""Compatibility entrypoint for complete local source recovery."""

import sys

from bootstrap import project_root

PROJECT_ROOT = project_root()


def main() -> None:
    from blake.recovery import recover_command

    recover_command.main(
        args=["--data-dir", str(PROJECT_ROOT / "blake_data"), *sys.argv[1:]],
        prog_name="download_complete_archive.py",
    )


if __name__ == "__main__":
    main()
