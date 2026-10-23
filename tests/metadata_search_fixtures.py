"""Real SQLite work records for metadata navigation tests."""

from datetime import datetime
from pathlib import Path

from PIL import Image
import pytest

from blake.metadata.database import MetadataDatabase
from blake.models import BlakeImage, BlakeMetadata, BlakeWork, SourceType, WorkType


@pytest.fixture
def stored_works(tmp_path: Path):
    data = tmp_path / "data"
    (data / "texts").mkdir(parents=True)
    database = MetadataDatabase(data / "metadata/metadata.db")
    rows = [
        (
            "a",
            "State study",
            "Time time",
            SourceType.BLAKE_ARCHIVE,
            WorkType.POEM,
            datetime(1794, 1, 1),
            ["state", "alpha"],
            ["Time"],
            ["Mind"],
            "A",
            True,
        ),
        (
            "b",
            "Poem",
            "State",
            SourceType.PROJECT_GUTENBERG,
            WorkType.LETTER,
            datetime(1794, 6, 1),
            ["beta"],
            ["TIME"],
            ["Other"],
            "A",
            False,
        ),
        (
            "c",
            "Remote",
            "  ",
            SourceType.BLAKE_ARCHIVE,
            WorkType.POEM,
            datetime(1800, 1, 1),
            ["alpha"],
            [],
            ["Mind"],
            "B",
            False,
        ),
        (
            "d",
            "No date",
            None,
            SourceType.INTERNET_ARCHIVE,
            WorkType.MANUSCRIPT,
            None,
            [],
            [],
            [],
            None,
            False,
        ),
    ]
    for (
        identifier,
        title,
        text,
        source,
        kind,
        date,
        tags,
        themes,
        subjects,
        series,
        processed,
    ) in rows:
        path = data / "texts" / (identifier + ".txt") if text is not None else None
        if path is not None:
            path.write_text(text)
        images = []
        if identifier in ("a", "c"):
            image_path = data / (identifier + ".png")
            Image.new("RGB", (2, 2), "red").save(image_path)
            images.append(
                BlakeImage(
                    id="image-" + identifier,
                    metadata_id=identifier,
                    title="Synthetic",
                    file_path=image_path,
                    description="state time" if identifier == "a" else None,
                )
            )
        metadata = BlakeMetadata(
            id=identifier,
            title=title,
            work_type=kind,
            source=source,
            creation_date=date,
            tags=tags,
            themes=themes,
            subjects=subjects,
            series=series,
            processed=processed,
            description="eternity" if identifier == "a" else None,
            file_path=path,
        )
        database.save_work(
            BlakeWork(
                id=identifier, metadata=metadata, images=images, text_content=text
            )
        )
    return sorted(database.load_all_works(), key=lambda work: work.id)
