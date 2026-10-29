from __future__ import annotations

from pathlib import Path

import pytest

from blake.recovery_models import RecoveryError
from blake.recovery_pipeline import recover_corpus
from blake.recovery_registration import register_recovery

from .recovery_fixtures import COMMIT
from tests import recovery_fixtures

saved_sources = recovery_fixtures.saved_sources


def test_register_when_recovery_is_repeated_preserves_analysis_and_other_works(
    saved_sources: Path,
) -> None:
    from blake.metadata.database import MetadataDatabase
    from blake.models import BlakeMetadata, BlakeWork, SourceType, WorkType

    recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)
    count = register_recovery(saved_sources)
    database = MetadataDatabase(saved_sources / "metadata/metadata.db")
    existing = database.load_work("recovered--mhh.a")
    assert existing is not None
    existing.metadata.analysis_results["retained"] = {"value": 7}
    database.save_work(existing)
    unrelated = BlakeWork(
        id="existing",
        metadata=BlakeMetadata(
            id="existing",
            title="Existing",
            source=SourceType.PROJECT_GUTENBERG,
            work_type=WorkType.POEM,
        ),
    )
    database.save_work(unrelated)

    rerun = register_recovery(saved_sources)

    loaded = database.load_work("recovered--mhh.a")
    assert loaded is not None
    assert loaded.text_content == "Eternity is in love\nwith time."
    assert loaded.metadata.work_type == WorkType.ILLUMINATED_BOOK
    assert loaded.metadata.analysis_results["retained"] == {"value": 7}
    assert count == rerun == 6
    assert len(database.load_all_works()) == 7
    assert database.load_work("existing") is not None


@pytest.mark.parametrize("dpi", [300, 100])
def test_register_when_images_are_recovered_preserves_their_metadata(
    saved_sources: Path, dpi: int
) -> None:
    from PIL import Image
    from blake.metadata.database import MetadataDatabase

    path = saved_sources / f"recovery/images/mhh.a.P1.{dpi}.jpg"
    path.parent.mkdir()
    Image.new("RGB", (12, 8), "red").save(path)
    manifest = recover_corpus(saved_sources, commit=COMMIT, offline=True)

    assert register_recovery(saved_sources) == 6

    database = MetadataDatabase(saved_sources / "metadata/metadata.db")
    work = database.load_work("recovered--mhh.a")
    assert work is not None
    assert len(work.images) == 1
    image = work.images[0]
    copy = next(c for c in manifest.copies if c.document_id == "mhh.a")
    assert image.title == f"{copy.title} (mhh.a.P1)"
    assert image.dpi == dpi
    assert image.file_path == path.resolve()
    assert image.original_url == f"https://blakearchive.org/images/mhh.a.p1.{dpi}.jpg"
    assert work.metadata.analysis_results["image_depth"]["image_depth_status"] == (
        "complete" if dpi == 300 else "partial"
    )
    assert image.file_path.read_bytes() == path.read_bytes()


def test_register_when_existing_id_has_different_provenance_refuses(
    saved_sources: Path,
) -> None:
    from blake.metadata.database import MetadataDatabase

    recover_corpus(saved_sources, commit=COMMIT, offline=True, images=False)
    register_recovery(saved_sources)
    database = MetadataDatabase(saved_sources / "metadata/metadata.db")
    work = database.load_work("recovered--mhh.a")
    assert work is not None
    work.metadata.analysis_results["recovery"] = {"source_sha256": "different source"}
    database.save_work(work)

    with pytest.raises(RecoveryError, match="different provenance"):
        register_recovery(saved_sources)

    assert database.load_work("recovered--mhh.a").metadata.analysis_results[
        "recovery"
    ] == {"source_sha256": "different source"}
