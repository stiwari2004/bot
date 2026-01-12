"""
Terraform service for executing Terraform plans and applying infrastructure changes
"""
import os
import json
import subprocess
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path
from app.core.logging import get_logger

logger = get_logger(__name__)


class TerraformService:
    """Service for executing Terraform operations"""
    
    def __init__(self):
        self.terraform_binary = os.getenv("TERRAFORM_BINARY", "terraform")
    
    async def init_workspace(
        self,
        project_id: int,
        template_content: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Initialize a Terraform workspace for a project
        
        Args:
            project_id: Provisioning project ID
            template_content: Terraform configuration content
            variables: Optional variables to inject
            
        Returns:
            Dict with workspace_path and status
        """
        try:
            # Create temporary directory for this project
            workspace_path = Path(tempfile.mkdtemp(prefix=f"terraform_project_{project_id}_"))
            
            # Write main.tf
            main_tf = workspace_path / "main.tf"
            main_tf.write_text(template_content)
            
            # Write variables.tfvars if provided
            if variables:
                tfvars = workspace_path / "terraform.tfvars.json"
                tfvars.write_text(json.dumps(variables, indent=2))
            
            # Initialize Terraform
            result = await self._run_terraform_command(
                ["init"],
                workspace_path=workspace_path
            )
            
            if result["returncode"] != 0:
                return {
                    "success": False,
                    "error": result["stderr"],
                    "workspace_path": str(workspace_path)
                }
            
            return {
                "success": True,
                "workspace_path": str(workspace_path),
                "output": result["stdout"]
            }
            
        except Exception as e:
            logger.error(f"Error initializing Terraform workspace: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def plan(
        self,
        workspace_path: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a Terraform plan
        
        Args:
            workspace_path: Path to Terraform workspace
            variables: Optional variables to override
            
        Returns:
            Dict with plan output and changes
        """
        try:
            path = Path(workspace_path)
            if not path.exists():
                return {
                    "success": False,
                    "error": f"Workspace path does not exist: {workspace_path}"
                }
            
            # Write variables if provided
            if variables:
                tfvars = path / "terraform.tfvars.json"
                tfvars.write_text(json.dumps(variables, indent=2))
            
            # Run terraform plan
            result = await self._run_terraform_command(
                ["plan", "-out=tfplan", "-json"],
                workspace_path=path
            )
            
            if result["returncode"] != 0:
                return {
                    "success": False,
                    "error": result["stderr"],
                    "output": result["stdout"]
                }
            
            # Parse plan output (JSON format)
            plan_data = self._parse_plan_output(result["stdout"])
            
            return {
                "success": True,
                "plan_output": plan_data,
                "raw_output": result["stdout"]
            }
            
        except Exception as e:
            logger.error(f"Error running Terraform plan: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def apply(
        self,
        workspace_path: str,
        auto_approve: bool = False
    ) -> Dict[str, Any]:
        """
        Apply Terraform plan
        
        Args:
            workspace_path: Path to Terraform workspace
            auto_approve: Whether to auto-approve (skip confirmation)
            
        Returns:
            Dict with apply results and outputs
        """
        try:
            path = Path(workspace_path)
            if not path.exists():
                return {
                    "success": False,
                    "error": f"Workspace path does not exist: {workspace_path}"
                }
            
            # Check if plan file exists
            plan_file = path / "tfplan"
            if not plan_file.exists():
                return {
                    "success": False,
                    "error": "No plan file found. Run plan first."
                }
            
            # Run terraform apply
            cmd = ["apply", "-json"]
            if auto_approve:
                cmd.append("-auto-approve")
            else:
                cmd.append("tfplan")
            
            result = await self._run_terraform_command(
                cmd,
                workspace_path=path
            )
            
            if result["returncode"] != 0:
                return {
                    "success": False,
                    "error": result["stderr"],
                    "output": result["stdout"]
                }
            
            # Get outputs
            outputs = await self._get_outputs(path)
            
            # Get state
            state = await self._get_state(path)
            
            return {
                "success": True,
                "outputs": outputs,
                "state": state,
                "raw_output": result["stdout"]
            }
            
        except Exception as e:
            logger.error(f"Error running Terraform apply: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def destroy(
        self,
        workspace_path: str,
        auto_approve: bool = False
    ) -> Dict[str, Any]:
        """
        Destroy Terraform-managed infrastructure
        
        Args:
            workspace_path: Path to Terraform workspace
            auto_approve: Whether to auto-approve
            
        Returns:
            Dict with destroy results
        """
        try:
            path = Path(workspace_path)
            if not path.exists():
                return {
                    "success": False,
                    "error": f"Workspace path does not exist: {workspace_path}"
                }
            
            cmd = ["destroy", "-json"]
            if auto_approve:
                cmd.append("-auto-approve")
            
            result = await self._run_terraform_command(
                cmd,
                workspace_path=path
            )
            
            if result["returncode"] != 0:
                return {
                    "success": False,
                    "error": result["stderr"],
                    "output": result["stdout"]
                }
            
            return {
                "success": True,
                "raw_output": result["stdout"]
            }
            
        except Exception as e:
            logger.error(f"Error running Terraform destroy: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def validate(
        self,
        template_content: str
    ) -> Dict[str, Any]:
        """
        Validate Terraform configuration
        
        Args:
            template_content: Terraform configuration content
            
        Returns:
            Dict with validation results
        """
        try:
            # Create temporary directory
            temp_dir = Path(tempfile.mkdtemp(prefix="terraform_validate_"))
            main_tf = temp_dir / "main.tf"
            main_tf.write_text(template_content)
            
            # Run terraform validate
            result = await self._run_terraform_command(
                ["validate", "-json"],
                workspace_path=temp_dir
            )
            
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            if result["returncode"] != 0:
                return {
                    "success": False,
                    "valid": False,
                    "error": result["stderr"],
                    "output": result["stdout"]
                }
            
            return {
                "success": True,
                "valid": True,
                "output": result["stdout"]
            }
            
        except Exception as e:
            logger.error(f"Error validating Terraform configuration: {e}")
            return {
                "success": False,
                "valid": False,
                "error": str(e)
            }
    
    async def _run_terraform_command(
        self,
        cmd: List[str],
        workspace_path: Path
    ) -> Dict[str, Any]:
        """Run a Terraform command in the specified workspace"""
        import asyncio
        
        full_cmd = [self.terraform_binary] + cmd
        process = await asyncio.create_subprocess_exec(
            *full_cmd,
            cwd=str(workspace_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            "returncode": process.returncode,
            "stdout": stdout.decode("utf-8") if stdout else "",
            "stderr": stderr.decode("utf-8") if stderr else ""
        }
    
    def _parse_plan_output(self, output: str) -> Dict[str, Any]:
        """Parse Terraform plan JSON output"""
        try:
            # Terraform plan -json outputs multiple JSON objects, one per line
            lines = output.strip().split("\n")
            changes = []
            for line in lines:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if data.get("type") == "planned_change":
                            changes.append(data)
                    except json.JSONDecodeError:
                        continue
            
            return {
                "changes": changes,
                "change_count": len(changes)
            }
        except Exception as e:
            logger.warning(f"Error parsing plan output: {e}")
            return {
                "changes": [],
                "change_count": 0,
                "raw": output
            }
    
    async def _get_outputs(self, workspace_path: Path) -> Dict[str, Any]:
        """Get Terraform outputs"""
        try:
            result = await self._run_terraform_command(
                ["output", "-json"],
                workspace_path=workspace_path
            )
            
            if result["returncode"] == 0:
                return json.loads(result["stdout"])
            return {}
        except Exception as e:
            logger.warning(f"Error getting Terraform outputs: {e}")
            return {}
    
    async def _get_state(self, workspace_path: Path) -> Dict[str, Any]:
        """Get Terraform state"""
        try:
            result = await self._run_terraform_command(
                ["show", "-json"],
                workspace_path=workspace_path
            )
            
            if result["returncode"] == 0:
                return json.loads(result["stdout"])
            return {}
        except Exception as e:
            logger.warning(f"Error getting Terraform state: {e}")
            return {}

