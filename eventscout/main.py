"""
Main entry point for EventScout Multi-Source Scraper Pipeline.
"""

import sys
from pathlib import Path

parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from main import main

if __name__ == "__main__":
    main()
