#!/usr/bin/env python3
"""
Installation script for Troubleshooting RAG System
"""

import subprocess
import sys
import os

def run_command(command):
    """Run a command and return success status"""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {command}")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Install dependencies"""
    print("Installing Troubleshooting RAG System dependencies...")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("Error: Python 3.7 or higher is required")
        return 1
    
    print(f"Python version: {sys.version}")
    
    # Upgrade pip first
    print("\n1. Upgrading pip...")
    run_command(f"{sys.executable} -m pip install --upgrade pip")
    
    # Install dependencies
    print("\n2. Installing dependencies...")
    success = run_command(f"{sys.executable} -m pip install -r requirements.txt")
    
    if success:
        print("\n✓ Installation completed successfully!")
        print("\nYou can now run the application with:")
        print("  python3 run.py")
        print("\nOr create sample data first:")
        print("  python3 main.py --create-sample")
        return 0
    else:
        print("\n✗ Installation failed!")
        print("\nTry installing dependencies manually:")
        print("  pip3 install --upgrade pip")
        print("  pip3 install sentence-transformers>=2.5.0")
        print("  pip3 install chromadb>=0.4.18")
        print("  pip3 install pandas>=1.5.0")
        print("  pip3 install pyyaml>=6.0")
        return 1

if __name__ == "__main__":
    sys.exit(main())
