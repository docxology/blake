#!/usr/bin/env python3
"""
Interactive Orchestrator Demo

Demonstrates the capabilities of the Blake Interactive Orchestrator.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from blake.interactive_orchestrator import InteractiveOrchestrator


async def demo_interactive_orchestrator():
    """Demo the interactive orchestrator capabilities."""
    print("🎨 Blake Interactive Orchestrator Demo")
    print("=" * 50)
    
    # Initialize orchestrator
    orchestrator = InteractiveOrchestrator("./demo_data")
    
    try:
        # Initialize the system
        print("1. Initializing Blake system...")
        await orchestrator.initialize()
        print("✅ System initialized successfully!")
        
        # Show welcome screen
        print("\n2. Displaying welcome screen...")
        orchestrator.display_welcome()
        
        # Show main menu
        print("\n3. Displaying main menu...")
        orchestrator.display_main_menu()
        
        # Demo downloading works
        print("\n4. Demo: Downloading works...")
        await orchestrator.download_all_works()
        
        # Demo viewing works
        print("\n5. Demo: Viewing available works...")
        await orchestrator.view_available_works()
        
        # Demo search
        print("\n6. Demo: Searching works...")
        # Simulate search without user input
        print("   (Search demo would require user input)")
        
        # Demo analysis
        print("\n7. Demo: Running text analysis...")
        await orchestrator.run_text_analysis()
        
        # Demo visualizations
        print("\n8. Demo: Creating visualizations...")
        await orchestrator.create_visualizations()
        
        # Demo dashboards
        print("\n9. Demo: Viewing dashboards...")
        await orchestrator.view_dashboards()
        
        # Demo reports
        print("\n10. Demo: Generating reports...")
        await orchestrator.generate_reports()
        
        print("\n✅ Demo completed successfully!")
        print("\nTo use the full interactive experience, run:")
        print("  python blake_interactive.py")
        print("  or")
        print("  blake interactive")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(demo_interactive_orchestrator())

