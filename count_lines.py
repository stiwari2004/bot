#!/usr/bin/env python3
"""Simple line counter that won't hang on large files"""
import os
import sys
from pathlib import Path

def count_lines(file_path):
    """Count lines in a file efficiently"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception as e:
        return f"Error: {e}"

def main():
    if len(sys.argv) < 2:
        print("Usage: python count_lines.py <directory>")
        sys.exit(1)
    
    directory = sys.argv[1]
    if not os.path.exists(directory):
        print(f"Directory not found: {directory}")
        sys.exit(1)
    
    print(f"\nLine counts for Python files in: {directory}\n")
    print(f"{'File':<50} {'Lines':>10}")
    print("-" * 62)
    
    total_lines = 0
    file_count = 0
    
    for root, dirs, files in os.walk(directory):
        # Skip __pycache__ and .git directories
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules']]
        
        for file in sorted(files):
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, directory)
                lines = count_lines(file_path)
                
                if isinstance(lines, int):
                    print(f"{rel_path:<50} {lines:>10}")
                    total_lines += lines
                    file_count += 1
                else:
                    print(f"{rel_path:<50} {str(lines):>10}")
    
    print("-" * 62)
    print(f"{'TOTAL':<50} {total_lines:>10}")
    print(f"\nFiles: {file_count}")

if __name__ == "__main__":
    main()




