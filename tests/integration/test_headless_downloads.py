#!/usr/bin/env python3
"""
Comprehensive Headless Download Test

Tests the full download functionality in headless mode to verify
we can successfully download all web resources.
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

from blake.downloader.downloader import BlakeDownloader
from blake.downloader.manager import DownloadManager
from blake.metadata.manager import MetadataManager
from blake.models import SourceType, WorkType

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class HeadlessDownloadTester:
    """Comprehensive headless download testing."""
    
    def __init__(self, data_dir: str = "./headless_test_data"):
        """Initialize the tester."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.downloader = BlakeDownloader(self.data_dir)
        self.download_manager = DownloadManager(self.data_dir)
        self.metadata_manager = MetadataManager(self.data_dir)
        
        self.results = {
            "start_time": datetime.now().isoformat(),
            "sources_tested": [],
            "total_works_downloaded": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "download_errors": [],
            "works_by_source": {},
            "file_sizes": {},
            "download_times": {}
        }
    
    async def test_all_sources(self):
        """Test downloading from all available sources."""
        print("🚀 Starting Comprehensive Headless Download Test")
        print("=" * 60)
        
        # Test each source
        sources_to_test = [
            SourceType.PROJECT_GUTENBERG,
            SourceType.BLAKE_ARCHIVE,
            SourceType.INTERNET_ARCHIVE
        ]
        
        for source in sources_to_test:
            print(f"\n📥 Testing {source.value}...")
            await self.test_source(source)
        
        # Generate comprehensive report
        await self.generate_report()
    
    async def test_source(self, source: SourceType):
        """Test downloading from a specific source."""
        source_start = datetime.now()
        
        try:
            print(f"  🔍 Getting work list from {source.value}...")
            
            # Get work list
            if source in self.downloader.sources:
                work_list = await self.downloader.sources[source].get_work_list()
                print(f"  📋 Found {len(work_list)} works available")
                
                # Download a subset for testing (limit to 5 works per source)
                test_works = work_list[:5]
                print(f"  📥 Downloading {len(test_works)} test works...")
                
                successful_downloads = 0
                failed_downloads = 0
                
                for i, work_info in enumerate(test_works, 1):
                    try:
                        print(f"    [{i}/{len(test_works)}] Downloading: {work_info.get('title', 'Unknown')}")
                        
                        work = await self.downloader.download_work(
                            work_info['id'], 
                            source=source
                        )
                        
                        if work and work.text_content:
                            successful_downloads += 1
                            self.results["successful_downloads"] += 1
                            
                            # Record file size
                            if work.text_content:
                                file_size = len(work.text_content.encode('utf-8'))
                                self.results["file_sizes"][work.id] = file_size
                                print(f"      ✅ Downloaded {file_size} bytes")
                            
                            # Record work details
                            if source.value not in self.results["works_by_source"]:
                                self.results["works_by_source"][source.value] = []
                            
                            self.results["works_by_source"][source.value].append({
                                "id": work.id,
                                "title": work.metadata.title,
                                "file_size": len(work.text_content.encode('utf-8')) if work.text_content else 0,
                                "has_text": bool(work.text_content),
                                "has_images": len(work.images) > 0
                            })
                        else:
                            failed_downloads += 1
                            self.results["failed_downloads"] += 1
                            print(f"      ❌ Failed to download content")
                            
                    except Exception as e:
                        failed_downloads += 1
                        self.results["failed_downloads"] += 1
                        error_msg = f"Error downloading {work_info.get('id', 'unknown')}: {str(e)}"
                        self.results["download_errors"].append(error_msg)
                        print(f"      ❌ {error_msg}")
                
                # Record source results
                source_time = (datetime.now() - source_start).total_seconds()
                self.results["sources_tested"].append({
                    "source": source.value,
                    "works_available": len(work_list),
                    "works_tested": len(test_works),
                    "successful": successful_downloads,
                    "failed": failed_downloads,
                    "success_rate": successful_downloads / len(test_works) * 100 if test_works else 0,
                    "time_seconds": source_time
                })
                
                self.results["total_works_downloaded"] += len(test_works)
                self.results["download_times"][source.value] = source_time
                
                print(f"  ✅ {source.value} completed: {successful_downloads}/{len(test_works)} successful ({source_time:.1f}s)")
                
            else:
                print(f"  ⚠️  Source {source.value} not available")
                self.results["sources_tested"].append({
                    "source": source.value,
                    "status": "not_available",
                    "error": "Source not configured"
                })
                
        except Exception as e:
            print(f"  ❌ Error testing {source.value}: {e}")
            self.results["download_errors"].append(f"Source {source.value}: {str(e)}")
    
    async def test_download_manager(self):
        """Test the download manager functionality."""
        print("\n📊 Testing Download Manager...")
        
        try:
            # Test download all sources
            print("  🔄 Testing download_all_sources...")
            session_id = await self.download_manager.download_all_sources()
            print(f"  ✅ Download session created: {session_id}")
            
            # Test statistics
            print("  📈 Getting download statistics...")
            stats = await self.download_manager.get_download_statistics()
            print(f"  📊 Statistics: {stats}")
            
            # Test session listing
            print("  📋 Listing download sessions...")
            sessions = await self.download_manager.list_sessions()
            print(f"  📝 Found {len(sessions)} sessions")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Download manager test failed: {e}")
            return False
    
    async def test_metadata_processing(self):
        """Test metadata processing and storage."""
        print("\n📚 Testing Metadata Processing...")
        
        try:
            # Get all downloaded works
            works = await self.downloader.get_all_works()
            print(f"  📖 Processing metadata for {len(works)} works...")
            
            processed_count = 0
            for work in works:
                try:
                    # Save metadata
                    await self.metadata_manager.save_work_metadata(work)
                    processed_count += 1
                except Exception as e:
                    print(f"    ⚠️  Error processing {work.id}: {e}")
            
            print(f"  ✅ Processed metadata for {processed_count} works")
            return True
            
        except Exception as e:
            print(f"  ❌ Metadata processing failed: {e}")
            return False
    
    async def verify_downloaded_files(self):
        """Verify that downloaded files exist and have content."""
        print("\n🔍 Verifying Downloaded Files...")
        
        try:
            works = await self.downloader.get_all_works()
            verified_count = 0
            total_size = 0
            
            for work in works:
                if work.text_content:
                    verified_count += 1
                    total_size += len(work.text_content.encode('utf-8'))
                    
                    # Check if file was saved
                    if work.metadata.file_path and work.metadata.file_path.exists():
                        file_size = work.metadata.file_path.stat().st_size
                        print(f"  ✅ {work.id}: {file_size} bytes on disk")
                    else:
                        print(f"  ⚠️  {work.id}: File not saved to disk")
            
            print(f"  📊 Verification complete: {verified_count} works verified, {total_size} total bytes")
            return verified_count, total_size
            
        except Exception as e:
            print(f"  ❌ File verification failed: {e}")
            return 0, 0
    
    async def generate_report(self):
        """Generate comprehensive test report."""
        print("\n📄 Generating Comprehensive Report...")
        
        self.results["end_time"] = datetime.now().isoformat()
        self.results["total_time"] = (
            datetime.fromisoformat(self.results["end_time"]) - 
            datetime.fromisoformat(self.results["start_time"])
        ).total_seconds()
        
        # Calculate overall success rate
        total_attempts = self.results["successful_downloads"] + self.results["failed_downloads"]
        self.results["overall_success_rate"] = (
            self.results["successful_downloads"] / total_attempts * 100 
            if total_attempts > 0 else 0
        )
        
        # Save detailed report
        report_path = self.data_dir / "headless_download_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 HEADLESS DOWNLOAD TEST SUMMARY")
        print("=" * 60)
        print(f"⏱️  Total Time: {self.results['total_time']:.1f} seconds")
        print(f"📥 Total Works Downloaded: {self.results['total_works_downloaded']}")
        print(f"✅ Successful Downloads: {self.results['successful_downloads']}")
        print(f"❌ Failed Downloads: {self.results['failed_downloads']}")
        print(f"📈 Success Rate: {self.results['overall_success_rate']:.1f}%")
        print(f"📁 Data Directory: {self.data_dir}")
        print(f"📄 Detailed Report: {report_path}")
        
        print("\n📚 Sources Tested:")
        for source in self.results["sources_tested"]:
            if "success_rate" in source:
                print(f"  • {source['source']}: {source['successful']}/{source['works_tested']} ({source['success_rate']:.1f}%)")
            else:
                print(f"  • {source['source']}: {source.get('status', 'unknown')}")
        
        if self.results["download_errors"]:
            print(f"\n❌ Errors ({len(self.results['download_errors'])}):")
            for error in self.results["download_errors"][:5]:  # Show first 5 errors
                print(f"  • {error}")
            if len(self.results["download_errors"]) > 5:
                print(f"  ... and {len(self.results['download_errors']) - 5} more errors")
        
        print("\n✅ Headless download test completed!")
        return self.results


async def main():
    """Main test function."""
    tester = HeadlessDownloadTester()
    
    try:
        # Run comprehensive tests
        await tester.test_all_sources()
        await tester.test_download_manager()
        await tester.test_metadata_processing()
        verified_count, total_size = await tester.verify_downloaded_files()
        
        print(f"\n🎉 COMPREHENSIVE TEST COMPLETED!")
        print(f"📊 Final Results: {verified_count} works verified, {total_size:,} bytes downloaded")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
