
import sys
import os
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from blake.utils.file_utils import sanitize_filename
from blake.metadata.manager import MetadataManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_filenames():
    data_dir = project_root / "data" / "blake"
    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        return

    metadata_manager = MetadataManager(data_dir)
    
    # Load all works
    works = await metadata_manager.load_all_works()
    logger.info(f"Loaded {len(works)} works")
    
    text_dir = data_dir / "texts"
    migrated_count = 0
    
    for work in works:
        if not work.metadata.title:
            continue
            
        safe_title = sanitize_filename(work.metadata.title)
        if not safe_title:
            continue
            
        old_filename = f"{work.id}.txt"
        new_filename = f"{work.id}_{safe_title}.txt"
        
        old_path = text_dir / old_filename
        new_path = text_dir / new_filename
        
        if old_path.exists() and not new_path.exists():
            logger.info(f"Renaming {old_filename} -> {new_filename}")
            old_path.rename(new_path)
            
            # Update metadata if needed (though file_path relies on finding it?)
            # The Metadata object has a file_path field. We should update it.
            if work.metadata.file_path and str(work.metadata.file_path).endswith(old_filename):
                work.metadata.file_path = new_path
                await metadata_manager.save_work(work)
                
            migrated_count += 1
        elif new_path.exists() and old_path.exists():
            logger.info(f"Target {new_filename} exists. Removing old {old_filename}")
            old_path.unlink()
            migrated_count += 1
            
    logger.info(f"Migration complete. Renamed {migrated_count} files.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(migrate_filenames())
