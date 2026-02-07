"""
Storage / SAN / NAS scanner: discover arrays and NAS via vendor REST APIs or generic REST.
Runs from a central host.
"""
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

SOURCE = "storage_scanner"


def _http_get(url: str, timeout: int = 15, verify_ssl: bool = True) -> Optional[dict]:
    """GET URL, return JSON dict or None."""
    req = urllib.request.Request(url)
    ctx = ssl.create_default_context() if verify_ssl else ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(url, timeout=timeout, context=ctx) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError):
        return None


def _http_post_form(url: str, data: dict, timeout: int = 15, verify_ssl: bool = True) -> Optional[dict]:
    """POST form data, return JSON dict or None."""
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    ctx = ssl.create_default_context() if verify_ssl else ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError):
        return None


def discover_synology(
    host: str,
    username: str,
    password: str,
    port: int = 5001,
    use_https: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Discover one Synology NAS via DSM API (login + SYNO.Core.System).
    Returns one asset dict for the NAS.
    """
    scheme = "https" if use_https else "http"
    base = f"{scheme}://{host}:{port}/webapi"
    login_url = f"{base}/auth.cgi"
    login_data = {
        "api": "SYNO.API.Auth",
        "version": "3",
        "method": "login",
        "account": username,
        "passwd": password,
        "format": "sid",
    }
    resp = _http_post_form(login_url, login_data, verify_ssl=use_https)
    if not resp or not resp.get("success"):
        return None
    sid = resp.get("data", {}).get("sid")
    if not sid:
        return None
    # System info
    info_url = f"{base}/entry.cgi?api=SYNO.Core.System&version=1&method=info"
    # Sid must be in query for some DSM versions
    info_url += f"&_sid={sid}"
    info_req = urllib.request.Request(info_url)
    ctx = ssl.create_default_context() if use_https else ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(info_req, timeout=15, context=ctx) as r:
            info = json.loads(r.read().decode("utf-8"))
    except Exception:
        info = {}
    data = (info.get("data") or {})
    name = data.get("model") or data.get("hostname") or host
    serial = data.get("serial") or ""
    source_native_id = f"{host}:{name}:{serial}" if serial else f"{host}:{name}"
    tags = {"vendor": "synology", "model": data.get("model", ""), "serial": serial}
    return {
        "source": SOURCE,
        "source_native_id": source_native_id,
        "fingerprint": name,
        "name": name,
        "primary_ip": host,
        "ips": [host],
        "tags": tags,
    }


def discover_generic_rest(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    items_path: Optional[str] = None,
    name_key: str = "name",
    id_key: str = "id",
    ip_key: Optional[str] = "ip",
    timeout: int = 15,
    verify_ssl: bool = True,
) -> List[Dict[str, Any]]:
    """
    Call a REST URL and interpret the response as a list of assets.
    - If items_path is set (e.g. "data.hosts"), walk into that path to get the list.
    - Otherwise assume the root is a list.
    Each item should have name_key and id_key; optional ip_key.
    Returns list of asset dicts.
    """
    req = urllib.request.Request(url, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    ctx = ssl.create_default_context() if verify_ssl else ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []
    if items_path:
        for part in items_path.split("."):
            data = (data or {}).get(part)
        if not isinstance(data, list):
            data = [data] if data is not None else []
    elif not isinstance(data, list):
        data = [data] if data is not None else []
    assets = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        name = item.get(name_key) or item.get("hostname") or f"storage-{i}"
        native_id = item.get(id_key) or item.get("serial") or f"{name}-{i}"
        ip = item.get(ip_key) if ip_key else None
        primary_ip = ip or "0.0.0.0"
        source_native_id = f"rest:{native_id}"
        tags = {"vendor": "generic_rest", "raw_id": str(native_id)}
        assets.append({
            "source": SOURCE,
            "source_native_id": source_native_id,
            "fingerprint": str(native_id),
            "name": str(name),
            "primary_ip": primary_ip,
            "ips": [primary_ip] if primary_ip != "0.0.0.0" else [],
            "tags": tags,
        })
    return assets


def scan_storage_targets(targets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Scan storage/NAS targets. Each target can be:
    - type: synology -> host, username, password, port?, use_https?
    - type: generic_rest -> url, method?, headers?, items_path?, name_key?, id_key?, ip_key?
    Returns list of asset dicts.
    """
    assets = []
    for t in targets:
        kind = (t.get("type") or "synology").lower()
        if kind == "synology":
            a = discover_synology(
                host=t.get("host", ""),
                username=t.get("username", "admin"),
                password=t.get("password", ""),
                port=int(t.get("port", 5001)),
                use_https=bool(t.get("use_https", True)),
            )
            if a:
                assets.append(a)
        elif kind == "generic_rest":
            for a in discover_generic_rest(
                url=t.get("url", ""),
                method=t.get("method", "GET"),
                headers=t.get("headers"),
                items_path=t.get("items_path"),
                name_key=t.get("name_key", "name"),
                id_key=t.get("id_key", "id"),
                ip_key=t.get("ip_key"),
                timeout=int(t.get("timeout", 15)),
                verify_ssl=bool(t.get("verify_ssl", True)),
            ):
                assets.append(a)
    return assets
