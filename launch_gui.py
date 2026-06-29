#!/usr/bin/env python3
"""
Blake GUI Launcher

Convenient script to launch the Streamlit GUI from the project root.
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Launch the Blake works exploration GUI."""
    project_root = Path(__file__).parent
    gui_path = project_root / "blake" / "gui" / "gui.py"
    
    if not gui_path.exists():
        print(f"Error: GUI file not found at {gui_path}")
        sys.exit(1)
    
    print("🚀 Launching Blake Works Explorer...")
    print("   Open http://localhost:8501 in your browser")
    print()
    
    # Run streamlit with the GUI script
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        str(gui_path),
        "--server.headless", "true"
    ])


if __name__ == "__main__":
    main()
