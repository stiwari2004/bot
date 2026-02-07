#!/usr/bin/env python3
"""
Single-command entry point: install dependencies if needed, then run full discovery
(agent + network + storage). Works on Windows, Linux, and macOS.

  python run.py
  python3 run.py
"""
import os
import subprocess
import sys

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    reqs = os.path.join(script_dir, "requirements.txt")
    if os.path.isfile(reqs):
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
            cwd=script_dir,
            check=False,
        )

    # Run the unified discovery runner
    import run_discovery
    return run_discovery.main()

if __name__ == "__main__":
    sys.exit(main())
