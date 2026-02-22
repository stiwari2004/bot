#!/usr/bin/env python3
"""
Standalone script to test SSH connectivity from the same environment as the worker.
Run inside the worker container or on the host to isolate network vs code issues.

Usage:
  # From host (if worker uses docker network):
  docker exec -it bot-dev-worker python3 /app/scripts/diagnose_ssh.py 192.168.48.10 YOUR_USERNAME YOUR_PASSWORD

  # Or copy and run with your values:
  python3 diagnose_ssh.py 192.168.48.10 myuser mypass

  # With port:
  python3 diagnose_ssh.py 192.168.48.10 myuser mypass --port 22
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Test SSH connectivity (Paramiko)")
    parser.add_argument("host", help="Target host (IP or hostname)")
    parser.add_argument("username", help="SSH username")
    parser.add_argument("password", help="SSH password")
    parser.add_argument("--port", type=int, default=22, help="SSH port (default: 22)")
    parser.add_argument("--timeout", type=int, default=15, help="Connect timeout seconds (default: 15)")
    args = parser.parse_args()

    print("=" * 60)
    print("SSH connectivity diagnostic")
    print("=" * 60)
    print(f"Host:     {args.host}")
    print(f"Port:     {args.port}")
    print(f"Username: {args.username}")
    print(f"Password: {'[SET]' if args.password else '[EMPTY]'} ({len(args.password)} chars)")
    print(f"Timeout:  {args.timeout}s")
    print("=" * 60)

    try:
        import paramiko
    except ImportError as e:
        print(f"ERROR: Paramiko not installed: {e}")
        sys.exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print("Connecting...")
        client.connect(
            hostname=args.host,
            port=args.port,
            username=args.username,
            password=args.password,
            timeout=args.timeout,
            banner_timeout=args.timeout,
            auth_timeout=args.timeout,
            look_for_keys=False,
            allow_agent=False,
        )
        print("OK: SSH connection established")

        stdin, stdout, stderr = client.exec_command("echo ok", timeout=5)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        code = stdout.channel.recv_exit_status()
        print(f"OK: Command echo ok -> exit_code={code} output='{out}' stderr='{err}'")
        client.close()
        sys.exit(0)

    except Exception as e:
        exc_type = type(e).__name__
        exc_msg = str(e)
        print(f"FAIL: {exc_type}: {exc_msg}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
