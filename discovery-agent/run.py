#!/usr/bin/env python3
"""
Entry point for discovery. Run via ./discover (recommended) so deps install into
a venv and avoid system "externally-managed-environment" errors.

  ./discover                                    # use config.yaml
  ./discover "https://.../ingest" YOUR_TOKEN    # no config file; uses env

Or with existing venv:  .venv/bin/python run.py [config.yaml]
"""
import os
import sys

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Run the unified discovery runner (no pip install here; use ./discover for that)
    import run_discovery
    return run_discovery.main()

if __name__ == "__main__":
    sys.exit(main())
