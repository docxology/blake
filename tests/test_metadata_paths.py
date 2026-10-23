from pathlib import Path

from blake.metadata.database import MetadataDatabase
from blake.models import BlakeMetadata, BlakeWork, SourceType, WorkType


def test_load_when_recovered_text_has_a_recorded_nested_path(tmp_path: Path) -> None:
    text_path = tmp_path / "recovery/texts/archive/mhh.a.txt"
    text_path.parent.mkdir(parents=True)
    text_path.write_text(
        "Eternity is in love with the productions of time.", encoding="utf-8"
    )
    database = MetadataDatabase(tmp_path / "metadata/metadata.db")
    metadata = BlakeMetadata(
        id="mhh.a",
        title="Marriage, copy A",
        work_type=WorkType.ILLUMINATED_BOOK,
        source=SourceType.BLAKE_ARCHIVE,
        file_path=text_path,
    )
    database.save_work(
        BlakeWork(id=metadata.id, metadata=metadata, text_content=text_path.read_text())
    )

    loaded = database.load_work("mhh.a")

    assert loaded is not None
    assert loaded.text_content == text_path.read_text()


def test_load_when_recorded_text_is_outside_data_root_does_not_read_it(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("not part of the corpus", encoding="utf-8")
    database = MetadataDatabase(tmp_path / "corpus/metadata/metadata.db")
    metadata = BlakeMetadata(
        id="mhh.a",
        title="Marriage",
        work_type=WorkType.ILLUMINATED_BOOK,
        source=SourceType.BLAKE_ARCHIVE,
        file_path=outside,
    )
    database.save_work(BlakeWork(id=metadata.id, metadata=metadata))

    loaded = database.load_work("mhh.a")

    assert loaded is not None
    assert loaded.text_content is None
