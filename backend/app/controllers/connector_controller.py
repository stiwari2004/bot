"""
Controller for connector endpoints - handles request/response logic
"""
from typing import Optional, Dict, Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.controllers.base_controller import BaseController
from app.controllers.connector_credential_mixin import ConnectorCredentialMixin
from app.controllers.connector_infrastructure_mixin import ConnectorInfrastructureMixin
from app.controllers.connector_catalog_mixin import ConnectorCatalogMixin
from app.repositories.credential_repository import CredentialRepository
from app.repositories.infrastructure_repository import InfrastructureRepository
from app.services.credential_service import get_credential_service
from app.services.connector.connector_service import ConnectorService
from app.core.logging import get_logger

logger = get_logger(__name__)


class CredentialCreate(BaseModel):
    name: str
    credential_type: str
    environment: str
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    subscription_id: Optional[str] = None
    service_account_key: Optional[str] = None
    project_id: Optional[str] = None
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    region: Optional[str] = None


class InfrastructureConnectionCreate(BaseModel):
    name: str
    connection_type: str
    credential_id: Optional[int] = None
    target_host: Optional[str] = None
    target_port: Optional[int] = None
    target_service: Optional[str] = None
    environment: str
    meta_data: Optional[Dict[str, Any]] = None


class TestCommandRequest(BaseModel):
    vm_resource_id: str
    command: str
    shell: Optional[str] = None


class ConnectorController(ConnectorCredentialMixin, ConnectorInfrastructureMixin, ConnectorCatalogMixin, BaseController):
    """Controller for connector operations"""

    def __init__(self, db: Session, tenant_id: int = 1):
        self.db = db
        self.tenant_id = tenant_id
        self.credential_repo = CredentialRepository(db)
        self.infrastructure_repo = InfrastructureRepository(db)
        self.connector_service = ConnectorService()
        self.credential_service = get_credential_service()
