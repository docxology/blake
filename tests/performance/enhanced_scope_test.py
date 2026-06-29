#!/usr/bin/env python3
"""
Enhanced Scope Test - Comprehensive Resource Discovery

This test explores all available sources and attempts to maximize
the scope of downloadable content to assess true system capabilities.
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime
import json
import time
import requests
from urllib.parse import urljoin

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from blake.downloader.manager import DownloadManager
from blake.downloader.sources import ProjectGutenbergSource, BlakeArchiveSource, InternetArchiveSource
from blake.models import SourceType, WorkType

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnhancedScopeTester:
    """Enhanced scope testing with comprehensive resource discovery."""
    
    def __init__(self, data_dir: str = "./enhanced_scope_data"):
        """Initialize the enhanced scope tester."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.download_manager = DownloadManager(self.data_dir)
        
        self.results = {
            "start_time": datetime.now().isoformat(),
            "discovered_resources": {},
            "total_works_found": 0,
            "total_works_downloaded": 0,
            "total_texts": 0,
            "total_images": 0,
            "total_bytes_downloaded": 0,
            "source_analysis": {},
            "scope_metrics": {},
            "recommendations": []
        }
    
    async def discover_all_resources(self):
        """Discover all available resources across all sources."""
        print("🔍 ENHANCED SCOPE TEST - COMPREHENSIVE RESOURCE DISCOVERY")
        print("=" * 70)
        print("🌐 Exploring all available sources for maximum content...")
        print("=" * 70)
        
        # Test each source individually for maximum discovery
        sources_to_test = [
            ("Project Gutenberg", self.test_project_gutenberg_comprehensive),
            ("Blake Archive", self.test_blake_archive_comprehensive),
            ("Internet Archive", self.test_internet_archive_comprehensive),
            ("Additional Sources", self.test_additional_sources)
        ]
        
        for source_name, test_func in sources_to_test:
            print(f"\n📡 Testing {source_name}...")
            try:
                await test_func()
            except Exception as e:
                print(f"❌ Error testing {source_name}: {e}")
                self.results["recommendations"].append(f"Fix {source_name}: {str(e)}")
    
    async def test_project_gutenberg_comprehensive(self):
        """Comprehensive Project Gutenberg testing."""
        print("  🔍 Comprehensive Project Gutenberg analysis...")
        
        try:
            # Initialize PG source
            pg_source = ProjectGutenbergSource(self.data_dir)
            
            # Get work list
            works = await pg_source.get_work_list()
            print(f"  📚 Found {len(works)} Blake works in Project Gutenberg")
            
            # Analyze each work
            downloadable_works = []
            for work in works:
                work_id = work['id']
                title = work['title']
                
                # Try to download each work
                try:
                    downloaded_work = await pg_source.download_work(work_id)
                    if downloaded_work and downloaded_work.text_content:
                        downloadable_works.append({
                            "id": work_id,
                            "title": title,
                            "size": len(downloaded_work.text_content.encode('utf-8')),
                            "success": True
                        })
                        print(f"    ✅ {work_id}: {title} ({len(downloaded_work.text_content.encode('utf-8'))} bytes)")
                    else:
                        print(f"    ⚠️  {work_id}: {title} - No text content")
                except Exception as e:
                    print(f"    ❌ {work_id}: {title} - Error: {e}")
            
            self.results["discovered_resources"]["project_gutenberg"] = {
                "total_works": len(works),
                "downloadable_works": len(downloadable_works),
                "works": downloadable_works,
                "success_rate": len(downloadable_works) / len(works) * 100 if works else 0
            }
            
            self.results["total_works_found"] += len(works)
            self.results["total_works_downloaded"] += len(downloadable_works)
            
        except Exception as e:
            print(f"  ❌ Project Gutenberg test failed: {e}")
            self.results["recommendations"].append(f"Project Gutenberg issue: {str(e)}")
    
    async def test_blake_archive_comprehensive(self):
        """Comprehensive Blake Archive testing."""
        print("  🔍 Comprehensive Blake Archive analysis...")
        
        try:
            # Initialize Blake Archive source
            ba_source = BlakeArchiveSource(self.data_dir)
            
            # Get work list
            works = await ba_source.get_work_list()
            print(f"  📚 Found {len(works)} works in Blake Archive")
            
            if works:
                # Try to download a few works
                downloadable_works = []
                for work in works[:3]:  # Test first 3 works
                    work_id = work['id']
                    title = work['title']
                    
                    try:
                        downloaded_work = await ba_source.download_work(work_id)
                        if downloaded_work:
                            downloadable_works.append({
                                "id": work_id,
                                "title": title,
                                "success": True
                            })
                            print(f"    ✅ {work_id}: {title}")
                        else:
                            print(f"    ⚠️  {work_id}: {title} - No content")
                    except Exception as e:
                        print(f"    ❌ {work_id}: {title} - Error: {e}")
                
                self.results["discovered_resources"]["blake_archive"] = {
                    "total_works": len(works),
                    "downloadable_works": len(downloadable_works),
                    "works": downloadable_works,
                    "success_rate": len(downloadable_works) / len(works) * 100 if works else 0
                }
                
                self.results["total_works_found"] += len(works)
                self.results["total_works_downloaded"] += len(downloadable_works)
            else:
                print("  ⚠️  No works found in Blake Archive")
                self.results["discovered_resources"]["blake_archive"] = {
                    "total_works": 0,
                    "downloadable_works": 0,
                    "works": [],
                    "success_rate": 0
                }
                
        except Exception as e:
            print(f"  ❌ Blake Archive test failed: {e}")
            self.results["recommendations"].append(f"Blake Archive issue: {str(e)}")
    
    async def test_internet_archive_comprehensive(self):
        """Comprehensive Internet Archive testing."""
        print("  🔍 Comprehensive Internet Archive analysis...")
        
        try:
            # Initialize IA source
            ia_source = InternetArchiveSource(self.data_dir)
            
            # Get work list
            works = await ia_source.get_work_list()
            print(f"  📚 Found {len(works)} works in Internet Archive")
            
            if works:
                # Try to download a few works
                downloadable_works = []
                for work in works[:3]:  # Test first 3 works
                    work_id = work['id']
                    title = work['title']
                    
                    try:
                        downloaded_work = await ia_source.download_work(work_id)
                        if downloaded_work:
                            downloadable_works.append({
                                "id": work_id,
                                "title": title,
                                "success": True
                            })
                            print(f"    ✅ {work_id}: {title}")
                        else:
                            print(f"    ⚠️  {work_id}: {title} - No content")
                    except Exception as e:
                        print(f"    ❌ {work_id}: {title} - Error: {e}")
                
                self.results["discovered_resources"]["internet_archive"] = {
                    "total_works": len(works),
                    "downloadable_works": len(downloadable_works),
                    "works": downloadable_works,
                    "success_rate": len(downloadable_works) / len(works) * 100 if works else 0
                }
                
                self.results["total_works_found"] += len(works)
                self.results["total_works_downloaded"] += len(downloadable_works)
            else:
                print("  ⚠️  No works found in Internet Archive")
                self.results["discovered_resources"]["internet_archive"] = {
                    "total_works": 0,
                    "downloadable_works": 0,
                    "works": [],
                    "success_rate": 0
                }
                
        except Exception as e:
            print(f"  ❌ Internet Archive test failed: {e}")
            self.results["recommendations"].append(f"Internet Archive issue: {str(e)}")
    
    async def test_additional_sources(self):
        """Test additional potential sources."""
        print("  🔍 Testing additional sources...")
        
        # Test direct API access to other sources
        additional_sources = [
            ("British Museum API", "https://www.britishmuseum.org/api/"),
            ("Tate API", "https://www.tate.org.uk/api/"),
            ("Wikimedia Commons", "https://commons.wikimedia.org/api/"),
            ("HathiTrust", "https://www.hathitrust.org/api/"),
            ("Google Arts & Culture", "https://artsandculture.google.com/api/")
        ]
        
        for source_name, api_url in additional_sources:
            try:
                print(f"    🌐 Testing {source_name}...")
                response = requests.get(api_url, timeout=5)
                if response.status_code == 200:
                    print(f"      ✅ {source_name} - API accessible")
                    self.results["discovered_resources"][source_name.lower().replace(" ", "_")] = {
                        "api_accessible": True,
                        "status_code": response.status_code
                    }
                else:
                    print(f"      ⚠️  {source_name} - Status: {response.status_code}")
                    self.results["discovered_resources"][source_name.lower().replace(" ", "_")] = {
                        "api_accessible": False,
                        "status_code": response.status_code
                    }
            except Exception as e:
                print(f"      ❌ {source_name} - Error: {e}")
                self.results["discovered_resources"][source_name.lower().replace(" ", "_")] = {
                    "api_accessible": False,
                    "error": str(e)
                }
    
    async def analyze_downloaded_content(self):
        """Analyze all downloaded content."""
        print("\n📊 ANALYZING DOWNLOADED CONTENT...")
        
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
            self.results["total_bytes_downloaded"] = total_text_size + total_image_size
            
            print(f"  📄 Text files: {len(text_files)} ({total_text_size:,} bytes)")
            print(f"  🖼️  Image files: {len(image_files)} ({total_image_size:,} bytes)")
            print(f"  💾 Total data: {total_text_size + total_image_size:,} bytes")
            
        except Exception as e:
            print(f"❌ Content analysis failed: {e}")
    
    async def assess_scope_and_recommendations(self):
        """Assess scope and provide recommendations."""
        print("\n📈 SCOPE ASSESSMENT AND RECOMMENDATIONS")
        print("=" * 50)
        
        # Calculate scope metrics
        scope_metrics = {
            "texts_acquired": self.results["total_texts"],
            "images_acquired": self.results["total_images"],
            "total_works": self.results["total_works_downloaded"],
            "total_bytes": self.results["total_bytes_downloaded"],
            "sources_working": len([s for s in self.results["discovered_resources"].values() 
                                  if isinstance(s, dict) and s.get("success_rate", 0) > 0]),
            "total_sources_tested": len(self.results["discovered_resources"])
        }
        
        # Generate recommendations
        recommendations = []
        
        if scope_metrics["texts_acquired"] < 20:
            recommendations.append("Implement additional text sources (Blake Archive, Internet Archive)")
        
        if scope_metrics["images_acquired"] < 100:
            recommendations.append("Implement image download from museum APIs (British Museum, Tate)")
        
        if scope_metrics["total_works"] < 50:
            recommendations.append("Expand work discovery across all available sources")
        
        if scope_metrics["sources_working"] < 3:
            recommendations.append("Fix source implementations for better coverage")
        
        self.results["scope_metrics"] = scope_metrics
        self.results["recommendations"].extend(recommendations)
        
        # Print assessment
        print(f"📊 CURRENT SCOPE:")
        print(f"  📄 Texts: {scope_metrics['texts_acquired']}")
        print(f"  🖼️  Images: {scope_metrics['images_acquired']}")
        print(f"  📚 Total works: {scope_metrics['total_works']}")
        print(f"  💾 Total bytes: {scope_metrics['total_bytes']:,}")
        print(f"  🌐 Working sources: {scope_metrics['sources_working']}/{scope_metrics['total_sources_tested']}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
        
        return scope_metrics
    
    async def generate_final_report(self):
        """Generate final comprehensive report."""
        print("\n📄 GENERATING FINAL REPORT...")
        
        self.results["end_time"] = datetime.now().isoformat()
        self.results["total_time"] = (
            datetime.fromisoformat(self.results["end_time"]) - 
            datetime.fromisoformat(self.results["start_time"])
        ).total_seconds()
        
        # Save detailed report
        report_path = self.data_dir / "enhanced_scope_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Print final summary
        print("\n" + "=" * 70)
        print("🎉 ENHANCED SCOPE TEST COMPLETED!")
        print("=" * 70)
        print(f"⏱️  Total execution time: {self.results['total_time']:.1f} seconds")
        print(f"📊 FINAL SCOPE ASSESSMENT:")
        print(f"  📄 Texts: {self.results['total_texts']}")
        print(f"  🖼️  Images: {self.results['total_images']}")
        print(f"  📚 Total works: {self.results['total_works_downloaded']}")
        print(f"  💾 Total data: {self.results['total_bytes_downloaded']:,}")
        print(f"  🌐 Sources tested: {self.results['scope_metrics']['total_sources_tested']}")
        print(f"  ✅ Working sources: {self.results['scope_metrics']['sources_working']}")
        print(f"📁 Data directory: {self.data_dir}")
        print(f"📄 Detailed report: {report_path}")
        
        print(f"\n💡 KEY RECOMMENDATIONS:")
        for i, rec in enumerate(self.results["recommendations"][:5], 1):
            print(f"  {i}. {rec}")
        
        print("\n✅ Enhanced scope test completed successfully!")
        return self.results


async def main():
    """Main execution function."""
    tester = EnhancedScopeTester()
    
    try:
        # Discover all resources
        await tester.discover_all_resources()
        
        # Analyze downloaded content
        await tester.analyze_downloaded_content()
        
        # Assess scope and provide recommendations
        await tester.assess_scope_and_recommendations()
        
        # Generate final report
        await tester.generate_final_report()
        
        print(f"\n🎉 ENHANCED SCOPE TEST COMPLETED!")
        print(f"📊 Final Results: {tester.results['total_texts']} texts, {tester.results['total_images']} images, {tester.results['total_bytes_downloaded']:,} bytes")
        
    except Exception as e:
        print(f"❌ Enhanced scope test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
