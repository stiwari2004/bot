"""
Shared client to POST discovery asset payloads to the Resolvify ingest API.
Used by the host agent, network scanner, and storage scanner.
"""
import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


def post_asset(
    ingest_url: str,
    token: str,
    asset: Dict[str, Any],
    run_id: Optional[int] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    POST a single asset to the ingest endpoint.
    Returns {"ok": True} on success or raises / returns error info.
    """
    payload = {"asset": asset}
    if run_id is not None:
        payload["run_id"] = run_id
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
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"ok": False, "raw": raw}


def post_assets_batch(
    ingest_url: str,
    token: str,
    assets: list,
    run_id: Optional[int] = None,
    timeout: int = 30,
) -> list:
    """
    POST each asset one by one. Returns list of results (one per asset).
    """
    results = []
    for asset in assets:
        try:
            out = post_asset(ingest_url, token, asset, run_id=run_id, timeout=timeout)
            results.append({"asset": asset.get("source_native_id"), "result": out})
        except urllib.error.HTTPError as e:
            results.append({
                "asset": asset.get("source_native_id"),
                "result": {"ok": False, "error": f"HTTP {e.code}", "body": e.read().decode("utf-8")[:500]},
            })
        except Exception as e:
            results.append({"asset": asset.get("source_native_id"), "result": {"ok": False, "error": str(e)}})
    return results
