"""Source parsing contracts on explicit synthetic documents."""

from pathlib import Path

from bs4 import BeautifulSoup
import pytest

from blake.downloader.sources import (
    BaseSource,
    BlakeArchiveSource,
    InternetArchiveSource,
    ProjectGutenbergSource,
)
from blake.models import LicenseType, WorkType


@pytest.mark.parametrize("cls", [BlakeArchiveSource, InternetArchiveSource])
@pytest.mark.asyncio
async def test_provider_metadata_does_not_grant_unreviewed_edition_rights(
    tmp_path: Path, cls
) -> None:
    source = cls(tmp_path)
    soup = BeautifulSoup(
        '<h1>Test poem</h1><div class="description item-description">Description</div><span class="date">1794</span><span class="medium">ink</span><span class="dimensions">4 x 4</span><span class="location">Test</span>',
        "html.parser",
    )
    metadata = await source._extract_metadata(
        soup, {"id": "test", "title": "Fallback", "url": "https://example.test/work"}
    )
    assert metadata.id == "test" and metadata.title == "Test poem"
    assert metadata.creation_date.year == 1794
    assert metadata.description == "Description"
    assert metadata.license_type == LicenseType.UNKNOWN
    assert metadata.source_url == "https://example.test/work"
    if cls is BlakeArchiveSource:
        assert (metadata.medium, metadata.dimensions, metadata.location) == (
            "ink",
            "4 x 4",
            "Test",
        )


@pytest.mark.parametrize(
    "title,kind",
    [
        ("Song", WorkType.POEM),
        ("Letter", WorkType.LETTER),
        ("Manuscript", WorkType.MANUSCRIPT),
        ("Plate", WorkType.PLATE),
        ("Drawing", WorkType.DRAWING),
        ("Painting", WorkType.PAINTING),
        ("Untitled", WorkType.POEM),
    ],
)
def test_archive_work_type_uses_declared_title(
    tmp_path: Path, title: str, kind: WorkType
) -> None:
    assert (
        BlakeArchiveSource(tmp_path)._determine_work_type(
            BeautifulSoup("", "html.parser"), title
        )
        == kind
    )


@pytest.mark.parametrize(
    "title,body,kind",
    [
        ("Poems", "", WorkType.POEM),
        ("Marriage", "", WorkType.PROPHECY),
        ("Correspondence", "", WorkType.LETTER),
        ("Illustrations", "", WorkType.DRAWING),
        ("Manuscript", "", WorkType.MANUSCRIPT),
        ("Engravings", "", WorkType.PLATE),
        ("Untitled", "A vision", WorkType.PROPHECY),
        ("Untitled", "Poetry", WorkType.POEM),
        ("Untitled", "Painting", WorkType.DRAWING),
        ("Untitled", "", WorkType.POEM),
    ],
)
def test_gutenberg_type_uses_title_then_page_clues(
    tmp_path: Path, title: str, body: str, kind: WorkType
) -> None:
    assert (
        ProjectGutenbergSource(tmp_path)._determine_work_type_from_page(
            BeautifulSoup(body, "html.parser"), title
        )
        == kind
    )


@pytest.mark.parametrize("cls", [BlakeArchiveSource, InternetArchiveSource])
@pytest.mark.parametrize(
    "value,year", [("circa 1794", 1794), ("1804-1808", 1804), ("unknown", None)]
)
def test_source_dates_preserve_unknowns(tmp_path: Path, cls, value: str, year) -> None:
    date = cls(tmp_path)._parse_date(value)
    assert (date.year if date else None) == year


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "html",
    [
        "<div class='poem-text'><p>First</p><p>Second</p></div>",
        "<body><p>First</p><p>Second</p></body>",
    ],
)
async def test_archive_text_keeps_adjacent_words_separate(
    tmp_path: Path, html: str
) -> None:
    text = await BlakeArchiveSource(tmp_path)._extract_text_content(
        BeautifulSoup(html, "html.parser")
    )
    assert text.split() == ["First", "Second"]


@pytest.mark.asyncio
async def test_archive_text_without_content_is_absent(tmp_path: Path) -> None:
    assert (
        await BlakeArchiveSource(tmp_path)._extract_text_content(
            BeautifulSoup("<head></head>", "html.parser")
        )
        is None
    )


@pytest.mark.parametrize("header", ["*** START OF BOOK ***", "***START OF BOOK***"])
def test_gutenberg_wrapper_cleaning_keeps_only_body(
    tmp_path: Path, header: str
) -> None:
    source = ProjectGutenbergSource(tmp_path)
    assert (
        source._clean_gutenberg_text(
            "Header\n" + header + "\nFirst\nSecond\n*** END OF BOOK ***\nLicense"
        )
        == "First\nSecond"
    )
    assert source._clean_gutenberg_text("Unverified body without markers") == ""


def test_html_gutenberg_reader_retains_marker_line_boundaries(tmp_path: Path) -> None:
    source = ProjectGutenbergSource(tmp_path)
    text = source._extract_text_from_html(
        "<style>hidden</style><p>*** START OF BOOK ***</p><p>First</p><p>Second</p><p>*** END OF BOOK ***</p><script>hidden</script>"
    )
    assert source._clean_gutenberg_text(text) == "First\nSecond"
    assert "hidden" not in text


@pytest.mark.asyncio
async def test_base_source_refuses_without_creating_work_files(tmp_path: Path) -> None:
    source = BaseSource(tmp_path)
    with pytest.raises(NotImplementedError):
        await source.get_work_list()
    with pytest.raises(NotImplementedError):
        await source.download_work({})
    assert source._extract_work_id("https://example.test/works/id?query=1") == "id"
    assert list(source.scraper.texts_dir.iterdir()) == []
