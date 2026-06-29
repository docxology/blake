#!/usr/bin/env python3
"""
Script to download the complete Blake Archive catalog.
Uses the fixed BlakeArchiveScraper to fetch TEI content and metadata.
Skips already downloaded works to allow resuming.
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
import json

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Import directly from submodule to avoid loading GUI
from blake.downloader.blake_archive_scraper import BlakeArchiveScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("blake_download.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("blake_download")

async def main():
    print("🚀 Starting Complete Blake Archive Download")
    print("==========================================")
    
    data_dir = project_root / "data" / "blake"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    start_time = datetime.now()
    
    async with BlakeArchiveScraper(data_dir, rate_limit=0.5) as scraper:
        # 1. Fetch Catalog
        print("\n📚 Fetching works catalog...")
        catalog = await scraper.fetch_works_catalog()
        print(f"✅ Found {len(catalog)} works in catalog")
        
        # 2. Check existing
        existing_texts = list((data_dir / "texts" / "blake_archive").glob("*.txt"))
        print(f"📂 Found {len(existing_texts)} existing downloaded works")
        
        # 3. Download All (force=False will skip existing)
        print("\n⬇️  Starting download process...")
        print("   (This may take a while for 150+ works)")
        
        works = await scraper.download_all_works(
            include_images=False,  # Skip images for speed/storage
            image_dpi=100,
            force=False  # CRITICAL: Skip existing
        )
        
        # 4. Analysis
        downloaded_count = len(works)
        text_count = len([w for w in works if w.text_content])
        new_downloads = downloaded_count - len(existing_texts)
        
        duration = datetime.now() - start_time
        
        print("\n🎉 Download Complete!")
        print("======================")
        print(f"⏱️  Duration: {duration}")
        print(f"📚 Total Works Processed: {downloaded_count}")
        print(f"📄 Works with Text: {text_count}")
        print(f"🆕 New Downloads: {new_downloads}")
        
        # Save summary
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_works": downloaded_count,
            "works_with_text": text_count,
            "duration_seconds": duration.total_seconds(),
            "data_dir": str(data_dir)
        }
        
        with open(data_dir / "download_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Download interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
