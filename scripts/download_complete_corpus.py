#!/usr/bin/env python3
"""
Target-Aware Blake Corpus Downloader

Downloads target-ledger Blake corpus candidates from multiple sources:
1. Project Gutenberg (clean poem texts)
2. Blake Archive (TEI transcriptions)
3. Wikisource (additional texts)

Outputs unified, descriptively named files.
"""

import asyncio
import aiohttp
import aiofiles
import logging
import sys
from pathlib import Path
from datetime import datetime
import json
import re

# Setup
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("blake_corpus")

DATA_DIR = project_root / "data" / "blake" / "texts"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# GUTENBERG SOURCES (Clean poem texts)
# ============================================================================
GUTENBERG_WORKS = {
    # ID: (filename, title, description)
    "574": ("poems_collected.txt", "Poems of William Blake", "Anthology of poems"),
    "1934": ("songs_innocence_experience.txt", "Songs of Innocence and of Experience", "Complete collection 1789-1794"),
    "45315": ("marriage_heaven_hell.txt", "The Marriage of Heaven and Hell", "Illuminated book c.1790"),
    "52300": ("illustrations_job.txt", "Illustrations of the Book of Job", "Engravings with inscriptions 1825"),
}

# ============================================================================
# BLAKE ARCHIVE TEI WORKS (Illuminated books with transcriptions)
# ============================================================================
BLAKE_ARCHIVE_WORKS = {
    # work_id: (filename, title, date, copies_to_try)
    "america": ("america_prophecy.txt", "America a Prophecy", "1793", ["a", "b", "e", "f"]),
    "europe": ("europe_prophecy.txt", "Europe a Prophecy", "1794", ["a", "b", "e", "g"]),
    "urizen": ("book_of_urizen.txt", "The Book of Urizen", "1794", ["a", "b", "c", "g"]),
    "thel": ("book_of_thel.txt", "The Book of Thel", "1789", ["a", "f", "h", "j"]),
    "vda": ("visions_daughters_albion.txt", "Visions of the Daughters of Albion", "1793", ["a", "c", "e", "g"]),
    "mhh": ("marriage_heaven_hell_archive.txt", "The Marriage of Heaven and Hell", "1790", ["a", "b", "c", "d"]),
    "songsie": ("songs_innocence_experience_archive.txt", "Songs of Innocence and of Experience", "1794", ["a", "b", "c", "l"]),
    "s-inn": ("songs_innocence.txt", "Songs of Innocence", "1789", ["a", "b", "u"]),
    "milton": ("milton.txt", "Milton a Poem", "1804-1811", ["a", "b", "c", "d"]),
    "jerusalem": ("jerusalem.txt", "Jerusalem The Emanation of The Giant Albion", "1804-1820", ["a", "c", "e"]),
    "ahania": ("book_of_ahania.txt", "The Book of Ahania", "1795", ["a"]),
    "b-los": ("book_of_los.txt", "The Book of Los", "1795", ["a"]),
    "s-los": ("song_of_los.txt", "The Song of Los", "1795", ["a", "b"]),
    "aro": ("all_religions_one.txt", "All Religions are One", "1788", ["a"]),
    "nnr": ("no_natural_religion.txt", "There is No Natural Religion", "1788", ["a", "b", "l"]),
    "gates-child": ("gates_paradise_children.txt", "For Children: The Gates of Paradise", "1793", ["a", "d"]),
    "gates-sexes": ("gates_paradise_sexes.txt", "For the Sexes: The Gates of Paradise", "1818", ["d", "f"]),
    "abel": ("ghost_of_abel.txt", "The Ghost of Abel", "1822", ["a"]),
    "laocoon": ("laocoon.txt", "Laocoön", "1826", ["a"]),
    "homer": ("on_homers_poetry.txt", "On Homer's Poetry [and] On Virgil", "1822", ["a"]),
}

async def download_gutenberg(session: aiohttp.ClientSession) -> dict:
    """Download from Project Gutenberg."""
    results = {}
    
    for guten_id, (filename, title, desc) in GUTENBERG_WORKS.items():
        url = f"https://www.gutenberg.org/cache/epub/{guten_id}/pg{guten_id}.txt"
        logger.info(f"Downloading Gutenberg #{guten_id}: {title}")
        
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    
                    # Save
                    filepath = DATA_DIR / filename
                    async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                        await f.write(content)
                    
                    results[filename] = {
                        "title": title,
                        "source": "gutenberg",
                        "chars": len(content),
                        "status": "complete"
                    }
                    logger.info(f"  ✅ {len(content):,} chars")
                else:
                    results[filename] = {"title": title, "status": "failed", "error": f"HTTP {resp.status}"}
                    logger.warning(f"  ❌ HTTP {resp.status}")
        except Exception as e:
            results[filename] = {"title": title, "status": "failed", "error": str(e)}
            logger.error(f"  ❌ {e}")
    
    return results

