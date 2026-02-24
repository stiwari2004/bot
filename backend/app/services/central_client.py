"""
Central Resolvify API client for PaaS/edge deployments.

When DEPLOYMENT_MODE=paas and CENTRAL_SERVER_URL is set, the edge (jump server)
uses this client to:
- Validate tenant-admin/MSP login against central (Phase 2)
- Sync user details to central for billing (Phase 3)

All calls use httpx with timeout and log failures; no auth to central
until CENTRAL_API_KEY is configured (same key as central's PAAS_EDGE_API_KEY).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Timeout for central API calls (seconds)
CENTRAL_REQUEST_TIMEOUT = 15.0


def _base_url() -> Optional[str]:
    """Central base URL without trailing slash, or None if not configured."""
    url = getattr(settings, "CENTRAL_SERVER_URL", None) or ""
    url = (url or "").strip()
    return url.rstrip("/") if url else None


def _headers() -> Dict[str, str]:
    """Headers for central API requests (API key if set)."""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    api_key = getattr(settings, "CENTRAL_API_KEY", None) or ""
    if (api_key or "").strip():
        headers["X-Paas-API-Key"] = api_key.strip()
    return headers


def validate_paas_login(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Validate tenant-admin/MSP credentials against central Resolvify.

    Calls POST {CENTRAL_SERVER_URL}/api/v1/paas/validate-login with
    username/password. On success returns the JSON body (user, tenant, limits).
    On failure or if central is not configured, returns None.

    Used by the edge login flow when DEPLOYMENT_MODE=paas and CENTRAL_SERVER_URL
    is set (Phase 2).
    """
    base = _base_url()
    if not base:
        logger.debug("Central server not configured (CENTRAL_SERVER_URL); skipping validate_paas_login")
        return None

    url = f"{base}/api/v1/paas/validate-login"
    payload = {"username": email, "password": password}

    try:
        with httpx.Client(timeout=CENTRAL_REQUEST_TIMEOUT) as client:
            response = client.post(url, json=payload, headers=_headers())
        if response.status_code != 200:
            try:
                body = response.text[:500] if response.text else ""
            except Exception:
                body = ""
            logger.warning(
                "Central validate-login returned status=%s for email=%s body=%s",
                response.status_code,
                email,
                body,
            )
            return None
        data = response.json()
        if not isinstance(data, dict):
            logger.warning("Central validate-login returned non-dict body")
            return None
        return data
    except httpx.TimeoutException as e:
        logger.warning("Central validate-login timeout for %s: %s", email, e)
        return None
    except httpx.RequestError as e:
        logger.warning("Central validate-login request error for %s: %s", email, e)
        return None
    except Exception as e:
        logger.exception("Central validate_paas_login unexpected error: %s", e)
        return None


def sync_users_for_billing(tenant_id: int, users: List[Dict[str, Any]]) -> bool:
    """
    Sync user details to central for billing.

    POSTs to {CENTRAL_SERVER_URL}/api/v1/paas/billing/sync-users with
    tenant_id and list of user payloads (id, email, full_name, role, etc.).
    Returns True on 2xx, False otherwise. Logs failures.

    Called by the edge after creating/updating users (Phase 3).
    """
    base = _base_url()
    if not base:
        logger.debug("Central server not configured; skipping sync_users_for_billing")
        return False

    url = f"{base}/api/v1/paas/billing/sync-users"
    payload = {"tenant_id": tenant_id, "users": users}

    try:
        with httpx.Client(timeout=CENTRAL_REQUEST_TIMEOUT) as client:
            response = client.post(url, json=payload, headers=_headers())
        if response.status_code >= 200 and response.status_code < 300:
            logger.debug("Central sync-users succeeded for tenant_id=%s, count=%s", tenant_id, len(users))
            return True
        logger.warning(
            "Central sync-users returned status=%s for tenant_id=%s: %s",
            response.status_code,
            tenant_id,
            response.text[:200] if response.text else "",
        )
        return False
    except httpx.TimeoutException as e:
        logger.warning("Central sync-users timeout for tenant_id=%s: %s", tenant_id, e)
        return False
    except httpx.RequestError as e:
        logger.warning("Central sync-users request error for tenant_id=%s: %s", tenant_id, e)
        return False
    except Exception as e:
        logger.exception("Central sync_users_for_billing unexpected error: %s", e)
        return False


def is_central_connected() -> bool:
    """Return True if this instance is configured to use central (PaaS edge)."""
    base = _base_url()
    mode = (getattr(settings, "DEPLOYMENT_MODE", "") or "").lower()
    return bool(base and mode == "paas")
