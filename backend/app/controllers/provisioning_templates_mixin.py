"""
Mixin: IaC template CRUD and validation operations
"""
from typing import Optional

from fastapi import HTTPException

from app.services.provisioning.terraform_service import TerraformService
from app.services.provisioning.cloudformation_service import CloudFormationService
from app.services.provisioning.iac_project_service import IacProjectService


class ProvisioningTemplatesMixin:
    """Template management operations for ProvisioningController."""

    async def list_templates(
        self, provider: Optional[str] = None, template_type: Optional[str] = None
    ) -> dict:
        templates = await IacProjectService().list_templates(
            tenant_id=self.tenant_id, provider=provider, template_type=template_type, db=self.db
        )
        return {
            "success": True,
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "provider": t.provider,
                    "template_type": t.template_type,
                    "is_public": t.is_public,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in templates
            ],
        }

    async def create_template(self, request) -> dict:
        from app.models.infrastructure_template import InfrastructureTemplate
        db = self.db
        template = InfrastructureTemplate(
            tenant_id=self.tenant_id,
            name=request.name,
            description=request.description,
            provider=request.provider,
            template_type=request.template_type,
            template_content=request.template_content,
            variables_schema=request.variables_schema,
            is_public=request.is_public,
            created_by=self.user_id,
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return {
            "success": True,
            "template": {
                "id": template.id,
                "name": template.name,
                "provider": template.provider,
                "template_type": template.template_type,
            },
        }

    async def validate_template(self, provider: str, template_content: str) -> dict:
        if provider == "terraform":
            return await TerraformService().validate(template_content)
        elif provider == "cloudformation":
            return await CloudFormationService().validate_template(template_body=template_content)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
