"""
Advanced analysis examples for the Blake package.
"""

import asyncio
from pathlib import Path
from blake import BlakeCorpus
from blake.models import ExportConfig


async def main():
    """Advanced analysis examples."""
    print("Blake Package - Advanced Analysis Examples")
    print("=" * 45)
    
    # Initialize BlakeCorpus
    data_dir = Path("./data/blake")
    blake = BlakeCorpus(data_dir)
    
    # Example 1: Comprehensive analysis of all works
    print("\n1. Running comprehensive analysis...")
    try:
        works = await blake.get_all_works()
        if works:
            print(f"Analyzing {len(works)} works...")
            
            # Run all types of analysis
            analysis_types = ['text', 'visual', 'cross']
            results = await blake.analyze_all(analysis_types)
            
            print(f"Analysis completed for {len(results)} works")
            
            # Show analysis summary
            for work_id, analysis in list(results.items())[:3]:
                print(f"\nWork {work_id}:")
                if 'text_analysis' in analysis:
                    print("  ✅ Text analysis completed")
                if 'visual_analysis' in analysis:
                    print("  ✅ Visual analysis completed")
                if 'cross_analysis' in analysis:
                    print("  ✅ Cross analysis completed")
    except Exception as e:
        print(f"Error in comprehensive analysis: {e}")
    
    # Example 2: Compare works
    print("\n2. Comparing works...")
    try:
        works = await blake.get_all_works()
        if len(works) >= 2:
            # Compare first 3 works
            compare_works = works[:3]
            comparison = await blake.analyzer.compare_works(compare_works)
            
            print("Comparison results:")
            if 'text_comparison' in comparison:
                text_comp = comparison['text_comparison']
                if 'most_similar_pairs' in text_comp:
                    print("Most similar text pairs:")
                    for pair in text_comp['most_similar_pairs'][:2]:
                        print(f"  {pair['work1_id']} <-> {pair['work2_id']}: {pair['similarity']:.3f}")
            
            if 'thematic_comparison' in comparison:
                theme_comp = comparison['thematic_comparison']
                if 'common_themes' in theme_comp:
                    print(f"Common themes: {theme_comp['common_themes']}")
    except Exception as e:
        print(f"Error comparing works: {e}")
    
    # Example 3: Export analysis results
    print("\n3. Exporting analysis results...")
    try:
        works = await blake.get_all_works()
        if works:
            # Export only analysis results
            config = ExportConfig(
                format="json",
                output_dir=Path("./exports"),
                include_images=False,
                include_metadata=False,
                include_analysis=True
            )
            
            output_path = await blake.export_works(works, config)
            print(f"Analysis results exported to: {output_path}")
    except Exception as e:
        print(f"Error exporting analysis results: {e}")
    
    # Example 4: Search with complex filters
    print("\n4. Advanced search...")
    try:
        # Search for works with specific criteria
        filters = {
            'work_type': 'poem',
            'has_images': True,
            'has_text': True
        }
        
        results = await blake.search_works("", filters)
        print(f"Found {len(results)} poems with both text and images")
        
        for work in results[:3]:
            print(f"  - {work.metadata.title}")
            print(f"    Images: {len(work.images)}")
            print(f"    Text length: {len(work.text_content) if work.text_content else 0} chars")
    except Exception as e:
        print(f"Error in advanced search: {e}")
    
    # Example 5: Get detailed work information
    print("\n5. Detailed work information...")
    try:
        works = await blake.get_all_works()
        if works:
            work = works[0]
            print(f"Work: {work.metadata.title}")
            print(f"Type: {work.metadata.work_type}")
            print(f"Date: {work.metadata.creation_date}")
            print(f"Source: {work.metadata.source}")
            print(f"Tags: {work.metadata.tags}")
            print(f"Themes: {work.metadata.themes}")
            print(f"Subjects: {work.metadata.subjects}")
            
            if work.text_content:
                print(f"Text length: {len(work.text_content)} characters")
            
            if work.images:
                print(f"Images: {len(work.images)}")
                for i, image in enumerate(work.images[:2]):
                    print(f"  Image {i+1}: {image.title}")
                    if image.dominant_colors:
                        print(f"    Dominant colors: {image.dominant_colors[:3]}")
            
            if work.text_analysis:
                print("Text analysis available:")
                if 'sentiment' in work.text_analysis:
                    sentiment = work.text_analysis['sentiment']
                    print(f"  Sentiment: {sentiment.get('sentiment', 'Unknown')}")
                
                if 'themes' in work.text_analysis:
                    themes = work.text_analysis['themes']
                    if 'themes' in themes:
                        print(f"  Detected themes: {themes['themes']}")
    except Exception as e:
        print(f"Error getting work details: {e}")
    
    print("\nAdvanced analysis examples completed!")


if __name__ == "__main__":
    asyncio.run(main())

