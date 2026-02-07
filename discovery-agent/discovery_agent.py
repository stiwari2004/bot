#!/usr/bin/env python3
"""
Resolvify Discovery Agent: collect host identity and optional components, POST to ingest.
Configure via environment or .env:
  DISCOVERY_INGEST_URL  - e.g. https://your-app.example.com/api/v1/tenant-admin/discovery/ingest
  DISCOVERY_TOKEN      - token from Tenant Admin → Discovery → Generate token
  DISCOVERY_RUN_ID      - (optional) run ID; if omitted, backend creates a run for you
"""
import json
import os
import platform
import socket
import sys
import urllib.error
import urllib.request


def get_hostname() -> str:
    try:
        return socket.gethostname() or "unknown"
    except Exception:
        return "unknown"


def get_primary_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass
    try:
        return socket.gethostbyname(socket.gethostname()) or "127.0.0.1"
    except Exception:
        return "127.0.0.1"


def get_all_ips() -> list:
    ips = []
    try:
        host = socket.gethostname()
        for info in socket.getaddrinfo(host, None, socket.AF_INET):
            ip = info[4][0]
            if ip and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    primary = get_primary_ip()
    if primary and primary not in ips:
        ips.insert(0, primary)
    return ips or [get_primary_ip()]


def build_asset_payload() -> dict:
    hostname = get_hostname()
    primary_ip = get_primary_ip()
    ips = get_all_ips()
    os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
    source_native_id = f"{hostname}:{primary_ip}"
    return {
        "source": "discovery_agent",
        "source_native_id": source_native_id,
        "fingerprint": hostname,
        "name": hostname,
        "primary_ip": primary_ip,
        "ips": ips,
        "tags": {
            "os": os_info,
            "python": platform.python_version(),
        },
    }


def main() -> int:
    ingest_url = os.environ.get("DISCOVERY_INGEST_URL", "").strip()
    token = os.environ.get("DISCOVERY_TOKEN", "").strip()
    run_id = os.environ.get("DISCOVERY_RUN_ID", "").strip()

    if not ingest_url or not token:
        print("Set DISCOVERY_INGEST_URL and DISCOVERY_TOKEN.", file=sys.stderr)
        print("Example: DISCOVERY_INGEST_URL=https://app.example.com/api/v1/tenant-admin/discovery/ingest DISCOVERY_TOKEN=your-token python discovery_agent.py", file=sys.stderr)
        return 1

    asset = build_asset_payload()
    payload = {"asset": asset}
    if run_id:
        try:
            payload["run_id"] = int(run_id)
        except ValueError:
            print("DISCOVERY_RUN_ID must be an integer; ignoring.", file=sys.stderr)

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ingest_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Discovery-Token": token,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            code = resp.getcode()
            raw = resp.read().decode("utf-8")
            try:
                data = json.loads(raw)
                print(json.dumps(data, indent=2))
            except json.JSONDecodeError:
                print(raw)
            return 0 if 200 <= code < 300 else 1
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.reason}", file=sys.stderr)
        try:
            print(e.read().decode("utf-8"), file=sys.stderr)
        except Exception:
            pass
        return 1
    except urllib.error.URLError as e:
        print(f"Request failed: {e.reason}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
