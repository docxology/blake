"""
Basic usage examples for the Blake package.
"""

import asyncio
from pathlib import Path
from blake import BlakeWorks
from blake.models import ExportConfig


async def main():
    """Main example function."""
    print("Blake Package - Basic Usage Examples")
    print("=" * 40)
    
    # Initialize BlakeWorks
    data_dir = Path("./data/blake")
    blake = BlakeWorks(data_dir)
    
    # Example 1: Download all works
    print("\n1. Downloading all Blake works...")
    try:
        works = await blake.download_all()
        print(f"Downloaded {len(works)} works")
        
        # Show first few works
        for work in works[:3]:
            print(f"  - {work.metadata.title} ({work.metadata.work_type})")
    except Exception as e:
        print(f"Error downloading works: {e}")
    
    # Example 2: Search works
    print("\n2. Searching for works...")
    try:
        results = await blake.search_works("innocence")
        print(f"Found {len(results)} works containing 'innocence'")
        
        for work in results[:2]:
            print(f"  - {work.metadata.title}")
    except Exception as e:
        print(f"Error searching works: {e}")
    
    # Example 3: Analyze a work
    print("\n3. Analyzing a work...")
    try:
        works = await blake.get_all_works()
        if works:
            work = works[0]
            print(f"Analyzing: {work.metadata.title}")
            
            analysis_results = await blake.analyze_work(work.id)
            print("Analysis completed")
            
            # Show basic text analysis
            if 'text_analysis' in analysis_results:
                text_analysis = analysis_results['text_analysis']
                if 'basic_stats' in text_analysis:
                    stats = text_analysis['basic_stats']
                    print(f"  Word count: {stats.get('word_count', 0)}")
                    print(f"  Sentences: {stats.get('sentence_count', 0)}")
                
                if 'sentiment' in text_analysis:
                    sentiment = text_analysis['sentiment']
                    print(f"  Sentiment: {sentiment.get('sentiment', 'Unknown')}")
    except Exception as e:
        print(f"Error analyzing work: {e}")
    
    # Example 4: Export works
    print("\n4. Exporting works...")
    try:
        works = await blake.get_all_works()
        if works:
            # Export first 3 works
            export_works = works[:3]
            
            config = ExportConfig(
                format="json",
                output_dir=Path("./exports"),
                include_images=True,
                include_analysis=True
            )
            
            output_path = await blake.export_works(export_works, config)
            print(f"Exported {len(export_works)} works to: {output_path}")
    except Exception as e:
        print(f"Error exporting works: {e}")
    
    # Example 5: Get statistics
    print("\n5. Collection statistics...")
    try:
        stats = await blake.get_statistics()
        print(f"Total works: {stats.get('total_works', 0)}")
        print(f"Total images: {stats.get('total_images', 0)}")
        print(f"Processed works: {stats.get('processed_works', 0)}")
        
        if 'work_types' in stats:
            print("Work types:")
            for work_type, count in stats['work_types'].items():
                print(f"  {work_type}: {count}")
    except Exception as e:
        print(f"Error getting statistics: {e}")
    
    print("\nExamples completed!")


if __name__ == "__main__":
    asyncio.run(main())

