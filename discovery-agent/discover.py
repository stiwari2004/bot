#!/usr/bin/env python3
"""
One-command discovery: creates venv, installs deps, runs scan.
Usage:
  python3 discover.py                                    # uses config.yaml
  python3 discover.py "https://app/api/.../ingest" TOKEN # no config file needed
"""
import os
import sys
import subprocess

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    venv_dir = os.path.join(script_dir, ".venv")
    # Windows: venv uses Scripts/, Linux/macOS: bin/
    if sys.platform == "win32":
        python = os.path.join(venv_dir, "Scripts", "python.exe")
        pip = os.path.join(venv_dir, "Scripts", "pip.exe")
    else:
        python = os.path.join(venv_dir, "bin", "python")
        pip = os.path.join(venv_dir, "bin", "pip")
    
    # Create venv if missing
    if not os.path.isfile(python):
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
    
    # Install deps into venv (no sudo). --no-cache-dir reduces memory use on small systems.
    reqs = os.path.join(script_dir, "requirements.txt")
    if os.path.isfile(reqs):
        env = os.environ.copy()
        env["PIP_NO_CACHE_DIR"] = "1"
        subprocess.run(
            [pip, "install", "-q", "--no-cache-dir", "-r", reqs],
            check=False,
            env=env,
        )
    
    # Optional: pass INGEST_URL and TOKEN as first two args (no config file needed)
    if len(sys.argv) >= 3:
        os.environ["DISCOVERY_INGEST_URL"] = sys.argv[1]
        os.environ["DISCOVERY_TOKEN"] = sys.argv[2]
        args = sys.argv[3:]
    else:
        args = sys.argv[1:]
    
    # Auto-discover servers from /etc/hosts and ~/.ssh/known_hosts when running on jump server
    # Set DISCOVERY_AUTO_SCAN=0 to disable
    if "DISCOVERY_AUTO_SCAN" not in os.environ:
        os.environ["DISCOVERY_AUTO_SCAN"] = "1"
    
    # Run discovery
    sys.exit(subprocess.run([python, "run.py"] + args).returncode)

if __name__ == "__main__":
    main()
