"""Hydration must use its explicitly selected framework, never an ancestor guess."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts/z_generate_manuscript_variables.py"
)


def observe(tmp_path, selection):
    environment = dict(os.environ)
    environment.pop("TEMPLATE_REPO_ROOT", None)
    if selection is not None:
        environment["TEMPLATE_REPO_ROOT"] = str(selection)
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            "import runpy,sys; m=runpy.run_path(sys.argv[1]); "
            "print(m['_find_repo_root']())",
            str(SCRIPT),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def framework(tmp_path):
    root = tmp_path / "framework"
    marker = root / "infrastructure/rendering/__init__.py"
    marker.parent.mkdir(parents=True)
    marker.write_text(
        '"""A filesystem admission fixture, not a native framework run."""\n'
    )
    return root


def test_current_package_layout_is_admitted(tmp_path):
    root = framework(tmp_path)
    result = observe(tmp_path, root)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(root)


@pytest.mark.parametrize("selection", (None, "", "missing"))
def test_missing_selection_refuses_instead_of_searching_ancestors(tmp_path, selection):
    framework(tmp_path)
    result = observe(tmp_path, selection)
    assert result.returncode != 0
    code = "template_root_required" if not selection else "template_root_invalid"
    assert code in result.stderr


def test_symlink_selection_refuses(tmp_path):
    root = framework(tmp_path)
    link = tmp_path / "alias"
    link.symlink_to(root, target_is_directory=True)
    result = observe(tmp_path, link)
    assert result.returncode != 0
    assert "template_root_symlink" in result.stderr
