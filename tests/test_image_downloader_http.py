"""Image transfer validation and processing on real PNG bytes."""

from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from blake.downloader.scraper import ImageDownloader
from tests import http_fixtures

local_responses = http_fixtures.local_responses


@pytest.mark.asyncio
async def test_image_download_metadata_thumbnail_and_cache(
    tmp_path: Path, local_responses
) -> None:
    downloader = ImageDownloader(tmp_path)
    url = local_responses.base + "/image.png"
    image = await downloader.download_image(url, "test.png")
    assert image is not None
    assert (image.width, image.height, image.format) == (16, 12, "PNG")
    assert image.original_url == url
    assert image.file_path.read_bytes() == local_responses.png
    with Image.open(image.file_path) as source:
        values = np.asarray(source)
    assert image.brightness == pytest.approx(float(values.mean()))
    assert image.contrast == pytest.approx(float(values.std()))
    assert len(image.dominant_colors) == 5
    assert image.thumbnail_path.is_file()
    with Image.open(image.thumbnail_path) as thumbnail:
        assert thumbnail.format == "JPEG"
        assert thumbnail.size == (16, 12)
    assert await downloader.download_image(url, "test.png") is not None
    assert local_responses.calls["/image.png"] == 1


@pytest.mark.asyncio
async def test_conversion_and_analysis_resize_keep_original_specs(
    tmp_path: Path, local_responses
) -> None:
    downloader = ImageDownloader(tmp_path, max_size=(8, 8))
    image = await downloader.download_image(
        local_responses.base + "/rgba.png", "rgba.png", create_thumbnail=False
    )
    assert image is not None
    assert (image.width, image.height, image.format) == (16, 12, "PNG")
    assert image.thumbnail_path is None
    with Image.open(image.file_path) as source:
        assert source.mode == "RGBA" and source.size == (16, 12)


@pytest.mark.asyncio
async def test_invalid_image_transfer_preserves_preexisting_image(
    tmp_path: Path, local_responses
) -> None:
    downloader = ImageDownloader(tmp_path)
    target = downloader.images_dir / "prior.png"
    target.write_bytes(local_responses.png)
    image = await downloader.download_image(
        local_responses.base + "/binary", "prior.png", force=True
    )
    assert image is None
    assert target.read_bytes() == local_responses.png


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["parent", "absolute", "extension"])
async def test_invalid_names_do_not_request_or_write(
    tmp_path: Path, local_responses, case: str
) -> None:
    filename = {
        "parent": "../outside.png",
        "absolute": str(tmp_path / "outside.png"),
        "extension": "bad.exe",
    }[case]
    downloader = ImageDownloader(tmp_path)
    assert (
        await downloader.download_image(local_responses.base + "/image.png", filename)
        is None
    )
    assert local_responses.calls["/image.png"] == 0
    assert not list(downloader.images_dir.rglob("*.png"))


@pytest.mark.asyncio
async def test_bad_image_processing_and_thumbnail_are_explicit(
    tmp_path: Path, caplog
) -> None:
    downloader = ImageDownloader(tmp_path)
    corrupt = tmp_path / "bad.png"
    corrupt.write_bytes(b"not an image")
    result = await downloader._process_image(corrupt)
    assert result["width"] is None and result["dominant_colors"] == []
    assert await downloader._create_thumbnail(corrupt, "bad.png") is None
    assert "Error processing image" in caplog.text
    assert "Error creating thumbnail" in caplog.text


def test_simple_color_groups_are_quantized_and_frequency_ordered(
    tmp_path: Path,
) -> None:
    downloader = ImageDownloader(tmp_path)
    pixels = np.array(
        [[[255, 0, 0], [255, 0, 0], [0, 255, 0], [0, 0, 255]]], dtype=np.uint8
    )
    assert downloader._extract_colors_simple(pixels, 2) == ["#e00000", "#00e000"]
    assert downloader._extract_colors_simple(np.array(1)) == []
    assert downloader._extract_dominant_colors(np.array(1)) == []
