"""
CloudFormation service for executing CloudFormation stacks
"""
import json
import boto3
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError
from app.core.logging import get_logger

logger = get_logger(__name__)


class CloudFormationService:
    """Service for executing CloudFormation operations"""
    
    def __init__(self):
        self.cf_client = None
    
    def _get_client(self, region: str = "us-east-1", aws_access_key_id: Optional[str] = None, aws_secret_access_key: Optional[str] = None):
        """Get CloudFormation client"""
        if not self.cf_client:
            session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region
            )
            self.cf_client = session.client('cloudformation')
        return self.cf_client
    
    async def validate_template(
        self,
        template_body: Optional[str] = None,
        template_url: Optional[str] = None,
        region: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a CloudFormation template
        
        Args:
            template_body: Template content as string
            template_url: URL to template (S3)
            region: AWS region
            aws_access_key_id: AWS access key
            aws_secret_access_key: AWS secret key
            
        Returns:
            Dict with validation results
        """
        try:
            client = self._get_client(region, aws_access_key_id, aws_secret_access_key)
            
            params = {}
            if template_body:
                params["TemplateBody"] = template_body
            elif template_url:
                params["TemplateURL"] = template_url
            else:
                return {
                    "success": False,
                    "valid": False,
                    "error": "Either template_body or template_url must be provided"
                }
            
            response = client.validate_template(**params)
            
            return {
                "success": True,
                "valid": True,
                "description": response.get("Description"),
                "parameters": response.get("Parameters", [])
            }
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            
            return {
                "success": False,
                "valid": False,
                "error": error_message,
                "error_code": error_code
            }
        except Exception as e:
            logger.error(f"Error validating CloudFormation template: {e}")
            return {
                "success": False,
                "valid": False,
                "error": str(e)
            }
    
    async def create_stack(
        self,
        stack_name: str,
        template_body: Optional[str] = None,
        template_url: Optional[str] = None,
        parameters: Optional[Dict[str, str]] = None,
        capabilities: Optional[list] = None,
        region: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a CloudFormation stack
        
        Args:
            stack_name: Name of the stack
            template_body: Template content
            template_url: URL to template
            parameters: Stack parameters
            capabilities: Required capabilities (e.g., ["CAPABILITY_IAM"])
            region: AWS region
            aws_access_key_id: AWS access key
            aws_secret_access_key: AWS secret key
            
        Returns:
            Dict with stack creation results
        """
        try:
            client = self._get_client(region, aws_access_key_id, aws_secret_access_key)
            
            params = {
                "StackName": stack_name
            }
            
            if template_body:
                params["TemplateBody"] = template_body
            elif template_url:
                params["TemplateURL"] = template_url
            else:
                return {
                    "success": False,
                    "error": "Either template_body or template_url must be provided"
                }
            
            if parameters:
                params["Parameters"] = [
                    {"ParameterKey": k, "ParameterValue": v}
                    for k, v in parameters.items()
                ]
            
            if capabilities:
                params["Capabilities"] = capabilities
            
            response = client.create_stack(**params)
            
            return {
                "success": True,
                "stack_id": response.get("StackId"),
                "stack_name": stack_name
            }
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            
            return {
                "success": False,
                "error": error_message,
                "error_code": error_code
            }
        except Exception as e:
            logger.error(f"Error creating CloudFormation stack: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_stack(
        self,
        stack_name: str,
        template_body: Optional[str] = None,
        template_url: Optional[str] = None,
        parameters: Optional[Dict[str, str]] = None,
        capabilities: Optional[list] = None,
        region: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update an existing CloudFormation stack"""
        try:
            client = self._get_client(region, aws_access_key_id, aws_secret_access_key)
            
            params = {
                "StackName": stack_name
            }
            
            if template_body:
                params["TemplateBody"] = template_body
            elif template_url:
                params["TemplateURL"] = template_url
            
            if parameters:
                params["Parameters"] = [
                    {"ParameterKey": k, "ParameterValue": v}
                    for k, v in parameters.items()
                ]
            
            if capabilities:
                params["Capabilities"] = capabilities
            
            response = client.update_stack(**params)
            
            return {
                "success": True,
                "stack_id": response.get("StackId"),
                "stack_name": stack_name
            }
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            
            # Stack doesn't exist or no updates
            if error_code == "ValidationError" and "No updates" in error_message:
                return {
                    "success": True,
                    "message": "No updates to perform"
                }
            
            return {
                "success": False,
                "error": error_message,
                "error_code": error_code
            }
        except Exception as e:
            logger.error(f"Error updating CloudFormation stack: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_stack(
        self,
        stack_name: str,
        region: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete a CloudFormation stack"""
        try:
            client = self._get_client(region, aws_access_key_id, aws_secret_access_key)
            
            client.delete_stack(StackName=stack_name)
            
            return {
                "success": True,
                "stack_name": stack_name
            }
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            
            return {
                "success": False,
                "error": error_message,
                "error_code": error_code
            }
        except Exception as e:
            logger.error(f"Error deleting CloudFormation stack: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_stack_status(
        self,
        stack_name: str,
        region: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get CloudFormation stack status"""
        try:
            client = self._get_client(region, aws_access_key_id, aws_secret_access_key)
            
            response = client.describe_stacks(StackName=stack_name)
            
            if not response.get("Stacks"):
                return {
                    "success": False,
                    "error": "Stack not found"
                }
            
            stack = response["Stacks"][0]
            
            return {
                "success": True,
                "stack_name": stack.get("StackName"),
                "stack_id": stack.get("StackId"),
                "stack_status": stack.get("StackStatus"),
                "stack_status_reason": stack.get("StackStatusReason"),
                "outputs": stack.get("Outputs", []),
                "parameters": stack.get("Parameters", [])
            }
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            
            return {
                "success": False,
                "error": error_message,
                "error_code": error_code
            }
        except Exception as e:
            logger.error(f"Error getting stack status: {e}")
            return {
                "success": False,
                "error": str(e)
            }

