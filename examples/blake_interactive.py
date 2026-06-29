#!/usr/bin/env python3
"""
Blake Interactive Orchestrator

A standalone script to launch the interactive terminal orchestrator.
This provides a user-friendly interface for managing the Blake system.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Main entry point."""
    try:
        from blake.interactive_orchestrator import InteractiveOrchestrator
        
        # Parse command line arguments
        data_dir = "./blake_data"
        if len(sys.argv) > 1:
            data_dir = sys.argv[1]
        
        print(f"🚀 Starting Blake Interactive Orchestrator...")
        print(f"📁 Data directory: {data_dir}")
        print()
        
        orchestrator = InteractiveOrchestrator(data_dir)
        asyncio.run(orchestrator.run())
        
    except ImportError as e:
        print(f"❌ Failed to import required modules: {e}")
        print("Please install required dependencies:")
        print("  pip install rich")
        print("  pip install -e .")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

