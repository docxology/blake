#!/usr/bin/env python3
"""
Full Scope Test - Complete Download Assessment

Executes the full methods of the thin orchestrator to download ALL available
web works and assess the complete scope and functionality of the Blake system.
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime
import json
import time

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from blake.downloader.manager import DownloadManager
from blake.metadata.manager import MetadataManager
from blake.models import SourceType, WorkType

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FullScopeTester:
    """Full scope testing to assess complete system capabilities."""
    
    def __init__(self, data_dir: str = "./full_scope_data"):
        """Initialize the full scope tester."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.download_manager = DownloadManager(self.data_dir)
        self.metadata_manager = MetadataManager(self.data_dir)
        
        self.results = {
            "start_time": datetime.now().isoformat(),
            "total_sources_tested": 0,
            "total_works_found": 0,
            "total_works_downloaded": 0,
            "total_texts": 0,
            "total_images": 0,
            "total_bytes_downloaded": 0,
            "sources_breakdown": {},
            "works_by_type": {},
            "download_times": {},
            "errors": [],
            "file_analysis": {},
            "scope_assessment": {}
        }
    
    async def execute_full_download(self):
        """Execute full download from all available sources."""
        print("🚀 FULL SCOPE TEST - COMPLETE DOWNLOAD ASSESSMENT")
        print("=" * 70)
        print("📥 Downloading ALL available works from ALL sources...")
        print("🎯 Target: Dozens of texts, hundreds of images")
        print("=" * 70)
        
        start_time = time.time()
        
        try:
            # Execute comprehensive download
            print("\n🔄 Starting comprehensive download from all sources...")
            session_result = await self.download_manager.download_all_sources()
            
            end_time = time.time()
            total_time = end_time - start_time
            
            print(f"\n✅ Download session completed: {session_result['session_id']}")
            print(f"⏱️  Total time: {total_time:.1f} seconds")
            print(f"📊 Total works found: {session_result['total_works']}")
            print(f"✅ Successful downloads: {session_result['successful_works']}")
            print(f"❌ Failed downloads: {session_result['failed_works']}")
            
            # Record basic results
            self.results["total_works_found"] = session_result['total_works']
            self.results["total_works_downloaded"] = session_result['successful_works']
            self.results["download_times"]["total"] = total_time
            self.results["errors"] = session_result.get('errors', [])
            
            # Process detailed source breakdown
            for source_name, source_data in session_result['sources'].items():
                self.results["sources_breakdown"][source_name] = {
                    "works_found": source_data['works_found'],
                    "works_downloaded": source_data['works_downloaded'],
                    "works_failed": source_data['works_failed'],
                    "success_rate": (
                        source_data['works_downloaded'] / source_data['works_found'] * 100 
                        if source_data['works_found'] > 0 else 0
                    ),
                    "time_seconds": (
                        datetime.fromisoformat(source_data['end_time']) - 
                        datetime.fromisoformat(source_data['start_time'])
                    ).total_seconds(),
                    "errors": source_data.get('errors', [])
                }
                self.results["total_sources_tested"] += 1
            
            return session_result
            
        except Exception as e:
            print(f"❌ Full download failed: {e}")
            self.results["errors"].append(f"Full download error: {str(e)}")
            return None
    
    async def analyze_downloaded_content(self):
        """Analyze all downloaded content to assess scope."""
        print("\n🔍 ANALYZING DOWNLOADED CONTENT...")
        print("=" * 50)
        
        try:
            # Analyze texts
            texts_dir = self.data_dir / "texts"
            text_files = list(texts_dir.glob("*.txt")) if texts_dir.exists() else []
            
            print(f"📄 Text files found: {len(text_files)}")
            
            total_text_size = 0
            text_analysis = {
                "count": len(text_files),
                "total_size": 0,
                "files": [],
                "works_by_title": {},
                "content_samples": []
            }
            
            for text_file in text_files:
                try:
                    file_size = text_file.stat().st_size
                    total_text_size += file_size
                    
                    # Read content for analysis
                    content = text_file.read_text(encoding='utf-8')
                    
                    # Extract title and basic info
                    lines = content.split('\n')
                    title = "Unknown"
                    author = "Unknown"
                    work_type = "Unknown"
                    
                    for line in lines[:20]:  # Check first 20 lines
                        if "Title:" in line:
                            title = line.split("Title:")[-1].strip()
                        elif "Author:" in line:
                            author = line.split("Author:")[-1].strip()
                        elif "William Blake" in line:
                            author = "William Blake"
                    
                    # Determine work type
                    if any(word in title.lower() for word in ['song', 'poem', 'poetry']):
                        work_type = "Poetry"
                    elif any(word in title.lower() for word in ['prophecy', 'vision']):
                        work_type = "Prophecy"
                    elif any(word in title.lower() for word in ['marriage', 'heaven', 'hell']):
                        work_type = "Prophecy"
                    else:
                        work_type = "Other"
                    
                    text_analysis["files"].append({
                        "file": str(text_file),
                        "size": file_size,
                        "title": title,
                        "author": author,
                        "work_type": work_type,
                        "line_count": len(content.split('\n')),
                        "word_count": len(content.split())
                    })
                    
                    # Group by work type
                    if work_type not in text_analysis["works_by_title"]:
                        text_analysis["works_by_title"][work_type] = []
                    text_analysis["works_by_title"][work_type].append(title)
                    
                    # Collect content samples
                    if len(text_analysis["content_samples"]) < 3:
                        sample = content[:500] + "..." if len(content) > 500 else content
                        text_analysis["content_samples"].append({
                            "file": text_file.name,
                            "title": title,
                            "sample": sample
                        })
                    
                    print(f"  📝 {text_file.name}: {file_size:,} bytes - {title}")
                    
                except Exception as e:
                    print(f"  ❌ Error analyzing {text_file.name}: {e}")
            
            text_analysis["total_size"] = total_text_size
            self.results["total_texts"] = len(text_files)
            self.results["total_bytes_downloaded"] += total_text_size
            self.results["file_analysis"]["texts"] = text_analysis
            
            # Analyze images
            images_dir = self.data_dir / "images"
            image_files = list(images_dir.glob("*")) if images_dir.exists() else []
            
            print(f"\n🖼️  Image files found: {len(image_files)}")
            
            total_image_size = 0
            image_analysis = {
                "count": len(image_files),
                "total_size": 0,
                "files": [],
                "formats": {}
            }
            
            for image_file in image_files:
                try:
                    file_size = image_file.stat().st_size
                    total_image_size += file_size
                    
                    # Determine format
                    file_ext = image_file.suffix.lower()
                    if file_ext not in image_analysis["formats"]:
                        image_analysis["formats"][file_ext] = 0
                    image_analysis["formats"][file_ext] += 1
                    
                    image_analysis["files"].append({
                        "file": str(image_file),
                        "size": file_size,
                        "format": file_ext
                    })
                    
                    print(f"  🖼️  {image_file.name}: {file_size:,} bytes")
                    
                except Exception as e:
                    print(f"  ❌ Error analyzing {image_file.name}: {e}")
            
            image_analysis["total_size"] = total_image_size
            self.results["total_images"] = len(image_files)
            self.results["total_bytes_downloaded"] += total_image_size
            self.results["file_analysis"]["images"] = image_analysis
            
            # Analyze metadata
            metadata_dir = self.data_dir / "metadata"
            metadata_files = list(metadata_dir.glob("*")) if metadata_dir.exists() else []
            
            print(f"\n📚 Metadata files found: {len(metadata_files)}")
            self.results["file_analysis"]["metadata"] = {
                "count": len(metadata_files),
                "files": [str(f) for f in metadata_files]
            }
            
            return text_analysis, image_analysis
            
        except Exception as e:
            print(f"❌ Content analysis failed: {e}")
            self.results["errors"].append(f"Content analysis error: {str(e)}")
            return None, None
    
    async def assess_scope_and_functionality(self):
        """Assess the complete scope and functionality achieved."""
        print("\n📊 SCOPE AND FUNCTIONALITY ASSESSMENT")
        print("=" * 50)
        
        try:
            # Calculate scope metrics
            scope_metrics = {
                "texts_acquired": self.results["total_texts"],
                "images_acquired": self.results["total_images"],
                "total_works": self.results["total_works_downloaded"],
                "total_bytes": self.results["total_bytes_downloaded"],
                "sources_utilized": self.results["total_sources_tested"],
                "success_rate": (
                    self.results["total_works_downloaded"] / self.results["total_works_found"] * 100 
                    if self.results["total_works_found"] > 0 else 0
                )
            }
            
            # Assess against targets
            targets = {
                "texts_target": 20,  # "dozens of texts"
                "images_target": 100,  # "hundreds of images"
                "works_target": 50,
                "bytes_target": 1000000  # 1MB
            }
            
            achievements = {
                "texts_achieved": scope_metrics["texts_acquired"] >= targets["texts_target"],
                "images_achieved": scope_metrics["images_acquired"] >= targets["images_target"],
                "works_achieved": scope_metrics["total_works"] >= targets["works_target"],
                "bytes_achieved": scope_metrics["total_bytes"] >= targets["bytes_target"]
            }
            
            # Calculate achievement percentage
            achievement_percentage = sum(achievements.values()) / len(achievements) * 100
            
            scope_metrics["targets"] = targets
            scope_metrics["achievements"] = achievements
            scope_metrics["achievement_percentage"] = achievement_percentage
            
            self.results["scope_assessment"] = scope_metrics
            
            # Print assessment
            print(f"📈 SCOPE METRICS:")
            print(f"  📄 Texts acquired: {scope_metrics['texts_acquired']} (target: {targets['texts_target']}) {'✅' if achievements['texts_achieved'] else '❌'}")
            print(f"  🖼️  Images acquired: {scope_metrics['images_acquired']} (target: {targets['images_target']}) {'✅' if achievements['images_achieved'] else '❌'}")
            print(f"  📚 Total works: {scope_metrics['total_works']} (target: {targets['works_target']}) {'✅' if achievements['works_achieved'] else '❌'}")
            print(f"  💾 Total bytes: {scope_metrics['total_bytes']:,} (target: {targets['bytes_target']:,}) {'✅' if achievements['bytes_achieved'] else '❌'}")
            print(f"  🌐 Sources utilized: {scope_metrics['sources_utilized']}")
            print(f"  📊 Success rate: {scope_metrics['success_rate']:.1f}%")
            print(f"  🎯 Overall achievement: {achievement_percentage:.1f}%")
            
            return scope_metrics
            
        except Exception as e:
            print(f"❌ Scope assessment failed: {e}")
            self.results["errors"].append(f"Scope assessment error: {str(e)}")
            return None
    
    async def generate_comprehensive_report(self):
        """Generate comprehensive scope and functionality report."""
        print("\n📄 GENERATING COMPREHENSIVE REPORT...")
        
        self.results["end_time"] = datetime.now().isoformat()
        self.results["total_time"] = (
            datetime.fromisoformat(self.results["end_time"]) - 
            datetime.fromisoformat(self.results["start_time"])
        ).total_seconds()
        
        # Save detailed report
        report_path = self.data_dir / "full_scope_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Print final summary
        print("\n" + "=" * 70)
        print("🎉 FULL SCOPE TEST COMPLETED!")
        print("=" * 70)
        print(f"⏱️  Total execution time: {self.results['total_time']:.1f} seconds")
        print(f"📊 FINAL SCOPE ASSESSMENT:")
        print(f"  📄 Texts: {self.results['total_texts']}")
        print(f"  🖼️  Images: {self.results['total_images']}")
        print(f"  📚 Total works: {self.results['total_works_downloaded']}")
        print(f"  💾 Total data: {self.results['total_bytes_downloaded']:,} bytes")
        print(f"  🌐 Sources tested: {self.results['total_sources_tested']}")
        print(f"📁 Data directory: {self.data_dir}")
        print(f"📄 Detailed report: {report_path}")
        
        if self.results["scope_assessment"]:
            achievement = self.results["scope_assessment"]["achievement_percentage"]
            print(f"🎯 Target achievement: {achievement:.1f}%")
            
            if achievement >= 75:
                print("✅ EXCELLENT: Most targets achieved!")
            elif achievement >= 50:
                print("⚠️  GOOD: Some targets achieved")
            else:
                print("❌ NEEDS IMPROVEMENT: Few targets achieved")
        
        print("\n✅ Full scope test completed successfully!")
        return self.results


async def main():
    """Main execution function."""
    tester = FullScopeTester()
    
    try:
        # Execute full download
        session_result = await tester.execute_full_download()
        
        if session_result:
            # Analyze downloaded content
            text_analysis, image_analysis = await tester.analyze_downloaded_content()
            
            # Assess scope and functionality
            scope_metrics = await tester.assess_scope_and_functionality()
            
            # Generate comprehensive report
            await tester.generate_comprehensive_report()
            
            print(f"\n🎉 FULL SCOPE TEST COMPLETED!")
            print(f"📊 Final Results: {tester.results['total_texts']} texts, {tester.results['total_images']} images, {tester.results['total_bytes_downloaded']:,} bytes")
            
        else:
            print("❌ Full download failed, cannot assess scope")
        
    except Exception as e:
        print(f"❌ Full scope test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
