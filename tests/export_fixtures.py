"""Synthetic export records with real local image bytes."""

from datetime import datetime
from pathlib import Path

from PIL import Image

from blake.models import BlakeImage, BlakeMetadata, BlakeWork, SourceType, WorkType


def export_work(root: Path, *, rich: bool = True) -> BlakeWork:
    root.mkdir(parents=True, exist_ok=True)
    metadata = BlakeMetadata(
        id="rich" if rich else "empty",
        title="Synthetic export study with a deliberately long descriptive title"
        if rich
        else "Empty",
        work_type=WorkType.POEM,
        source=SourceType.PROJECT_GUTENBERG,
        creation_date=datetime(1794, 1, 2) if rich else None,
        publication_date=datetime(1804, 3, 4) if rich else None,
        description="Synthetic description, with punctuation." if rich else None,
        medium="ink" if rich else None,
        dimensions="4 x 4" if rich else None,
        location="Test storage" if rich else None,
        tags=["alpha", "beta"] if rich else [],
        themes=["states", "time"] if rich else [],
        subjects=["synthetic"] if rich else [],
        source_url="https://example.test/synthetic" if rich else None,
        source_id="test-edition" if rich else None,
        checksum="a" * 64 if rich else None,
        usage_terms="Synthetic test record",
        analysis_results={
            "source_authority_tier": "fallback_text_validated",
            "run_id": "test-run",
        }
        if rich
        else {},
    )
    images = []
    if rich:
        original = root / "plate.png"
        thumb = root / "thumb.png"
        Image.new("RGB", (4, 4), (10, 20, 30)).save(original)
        Image.new("RGB", (2, 2), (10, 20, 30)).save(thumb)
        images.append(
            BlakeImage(
                id="plate",
                metadata_id=metadata.id,
                title="Synthetic plate",
                file_path=original,
                thumbnail_path=thumb,
            )
        )
    return BlakeWork(
        id=metadata.id,
        metadata=metadata,
        images=images,
        text_content='State, "quoted"\nAlbion’s & time.' if rich else None,
        fully_processed=rich,
        text_analysis={
            "basic_stats": {
                "word_count": 5,
                "sentence_count": 2,
                "vocabulary_richness": 0.75,
            },
            "sentiment": {"sentiment": "positive", "compound_score": 0.5},
        }
        if rich
        else {},
        visual_analysis={"brightness": 0.25} if rich else {},
        cross_analysis={"links": ["test"]} if rich else {},
    )
