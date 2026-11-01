"""Real on-disk distribution fixtures shared by installed-provenance controls."""

import base64
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import blake

COMMIT = "a" * 40
ROOT = Path(blake.__file__).resolve().parent.parent


def distribution(root: Path) -> tuple[Path, Path]:
    package = root / "sample_sdk"
    package.mkdir()
    (package / "__init__.py").write_text("from . import child\n")
    (package / "child.py").write_text("VALUE = 7\n")
    info = root / "sample_sdk-1.2.3.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: sample-sdk\nVersion: 1.2.3\n"
    )
    (info / "direct_url.json").write_text(
        json.dumps(
            {
                "url": "https://example.invalid/sample-sdk.git",
                "vcs_info": {
                    "vcs": "git",
                    "commit_id": COMMIT,
                    "requested_revision": COMMIT,
                },
            }
        )
    )
    record(root, info)
    return package, info


def record(root: Path, info: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "RECORD":
            data = path.read_bytes()
            hashed = (
                base64.urlsafe_b64encode(hashlib.sha256(data).digest())
                .rstrip(b"=")
                .decode()
            )
            rows.append(
                (path.relative_to(root).as_posix(), "sha256=" + hashed, str(len(data)))
            )
    rows.append((info.relative_to(root).as_posix() + "/RECORD", "", ""))
    with (info / "RECORD").open("w", newline="") as stream:
        csv.writer(stream).writerows(rows)


def invoke(root: Path, prefix: str = "") -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ, PYTHONPATH=os.pathsep.join((str(root), str(ROOT))))
    script = (
        prefix
        + "\nfrom blake.methods.installed import verify_installed_git\n"
        + (
            "receipt = verify_installed_git('sample_sdk', '"
            + COMMIT
            + "', 'sample-sdk')\n"
            "print(receipt.model_dump_json())\n"
        )
    )
    return subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
