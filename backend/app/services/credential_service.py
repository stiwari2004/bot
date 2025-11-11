"""
Credential encryption service
POC version - uses Fernet encryption (symmetric)
For production, use KMS or HashiCorp Vault
"""
import json
import os
from datetime import datetime
from typing import Optional

from cryptography.fernet import Fernet

from app.core.logging import get_logger

logger = get_logger(__name__)


class CredentialEncryption:
    """Simple credential encryption for POC"""
    
    def __init__(self):
        # Get encryption key from environment or generate one
        key = os.getenv("CREDENTIAL_ENCRYPTION_KEY")
        if not key:
            # Generate a key and log it (for POC only - in production, use KMS)
            key = Fernet.generate_key()
            logger.warning(f"CREDENTIAL_ENCRYPTION_KEY not set. Generated key: {key.decode()}")
            logger.warning("For production, set CREDENTIAL_ENCRYPTION_KEY from secure KMS")
        else:
            # Ensure key is bytes
            if isinstance(key, str):
                key = key.encode()
        
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext credential"""
        if not plaintext:
            return ""
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, encrypted: str) -> str:
        """Decrypt encrypted credential"""
        if not encrypted:
            return ""
        return self.cipher.decrypt(encrypted.encode()).decode()


# Global encryption instance
_encryption = None

def get_encryption() -> CredentialEncryption:
    """Get singleton encryption instance"""
    global _encryption
    if _encryption is None:
        _encryption = CredentialEncryption()
    return _encryption


class CredentialService:
    """Service for managing credentials"""
    
    def __init__(self):
        self.encryption = get_encryption()
    
    def save_credential(
        self,
        db,
        tenant_id: int,
        name: str,
        type: str,
        value: str,
        metadata: dict = None
    ):
        """Save encrypted credential to database"""
        from app.models.credential import Credential
        
        # Encrypt the value
        encrypted_value = self.encryption.encrypt(value)
        
        # Determine which field to use
        credential = Credential(
            tenant_id=tenant_id,
            name=name,
            credential_type=type,
            environment=metadata.get("environment", "prod") if metadata else "prod",
            username=metadata.get("username") if metadata else None,
            encrypted_password=encrypted_value if type in ["ssh", "database"] else None,
            encrypted_api_key=encrypted_value if type == "api_key" else None,
            host=metadata.get("host") if metadata else None,
            port=metadata.get("port") if metadata else None,
            database_name=metadata.get("database_name") if metadata else None,
            meta_data=json.dumps(metadata) if metadata else None
        )
        
        db.add(credential)
        db.commit()
        db.refresh(credential)
        return credential
    
    def get_credential(self, db, credential_id: int, tenant_id: int) -> dict:
        """Get and decrypt credential from database"""
        from app.models.credential import Credential
        
        credential = db.query(Credential).filter(
            Credential.id == credential_id,
            Credential.tenant_id == tenant_id
        ).first()
        
        if not credential:
            return None
        
        # Decrypt the value
        encrypted_value = credential.encrypted_password or credential.encrypted_api_key
        if encrypted_value:
            decrypted_value = self.encryption.decrypt(encrypted_value)
        else:
            decrypted_value = None
        
        result = {
            "username": credential.username,
            "password": decrypted_value if credential.encrypted_password else None,
            "api_key": decrypted_value if credential.encrypted_api_key else None,
            "host": credential.host,
            "port": credential.port,
            "database_name": credential.database_name
        }
        
        return result

    def resolve_alias(
        self,
        db,
        tenant_id: int,
        alias: str,
        environment: Optional[str] = None,
    ) -> Optional[dict]:
        """Resolve a credential alias to decrypted material."""
        from app.models.credential import Credential

        if not alias:
            return None

        query = (
            db.query(Credential)
            .filter(Credential.tenant_id == tenant_id, Credential.name == alias)
        )
        if environment:
            query = query.filter(Credential.environment == environment)

        credential = query.first()
        if not credential and environment:
            credential = (
                db.query(Credential)
                .filter(Credential.tenant_id == tenant_id, Credential.name == alias)
                .first()
            )

        if not credential:
            return None

        encrypted_value = credential.encrypted_password or credential.encrypted_api_key
        decrypted_value = (
            self.encryption.decrypt(encrypted_value) if encrypted_value else None
        )

        metadata_payload = {}
        if credential.meta_data:
            try:
                metadata_payload = json.loads(credential.meta_data)
            except json.JSONDecodeError:
                logger.warning("Unable to parse credential metadata for alias %s", alias)

        credential.last_used_at = datetime.utcnow()
        db.add(credential)

        resolved = {
            "alias": alias,
            "credential_id": credential.id,
            "type": credential.credential_type,
            "environment": credential.environment,
            "username": credential.username or metadata_payload.get("username"),
            "password": decrypted_value if credential.encrypted_password else metadata_payload.get("password"),
            "api_key": decrypted_value if credential.encrypted_api_key else metadata_payload.get("api_key"),
            "private_key": metadata_payload.get("private_key"),
            "domain": metadata_payload.get("domain"),
            "host": credential.host or metadata_payload.get("host"),
            "port": credential.port or metadata_payload.get("port"),
            "metadata": metadata_payload,
            "source": metadata_payload.get("source") or "alias",
            "rotated_at": metadata_payload.get("rotated_at"),
        }

        if metadata_payload.get("secrets"):
            resolved["secrets"] = metadata_payload["secrets"]

        return resolved


# Global credential service instance
_credential_service = None

def get_credential_service() -> CredentialService:
    """Get singleton credential service instance"""
    global _credential_service
    if _credential_service is None:
        _credential_service = CredentialService()
    return _credential_service
