"""Manuscript diagnostics must follow the saved run's actual data store."""

import hashlib
import json

import pytest

from manuscript_tools.nlp_diagnostics import build_nlp_diagnostics
from manuscript_tools.epoch import prepare_analysis_epoch
from blake.metadata.database import MetadataDatabase
from tests.gui_fixtures import seed_gui


def inputs(root, data_dir):
    metrics = root / "analysis_output/visualizations/text_metrics.json"
    metrics.parent.mkdir(parents=True)
    metrics.write_text(json.dumps([{"work_id": "a", "has_text": True}]))
    manifest = root / "analysis_output/corpus_manifest.json"
    manifest.write_text(
        json.dumps({"data_dir": str(data_dir) if data_dir is not None else None})
    )
    return manifest


def test_diagnostics_bind_the_saved_data_directory_and_manifest(tmp_path):
    current = tmp_path / "blake_data/publication/current"
    (current / "texts").mkdir(parents=True)
    text = "Current source vision and identity"
    (current / "texts/a.txt").write_text(text)
    stale = tmp_path / "blake_data/texts"
    stale.mkdir()
    (stale / "a.txt").write_text("Wrong stale source")
    manifest = inputs(tmp_path, current)
    result = build_nlp_diagnostics(tmp_path)
    assert (
        result["membership"]["text_sha256"]["a"]
        == hashlib.sha256(text.encode()).hexdigest()
    )
    assert (
        result["sources"]["corpus_manifest_sha256"]
        == hashlib.sha256(manifest.read_bytes()).hexdigest()
    )
    assert "publication/current/texts" in result["sources"]["texts"]


@pytest.mark.parametrize("kind", ["outside", "symlink", "invalid"])
def test_saved_data_directory_cannot_escape_or_fall_back(tmp_path, kind):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    if kind == "outside":
        data = outside
    elif kind == "symlink":
        data = root / "link"
        data.symlink_to(outside, target_is_directory=True)
    else:
        data = None
    inputs(root, data)
    with pytest.raises(ValueError):
        build_nlp_diagnostics(root)


def test_epoch_copies_text_and_metadata_without_copying_or_changing_images(tmp_path):
    source = tmp_path / "blake_data"
    rich, _ = seed_gui(source)
    original = source / "metadata/metadata.db"
    before = original.read_bytes()
    target = prepare_analysis_epoch(tmp_path, "blake_data/publication/test-run")
    works = MetadataDatabase(target / "metadata/metadata.db").load_all_works()
    copied = next(work for work in works if work.id == rich.id)
    assert copied.text_content == rich.text_content
    assert copied.metadata.file_path.is_relative_to(target)
    assert copied.images[0].file_path == rich.images[0].file_path
    assert not (target / "images").exists()
    assert original.read_bytes() == before
    assert not copied.text_analysis and not copied.fully_processed
    assert (
        json.loads((target / "epoch-inputs.json").read_text())["images_copied"] is False
    )
    with pytest.raises(ValueError, match="new"):
        prepare_analysis_epoch(tmp_path, "blake_data/publication/test-run")


def test_epoch_rejects_escape_and_symlink_destinations(tmp_path):
    seed_gui(tmp_path / "blake_data")
    with pytest.raises(ValueError):
        prepare_analysis_epoch(tmp_path, "../outside")
    publication = tmp_path / "blake_data/publication"
    publication.symlink_to(tmp_path / "outside", target_is_directory=True)
    with pytest.raises(ValueError):
        prepare_analysis_epoch(tmp_path, "blake_data/publication/new")
