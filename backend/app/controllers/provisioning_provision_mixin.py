"""
Mixin: infrastructure provisioning operations across cloud providers
"""
from fastapi import HTTPException

from app.core.logging import get_logger
from app.services.provisioning.terraform_service import TerraformService
from app.services.provisioning.cloudformation_service import CloudFormationService
from app.services.provisioning.iac_project_service import IacProjectService

logger = get_logger(__name__)


class ProvisioningProvisionMixin:
    """Provision/destroy infrastructure operations for ProvisioningController."""

    async def provision(self, request) -> dict:
        db = self.db
        tenant_id = self.tenant_id
        project_service = IacProjectService()

        project_result = await project_service.create_project(
            tenant_id=tenant_id,
            name=request.name,
            provider=request.provider,
            template_id=request.template_id,
            description=request.description,
            variables=request.variables or {},
            created_by=self.user_id,
            db=db,
        )
        if not project_result["success"]:
            raise HTTPException(status_code=400, detail=project_result.get("error", "Failed to create project"))

        project = project_result["project"]
        await project_service.update_project_state(
            project_id=project.id, tenant_id=tenant_id, state="provisioning", db=db
        )

        try:
            if request.provider == "terraform":
                await self._provision_terraform(project, request, project_service)
            elif request.provider in ["azure", "gcp", "aws"]:
                await self._provision_cloud(project, request, project_service)
            elif request.provider == "cloudformation":
                await self._provision_cloudformation(project, request, project_service)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported provider: {request.provider}")
        except HTTPException:
            raise
        except Exception:
            await project_service.update_project_state(
                project_id=project.id, tenant_id=tenant_id, state="failed", db=db
            )
            raise

        return {"success": True, "project_id": project.id, "message": "Infrastructure provisioned successfully"}

    async def _provision_terraform(self, project, request, project_service: IacProjectService):
        terraform_service = TerraformService()
        tenant_id = self.tenant_id
        db = self.db

        template_content = request.template_content
        if not template_content and request.template_id:
            template = await project_service.get_template(request.template_id, tenant_id, db)
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")
            template_content = template.template_content

        if not template_content:
            raise HTTPException(status_code=400, detail="Template content required")

        init_result = await terraform_service.init_workspace(
            project_id=project.id, template_content=template_content, variables=request.variables
        )
        if not init_result["success"]:
            await project_service.update_project_state(project_id=project.id, tenant_id=tenant_id, state="failed", db=db)
            raise HTTPException(status_code=500, detail=init_result.get("error", "Failed to initialize Terraform"))

        plan_result = await terraform_service.plan(
            workspace_path=init_result["workspace_path"], variables=request.variables
        )
        if not plan_result["success"]:
            await project_service.update_project_state(project_id=project.id, tenant_id=tenant_id, state="failed", db=db)
            raise HTTPException(status_code=500, detail=plan_result.get("error", "Failed to create plan"))

        apply_result = await terraform_service.apply(
            workspace_path=init_result["workspace_path"], auto_approve=True
        )
        if not apply_result["success"]:
            await project_service.update_project_state(project_id=project.id, tenant_id=tenant_id, state="failed", db=db)
            raise HTTPException(status_code=500, detail=apply_result.get("error", "Failed to apply"))

        await project_service.update_project_state(
            project_id=project.id, tenant_id=tenant_id, state="active",
            outputs=apply_result.get("outputs", {}), terraform_state=apply_result.get("state", {}), db=db,
        )

    async def _provision_cloud(self, project, request, project_service: IacProjectService):
        from app.services.credential_service import CredentialService
        from app.models.credential import Credential
        db = self.db
        tenant_id = self.tenant_id

        credentials = request.credentials or {}
        credential_id = credentials.get("credential_id")
        if credential_id:
            cred_service = CredentialService()
            cred = db.query(Credential).filter(
                Credential.id == credential_id, Credential.tenant_id == tenant_id
            ).first()
            if cred:
                credentials.update(cred_service.get_credential(db, cred.id, tenant_id))

        if request.provider == "azure":
            await self._provision_azure(project, request, project_service, credentials)
        elif request.provider == "gcp":
            await self._provision_gcp(project, request, project_service, credentials)
        elif request.provider == "aws":
            await self._provision_aws(project, request, project_service, credentials)

    async def _provision_azure(self, project, request, project_service, credentials):
        from app.services.provisioning.cloud_providers.azure_provider import AzureProvider
        azure_provider = AzureProvider()
        tenant_id = self.tenant_id
        db = self.db

        resource_group = request.variables.get("resource_group") if request.variables else None
        location = (request.variables.get("location") if request.variables else None) or request.region or "eastus"

        if not resource_group:
            rg_name = f"resolvify-{project.id}"
            rg_result = await azure_provider.create_resource_group(
                resource_group_name=rg_name, location=location,
                subscription_id=credentials.get("subscription_id") or (request.variables.get("subscription_id") if request.variables else None),
                tenant_id=credentials.get("tenant_id"), client_id=credentials.get("client_id"),
                client_secret=credentials.get("client_secret"),
            )
            if not rg_result["success"]:
                await project_service.update_project_state(project_id=project.id, tenant_id=tenant_id, state="failed", db=db)
                raise HTTPException(status_code=500, detail=rg_result.get("error", "Failed to create resource group"))
            resource_group = rg_name

        if request.variables and request.variables.get("create_vm"):
            vm_result = await azure_provider.create_vm(
                resource_group=resource_group,
                vm_name=request.variables.get("vm_name", f"vm-{project.id}"),
                location=location,
                vm_size=request.variables.get("vm_size", "Standard_B1s"),
                subscription_id=credentials.get("subscription_id") or request.variables.get("subscription_id"),
                tenant_id=credentials.get("tenant_id"), client_id=credentials.get("client_id"),
                client_secret=credentials.get("client_secret"),
                admin_username=request.variables.get("admin_username", "azureuser"),
                admin_password=request.variables.get("admin_password"),
                ssh_public_key=request.variables.get("ssh_public_key"),
            )
            if not vm_result["success"]:
                await project_service.update_project_state(project_id=project.id, tenant_id=tenant_id, state="failed", db=db)
                raise HTTPException(status_code=500, detail=vm_result.get("error", "Failed to create VM"))
            await project_service.add_resource(
                project_id=project.id, resource_type="virtual_machine",
                resource_id=vm_result.get("vm_id", ""), provider="azure",
                name=vm_result.get("vm_name"), region=location, metadata=vm_result, db=db,
            )

        await project_service.update_project_state(
            project_id=project.id, tenant_id=tenant_id, state="active",
            outputs={"resource_group": resource_group}, db=db,
        )

    async def _provision_gcp(self, project, request, project_service, credentials):
        from app.services.provisioning.cloud_providers.gcp_provider import GCPProvider
        gcp_provider = GCPProvider()
        tenant_id = self.tenant_id
        db = self.db

        project_id = credentials.get("project_id") or (request.variables.get("project_id") if request.variables else None)
        if not project_id:
            raise HTTPException(status_code=400, detail="GCP project_id required")
        zone = (request.variables.get("zone") if request.variables else None) or "us-central1-a"

        if request.variables and request.variables.get("create_vm"):
            vm_result = await gcp_provider.create_vm(
                project_id=project_id, zone=zone,
                instance_name=request.variables.get("instance_name", f"instance-{project.id}"),
                machine_type=request.variables.get("machine_type", "e2-micro"),
                service_account_key=credentials.get("service_account_key"),
                credentials_path=credentials.get("credentials_path"),
                ssh_public_key=request.variables.get("ssh_public_key"),
            )
            if not vm_result["success"]:
                await project_service.update_project_state(project_id=project.id, tenant_id=tenant_id, state="failed", db=db)
                raise HTTPException(status_code=500, detail=vm_result.get("error", "Failed to create VM"))
            await project_service.add_resource(
                project_id=project.id, resource_type="compute_instance",
                resource_id=str(vm_result.get("instance_id", "")), provider="gcp",
                name=vm_result.get("instance_name"), region=zone, metadata=vm_result, db=db,
            )

        await project_service.update_project_state(
            project_id=project.id, tenant_id=tenant_id, state="active",
            outputs={"project_id": project_id}, db=db,
        )

    async def _provision_aws(self, project, request, project_service, credentials):
        from app.services.provisioning.cloud_providers.aws_provider import AWSProvider
        aws_provider = AWSProvider()
        tenant_id = self.tenant_id
        db = self.db

        region = request.region or (request.variables.get("region") if request.variables else None) or "us-east-1"

        if request.variables and request.variables.get("create_instance"):
            instance_result = await aws_provider.create_ec2_instance(
                instance_type=request.variables.get("instance_type", "t2.micro"),
                image_id=request.variables.get("image_id", "ami-0c55b159cbfafe1f0"),
                key_name=request.variables.get("key_name"),
                security_group_ids=request.variables.get("security_group_ids"),
                subnet_id=request.variables.get("subnet_id"),
                region=region,
                aws_access_key_id=credentials.get("access_key_id"),
                aws_secret_access_key=credentials.get("secret_access_key"),
            )
            if not instance_result["success"]:
                await project_service.update_project_state(project_id=project.id, tenant_id=tenant_id, state="failed", db=db)
                raise HTTPException(status_code=500, detail=instance_result.get("error", "Failed to create instance"))
            await project_service.add_resource(
                project_id=project.id, resource_type="ec2_instance",
                resource_id=instance_result.get("instance_id", ""), provider="aws",
                name=request.variables.get("instance_name"), region=region, metadata=instance_result, db=db,
            )

        await project_service.update_project_state(
            project_id=project.id, tenant_id=tenant_id, state="active",
            outputs={"region": region}, db=db,
        )

    async def _provision_cloudformation(self, project, request, project_service: IacProjectService):
        cf_service = CloudFormationService()
        tenant_id = self.tenant_id
        db = self.db

        template_content = request.template_content
        if not template_content and request.template_id:
            template = await project_service.get_template(request.template_id, tenant_id, db)
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")
            template_content = template.template_content

        if not template_content:
            raise HTTPException(status_code=400, detail="Template content required")

        credentials = request.credentials or {}
        validate_result = await cf_service.validate_template(
            template_body=template_content,
            region=request.region or "us-east-1",
            aws_access_key_id=credentials.get("aws_access_key_id"),
            aws_secret_access_key=credentials.get("aws_secret_access_key"),
        )
        if not validate_result["success"]:
            await project_service.update_project_state(project_id=project.id, tenant_id=tenant_id, state="failed", db=db)
            raise HTTPException(status_code=400, detail=validate_result.get("error", "Template validation failed"))

        stack_name = f"resolvify-{project.id}"
        create_result = await cf_service.create_stack(
            stack_name=stack_name, template_body=template_content,
            parameters=request.variables, region=request.region or "us-east-1",
            aws_access_key_id=credentials.get("aws_access_key_id"),
            aws_secret_access_key=credentials.get("aws_secret_access_key"),
        )
        if not create_result["success"]:
            await project_service.update_project_state(project_id=project.id, tenant_id=tenant_id, state="failed", db=db)
            raise HTTPException(status_code=500, detail=create_result.get("error", "Failed to create stack"))

        await project_service.update_project_state(
            project_id=project.id, tenant_id=tenant_id, state="active",
            outputs={"stack_id": create_result.get("stack_id")}, db=db,
        )
