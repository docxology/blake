#!/usr/bin/env python3
"""
Test Improved Download Methods

Tests the improved underlying web methods to verify they can
download all available works and formats.
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


class ImprovedDownloadTester:
    """Test the improved download methods."""
    
    def __init__(self, data_dir: str = "./improved_test_data"):
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
            "errors": []
        }
    
    async def test_project_gutenberg_improved(self):
        """Test the improved Project Gutenberg downloader."""
        print("🔍 Testing Improved Project Gutenberg Downloader...")
        
        try:
            source = ProjectGutenbergSource(self.data_dir)
            
            # Get work list
            works = await source.get_work_list()
            print(f"  📚 Found {len(works)} works")
            
            # Test downloading first 5 works
            downloaded_works = []
            for i, work_info in enumerate(works[:5]):
                print(f"  📥 Downloading {i+1}/5: {work_info['title']}")
                try:
                    work = await source.download_work(work_info)
                    if work and work.text_content:
                        downloaded_works.append(work)
                        print(f"    ✅ Success: {len(work.text_content)} bytes")
                    else:
                        print(f"    ❌ Failed: No content")
                except Exception as e:
                    print(f"    ❌ Error: {e}")
                    self.results["errors"].append(f"PG {work_info['id']}: {e}")
            
            self.results["sources_tested"]["project_gutenberg"] = {
                "works_found": len(works),
                "works_downloaded": len(downloaded_works),
                "success_rate": len(downloaded_works) / len(works[:5]) * 100 if works else 0
            }
            
            self.results["total_works_found"] += len(works)
            self.results["total_works_downloaded"] += len(downloaded_works)
            
            # Count downloaded files
            texts_dir = self.data_dir / "texts"
            if texts_dir.exists():
                text_files = list(texts_dir.glob("*.txt"))
                total_size = sum(f.stat().st_size for f in text_files)
                self.results["total_texts"] += len(text_files)
                self.results["total_bytes"] += total_size
                print(f"  📄 Downloaded {len(text_files)} text files ({total_size:,} bytes)")
            
            return downloaded_works
            
        except Exception as e:
            print(f"  ❌ Project Gutenberg test failed: {e}")
            self.results["errors"].append(f"Project Gutenberg: {e}")
            return []
    
    async def test_blake_archive_improved(self):
        """Test the improved Blake Archive downloader."""
        print("\n🔍 Testing Improved Blake Archive Downloader...")
        
        try:
            source = BlakeArchiveSource(self.data_dir)
            
            # Get work list
            works = await source.get_work_list()
            print(f"  📚 Found {len(works)} works")
            
            if works:
                # Test downloading first 3 works
                downloaded_works = []
                for i, work_info in enumerate(works[:3]):
                    print(f"  📥 Downloading {i+1}/3: {work_info['title']}")
                    try:
                        work = await source.download_work(work_info)
                        if work and work.text_content:
                            downloaded_works.append(work)
                            print(f"    ✅ Success: {len(work.text_content)} bytes")
                        else:
                            print(f"    ❌ Failed: No content")
                    except Exception as e:
                        print(f"    ❌ Error: {e}")
                        self.results["errors"].append(f"BA {work_info['id']}: {e}")
                
                self.results["sources_tested"]["blake_archive"] = {
                    "works_found": len(works),
                    "works_downloaded": len(downloaded_works),
                    "success_rate": len(downloaded_works) / len(works[:3]) * 100 if works else 0
                }
                
                self.results["total_works_found"] += len(works)
                self.results["total_works_downloaded"] += len(downloaded_works)
                
                return downloaded_works
            else:
                print("  ⚠️  No works found in Blake Archive")
                self.results["sources_tested"]["blake_archive"] = {
                    "works_found": 0,
                    "works_downloaded": 0,
                    "success_rate": 0
                }
                return []
                
        except Exception as e:
            print(f"  ❌ Blake Archive test failed: {e}")
            self.results["errors"].append(f"Blake Archive: {e}")
            return []
    
    async def test_internet_archive_improved(self):
        """Test the improved Internet Archive downloader."""
        print("\n🔍 Testing Improved Internet Archive Downloader...")
        
        try:
            source = InternetArchiveSource(self.data_dir)
            
            # Get work list
            works = await source.get_work_list()
            print(f"  📚 Found {len(works)} works")
            
            if works:
                # Test downloading first 3 works
                downloaded_works = []
                for i, work_info in enumerate(works[:3]):
                    print(f"  📥 Downloading {i+1}/3: {work_info['title']}")
                    try:
                        work = await source.download_work(work_info)
                        if work and work.text_content:
                            downloaded_works.append(work)
                            print(f"    ✅ Success: {len(work.text_content)} bytes")
                        else:
                            print(f"    ❌ Failed: No content")
                    except Exception as e:
                        print(f"    ❌ Error: {e}")
                        self.results["errors"].append(f"IA {work_info['id']}: {e}")
                
                self.results["sources_tested"]["internet_archive"] = {
                    "works_found": len(works),
                    "works_downloaded": len(downloaded_works),
                    "success_rate": len(downloaded_works) / len(works[:3]) * 100 if works else 0
                }
                
                self.results["total_works_found"] += len(works)
                self.results["total_works_downloaded"] += len(downloaded_works)
                
                return downloaded_works
            else:
                print("  ⚠️  No works found in Internet Archive")
                self.results["sources_tested"]["internet_archive"] = {
                    "works_found": 0,
                    "works_downloaded": 0,
                    "success_rate": 0
                }
                return []
                
        except Exception as e:
            print(f"  ❌ Internet Archive test failed: {e}")
            self.results["errors"].append(f"Internet Archive: {e}")
            return []
    
    async def test_download_manager_comprehensive(self):
        """Test the download manager with all sources."""
        print("\n🔍 Testing Comprehensive Download Manager...")
        
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
            
            return session_result
            
        except Exception as e:
            print(f"  ❌ Download manager test failed: {e}")
            self.results["errors"].append(f"Download Manager: {e}")
            return None
    
    async def analyze_downloaded_content(self):
        """Analyze all downloaded content."""
        print("\n📊 Analyzing Downloaded Content...")
        
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
            
            # Show sample content
            if text_files:
                sample_file = text_files[0]
                content = sample_file.read_text(encoding='utf-8')
                print(f"  📖 Sample content from {sample_file.name}:")
                print(f"    {content[:200]}...")
            
        except Exception as e:
            print(f"❌ Content analysis failed: {e}")
            self.results["errors"].append(f"Content analysis: {e}")
    
    async def generate_report(self):
        """Generate comprehensive test report."""
        print("\n📄 Generating Test Report...")
        
        self.results["end_time"] = datetime.now().isoformat()
        self.results["total_time"] = (
            datetime.fromisoformat(self.results["end_time"]) - 
            datetime.fromisoformat(self.results["start_time"])
        ).total_seconds()
        
        # Save detailed report
        report_path = self.data_dir / "improved_download_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Print summary
        print("\n" + "=" * 60)
        print("🎉 IMPROVED DOWNLOAD TEST COMPLETED!")
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
    tester = ImprovedDownloadTester()
    
    try:
        # Test individual sources
        pg_works = await tester.test_project_gutenberg_improved()
        ba_works = await tester.test_blake_archive_improved()
        ia_works = await tester.test_internet_archive_improved()
        
        # Test comprehensive download manager
        session_result = await tester.test_download_manager_comprehensive()
        
        # Analyze downloaded content
        await tester.analyze_downloaded_content()
        
        # Generate report
        await tester.generate_report()
        
        print(f"\n🎉 IMPROVED DOWNLOAD TEST COMPLETED!")
        print(f"📊 Final Results: {tester.results['total_texts']} texts, {tester.results['total_images']} images, {tester.results['total_bytes']:,} bytes")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
