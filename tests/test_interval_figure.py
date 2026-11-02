"""Real small authoring figure production and destination/registry controls."""

import hashlib
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from xml.etree import ElementTree

import pytest
from PIL import Image

from blake.methods.common import EvidenceError
from manuscript_tools import figures
from manuscript_tools.core_architecture import architecture_tokens
from manuscript_tools.interval_figure import IntervalFigureReceipt, fig_interval_support
from manuscript_tools.interval_illustration import build_interval_illustration


def test_actual_figure_publishes_readable_formats_and_bound_sidecar(
    tmp_path: Path,
) -> None:
    # Given no analysis directory, when the code-only builder runs, then real assets are
    # bound.
    unused = tmp_path / "absent-analysis"
    path = fig_interval_support(unused, tmp_path / "figures")
    receipt = IntervalFigureReceipt.model_validate_json(
        path.with_suffix(".json").read_bytes()
    )
    with Image.open(path) as image:
        image.load()
        assert image.width > 1000
        assert image.height > 1000
    assert ElementTree.parse(path.with_suffix(".svg")).getroot().tag.endswith("svg")
    pdf = path.with_suffix(".pdf").read_bytes()
    assert pdf.startswith(b"%PDF-")
    assert b"%%EOF" in pdf[-32:]
    assert set(receipt.outputs) == {
        "core_interval_support.png",
        "core_interval_support.svg",
        "core_interval_support.pdf",
    }
    for name, expected in receipt.outputs.items():
        assert hashlib.sha256((path.parent / name).read_bytes()).hexdigest() == expected
    assert not unused.exists()


def test_occupied_figure_target_refuses_without_changing_bytes(tmp_path: Path) -> None:
    # Given one occupied output name, when asked to render, then the original is
    # preserved.
    target = tmp_path / "core_interval_support.svg"
    target.write_bytes(b"original bytes")
    with pytest.raises(EvidenceError, match="interval_figure_occupied"):
        fig_interval_support(tmp_path / "unused", tmp_path)
    assert target.read_bytes() == b"original bytes"
    assert not target.with_suffix(".png").exists()
    assert not target.with_suffix(".json").exists()


def test_symlinked_figure_root_refuses_before_production(tmp_path: Path) -> None:
    # Given a redirected output root, when asked to render, then no asset is written.
    directory = tmp_path / "real"
    directory.mkdir()
    redirected = tmp_path / "redirect"
    redirected.symlink_to(directory, target_is_directory=True)
    with pytest.raises(EvidenceError, match="interval_figure_symlink"):
        fig_interval_support(tmp_path / "unused", redirected)
    assert not tuple(directory.iterdir())


def test_registry_and_hydration_dispatch_expose_the_same_code_diagnostic(
    tmp_path: Path,
) -> None:
    # Given the existing dispatch surfaces, when queried, then the new diagnostic is
    # registered.
    builders = dict(figures.FIGURES)
    assert builders["core_interval_support"] is fig_interval_support
    stats = figures.compute_figure_statistics(
        tmp_path / "absent", "core_interval_support"
    )
    tokens = architecture_tokens()
    assert stats["CORE_INTERVAL_SOURCE_SHA256"] == tokens["CORE_INTERVAL_SOURCE_SHA256"]
    assert (
        stats["INTERVAL_EXAMPLE_UNION_LENGTH"]
        == tokens["INTERVAL_EXAMPLE_UNION_LENGTH"]
    )
    assert figures.BRIEF_FIELDS <= figures.FIGURE_BRIEFS["core_interval_support"].keys()
    assert not (tmp_path / "absent").exists()
    assert json.dumps(stats)


def test_actual_mid_production_source_change_refuses_the_completion_marker(
    tmp_path: Path,
) -> None:
    # Given an independent authoring copy, when its source changes after drawing, then
    # no seal.
    source = Path(__file__).resolve().parents[1]
    fixture = tmp_path / "producer"
    evidence = build_interval_illustration(source)
    for name in evidence.source_bindings:
        target = fixture / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((source / name).read_bytes())
    renderer = fixture / "manuscript_tools/interval_figure.py"
    text = renderer.read_text()
    trigger = "            _save_artifacts(figure, out_dir)"
    assert text.count(trigger) == 1
    renderer.write_text(
        text.replace(
            trigger,
            trigger
            + '\n            changed = root / "manuscript_tools/core_architecture.py"'
            + '\n            changed.write_bytes(changed.read_bytes() + b"\\n")',
        )
    )
    child = textwrap.dedent(
        f"""
        import sys
        from pathlib import Path
        import blake
        sys.path.insert(0, {str(fixture)!r})
        from blake.methods.common import EvidenceError
        from manuscript_tools.interval_figure import fig_interval_support
        try:
            fig_interval_support(Path("unused"), Path({str(tmp_path / "assets")!r}))
        except EvidenceError as error:
            if error.code != "interval_illustration_source_changed":
                raise
            print(error.code)
        else:
            raise AssertionError("changed source accepted")
    """
    )
    command = [sys.executable, "-B", "-c", child]
    (tmp_path / "prelaunch.json").write_text(json.dumps(command))
    with (
        subprocess.Popen(  # noqa: S603 -- Test-owned copied source and explicit Python.
            command,
            cwd=tmp_path,
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as process
    ):
        (tmp_path / "pid.json").write_text(json.dumps({"pid": process.pid}))
        stdout, stderr = process.communicate()
        (tmp_path / "stdout.log").write_text(stdout)
        (tmp_path / "stderr.log").write_text(stderr)
        (tmp_path / "completion.json").write_text(
            json.dumps({"returncode": process.returncode})
        )
    assert process.returncode == 0, stderr
    assert stdout.strip() == "interval_illustration_source_changed"
    assert (tmp_path / "assets/core_interval_support.png").is_file()
    assert not (tmp_path / "assets/core_interval_support.json").exists()
