#!/usr/bin/env python3
"""
Simple runner for Troubleshooting RAG System
"""

import sys
import os

# Check Python version
if sys.version_info < (3, 7):
    print("Error: Python 3.7 or higher is required")
    sys.exit(1)

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from main import main
except ImportError as e:
    print(f"Error importing main module: {e}")
    print("Please make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)

if __name__ == "__main__":
    main()
