"""Exercise the reproduction CLI with real source files and a tiny SQLite corpus."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from manuscript_tools.epoch import prepare_analysis_epoch, run_analysis_epoch
from tests.gui_fixtures import seed_gui
from tests.test_saved_analysis_epoch import seed_epoch


def test_reproduction_cli_runs_an_unused_real_store_and_preserves_source_bytes(
    tmp_path,
):
    source = Path(__file__).resolve().parents[1]
    source_receipt = source / "analysis_output/data/analysis_epoch_receipt.json"
    source_receipt_before = (
        source_receipt.read_bytes() if source_receipt.exists() else None
    )
    for name in ("blake", "manuscript_tools"):
        shutil.copytree(
            source / name,
            tmp_path / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "AGENTS.md"),
        )
    shutil.copyfile(source / "uv.lock", tmp_path / "uv.lock")
    (tmp_path / "scripts").mkdir()
    for name in ("bootstrap.py", "reproduce_manuscript_analysis.py"):
        shutil.copyfile(source / "scripts" / name, tmp_path / "scripts" / name)
    data = tmp_path / "blake_data"
    seed_gui(data)
    recovery = data / "recovery"
    recovery.mkdir()
    for name in ("manifest.json", "search.sqlite", "passages.jsonl"):
        (recovery / name).write_bytes(b"Synthetic retained input for the CLI test\n")
    original = (data / "metadata/metadata.db").read_bytes()
    prepare_analysis_epoch(tmp_path, "blake_data/publication/cli")
    environment = os.environ.copy()
    environment["NLTK_DATA"] = str(source / "blake_data/nltk_data")
    completed = subprocess.run(
        [
            sys.executable,
            str(tmp_path / "scripts/reproduce_manuscript_analysis.py"),
            "--data-dir",
            "blake_data/publication/cli",
            "--seed",
            "7",
        ],
        cwd=source,
        env=environment,
        text=True,
        capture_output=True,
        timeout=240,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    receipt = json.loads(
        (tmp_path / "analysis_output/data/analysis_epoch_receipt.json").read_text()
    )
    assert receipt["status"] == "completed"
    assert receipt["analysis_summary"]["works_analyzed"] == 2
    from blake.metadata.database import MetadataDatabase

    saved = MetadataDatabase(
        data / "publication/cli/metadata/metadata.db"
    ).load_all_works()
    rich = next(work for work in saved if work.text_content)
    assert rich.text_analysis["entities"]
    assert rich.visual_analysis
    assert rich.cross_analysis
    assert rich.ontological_analysis
    assert all(work.ontological_analysis for work in saved)
    assert receipt["protected_after"] == receipt["protected_before"]
    assert (
        receipt["protected_after"]["metadata/metadata.db"]
        == hashlib.sha256(original).hexdigest()
    )
    assert (data / "metadata/metadata.db").read_bytes() == original
    source_receipt_after = (
        source_receipt.read_bytes() if source_receipt.exists() else None
    )
    assert source_receipt_after == source_receipt_before


@pytest.mark.parametrize("seed", [-1, 2**32, True])
def test_reproduction_refuses_invalid_seeds_before_writing(tmp_path, seed):
    with pytest.raises(ValueError, match="seed"):
        run_analysis_epoch(tmp_path, "blake_data/publication/new", seed)
    assert not (tmp_path / "analysis_output").exists()


def test_reproduction_refuses_wrong_store_changed_source_and_existing_outputs(tmp_path):
    data, output, store, receipt = seed_epoch(tmp_path)
    with pytest.raises(ValueError, match="prepared"):
        run_analysis_epoch(tmp_path, "blake_data", 7)
    with pytest.raises(ValueError, match="Preserve existing"):
        run_analysis_epoch(tmp_path, str(store.relative_to(tmp_path)), 7)
    (data / "metadata/metadata.db").write_bytes(b"Changed synthetic source")
    with pytest.raises(ValueError, match="Captured metadata changed"):
        run_analysis_epoch(tmp_path, str(store.relative_to(tmp_path)), 7)
