"""
Helper service for retrieving cloud provider credentials from infrastructure connections
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.models.credential import Credential, InfrastructureConnection
from app.services.credential_service import CredentialService
import json

logger = get_logger(__name__)


class ProvisioningCredentialHelper:
    """Helper for retrieving credentials for provisioning"""
    
    def __init__(self):
        self.credential_service = CredentialService()
    
    async def get_azure_credentials(
        self,
        tenant_id: int,
        connection_id: Optional[int] = None,
        credential_id: Optional[int] = None,
        db: Session = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get Azure credentials from infrastructure connection or credential
        
        Args:
            tenant_id: Tenant ID
            connection_id: Infrastructure connection ID (optional)
            credential_id: Credential ID (optional)
            db: Database session
            
        Returns:
            Dict with tenant_id, client_id, client_secret, subscription_id
        """
        try:
            if connection_id:
                # Get from infrastructure connection
                connection = db.query(InfrastructureConnection).filter(
                    InfrastructureConnection.id == connection_id,
                    InfrastructureConnection.tenant_id == tenant_id,
                    InfrastructureConnection.is_active == True
                ).first()
                
                if not connection:
                    logger.warning(f"Infrastructure connection {connection_id} not found")
                    return None
                
                credential_id = connection.credential_id
            
            if credential_id:
                # Get credential
                credential = db.query(Credential).filter(
                    Credential.id == credential_id,
                    Credential.tenant_id == tenant_id,
                    Credential.credential_type == "azure"
                ).first()
                
                if not credential:
                    logger.warning(f"Azure credential {credential_id} not found")
                    return None
                
                # Decrypt and return
                cred_data = self.credential_service.get_credential(db, credential.id, tenant_id)
                
                return {
                    "tenant_id": cred_data.get("tenant_id"),
                    "client_id": cred_data.get("client_id"),
                    "client_secret": cred_data.get("client_secret"),
                    "subscription_id": cred_data.get("subscription_id")
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting Azure credentials: {e}")
            return None
    
    async def get_gcp_credentials(
        self,
        tenant_id: int,
        connection_id: Optional[int] = None,
        credential_id: Optional[int] = None,
        db: Session = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get GCP credentials from infrastructure connection or credential
        
        Returns:
            Dict with service_account_key, project_id, credentials_path
        """
        try:
            if connection_id:
                connection = db.query(InfrastructureConnection).filter(
                    InfrastructureConnection.id == connection_id,
                    InfrastructureConnection.tenant_id == tenant_id,
                    InfrastructureConnection.is_active == True
                ).first()
                
                if not connection:
                    return None
                
                credential_id = connection.credential_id
            
            if credential_id:
                credential = db.query(Credential).filter(
                    Credential.id == credential_id,
                    Credential.tenant_id == tenant_id,
                    Credential.credential_type == "gcp"
                ).first()
                
                if not credential:
                    return None
                
                cred_data = self.credential_service.get_credential(db, credential.id, tenant_id)
                
                return {
                    "service_account_key": cred_data.get("service_account_key"),
                    "project_id": cred_data.get("project_id"),
                    "credentials_path": None  # Could be stored in metadata
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting GCP credentials: {e}")
            return None
    
    async def get_aws_credentials(
        self,
        tenant_id: int,
        connection_id: Optional[int] = None,
        credential_id: Optional[int] = None,
        db: Session = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get AWS credentials from infrastructure connection or credential
        
        Returns:
            Dict with access_key_id, secret_access_key, region
        """
        try:
            if connection_id:
                connection = db.query(InfrastructureConnection).filter(
                    InfrastructureConnection.id == connection_id,
                    InfrastructureConnection.tenant_id == tenant_id,
                    InfrastructureConnection.is_active == True
                ).first()
                
                if not connection:
                    return None
                
                credential_id = connection.credential_id
            
            if credential_id:
                credential = db.query(Credential).filter(
                    Credential.id == credential_id,
                    Credential.tenant_id == tenant_id,
                    Credential.credential_type == "aws"
                ).first()
                
                if not credential:
                    return None
                
                cred_data = self.credential_service.get_credential(db, credential.id, tenant_id)
                
                return {
                    "access_key_id": cred_data.get("access_key_id"),
                    "secret_access_key": cred_data.get("secret_access_key"),
                    "region": cred_data.get("region", "us-east-1")
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting AWS credentials: {e}")
            return None

