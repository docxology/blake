
import asyncio
import json
from pathlib import Path
from blake.metadata.manager import MetadataManager
from blake.models import BlakeWork, BlakeMetadata

async def main():
    data_dir = Path("./data/blake")
    metadata_dir = data_dir / "metadata"
    manager = MetadataManager(data_dir)
    
    print(f"Scanning {metadata_dir} for JSON files...")
    count = 0
    for json_file in metadata_dir.glob("*.json"):
        if json_file.name == "comprehensive_download_report_20260130_141609.json":
            continue
            
        try:
            print(f"Loading {json_file.name}...")
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if it's a BlakeWork export or just metadata
            if 'metadata' in data:
                work = BlakeWork(**data)
            else:
                # Treat as direct metadata
                try:
                    # Convert string dates if necessary, or let Pydantic handle it
                    metadata = BlakeMetadata(**data)
                    work = BlakeWork(id=metadata.id, metadata=metadata)
                except Exception as meta_err:
                    print(f"Skipping {json_file.name}: {meta_err}")
                    continue
                
            await manager.save_work(work)
            count += 1
            print(f"Saved {work.id} to database")
            
        except Exception as e:
            print(f"Error processing {json_file.name}: {e}")
            
    print(f"Repopulated {count} works into database.")

if __name__ == "__main__":
    asyncio.run(main())
