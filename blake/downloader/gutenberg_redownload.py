"""Re-download Project Gutenberg texts with a URL fallback chain.

Moved verbatim from ``scripts/redownload_texts.py`` (2026-09 scripts audit):
network download logic (Gutenberg ID list, URL fallback chain, validation
heuristic, corrupted-file removal) belongs in ``blake/downloader/``. The
output directory is injected by the caller.
"""
import os
import requests
import time

# Gutenberg IDs to (re)download
GUTENBERG_IDS = [
    "1934", "21487", "30526", "34596", "35995",
    "37407", "45315", "52300", "574", "60448",
    "64374", "67639"
]


def candidate_urls(work_id):
    """URL fallback chain for a Gutenberg ID, tried in order."""
    return [
        f"https://www.gutenberg.org/files/{work_id}/{work_id}-0.txt",
        f"https://www.gutenberg.org/cache/epub/{work_id}/pg{work_id}.txt",
        f"https://www.gutenberg.org/files/{work_id}/{work_id}.txt"
    ]


def download_text(work_id, output_dir):
    for url in candidate_urls(work_id):
        try:
            print(f"Trying {url}...")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Check if it looks like text
                content = response.text
                if "Project Gutenberg" in content[:1000] or len(content) > 100:
                    output_path = os.path.join(output_dir, f"{work_id}.txt")
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"Success: Saved {work_id}.txt ({len(content)} chars)")
                    return True
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        time.sleep(1)

    print(f"Failed to download text for {work_id}")
    return False


def redownload_texts(output_dir, ids=None):
    if ids is None:
        ids = GUTENBERG_IDS
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for work_id in ids:
        # Remove corrupted epub if exists
        epub_path = os.path.join(output_dir, f"{work_id}.epub")
        if os.path.exists(epub_path):
            os.remove(epub_path)
            print(f"Removed corrupted {epub_path}")

        download_text(work_id, output_dir)
