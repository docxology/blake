#!/usr/bin/env python3
"""
Headless Download All Script

A thin orchestrator that downloads all available Blake works using the high-level BlakeWorks API.
"""

import asyncio
import sys
from pathlib import Path
import logging

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from blake import BlakeWorks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

async def main():
    """Main function."""
    try:
        logger.info("🚀 Initializing BlakeWorks...")
        
        # Initialize BlakeWorks with default settings
        # You can pass data_dir here if needed, e.g. BlakeWorks(data_dir=Path("./my_data"))
        blake = BlakeWorks()
        
        logger.info("📥 Starting global download...")
        works = await blake.download_all()
        
        if works:
            logger.info(f"✅ Download complete! {len(works)} works available.")
            sys.exit(0)
        else:
            logger.warning("⚠️ No works were downloaded or found.")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"❌ Error during download: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
