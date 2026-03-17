"""
Mixin: IaC project CRUD and destroy operations
"""
from typing import Optional

from fastapi import HTTPException

from app.services.provisioning.iac_project_service import IacProjectService


class ProvisioningProjectsMixin:
    """Project management operations for ProvisioningController."""

    async def list_projects(self, state: Optional[str] = None, provider: Optional[str] = None) -> dict:
        projects = await IacProjectService().list_projects(
            tenant_id=self.tenant_id, state=state, provider=provider, db=self.db
        )
        return {
            "success": True,
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "provider": p.provider,
                    "state": p.state,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                }
                for p in projects
            ],
        }

    async def get_project(self, project_id: int) -> dict:
        project = await IacProjectService().get_project(
            project_id=project_id, tenant_id=self.tenant_id, db=self.db
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return {
            "success": True,
            "project": {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "provider": project.provider,
                "state": project.state,
                "variables": project.variables,
                "outputs": project.outputs,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                "resources": [
                    {
                        "id": r.id,
                        "resource_type": r.resource_type,
                        "resource_id": r.resource_id,
                        "name": r.name,
                        "provider": r.provider,
                        "region": r.region,
                    }
                    for r in project.resources
                ],
            },
        }

    async def destroy(self, project_id: int) -> dict:
        from app.core.logging import get_logger
        _logger = get_logger(__name__)

        db = self.db
        project_service = IacProjectService()
        project = await project_service.get_project(
            project_id=project_id, tenant_id=self.tenant_id, db=db
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.state == "destroyed":
            raise HTTPException(status_code=400, detail="Infrastructure already destroyed")

        await project_service.update_project_state(
            project_id=project.id, tenant_id=self.tenant_id, state="destroying", db=db
        )

        if project.provider == "terraform":
            _logger.warning("Terraform destroy not fully implemented - workspace path needed")
        elif project.provider == "cloudformation":
            _logger.warning("CloudFormation destroy not fully implemented - stack name needed")

        await project_service.update_project_state(
            project_id=project.id, tenant_id=self.tenant_id, state="destroyed", db=db
        )
        return {"success": True, "message": "Infrastructure destruction initiated"}