async def download_blake_archive(session: aiohttp.ClientSession) -> dict:
    """Download from Blake Archive GitHub."""
    results = {}
    base_url = "https://raw.githubusercontent.com/blakearchive/data/master/works"
    
    for work_id, (filename, title, date, copies) in BLAKE_ARCHIVE_WORKS.items():
        logger.info(f"Downloading Blake Archive: {title} ({date})")
        
        content = None
        for copy in copies:
            url = f"{base_url}/{work_id}.{copy}.xml"
            try:
                await asyncio.sleep(0.3)  # Rate limit
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        xml_content = await resp.text()
                        if '<?xml' in xml_content[:100] or '<bad' in xml_content[:100]:
                            # Extract text from XML
                            text = extract_text_from_tei(xml_content, title, date)
                            if text and len(text) > 100:
                                content = text
                                break
            except Exception as e:
                continue
        
        if content:
            filepath = DATA_DIR / filename
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            results[filename] = {
                "title": title,
                "date": date,
                "source": "blake_archive",
                "chars": len(content),
                "status": "complete"
            }
            logger.info(f"  ✅ {len(content):,} chars")
        else:
            results[filename] = {
                "title": title,
                "date": date,
                "source": "blake_archive",
                "status": "partial",
                "note": "TEI notes only, no full poem text"
            }
            logger.warning(f"  ⚠️ Partial (TEI notes only)")
    
    return results

def extract_text_from_tei(xml_content: str, title: str, date: str) -> str:
    """Extract readable text from Blake Archive TEI XML."""
    import xml.etree.ElementTree as ET
    
    try:
        # Remove namespaces
        xml_content = re.sub(r'\sxmlns[^"]*"[^"]*"', '', xml_content)
        root = ET.fromstring(xml_content)
        
        text_parts = []
        
        # Add header
        text_parts.append(f"{title.upper()}")
        text_parts.append(f"({date})")
        text_parts.append("=" * 50)
        text_parts.append("")
        
        # Extract text from various elements
        for tag in ['l', 'p', 'ab', 'head']:
            for elem in root.iter(tag):
                text = ''.join(elem.itertext()).strip()
                if text and len(text) > 3:
                    # Clean up
                    text = re.sub(r'\s+', ' ', text)
                    text_parts.append(text)
        
        return '\n'.join(text_parts)
    
    except Exception as e:
        return ""

async def main():
    print("Blake Target Corpus Download")
    print("=" * 50)
    print(f"Output: {DATA_DIR}")
    print()
    
    start = datetime.now()
    all_results = {}
    
    async with aiohttp.ClientSession() as session:
        # Download from Gutenberg
        print("\n📚 Phase 1: Project Gutenberg (Clean texts)")
        gutenberg_results = await download_gutenberg(session)
        all_results.update(gutenberg_results)
        
        # Download from Blake Archive
        print("\n📜 Phase 2: Blake Archive (TEI Transcriptions)")
        archive_results = await download_blake_archive(session)
        all_results.update(archive_results)
    
    # Summary
    duration = datetime.now() - start
    complete = [k for k, v in all_results.items() if v.get("status") == "complete"]
    partial = [k for k, v in all_results.items() if v.get("status") == "partial"]
    failed = [k for k, v in all_results.items() if v.get("status") == "failed"]
    
    print("\n" + "=" * 50)
    print("🎉 DOWNLOAD COMPLETE")
    print("=" * 50)
    print(f"⏱️  Duration: {duration}")
    print(f"✅ Complete: {len(complete)} works")
    print(f"⚠️  Partial: {len(partial)} works")
    print(f"❌ Failed: {len(failed)} works")
    
    # Save manifest
    manifest = {
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": duration.total_seconds(),
        "works": all_results
    }
    
    manifest_path = DATA_DIR / "MANIFEST.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    # Print file listing
    print("\n📁 Downloaded Files:")
    for f in sorted(DATA_DIR.glob("*.txt")):
        size = f.stat().st_size
        print(f"   {f.name}: {size:,} bytes")
    
    print(f"\n📋 Manifest saved to: {manifest_path}")

if __name__ == "__main__":
    asyncio.run(main())
