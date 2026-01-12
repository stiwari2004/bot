"""
AWS provider for infrastructure provisioning
"""
import boto3
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError
from app.core.logging import get_logger

logger = get_logger(__name__)


class AWSProvider:
    """AWS cloud provider integration"""
    
    def __init__(self):
        pass
    
    def _get_session(
        self,
        region: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ):
        """Get AWS session"""
        return boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region
        )
    
    async def create_ec2_instance(
        self,
        instance_type: str,
        image_id: str,
        key_name: Optional[str] = None,
        security_group_ids: Optional[List[str]] = None,
        subnet_id: Optional[str] = None,
        region: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create an EC2 instance"""
        try:
            session = self._get_session(region, aws_access_key_id, aws_secret_access_key)
            ec2 = session.client('ec2')
            
            params = {
                "ImageId": image_id,
                "InstanceType": instance_type,
                "MinCount": 1,
                "MaxCount": 1
            }
            
            if key_name:
                params["KeyName"] = key_name
            if security_group_ids:
                params["SecurityGroupIds"] = security_group_ids
            if subnet_id:
                params["SubnetId"] = subnet_id
            
            # Add any additional parameters
            params.update(kwargs)
            
            response = ec2.run_instances(**params)
            
            instance = response["Instances"][0]
            
            return {
                "success": True,
                "instance_id": instance["InstanceId"],
                "state": instance["State"]["Name"],
                "private_ip": instance.get("PrivateIpAddress"),
                "public_ip": instance.get("PublicIpAddress")
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
            logger.error(f"Error creating EC2 instance: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_vpc(
        self,
        cidr_block: str,
        region: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a VPC"""
        try:
            session = self._get_session(region, aws_access_key_id, aws_secret_access_key)
            ec2 = session.client('ec2')
            
            response = ec2.create_vpc(CidrBlock=cidr_block)
            vpc = response["Vpc"]
            
            return {
                "success": True,
                "vpc_id": vpc["VpcId"],
                "state": vpc["State"],
                "cidr_block": vpc["CidrBlock"]
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
            logger.error(f"Error creating VPC: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_subnet(
        self,
        vpc_id: str,
        cidr_block: str,
        availability_zone: Optional[str] = None,
        region: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a subnet"""
        try:
            session = self._get_session(region, aws_access_key_id, aws_secret_access_key)
            ec2 = session.client('ec2')
            
            params = {
                "VpcId": vpc_id,
                "CidrBlock": cidr_block
            }
            
            if availability_zone:
                params["AvailabilityZone"] = availability_zone
            
            response = ec2.create_subnet(**params)
            subnet = response["Subnet"]
            
            return {
                "success": True,
                "subnet_id": subnet["SubnetId"],
                "vpc_id": subnet["VpcId"],
                "cidr_block": subnet["CidrBlock"]
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
            logger.error(f"Error creating subnet: {e}")
            return {
                "success": False,
                "error": str(e)
            }

