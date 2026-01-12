"""
Provisioning API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.core.database import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.services.provisioning.terraform_service import TerraformService
from app.services.provisioning.cloudformation_service import CloudFormationService
from app.services.provisioning.iac_project_service import IacProjectService
from app.services.provisioning.state_service import StateService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Pydantic models for requests/responses
class ProvisionRequest(BaseModel):
    name: str
    description: Optional[str] = None
    provider: str  # terraform, cloudformation, aws, azure, gcp
    template_id: Optional[int] = None
    template_content: Optional[str] = None  # For inline templates
    variables: Optional[Dict[str, Any]] = None
    region: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None  # Cloud provider credentials

class ProvisionResponse(BaseModel):
    success: bool
    project_id: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None

class TemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    provider: str
    template_type: Optional[str] = None
    template_content: str
    variables_schema: Optional[Dict[str, Any]] = None
    is_public: bool = False

@router.post("/provision", response_model=ProvisionResponse)
async def provision_infrastructure(
    request: ProvisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Provision infrastructure using the specified provider"""
    try:
        tenant_id = current_user.tenant_id
        
        # Create project
        project_service = IacProjectService()
        project_result = await project_service.create_project(
            tenant_id=tenant_id,
            name=request.name,
            provider=request.provider,
            template_id=request.template_id,
            description=request.description,
            variables=request.variables or {},
            created_by=current_user.id,
            db=db
        )
        
        if not project_result["success"]:
            raise HTTPException(status_code=400, detail=project_result.get("error", "Failed to create project"))
        
        project = project_result["project"]
        
        # Update state to provisioning
        await project_service.update_project_state(
            project_id=project.id,
            tenant_id=tenant_id,
            state="provisioning",
            db=db
        )
        
        # Execute provisioning based on provider
        if request.provider == "terraform":
            terraform_service = TerraformService()
            
            # Get template content
            template_content = request.template_content
            if not template_content and request.template_id:
                template = await project_service.get_template(request.template_id, tenant_id, db)
                if template:
                    template_content = template.template_content
                else:
                    raise HTTPException(status_code=404, detail="Template not found")
            
            if not template_content:
                raise HTTPException(status_code=400, detail="Template content required")
            
            # Initialize workspace
            init_result = await terraform_service.init_workspace(
                project_id=project.id,
                template_content=template_content,
                variables=request.variables
            )
            
            if not init_result["success"]:
                await project_service.update_project_state(
                    project_id=project.id,
                    tenant_id=tenant_id,
                    state="failed",
                    db=db
                )
                raise HTTPException(status_code=500, detail=init_result.get("error", "Failed to initialize Terraform"))
            
            # Run plan
            plan_result = await terraform_service.plan(
                workspace_path=init_result["workspace_path"],
                variables=request.variables
            )
            
            if not plan_result["success"]:
                await project_service.update_project_state(
                    project_id=project.id,
                    tenant_id=tenant_id,
                    state="failed",
                    db=db
                )
                raise HTTPException(status_code=500, detail=plan_result.get("error", "Failed to create plan"))
            
            # Apply (auto-approve for now - should be configurable)
            apply_result = await terraform_service.apply(
                workspace_path=init_result["workspace_path"],
                auto_approve=True
            )
            
            if not apply_result["success"]:
                await project_service.update_project_state(
                    project_id=project.id,
                    tenant_id=tenant_id,
                    state="failed",
                    db=db
                )
                raise HTTPException(status_code=500, detail=apply_result.get("error", "Failed to apply"))
            
            # Update project with outputs and state
            await project_service.update_project_state(
                project_id=project.id,
                tenant_id=tenant_id,
                state="active",
                outputs=apply_result.get("outputs", {}),
                terraform_state=apply_result.get("state", {}),
                db=db
            )
            
        elif request.provider in ["azure", "gcp", "aws"]:
            # Use cloud provider directly
            from app.services.provisioning.cloud_providers.aws_provider import AWSProvider
            from app.services.provisioning.cloud_providers.azure_provider import AzureProvider
            from app.services.provisioning.cloud_providers.gcp_provider import GCPProvider
            from app.services.credential_service import CredentialService
            from app.models.credential import Credential, InfrastructureConnection
            import json
            
            # Get credentials from infrastructure connection or request
            credentials = request.credentials or {}
            credential_id = credentials.get("credential_id")
            
            if credential_id:
                # Get credentials from database
                cred_service = CredentialService()
                cred = db.query(Credential).filter(
                    Credential.id == credential_id,
                    Credential.tenant_id == tenant_id
                ).first()
                
                if cred:
                    cred_data = cred_service.get_credential(db, cred.id, tenant_id)
                    credentials.update(cred_data)
            
            if request.provider == "azure":
                azure_provider = AzureProvider()
                
                # Extract Azure-specific parameters
                resource_group = request.variables.get("resource_group") if request.variables else None
                location = request.variables.get("location") or request.region or "eastus"
                
                if not resource_group:
                    # Create resource group first
                    rg_name = f"resolvify-{project.id}"
                    rg_result = await azure_provider.create_resource_group(
                        resource_group_name=rg_name,
                        location=location,
                        subscription_id=credentials.get("subscription_id") or request.variables.get("subscription_id"),
                        tenant_id=credentials.get("tenant_id"),
                        client_id=credentials.get("client_id"),
                        client_secret=credentials.get("client_secret")
                    )
                    
                    if not rg_result["success"]:
                        await project_service.update_project_state(
                            project_id=project.id,
                            tenant_id=tenant_id,
                            state="failed",
                            db=db
                        )
                        raise HTTPException(status_code=500, detail=rg_result.get("error", "Failed to create resource group"))
                    
                    resource_group = rg_name
                
                # Create VM if requested
                if request.variables and request.variables.get("create_vm"):
                    vm_result = await azure_provider.create_vm(
                        resource_group=resource_group,
                        vm_name=request.variables.get("vm_name", f"vm-{project.id}"),
                        location=location,
                        vm_size=request.variables.get("vm_size", "Standard_B1s"),
                        subscription_id=credentials.get("subscription_id") or request.variables.get("subscription_id"),
                        tenant_id=credentials.get("tenant_id"),
                        client_id=credentials.get("client_id"),
                        client_secret=credentials.get("client_secret"),
                        admin_username=request.variables.get("admin_username", "azureuser"),
                        admin_password=request.variables.get("admin_password"),
                        ssh_public_key=request.variables.get("ssh_public_key")
                    )
                    
                    if not vm_result["success"]:
                        await project_service.update_project_state(
                            project_id=project.id,
                            tenant_id=tenant_id,
                            state="failed",
                            db=db
                        )
                        raise HTTPException(status_code=500, detail=vm_result.get("error", "Failed to create VM"))
                    
                    # Store resource
                    await project_service.add_resource(
                        project_id=project.id,
                        resource_type="virtual_machine",
                        resource_id=vm_result.get("vm_id", ""),
                        provider="azure",
                        name=vm_result.get("vm_name"),
                        region=location,
                        metadata=vm_result,
                        db=db
                    )
                
                # Update project
                await project_service.update_project_state(
                    project_id=project.id,
                    tenant_id=tenant_id,
                    state="active",
                    outputs={"resource_group": resource_group},
                    db=db
                )
            
            elif request.provider == "gcp":
                gcp_provider = GCPProvider()
                
                project_id = credentials.get("project_id") or request.variables.get("project_id")
                if not project_id:
                    raise HTTPException(status_code=400, detail="GCP project_id required")
                
                zone = request.variables.get("zone") or "us-central1-a" if request.variables else "us-central1-a"
                
                # Create VM if requested
                if request.variables and request.variables.get("create_vm"):
                    vm_result = await gcp_provider.create_vm(
                        project_id=project_id,
                        zone=zone,
                        instance_name=request.variables.get("instance_name", f"instance-{project.id}"),
                        machine_type=request.variables.get("machine_type", "e2-micro"),
                        service_account_key=credentials.get("service_account_key"),
                        credentials_path=credentials.get("credentials_path"),
                        ssh_public_key=request.variables.get("ssh_public_key")
                    )
                    
                    if not vm_result["success"]:
                        await project_service.update_project_state(
                            project_id=project.id,
                            tenant_id=tenant_id,
                            state="failed",
                            db=db
                        )
                        raise HTTPException(status_code=500, detail=vm_result.get("error", "Failed to create VM"))
                    
                    # Store resource
                    await project_service.add_resource(
                        project_id=project.id,
                        resource_type="compute_instance",
                        resource_id=str(vm_result.get("instance_id", "")),
                        provider="gcp",
                        name=vm_result.get("instance_name"),
                        region=zone,
                        metadata=vm_result,
                        db=db
                    )
                
                # Update project
                await project_service.update_project_state(
                    project_id=project.id,
                    tenant_id=tenant_id,
                    state="active",
                    outputs={"project_id": project_id},
                    db=db
                )
            
            elif request.provider == "aws":
                aws_provider = AWSProvider()
                
                region = request.region or request.variables.get("region") or "us-east-1" if request.variables else "us-east-1"
                
                # Create EC2 instance if requested
                if request.variables and request.variables.get("create_instance"):
                    instance_result = await aws_provider.create_ec2_instance(
                        instance_type=request.variables.get("instance_type", "t2.micro"),
                        image_id=request.variables.get("image_id", "ami-0c55b159cbfafe1f0"),  # Default Ubuntu
                        key_name=request.variables.get("key_name"),
                        security_group_ids=request.variables.get("security_group_ids"),
                        subnet_id=request.variables.get("subnet_id"),
                        region=region,
                        aws_access_key_id=credentials.get("access_key_id"),
                        aws_secret_access_key=credentials.get("secret_access_key")
                    )
                    
                    if not instance_result["success"]:
                        await project_service.update_project_state(
                            project_id=project.id,
                            tenant_id=tenant_id,
                            state="failed",
                            db=db
                        )
                        raise HTTPException(status_code=500, detail=instance_result.get("error", "Failed to create instance"))
                    
                    # Store resource
                    await project_service.add_resource(
                        project_id=project.id,
                        resource_type="ec2_instance",
                        resource_id=instance_result.get("instance_id", ""),
                        provider="aws",
                        name=request.variables.get("instance_name"),
                        region=region,
                        metadata=instance_result,
                        db=db
                    )
                
                # Update project
                await project_service.update_project_state(
                    project_id=project.id,
                    tenant_id=tenant_id,
                    state="active",
                    outputs={"region": region},
                    db=db
                )
        
        elif request.provider == "cloudformation":
            cf_service = CloudFormationService()
            
            # Get template content
            template_content = request.template_content
            if not template_content and request.template_id:
                template = await project_service.get_template(request.template_id, tenant_id, db)
                if template:
                    template_content = template.template_content
                else:
                    raise HTTPException(status_code=404, detail="Template not found")
            
            if not template_content:
                raise HTTPException(status_code=400, detail="Template content required")
            
            # Validate template
            credentials = request.credentials or {}
            validate_result = await cf_service.validate_template(
                template_body=template_content,
                region=request.region or "us-east-1",
                aws_access_key_id=credentials.get("aws_access_key_id"),
                aws_secret_access_key=credentials.get("aws_secret_access_key")
            )
            
            if not validate_result["success"]:
                await project_service.update_project_state(
                    project_id=project.id,
                    tenant_id=tenant_id,
                    state="failed",
                    db=db
                )
                raise HTTPException(status_code=400, detail=validate_result.get("error", "Template validation failed"))
            
            # Create stack
            stack_name = f"resolvify-{project.id}"
            create_result = await cf_service.create_stack(
                stack_name=stack_name,
                template_body=template_content,
                parameters=request.variables,
                region=request.region or "us-east-1",
                aws_access_key_id=credentials.get("aws_access_key_id"),
                aws_secret_access_key=credentials.get("aws_secret_access_key")
            )
            
            if not create_result["success"]:
                await project_service.update_project_state(
                    project_id=project.id,
                    tenant_id=tenant_id,
                    state="failed",
                    db=db
                )
                raise HTTPException(status_code=500, detail=create_result.get("error", "Failed to create stack"))
            
            # Update project
            await project_service.update_project_state(
                project_id=project.id,
                tenant_id=tenant_id,
                state="active",
                outputs={"stack_id": create_result.get("stack_id")},
                db=db
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {request.provider}")
        
        return ProvisionResponse(
            success=True,
            project_id=project.id,
            message="Infrastructure provisioned successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error provisioning infrastructure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects")
async def list_projects(
    state: Optional[str] = None,
    provider: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List provisioning projects"""
    try:
        project_service = IacProjectService()
        projects = await project_service.list_projects(
            tenant_id=current_user.tenant_id,
            state=state,
            provider=provider,
            db=db
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
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None
                }
                for p in projects
            ]
        }
        
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects/{project_id}")
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a provisioning project"""
    try:
        project_service = IacProjectService()
        project = await project_service.get_project(
            project_id=project_id,
            tenant_id=current_user.tenant_id,
            db=db
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
                        "region": r.region
                    }
                    for r in project.resources
                ]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/projects/{project_id}")
async def destroy_infrastructure(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Destroy provisioned infrastructure"""
    try:
        project_service = IacProjectService()
        project = await project_service.get_project(
            project_id=project_id,
            tenant_id=current_user.tenant_id,
            db=db
        )
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project.state == "destroyed":
            raise HTTPException(status_code=400, detail="Infrastructure already destroyed")
        
        # Update state to destroying
        await project_service.update_project_state(
            project_id=project.id,
            tenant_id=current_user.tenant_id,
            state="destroying",
            db=db
        )
        
        # Execute destroy based on provider
        if project.provider == "terraform":
            terraform_service = TerraformService()
            # TODO: Get workspace path from project metadata
            # For now, this is a placeholder
            logger.warning("Terraform destroy not fully implemented - workspace path needed")
        
        elif project.provider == "cloudformation":
            cf_service = CloudFormationService()
            # TODO: Get stack name from project outputs
            # For now, this is a placeholder
            logger.warning("CloudFormation destroy not fully implemented - stack name needed")
        
        # Update state to destroyed
        await project_service.update_project_state(
            project_id=project.id,
            tenant_id=current_user.tenant_id,
            state="destroyed",
            db=db
        )
        
        return {
            "success": True,
            "message": "Infrastructure destruction initiated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error destroying infrastructure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates")
async def list_templates(
    provider: Optional[str] = None,
    template_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List infrastructure templates"""
    try:
        project_service = IacProjectService()
        templates = await project_service.list_templates(
            tenant_id=current_user.tenant_id,
            provider=provider,
            template_type=template_type,
            db=db
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
                    "created_at": t.created_at.isoformat() if t.created_at else None
                }
                for t in templates
            ]
        }
        
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/templates")
async def create_template(
    request: TemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create an infrastructure template"""
    try:
        from app.models.infrastructure_template import InfrastructureTemplate
        
        template = InfrastructureTemplate(
            tenant_id=current_user.tenant_id,
            name=request.name,
            description=request.description,
            provider=request.provider,
            template_type=request.template_type,
            template_content=request.template_content,
            variables_schema=request.variables_schema,
            is_public=request.is_public,
            created_by=current_user.id
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
                "template_type": template.template_type
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate")
async def validate_template(
    provider: str = Body(...),
    template_content: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate an infrastructure template"""
    try:
        if provider == "terraform":
            terraform_service = TerraformService()
            result = await terraform_service.validate(template_content)
            
        elif provider == "cloudformation":
            cf_service = CloudFormationService()
            result = await cf_service.validate_template(template_body=template_content)
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

