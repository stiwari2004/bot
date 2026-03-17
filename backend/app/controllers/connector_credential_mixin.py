"""
Mixin: credential create/list operations
"""
from typing import Optional, Dict, Any

from fastapi import HTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectorCredentialMixin:
    """Credential operations for ConnectorController."""

    def create_credential(self, credential) -> Dict[str, Any]:
        """Create a new credential"""
        try:
            value_to_encrypt = None
            metadata = {
                "username": credential.username,
                "host": credential.host,
                "port": credential.port,
                "database_name": credential.database_name,
            }

            if credential.credential_type == "azure":
                if not credential.tenant_id or not credential.client_id or not credential.client_secret:
                    raise self.bad_request("Azure credentials require tenant_id, client_id, and client_secret")
                value_to_encrypt = credential.client_secret
                metadata.update({
                    "tenant_id": credential.tenant_id,
                    "client_id": credential.client_id,
                    "subscription_id": credential.subscription_id,
                })
            elif credential.credential_type == "gcp":
                if not credential.service_account_key:
                    raise self.bad_request("GCP credentials require service_account_key")
                value_to_encrypt = credential.service_account_key
                metadata.update({"project_id": credential.project_id})
            elif credential.credential_type == "aws":
                if not credential.access_key_id or not credential.secret_access_key:
                    raise self.bad_request("AWS credentials require access_key_id and secret_access_key")
                value_to_encrypt = credential.secret_access_key
                metadata.update({
                    "access_key_id": credential.access_key_id,
                    "region": credential.region,
                })
            elif credential.password:
                value_to_encrypt = credential.password
            elif credential.api_key:
                value_to_encrypt = credential.api_key

            if not value_to_encrypt:
                raise self.bad_request("Password, API key, or cloud credentials required")

            db_credential = self.credential_service.save_credential(
                db=self.db,
                tenant_id=self.tenant_id,
                name=credential.name,
                type=credential.credential_type,
                value=value_to_encrypt,
                metadata=metadata,
            )
            return {
                "id": db_credential.id,
                "name": db_credential.name,
                "type": db_credential.credential_type,
                "environment": db_credential.environment,
                "message": "Credential created successfully",
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating credential: {e}")
            raise self.handle_error(e, "Failed to create credential")

    def list_credentials(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """List all credentials"""
        try:
            credentials = self.credential_repo.get_by_tenant(self.tenant_id, environment)
            return {
                "credentials": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "type": c.credential_type,
                        "environment": c.environment,
                        "host": c.host,
                        "port": c.port,
                        "database_name": c.database_name,
                        "created_at": c.created_at.isoformat() if c.created_at else None,
                    }
                    for c in credentials
                ]
            }
        except Exception as e:
            logger.error(f"Error listing credentials: {e}")
            raise self.handle_error(e, "Failed to list credentials")
