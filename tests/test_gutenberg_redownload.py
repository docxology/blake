"""Tests for blake.downloader.gutenberg_redownload (moved from scripts/redownload_texts.py)."""

import blake.downloader.gutenberg_redownload as gr


def test_candidate_urls_orders_fallback_chain():
    assert gr.candidate_urls("1934") == [
        "https://www.gutenberg.org/files/1934/1934-0.txt",
        "https://www.gutenberg.org/cache/epub/1934/pg1934.txt",
        "https://www.gutenberg.org/files/1934/1934.txt",
    ]


def test_redownload_texts_removes_corrupted_epub_and_downloads(tmp_path, monkeypatch):
    out = tmp_path / "texts"
    out.mkdir()
    stale = out / "1934.epub"
    stale.write_bytes(b"PK\x03\x04")

    called = []
    monkeypatch.setattr(
        gr, "download_text", lambda work_id, directory: called.append((work_id, directory)) or True
    )

    gr.redownload_texts(out, ids=["1934"])

    assert not stale.exists()
    assert called == [("1934", out)]
