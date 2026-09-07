"""Tests for blake.corpus.text_repair (moved from scripts/fix_text_files.py)."""

import zipfile

from blake.corpus.text_repair import extract_text_from_epub, fix_text_files


def _make_disguised_epub(path, body_text):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "chapter.xhtml",
            f"<html><body><p>{body_text}</p></body></html>",
        )


def test_extract_text_from_epub_strips_markup(tmp_path):
    epub = tmp_path / "book.epub"
    _make_disguised_epub(epub, "Fear symmetries")

    text = extract_text_from_epub(epub)

    assert "Fear symmetries" in text


def test_fix_text_files_repairs_disguised_epub(tmp_path):
    texts = tmp_path / "texts"
    texts.mkdir()
    _make_disguised_epub(texts / "1934.txt", "Songs of Innocence")
    plain = texts / "plain.txt"
    plain.write_text("plain text", encoding="utf-8")

    fixed = fix_text_files(texts)

    assert fixed == 1
    assert (texts / "1934.epub").is_file()  # renamed original
    assert "Songs of Innocence" in (texts / "1934.txt").read_text(encoding="utf-8")
    assert (texts / "plain.txt").read_text(encoding="utf-8") == "plain text"


def test_fix_text_files_missing_dir_is_noop(tmp_path):
    assert fix_text_files(tmp_path / "absent") == 0
