#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


def main() -> int:
    from manuscript_tools.cover import generate_cover

    paths = generate_cover(_PROJECT_ROOT)
    for path in paths.values():
        print(str(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
