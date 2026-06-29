import json
import csv
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys
import os

# Add parent directory to path to import blake modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from blake.metadata.manager import MetadataManager
from blake.models import BlakeWork

logger = logging.getLogger(__name__)

class AvailabilityChecker:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.metadata_manager = MetadataManager(data_dir)
        self.master_list_path = data_dir / "master_works_list.json"
        
    async def generate_report(self, output_path: Path):
        """Generate availability report."""
        # Load master list
        if not self.master_list_path.exists():
            logger.error(f"Master list not found at {self.master_list_path}")
            return
            
        with open(self.master_list_path, 'r', encoding='utf-8') as f:
            master_data = json.load(f)
            master_works = master_data.get('works', [])
            
        # Load local works
        local_works = await self.metadata_manager.load_all_works()
        logger.info(f"Loaded {len(local_works)} local works")
        
        # Build availability table
        report_data = []
        
        # Map standardized titles for fuzzy matching
        local_map = {}
        for work in local_works:
            normalized_title = self._normalize(work.metadata.title)
            local_map[normalized_title] = work
            # store explicit ID too
            local_map[str(work.id)] = work
            
        # Statistics
        found_count = 0
        total_count = len(master_works)
        
        for title in master_works:
            status = "No Text"
            work_id = ""
            details = ""
            
            # Match logic
            match = self._find_match(title, local_map)
            
            if match:
                status = "Full Text" if match.text_content else "No Text (Metadata Only)"
                work_id = match.id
                details = f"Matched: {match.metadata.title}"
                if status.startswith("Full Text"):
                    found_count += 1
            
            report_data.append({
                "Title": title,
                "Status": status,
                "Work ID": work_id,
                "Details": details
            })
            
        # Check for works in local DB but not in Master List (Bonus)
        # (Optional, skipping to keep report focused on Master List gaps as requested)
            
        # Write CSV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ["Title", "Status", "Work ID", "Details"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(report_data)
            
        logger.info(f"Report generated at {output_path}")
        logger.info(f"Coverage: {found_count}/{total_count} ({found_count/total_count*100:.1f}%)")
        
    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        import re
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        return text.strip()
        
    def _find_match(self, title: str, local_map: Dict[str, BlakeWork]) -> Optional[BlakeWork]:
        """Find best match for title."""
        norm_title = self._normalize(title)
        
        # Exact match
        if norm_title in local_map:
            return local_map[norm_title]
            
        # Substring match (e.g. 'The Tyger' in 'The Tyger (1794)')
        for key, work in local_map.items():
            if norm_title in key or key in norm_title:
                # Basic check to avoid false positives with short words, but titles are usually distinct
                if len(norm_title) > 4 and len(key) > 4: 
                     return work
                     
        return None

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        checker = AvailabilityChecker(Path("data/blake"))
        await checker.generate_report(Path("output/reports/blake_text_availability.csv"))
        
    asyncio.run(main())
