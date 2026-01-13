"""
IaC Project Management Service
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timezone
from app.core.logging import get_logger
from app.models.provisioning_project import ProvisioningProject
from app.models.provisioned_resource import ProvisionedResource
from app.models.infrastructure_template import InfrastructureTemplate

logger = get_logger(__name__)


class IacProjectService:
    """Service for managing IaC projects"""
    
    def __init__(self):
        pass
    
    async def create_project(
        self,
        tenant_id: int,
        name: str,
        provider: str,
        template_id: Optional[int] = None,
        description: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        created_by: Optional[int] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Create a new provisioning project"""
        try:
            project = ProvisioningProject(
                tenant_id=tenant_id,
                name=name,
                description=description,
                provider=provider,
                template_id=template_id,
                state="pending",
                variables=variables or {},
                created_by=created_by
            )
            
            db.add(project)
            db.commit()
            db.refresh(project)
            
            return {
                "success": True,
                "project": project
            }
            
        except Exception as e:
            logger.error(f"Error creating provisioning project: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_project(
        self,
        project_id: int,
        tenant_id: int,
        db: Session
    ) -> Optional[ProvisioningProject]:
        """Get a provisioning project"""
        try:
            project = db.query(ProvisioningProject).filter(
                and_(
                    ProvisioningProject.id == project_id,
                    ProvisioningProject.tenant_id == tenant_id
                )
            ).first()
            
            return project
            
        except Exception as e:
            logger.error(f"Error getting provisioning project: {e}")
            return None
    
    async def update_project_state(
        self,
        project_id: int,
        tenant_id: int,
        state: str,
        outputs: Optional[Dict[str, Any]] = None,
        terraform_state: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Update project state"""
        try:
            project = await self.get_project(project_id, tenant_id, db)
            
            if not project:
                return {
                    "success": False,
                    "error": "Project not found"
                }
            
            project.state = state
            project.updated_at = datetime.now(timezone.utc)
            
            if outputs is not None:
                project.outputs = outputs
            
            if terraform_state is not None:
                project.terraform_state = terraform_state
            
            db.commit()
            db.refresh(project)
            
            return {
                "success": True,
                "project": project
            }
            
        except Exception as e:
            logger.error(f"Error updating project state: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_projects(
        self,
        tenant_id: int,
        state: Optional[str] = None,
        provider: Optional[str] = None,
        db: Session = None
    ) -> List[ProvisioningProject]:
        """List provisioning projects"""
        try:
            query = db.query(ProvisioningProject).filter(
                ProvisioningProject.tenant_id == tenant_id
            )
            
            if state:
                query = query.filter(ProvisioningProject.state == state)
            
            if provider:
                query = query.filter(ProvisioningProject.provider == provider)
            
            return query.order_by(ProvisioningProject.created_at.desc()).all()
            
        except Exception as e:
            logger.error(f"Error listing projects: {e}")
            return []
    
    async def add_resource(
        self,
        project_id: int,
        resource_type: str,
        resource_id: str,
        provider: str,
        name: Optional[str] = None,
        region: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Add a provisioned resource to a project"""
        try:
            resource = ProvisionedResource(
                project_id=project_id,
                resource_type=resource_type,
                resource_id=resource_id,
                name=name,
                provider=provider,
                region=region,
                resource_metadata=metadata or {}
            )
            
            db.add(resource)
            db.commit()
            db.refresh(resource)
            
            return {
                "success": True,
                "resource": resource
            }
            
        except Exception as e:
            logger.error(f"Error adding resource: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_template(
        self,
        template_id: int,
        tenant_id: Optional[int] = None,
        db: Session = None
    ) -> Optional[InfrastructureTemplate]:
        """Get an infrastructure template"""
        try:
            query = db.query(InfrastructureTemplate).filter(
                InfrastructureTemplate.id == template_id
            )
            
            # Filter by tenant or public templates
            if tenant_id:
                query = query.filter(
                    (InfrastructureTemplate.tenant_id == tenant_id) |
                    (InfrastructureTemplate.is_public == True)
                )
            else:
                query = query.filter(InfrastructureTemplate.is_public == True)
            
            return query.first()
            
        except Exception as e:
            logger.error(f"Error getting template: {e}")
            return None
    
    async def list_templates(
        self,
        tenant_id: Optional[int] = None,
        provider: Optional[str] = None,
        template_type: Optional[str] = None,
        db: Session = None
    ) -> List[InfrastructureTemplate]:
        """List infrastructure templates"""
        try:
            query = db.query(InfrastructureTemplate)
            
            # Filter by tenant or public templates
            if tenant_id:
                query = query.filter(
                    (InfrastructureTemplate.tenant_id == tenant_id) |
                    (InfrastructureTemplate.is_public == True)
                )
            else:
                query = query.filter(InfrastructureTemplate.is_public == True)
            
            if provider:
                query = query.filter(InfrastructureTemplate.provider == provider)
            
            if template_type:
                query = query.filter(InfrastructureTemplate.template_type == template_type)
            
            return query.order_by(InfrastructureTemplate.created_at.desc()).all()
            
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            return []

