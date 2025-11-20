"""
Factory for creating connector instances
"""
from app.services.infrastructure.base_connector import InfrastructureConnector
from app.services.infrastructure.ssh_connector import SSHConnector
from app.services.infrastructure.winrm_connector import WinRMConnector
from app.services.infrastructure.ssm_connector import SSMConnector
from app.services.infrastructure.database_connector import DatabaseConnector
from app.services.infrastructure.api_connector import APIConnector
from app.services.infrastructure.network_cluster_connector import NetworkClusterConnector
from app.services.infrastructure.network_device_connector import NetworkDeviceConnector
from app.services.infrastructure.azure_connector import AzureBastionConnector
from app.services.infrastructure.gcp_connector import GcpIapConnector
from app.services.infrastructure.local_connector import LocalConnector


def get_connector(connector_type: str) -> InfrastructureConnector:
    """Get connector instance by type"""
    connectors = {
        "ssh": SSHConnector(),
        "winrm": WinRMConnector(),
        "aws_ssm": SSMConnector(),
        "ssm": SSMConnector(),
        "database": DatabaseConnector(),
        "api": APIConnector(),
        "network_cluster": NetworkClusterConnector(),
        "network_device": NetworkDeviceConnector(),
        "azure_bastion": AzureBastionConnector(),
        "gcp_iap": GcpIapConnector(),
        "local": LocalConnector()
    }
    
    connector = connectors.get(connector_type.lower())
    if not connector:
        raise ValueError(f"Unknown connector type: {connector_type}")
    
    return connector


