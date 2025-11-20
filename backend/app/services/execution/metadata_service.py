"""
Metadata service for preparing and sanitizing execution metadata
"""
import copy
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.services.credential_service import get_credential_service

logger = get_logger(__name__)


class MetadataService:
    """Service for preparing and sanitizing execution metadata"""
    
    def __init__(self):
        self.credential_service = get_credential_service()
    
    def prepare_metadata(
        self,
        *,
        db: Session,
        tenant_id: int,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Return metadata enriched with resolved credentials while avoiding mutation."""
        if not metadata:
            return {}
        
        prepared = copy.deepcopy(metadata)
        if prepared.get("credentials") and not prepared.get("credential_source"):
            prepared["credential_source"] = "inline"
        
        credential_source = prepared.get("credential_source")
        if isinstance(credential_source, str) and credential_source.strip():
            prepared = self._apply_credential_source(db, tenant_id, prepared, credential_source)
        
        return prepared
    
    def _apply_credential_source(
        self,
        db: Session,
        tenant_id: int,
        metadata: Dict[str, Any],
        credential_source: str,
    ) -> Dict[str, Any]:
        source = credential_source.strip()
        lower_source = source.lower()
        
        if lower_source.startswith("alias:"):
            alias_reference = source.split(":", 1)[1].strip()
            if not alias_reference:
                raise ValueError("Credential alias provided but empty.")
            return self._hydrate_alias_credentials(db, tenant_id, metadata, alias_reference)
        
        return metadata
    
    def _hydrate_alias_credentials(
        self,
        db: Session,
        tenant_id: int,
        metadata: Dict[str, Any],
        alias_reference: str,
    ) -> Dict[str, Any]:
        alias_name, alias_environment = self._parse_alias_reference(alias_reference)
        environment_hint = (
            metadata.get("environment")
            or metadata.get("target", {}).get("environment")
            or alias_environment
        )
        credential = self.credential_service.resolve_alias(
            db=db,
            tenant_id=tenant_id,
            alias=alias_name,
            environment=environment_hint,
        )
        if not credential:
            raise ValueError(f"Credential alias '{alias_reference}' not found.")
        
        self.credential_service.log_credential_usage(
            tenant_id=tenant_id,
            alias=alias_name,
        )
        
        credentials_block = metadata.setdefault("credentials", {})
        
        def merge_if_missing(target: Dict[str, Any], key: str, value: Any) -> None:
            if value is None:
                return
            if key not in target or target[key] in (None, ""):
                target[key] = value
        
        merge_fields = {
            "username": credential.get("username"),
            "password": credential.get("password"),
            "api_key": credential.get("api_key"),
            "private_key": credential.get("private_key"),
            "domain": credential.get("domain"),
        }
        
        metadata_payload = credential.get("metadata") or {}
        for extra_key in (
            "access_key",
            "secret_key",
            "session_token",
            "client_id",
            "client_secret",
            "certificate",
            "keytab",
            "passphrase",
            "tenant",
        ):
            if extra_key not in merge_fields:
                merge_fields[extra_key] = metadata_payload.get(extra_key)
        
        for key, value in (credential.get("secrets") or {}).items():
            if key not in merge_fields:
                merge_fields[key] = value
        
        for key, value in merge_fields.items():
            merge_if_missing(credentials_block, key, value)
        
        metadata["credential_alias"] = credential.get("alias", alias_name)
        metadata["credential_source"] = f"alias:{credential.get('alias', alias_name)}"
        metadata.setdefault("credential_resolved", {})
        metadata["credential_resolved"].update(
            {
                "alias": credential.get("alias", alias_name),
                "type": credential.get("type"),
                "environment": credential.get("environment") or environment_hint,
                "source": credential.get("source", "alias"),
                "credential_id": credential.get("credential_id"),
            }
        )
        if credential.get("rotated_at"):
            metadata["credential_resolved"]["rotated_at"] = credential["rotated_at"]
        
        connection_block = metadata.setdefault("connection", {})
        merge_if_missing(connection_block, "host", credential.get("host"))
        merge_if_missing(connection_block, "port", credential.get("port"))
        
        target_block = metadata.setdefault("target", {})
        merge_if_missing(target_block, "host", credential.get("host"))
        merge_if_missing(target_block, "port", credential.get("port"))
        merge_if_missing(target_block, "environment", credential.get("environment"))
        
        return metadata
    
    @staticmethod
    def _parse_alias_reference(alias: str) -> Tuple[str, Optional[str]]:
        value = alias.strip()
        if not value:
            return "", None
        
        if "@" in value:
            name, environment = value.split("@", 1)
            return name.strip(), environment.strip() or None
        if "/" in value:
            environment, name = value.split("/", 1)
            return name.strip(), environment.strip() or None
        if ":" in value:
            environment, name = value.split(":", 1)
            if environment and name:
                return name.strip(), environment.strip() or None
        return value, None
    
    def sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Return a redacted copy of metadata suitable for emitting to clients."""
        if not metadata:
            return {}
        
        sensitive_exact = {
            "password",
            "secret",
            "token",
            "api_key",
            "access_key",
            "secret_key",
            "session_token",
            "private_key",
            "client_secret",
            "ssh_key",
            "key_material",
            "tls_key",
            "encryption_key",
            "key",
            "passphrase",
        }
        sensitive_fragments = ("password", "secret", "token", "passphrase")
        
        def is_sensitive(key: str) -> bool:
            key_lower = key.lower()
            if key_lower in sensitive_exact:
                return True
            return any(fragment in key_lower for fragment in sensitive_fragments)
        
        def sanitize(value: Any) -> Any:
            if isinstance(value, dict):
                result: Dict[str, Any] = {}
                for key, item in value.items():
                    if is_sensitive(key):
                        result[key] = "***"
                    else:
                        result[key] = sanitize(item)
                return result
            if isinstance(value, list):
                return [sanitize(item) for item in value]
            return value
        
        return sanitize(metadata.copy())


