import os
import sys

def count_lines(filepath):
    try:
        with open(filepath, 'rb') as f:
            return len(f.readlines())
    except:
        return 0

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python count_lines_simple.py <file_or_dir>")
        sys.exit(1)
    
    path = sys.argv[1]
    if os.path.isfile(path):
        print(f"{os.path.basename(path)}: {count_lines(path)} lines")
    elif os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules', '.next']]
            for f in sorted(files):
                if f.endswith('.py'):
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, path)
                    lines = count_lines(full_path)
                    print(f"{rel_path}: {lines} lines")
    else:
        print(f"Path not found: {path}")



