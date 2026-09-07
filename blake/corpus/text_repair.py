"""Repair text files that are actually EPUBs (zip archives) mislabeled as .txt.

Moved verbatim from ``scripts/fix_text_files.py`` (2026-09 scripts audit):
EPUB detection and HTML→text extraction are business logic and belong in
``blake/corpus/``. The texts directory is injected by the caller.
"""
import os
import shutil
import zipfile
from bs4 import BeautifulSoup
import warnings

# Suppress BS4 warnings
warnings.filterwarnings("ignore", category=UserWarning, module='bs4')


def extract_text_from_epub(epub_path):
    """Extracts text from an EPUB file (zip archive)."""
    text_content = []
    try:
        with zipfile.ZipFile(epub_path, 'r') as epub:
            for item in epub.infolist():
                if item.filename.endswith('.xhtml') or item.filename.endswith('.html'):
                    try:
                        content = epub.read(item.filename).decode('utf-8')
                        soup = BeautifulSoup(content, 'html.parser')
                        # Extract text, separate by newlines
                        text = soup.get_text(separator='\n')
                        text_content.append(text)
                    except Exception as e:
                        print(f"  Warning: Could not read {item.filename}: {e}")
    except zipfile.BadZipFile:
        print(f"  Error: {epub_path} is not a valid zip file.")
        return None

    return "\n".join(text_content)


def fix_text_files(texts_dir):
    """Iterates through text files and fixes those that are actually EPUBs."""
    print(f"Scanning {texts_dir} for mislabeled EPUBs...")

    if not os.path.exists(texts_dir):
        print(f"Directory {texts_dir} not found.")
        return 0

    files_fixed = 0

    for filename in os.listdir(texts_dir):
        if not filename.endswith(".txt"):
            continue

        file_path = os.path.join(texts_dir, filename)

        # Check header
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
        except Exception as e:
            print(f"Could not read {filename}: {e}")
            continue

        # PK header for Zip/EPUB
        if header.startswith(b'PK'):
            print(f"Found EPUB disguised as TXT: {filename}")

            epub_filename = filename.replace(".txt", ".epub")
            epub_path = os.path.join(texts_dir, epub_filename)

            # Rename to .epub
            print(f"  Renaming to {epub_filename}")
            shutil.move(file_path, epub_path)

            # Extract text
            print(f"  Extracting text from {epub_filename}...")
            text = extract_text_from_epub(epub_path)

            if text:
                # Write back to .txt
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                print(f"  Restored real text to {filename} (Size: {len(text)} chars)")
                files_fixed += 1
            else:
                print(f"  Failed to extract text from {epub_filename}")
                # Restore original file if extraction failed?
                # No, keep it as epub, user can inspect.

    print(f"\nFixed {files_fixed} files.")
    return files_fixed
