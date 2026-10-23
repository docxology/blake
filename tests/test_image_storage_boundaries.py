"""Symlink sentinels stay inside each test's synthetic temporary tree."""

from pathlib import Path

import pytest

from blake.downloader.scraper import ImageDownloader, WebScraper
from tests import http_fixtures

local_responses = http_fixtures.local_responses


@pytest.mark.parametrize("directory", ["images", "images/thumbnails"])
def test_constructor_refuses_symlinked_storage_before_creating_descendants(
    tmp_path: Path, directory: str
) -> None:
    data = tmp_path / "data"
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"preserve")
    link = data / directory
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="Symlink"):
        ImageDownloader(data)
    assert list(outside.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"preserve"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "boundary", ["cached-image", "cached-thumbnail", "replaced-images-directory"]
)
async def test_symlinked_image_paths_refuse_before_http_or_decode(
    tmp_path: Path, local_responses, boundary: str
) -> None:
    data = tmp_path / "data"
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.png"
    sentinel.write_bytes(local_responses.png)
    downloader = ImageDownloader(data)
    url = local_responses.base + "/image.png"
    if boundary == "cached-image":
        (downloader.images_dir / "test.png").symlink_to(sentinel)
        WebScraper(data)._record_download(url, downloader.images_dir / "test.png")
    elif boundary == "cached-thumbnail":
        original = downloader.images_dir / "test.png"
        original.write_bytes(local_responses.png)
        WebScraper(data)._record_download(url, original)
        (downloader.thumbnails_dir / "thumb_test.jpg").symlink_to(sentinel)
    else:
        downloader.images_dir.rename(data / "original-images")
        downloader.images_dir.symlink_to(outside, target_is_directory=True)
    result = await downloader.download_image(url, "test.png")
    assert result is None
    assert local_responses.calls["/image.png"] == 0
    assert sentinel.read_bytes() == local_responses.png
    assert list(outside.iterdir()) == [sentinel]
