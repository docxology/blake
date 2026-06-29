
import os
import requests
import time

IDs = [
    "1934", "21487", "30526", "34596", "35995", 
    "37407", "45315", "52300", "574", "60448", 
    "64374", "67639"
]

OUTPUT_DIR = "data/blake/texts"

def download_text(work_id):
    urls = [
        f"https://www.gutenberg.org/files/{work_id}/{work_id}-0.txt",
        f"https://www.gutenberg.org/cache/epub/{work_id}/pg{work_id}.txt",
        f"https://www.gutenberg.org/files/{work_id}/{work_id}.txt"
    ]
    
    for url in urls:
        try:
            print(f"Trying {url}...")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Check if it looks like text
                content = response.text
                if "Project Gutenberg" in content[:1000] or len(content) > 100:
                    output_path = os.path.join(OUTPUT_DIR, f"{work_id}.txt")
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"Success: Saved {work_id}.txt ({len(content)} chars)")
                    return True
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        time.sleep(1)
    
    print(f"Failed to download text for {work_id}")
    return False

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    for work_id in IDs:
        # Remove corrupted epub if exists
        epub_path = os.path.join(OUTPUT_DIR, f"{work_id}.epub")
        if os.path.exists(epub_path):
            os.remove(epub_path)
            print(f"Removed corrupted {epub_path}")
            
        download_text(work_id)

if __name__ == "__main__":
    main()
