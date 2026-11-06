"""Synthetic image compatibility, separate from historical corpus evidence."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from blake.downloader.scraper import ImageDownloader


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "format_name,suffix,mode",
    [
        ("JPEG", "jpg", "RGB"),
        ("PNG", "png", "RGBA"),
        ("TIFF", "tiff", "L"),
        ("GIF", "gif", "P"),
        ("WEBP", "webp", "RGB"),
        ("BMP", "bmp", "RGB"),
    ],
)
async def test_real_codecs_preserve_source_and_match_decoded_image_measurements(
    tmp_path: Path, format_name: str, suffix: str, mode: str
) -> None:
    values = np.arange(32 * 24 * 3, dtype=np.uint8).reshape(24, 32, 3)
    downloader = ImageDownloader(tmp_path / "data")
    path = downloader.images_dir / f"control.{suffix}"
    Image.fromarray(values).convert(mode).save(path, format=format_name)
    original = path.read_bytes()

    downloader._validate_image(path)
    actual = await downloader._process_image(path)
    thumbnail = await downloader._create_thumbnail(path, path.name)

    assert (actual["width"], actual["height"], actual["format"]) == (
        32,
        24,
        format_name,
    )
    with Image.open(path) as decoded:
        pixels = np.asarray(decoded.convert("RGB"))
    assert actual["brightness"] == pytest.approx(float(pixels.mean()))
    assert actual["contrast"] == pytest.approx(float(pixels.std()))
    assert actual["dominant_colors"]
    assert thumbnail is not None
    with Image.open(thumbnail) as decoded_thumbnail:
        decoded_thumbnail.load()
        assert decoded_thumbnail.format == "JPEG"
        assert decoded_thumbnail.mode == "RGB"
        assert decoded_thumbnail.size == (32, 24)
    assert path.read_bytes() == original


def test_truncated_jpeg_refuses_validation_without_rewriting_input(
    tmp_path: Path,
) -> None:
    path = tmp_path / "truncated.jpg"
    Image.new("RGB", (32, 24), "red").save(path, format="JPEG")
    truncated = path.read_bytes()[:40]
    path.write_bytes(truncated)

    with pytest.raises((OSError, ValueError)):
        ImageDownloader._validate_image(path)

    assert path.read_bytes() == truncated
