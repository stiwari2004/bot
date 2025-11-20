"""
Infrastructure connectors for executing commands
POC version - simplified implementations

NOTE: This file is kept for backward compatibility.
New code should import from app.services.infrastructure instead.
"""
# Backward compatibility - re-export from new structure
from app.services.infrastructure import (
    InfrastructureConnector,
    get_connector,
    SSHConnector,
    WinRMConnector,
    SSMConnector,
    DatabaseConnector,
    APIConnector,
    NetworkClusterConnector,
    NetworkDeviceConnector,
    AzureBastionConnector,
    GcpIapConnector,
    LocalConnector,
)

__all__ = [
    "InfrastructureConnector",
    "get_connector",
    "SSHConnector",
    "WinRMConnector",
    "SSMConnector",
    "DatabaseConnector",
    "APIConnector",
    "NetworkClusterConnector",
    "NetworkDeviceConnector",
    "AzureBastionConnector",
    "GcpIapConnector",
    "LocalConnector",
]
