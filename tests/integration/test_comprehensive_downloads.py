#!/usr/bin/env python3
"""
Comprehensive Download Test

Tests the full download system to demonstrate downloading all available works
and formats from all sources.
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime
import json

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from blake.downloader.sources import ProjectGutenbergSource, BlakeArchiveSource, InternetArchiveSource
from blake.downloader.manager import DownloadManager
from blake.models import SourceType

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ComprehensiveDownloadTester:
    """Test comprehensive downloading from all sources."""
    
    def __init__(self, data_dir: str = "./comprehensive_test_data"):
        """Initialize the tester."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.results = {
            "start_time": datetime.now().isoformat(),
            "sources_tested": {},
            "total_works_found": 0,
            "total_works_downloaded": 0,
            "total_texts": 0,
            "total_images": 0,
            "total_bytes": 0,
            "works_by_source": {},
            "errors": []
        }
    
    async def test_all_sources(self):
        """Test downloading from all available sources."""
        print("🚀 Starting Comprehensive Download Test")
        print("=" * 60)
        
        # Test Project Gutenberg
        await self.test_project_gutenberg_comprehensive()
        
        # Test Blake Archive
        await self.test_blake_archive_comprehensive()
        
        # Test Internet Archive
        await self.test_internet_archive_comprehensive()
        
        # Test Download Manager
        await self.test_download_manager_comprehensive()
        
        # Analyze results
        await self.analyze_comprehensive_results()
        
        # Generate report
        await self.generate_comprehensive_report()
    
    async def test_project_gutenberg_comprehensive(self):
        """Test comprehensive Project Gutenberg downloading."""
        print("\n📚 Testing Project Gutenberg Comprehensive Download...")
        
        try:
            source = ProjectGutenbergSource(self.data_dir)
            
            # Get all works
            works = await source.get_work_list()
            print(f"  📖 Found {len(works)} Blake works in Project Gutenberg")
            
            # Download all works
            downloaded_works = []
            for i, work_info in enumerate(works):
                print(f"  📥 Downloading {i+1}/{len(works)}: {work_info['title'][:50]}...")
                try:
                    work = await source.download_work(work_info)
                    if work and work.text_content:
                        downloaded_works.append(work)
                        print(f"    ✅ Success: {len(work.text_content)} characters")
                    else:
                        print(f"    ❌ Failed: No content")
                except Exception as e:
                    print(f"    ❌ Error: {e}")
                    self.results["errors"].append(f"PG {work_info['id']}: {e}")
            
            self.results["sources_tested"]["project_gutenberg"] = {
                "works_found": len(works),
                "works_downloaded": len(downloaded_works),
                "success_rate": len(downloaded_works) / len(works) * 100 if works else 0
            }
            
            self.results["total_works_found"] += len(works)
            self.results["total_works_downloaded"] += len(downloaded_works)
            self.results["works_by_source"]["project_gutenberg"] = downloaded_works
            
            print(f"  📊 Project Gutenberg Results: {len(downloaded_works)}/{len(works)} works downloaded")
            
        except Exception as e:
            print(f"  ❌ Project Gutenberg test failed: {e}")
            self.results["errors"].append(f"Project Gutenberg: {e}")
    
    async def test_blake_archive_comprehensive(self):
        """Test comprehensive Blake Archive downloading."""
        print("\n🏛️ Testing Blake Archive Comprehensive Download...")
        
        try:
            source = BlakeArchiveSource(self.data_dir)
            
            # Get all works
            works = await source.get_work_list()
            print(f"  📖 Found {len(works)} works in Blake Archive")
            
            if works:
                # Download all works
                downloaded_works = []
                for i, work_info in enumerate(works):
                    print(f"  📥 Downloading {i+1}/{len(works)}: {work_info['title'][:50]}...")
                    try:
                        work = await source.download_work(work_info)
                        if work and work.text_content:
                            downloaded_works.append(work)
                            print(f"    ✅ Success: {len(work.text_content)} characters")
                        else:
                            print(f"    ❌ Failed: No content")
                    except Exception as e:
                        print(f"    ❌ Error: {e}")
                        self.results["errors"].append(f"BA {work_info['id']}: {e}")
                
                self.results["sources_tested"]["blake_archive"] = {
                    "works_found": len(works),
                    "works_downloaded": len(downloaded_works),
                    "success_rate": len(downloaded_works) / len(works) * 100 if works else 0
                }
                
                self.results["total_works_found"] += len(works)
                self.results["total_works_downloaded"] += len(downloaded_works)
                self.results["works_by_source"]["blake_archive"] = downloaded_works
                
                print(f"  📊 Blake Archive Results: {len(downloaded_works)}/{len(works)} works downloaded")
            else:
                print("  ⚠️  No works found in Blake Archive")
                self.results["sources_tested"]["blake_archive"] = {
                    "works_found": 0,
                    "works_downloaded": 0,
                    "success_rate": 0
                }
                
        except Exception as e:
            print(f"  ❌ Blake Archive test failed: {e}")
            self.results["errors"].append(f"Blake Archive: {e}")
    
    async def test_internet_archive_comprehensive(self):
        """Test comprehensive Internet Archive downloading."""
        print("\n🌐 Testing Internet Archive Comprehensive Download...")
        
        try:
            source = InternetArchiveSource(self.data_dir)
            
            # Get all works
            works = await source.get_work_list()
            print(f"  📖 Found {len(works)} works in Internet Archive")
            
            if works:
                # Download all works
                downloaded_works = []
                for i, work_info in enumerate(works):
                    print(f"  📥 Downloading {i+1}/{len(works)}: {work_info['title'][:50]}...")
                    try:
                        work = await source.download_work(work_info)
                        if work and work.text_content:
                            downloaded_works.append(work)
                            print(f"    ✅ Success: {len(work.text_content)} characters")
                        else:
                            print(f"    ❌ Failed: No content")
                    except Exception as e:
                        print(f"    ❌ Error: {e}")
                        self.results["errors"].append(f"IA {work_info['id']}: {e}")
                
                self.results["sources_tested"]["internet_archive"] = {
                    "works_found": len(works),
                    "works_downloaded": len(downloaded_works),
                    "success_rate": len(downloaded_works) / len(works) * 100 if works else 0
                }
                
                self.results["total_works_found"] += len(works)
                self.results["total_works_downloaded"] += len(downloaded_works)
                self.results["works_by_source"]["internet_archive"] = downloaded_works
                
                print(f"  📊 Internet Archive Results: {len(downloaded_works)}/{len(works)} works downloaded")
            else:
                print("  ⚠️  No works found in Internet Archive")
                self.results["sources_tested"]["internet_archive"] = {
                    "works_found": 0,
                    "works_downloaded": 0,
                    "success_rate": 0
                }
                
        except Exception as e:
            print(f"  ❌ Internet Archive test failed: {e}")
            self.results["errors"].append(f"Internet Archive: {e}")
    
    async def test_download_manager_comprehensive(self):
        """Test comprehensive download manager."""
        print("\n⚙️ Testing Download Manager Comprehensive...")
        
        try:
            manager = DownloadManager(self.data_dir)
            
            # Run comprehensive download
            session_result = await manager.download_all_sources()
            
            print(f"  📊 Session: {session_result['session_id']}")
            print(f"  📚 Total works found: {session_result['total_works']}")
            print(f"  ✅ Successful downloads: {session_result['successful_works']}")
            print(f"  ❌ Failed downloads: {session_result['failed_works']}")
            
            # Analyze results by source
            for source_name, source_data in session_result['sources'].items():
                print(f"  📡 {source_name}: {source_data['works_downloaded']}/{source_data['works_found']} works")
            
            self.results["download_manager"] = session_result
            
        except Exception as e:
            print(f"  ❌ Download manager test failed: {e}")
            self.results["errors"].append(f"Download Manager: {e}")
    
    async def analyze_comprehensive_results(self):
        """Analyze comprehensive download results."""
        print("\n📊 Analyzing Comprehensive Results...")
        
        try:
            # Count text files
            texts_dir = self.data_dir / "texts"
            text_files = list(texts_dir.glob("*.txt")) if texts_dir.exists() else []
            
            total_text_size = 0
            for text_file in text_files:
                total_text_size += text_file.stat().st_size
            
            # Count image files
            images_dir = self.data_dir / "images"
            image_files = list(images_dir.glob("*")) if images_dir.exists() else []
            
            total_image_size = 0
            for image_file in image_files:
                total_image_size += image_file.stat().st_size
            
            self.results["total_texts"] = len(text_files)
            self.results["total_images"] = len(image_files)
            self.results["total_bytes"] = total_text_size + total_image_size
            
            print(f"  📄 Text files: {len(text_files)} ({total_text_size:,} bytes)")
            print(f"  🖼️  Image files: {len(image_files)} ({total_image_size:,} bytes)")
            print(f"  💾 Total data: {total_text_size + total_image_size:,} bytes")
            
            # Show sample works
            if self.results["works_by_source"].get("project_gutenberg"):
                print(f"\n  📖 Sample Project Gutenberg Works:")
                for work in self.results["works_by_source"]["project_gutenberg"][:3]:
                    print(f"    • {work.metadata.title} ({len(work.text_content)} chars)")
            
        except Exception as e:
            print(f"❌ Results analysis failed: {e}")
            self.results["errors"].append(f"Results analysis: {e}")
    
    async def generate_comprehensive_report(self):
        """Generate comprehensive test report."""
        print("\n📄 Generating Comprehensive Report...")
        
        self.results["end_time"] = datetime.now().isoformat()
        self.results["total_time"] = (
            datetime.fromisoformat(self.results["end_time"]) - 
            datetime.fromisoformat(self.results["start_time"])
        ).total_seconds()
        
        # Save detailed report
        report_path = self.data_dir / "comprehensive_download_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Print summary
        print("\n" + "=" * 60)
        print("🎉 COMPREHENSIVE DOWNLOAD TEST COMPLETED!")
        print("=" * 60)
        print(f"⏱️  Total time: {self.results['total_time']:.1f} seconds")
        print(f"📊 FINAL RESULTS:")
        print(f"  📚 Total works found: {self.results['total_works_found']}")
        print(f"  ✅ Total works downloaded: {self.results['total_works_downloaded']}")
        print(f"  📄 Text files: {self.results['total_texts']}")
        print(f"  🖼️  Image files: {self.results['total_images']}")
        print(f"  💾 Total bytes: {self.results['total_bytes']:,}")
        
        print(f"\n📡 SOURCE BREAKDOWN:")
        for source_name, source_data in self.results["sources_tested"].items():
            print(f"  • {source_name}: {source_data['works_downloaded']}/{source_data['works_found']} ({source_data['success_rate']:.1f}%)")
        
        if self.results["errors"]:
            print(f"\n❌ ERRORS ({len(self.results['errors'])}):")
            for error in self.results["errors"][:5]:
                print(f"  • {error}")
            if len(self.results["errors"]) > 5:
                print(f"  ... and {len(self.results['errors']) - 5} more errors")
        
        print(f"\n📁 Data directory: {self.data_dir}")
        print(f"📄 Detailed report: {report_path}")
        
        return self.results


async def main():
    """Main test function."""
    tester = ComprehensiveDownloadTester()
    
    try:
        await tester.test_all_sources()
        
        print(f"\n🎉 COMPREHENSIVE DOWNLOAD TEST COMPLETED!")
        print(f"📊 Final Results: {tester.results['total_texts']} texts, {tester.results['total_images']} images, {tester.results['total_bytes']:,} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)