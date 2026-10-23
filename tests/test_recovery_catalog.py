from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from blake.recovery import RecoveryError, recover_corpus
from blake.recovery_catalog import ERDMAN_COMMIT, recover_catalog
from .recovery_fixtures import COMMIT, seed_sources


def seed_catalog(root: Path) -> None:
    sources = root / "sources/live"
    sources.mkdir(parents=True, exist_ok=True)
    for kind, rows in (
        ("work", [{"bad_id": "mhh"}]),
        ("copy", [{"bad_id": "mhh.a"}]),
        (
            "object",
            [
                {"desc_id": "mhh.a.illbk.1", "dbi": "mhh.a.p1"},
                {"desc_id": "new.1", "dbi": "new.P1"},
                {"desc_id": "editorial", "dbi": "../figures/1.1"},
            ],
        ),
    ):
        (sources / f"{kind}-inventory.json").write_text(json.dumps({"results": rows}))
    with tarfile.open(
        root / f"sources/erdman-{ERDMAN_COMMIT}.tar.gz", "w:gz"
    ) as archive:
        content = b'<body><div1 id="b7"><head>THE EVERLASTING GOSPEL</head><p>Synthetic source control.</p></div1></body>'
        member = tarfile.TarInfo(f"erdman-{ERDMAN_COMMIT}/data/erd3.xml")
        member.size = len(content)
        archive.addfile(member, io.BytesIO(content))


def test_full_catalog_when_sources_are_cached_retains_all_bytes_and_explicit_references(
    tmp_path: Path,
) -> None:
    seed_catalog(tmp_path)

    summary, files = recover_catalog(tmp_path, [], offline=True)

    assert summary.work_records == summary.copy_records == 1
    assert summary.object_records == 3
    assert summary.extra_image_ids == ("mhh.a.p1", "new.p1")
    assert summary.non_image_references == ("../figures/1.1",)
    assert any(f.path.endswith("/data/erd3.xml") for f in files)
    assert all((tmp_path / f.path).stat().st_size == f.size for f in files)


@pytest.mark.parametrize("problem", ["empty", "duplicate_work", "duplicate_object"])
def test_catalog_when_inventory_is_empty_or_ambiguous_refuses(
    tmp_path: Path, problem: str
) -> None:
    seed_catalog(tmp_path)
    kind = "object" if problem == "duplicate_object" else "work"
    path = tmp_path / f"sources/live/{kind}-inventory.json"
    rows = json.loads(path.read_text())["results"]
    duplicate = dict(rows[0])
    if problem == "duplicate_object":
        duplicate["dbi"] = "different.P1"
    path.write_text(
        json.dumps({"results": [] if problem == "empty" else [*rows, duplicate]})
    )

    with pytest.raises(RecoveryError):
        recover_catalog(tmp_path, [], offline=True)


def test_real_cli_when_full_profile_is_requested_persists_it_for_offline_resume(
    tmp_path: Path,
) -> None:
    data = seed_sources(tmp_path)
    seed_catalog(data / "recovery")
    command = [
        sys.executable,
        "-m",
        "blake.recovery",
        "recover",
        "--data-dir",
        str(data),
        "--commit",
        COMMIT,
        "--offline",
        "--no-images",
        "--full",
    ]

    process = subprocess.run(command, check=True, capture_output=True, text=True)

    assert json.loads(process.stdout)["catalog"]["object_records"] == 3
    resumed = recover_corpus(data, commit=COMMIT, offline=True, images=False)
    assert resumed.catalog is not None
    assert resumed.catalog.extra_image_ids == ("new.p1",)
    assert resumed.images.expected == 3
