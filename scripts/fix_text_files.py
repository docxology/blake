
import os
import shutil
import zipfile
import re
from bs4 import BeautifulSoup
import warnings

# Suppress BS4 warnings
warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

TEXTS_DIR = "data/blake/texts"

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

def fix_text_files():
    """Iterates through text files and fixes those that are actually EPUBs."""
    print(f"Scanning {TEXTS_DIR} for mislabeled EPUBs...")
    
    if not os.path.exists(TEXTS_DIR):
        print(f"Directory {TEXTS_DIR} not found.")
        return

    files_fixed = 0
    
    for filename in os.listdir(TEXTS_DIR):
        if not filename.endswith(".txt"):
            continue
            
        file_path = os.path.join(TEXTS_DIR, filename)
        
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
            epub_path = os.path.join(TEXTS_DIR, epub_filename)
            
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

if __name__ == "__main__":
    fix_text_files()
