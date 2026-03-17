"""
Ticketing Connection Controller — manage connections to external ticketing tools
"""
import json
from typing import Optional, Dict, Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.ticketing_tool_connection import TicketingToolConnection
from app.repositories.ticketing_connection_repository import TicketingConnectionRepository
from app.controllers.ticketing_connection_test_mixin import TicketingConnectionTestMixin
from app.controllers.ticketing_connection_oauth_mixin import TicketingConnectionOAuthMixin

logger = get_logger(__name__)


class TicketingConnectionController(TicketingConnectionTestMixin, TicketingConnectionOAuthMixin):
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.connection_repo = TicketingConnectionRepository(db)

    # ── CRUD ─────────────────────────────────────────────────────────────

    def create_connection(self, connection_data) -> dict:
        db = self.db
        tenant_id = self.tenant_id

        existing = db.query(TicketingToolConnection).filter(
            TicketingToolConnection.tenant_id == tenant_id,
            TicketingToolConnection.tool_name == connection_data.tool_name,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Connection for {connection_data.tool_name} already exists")

        meta_data = dict(connection_data.meta_data) if connection_data.meta_data else {}

        if connection_data.tool_name == "zoho" and connection_data.client_id:
            meta_data.update({
                "client_id": connection_data.client_id,
                "client_secret": connection_data.client_secret,
                "redirect_uri": connection_data.redirect_uri or "",
            })
        elif connection_data.tool_name == "manageengine":
            from app.core.config import settings
            version = self._resolve_manageengine_version(connection_data.meta_data)
            if version == "v2" and connection_data.client_id:
                meta_data.update({
                    "client_id": connection_data.client_id,
                    "client_secret": connection_data.client_secret,
                    "redirect_uri": connection_data.redirect_uri or settings.OAUTH_CALLBACK_URL,
                    "version": "v2",
                })
            else:
                meta_data.setdefault("version", "v3")

        if connection_data.tool_name == "servicenow":
            if connection_data.api_username and connection_data.api_password:
                meta_data["username"] = connection_data.api_username
                meta_data["password"] = connection_data.api_password

        db_connection = TicketingToolConnection(
            tenant_id=tenant_id,
            tool_name=connection_data.tool_name,
            connection_type=connection_data.connection_type,
            webhook_url=connection_data.webhook_url,
            webhook_secret=connection_data.webhook_secret,
            api_base_url=connection_data.api_base_url,
            api_key=connection_data.api_key,
            api_username=connection_data.api_username,
            api_password=connection_data.api_password,
            sync_interval_minutes=connection_data.sync_interval_minutes,
            meta_data=json.dumps(meta_data) if meta_data else None,
            is_active=True,
        )
        db.add(db_connection)
        db.commit()
        db.refresh(db_connection)
        return {
            "id": db_connection.id,
            "tool_name": db_connection.tool_name,
            "connection_type": db_connection.connection_type,
            "is_active": db_connection.is_active,
            "webhook_url": db_connection.webhook_url,
            "message": "Ticketing tool connection created successfully",
        }

    def list_connections(self) -> dict:
        connections = self.connection_repo.list_for_tenant(self.tenant_id)
        result = []
        for c in connections:
            meta_data = self._parse_meta_data(c.meta_data)
            oauth_authorized, oauth_supported = self._oauth_status(c, meta_data)
            result.append({
                "id": c.id, "tool_name": c.tool_name, "connection_type": c.connection_type,
                "is_active": c.is_active, "webhook_url": c.webhook_url, "api_base_url": c.api_base_url,
                "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
                "last_sync_status": c.last_sync_status, "last_error": c.last_error,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "oauth_authorized": oauth_authorized, "oauth_supported": oauth_supported,
            })
        return {"connections": result}

    def get_connection(self, connection_id: int) -> dict:
        connection = self._fetch(connection_id)
        meta_data = self._parse_meta_data(connection.meta_data)
        oauth_authorized, oauth_supported = self._oauth_status(connection, meta_data)
        return {
            "id": connection.id, "tool_name": connection.tool_name,
            "connection_type": connection.connection_type, "is_active": connection.is_active,
            "webhook_url": connection.webhook_url, "api_base_url": connection.api_base_url,
            "last_sync_at": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
            "last_sync_status": connection.last_sync_status, "last_error": connection.last_error,
            "created_at": connection.created_at.isoformat() if connection.created_at else None,
            "oauth_authorized": oauth_authorized, "oauth_supported": oauth_supported,
        }

    def update_connection(self, connection_id: int, update_data) -> dict:
        db = self.db
        connection = self._fetch(connection_id)

        for field in ("is_active", "webhook_url", "webhook_secret", "api_base_url",
                      "api_key", "api_username", "api_password", "sync_interval_minutes"):
            value = getattr(update_data, field, None)
            if value is not None:
                setattr(connection, field, value)

        existing_meta = None
        if update_data.meta_data is not None:
            existing_meta = self._parse_meta_data(connection.meta_data)
            existing_meta.update(update_data.meta_data)
            connection.meta_data = json.dumps(existing_meta)

        if connection.tool_name == "servicenow":
            if existing_meta is None:
                existing_meta = self._parse_meta_data(connection.meta_data)
            updated = False
            if getattr(update_data, "api_username", None) is not None:
                existing_meta["username"] = update_data.api_username
                updated = True
            if getattr(update_data, "api_password", None) is not None:
                existing_meta["password"] = update_data.api_password
                updated = True
            if updated:
                connection.meta_data = json.dumps(existing_meta)

        db.commit()
        db.refresh(connection)
        return {
            "id": connection.id, "tool_name": connection.tool_name,
            "connection_type": connection.connection_type, "is_active": connection.is_active,
            "message": "Connection updated successfully",
        }

    def delete_connection(self, connection_id: int) -> dict:
        connection = self._fetch(connection_id)
        self.db.delete(connection)
        self.db.commit()
        return {"message": "Connection deleted successfully"}

    # ── Private helpers ───────────────────────────────────────────────────

    def _fetch(self, connection_id: int) -> TicketingToolConnection:
        connection = self.connection_repo.get_by_id_and_tenant(connection_id, self.tenant_id)
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        return connection

    @staticmethod
    def _parse_meta_data(raw: Any) -> Dict[str, Any]:
        if raw is None:
            return {}
        if isinstance(raw, dict):
            return raw
        if not isinstance(raw, str) or not raw.strip():
            return {}
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            logger.warning("Invalid ticketing connection meta_data JSON, using empty dict")
            return {}

    @staticmethod
    def _resolve_manageengine_version(meta_data_field) -> str:
        version = None
        if isinstance(meta_data_field, dict):
            version = meta_data_field.get("version")
        elif isinstance(meta_data_field, str):
            try:
                version = json.loads(meta_data_field).get("version")
            except Exception:
                pass
        return version or "v2"

    @staticmethod
    def _oauth_status(c: TicketingToolConnection, meta_data: Dict[str, Any]):
        oauth_authorized = False
        oauth_supported = False
        if c.tool_name == "zoho":
            oauth_supported = True
            oauth_authorized = bool(meta_data.get("access_token"))
        elif c.tool_name == "manageengine":
            version = str(meta_data.get("version", "v2")).lower()
            if version == "v2":
                oauth_supported = True
                oauth_authorized = bool(meta_data.get("access_token"))
        elif c.tool_name == "servicenow":
            has_username = bool(meta_data.get("username") or c.api_username)
            has_password = bool(meta_data.get("password") or c.api_password)
            has_oauth = bool(meta_data.get("client_id") and meta_data.get("client_secret"))
            oauth_authorized = (has_username and has_password) or has_oauth
        return oauth_authorized, oauth_supported

    def _sync_servicenow_credentials(self, connection: TicketingToolConnection, meta_data: Dict[str, Any]) -> bool:
        if connection.tool_name != "servicenow":
            return False
        synced = False
        if not meta_data.get("username") and connection.api_username:
            meta_data["username"] = connection.api_username
            synced = True
        if not meta_data.get("password") and connection.api_password:
            meta_data["password"] = connection.api_password
            synced = True
        if synced:
            connection.meta_data = json.dumps(meta_data)
            self.db.commit()
        return synced


def get_ticketing_connection_controller(db: Session, tenant_id: int) -> TicketingConnectionController:
    return TicketingConnectionController(db, tenant_id)
