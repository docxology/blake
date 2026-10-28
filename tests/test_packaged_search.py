"""Exercise producer custody from an installed-layout package in real subprocesses."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from blake.text_search.recovered import _producer


@pytest.mark.parametrize("include_lock", [True, False])
def test_installed_layout_requires_and_binds_dependency_lock(
    tmp_path: Path, include_lock: bool
) -> None:
    root = Path(__file__).resolve().parents[1]
    target = tmp_path / "installed"
    shutil.copytree(
        root / "blake", target / "blake", ignore=shutil.ignore_patterns("__pycache__")
    )
    if include_lock:
        resource = target / "blake/_resources/uv.lock"
        resource.parent.mkdir()
        shutil.copyfile(root / "uv.lock", resource)
    code = (
        f"import sys,json; sys.path.insert(0,{str(target)!r}); "
        "from blake.text_search.recovered import _producer; "
        "print(json.dumps(_producer().model_dump(),sort_keys=True))"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if include_lock:
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == _producer().model_dump()
        resource.write_bytes(resource.read_bytes() + b"\n# changed lock\n")
        changed = subprocess.run(
            [sys.executable, "-I", "-c", code],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert changed.returncode == 0, changed.stderr
        assert (
            json.loads(changed.stdout)["files"]["uv.lock"]
            != _producer().files["uv.lock"]
        )
    else:
        assert result.returncode != 0
        assert "Producer dependency lock is absent; reinstall Blake" in result.stderr



@pytest.mark.parametrize("missing", [None, "LICENSE", "pyproject.toml", "uv.lock"])
def test_installed_recovery_retains_complete_recipe_metadata(
    tmp_path: Path, missing: str | None
) -> None:
    # Given an installed package with its own recipe resources and no checkout.
    root = Path(__file__).resolve().parents[1]
    target = tmp_path / "installed"
    shutil.copytree(
        root / "blake", target / "blake", ignore=shutil.ignore_patterns("__pycache__")
    )
    resources = target / "blake/_resources"
    resources.mkdir(exist_ok=True)
    for name in ("LICENSE", "pyproject.toml", "uv.lock"):
        if name != missing:
            shutil.copyfile(root / name, resources / name)
    output = tmp_path / "recovered"
    code = (
        f"import sys; sys.path.insert(0,{str(target)!r}); "
        "from pathlib import Path; from blake.recovery_io import retain_recipe; "
        f"print(retain_recipe(Path({str(output)!r})).path)"
    )
    # When recovery captures the exact recipe through the installed module.
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    # Then all metadata is retained, or a missing required input rejects capture.
    if missing is None:
        assert result.returncode == 0, result.stderr
        with tarfile.open(output / result.stdout.strip()) as archive:
            for name in ("LICENSE", "pyproject.toml", "uv.lock"):
                handle = archive.extractfile(name)
                assert handle is not None
                with handle:
                    assert handle.read() == (root / name).read_bytes()
            assert "blake/recovery_io.py" in archive.getnames()
    else:
        assert result.returncode != 0
        assert "FileNotFoundError" in result.stderr and missing in result.stderr
        assert not output.exists()
