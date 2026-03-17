"""
Mixin: static connector catalog listings
"""
from typing import Dict, Any


class ConnectorCatalogMixin:
    """Catalog listing operations for ConnectorController."""

    def list_monitoring_connectors(self) -> Dict[str, Any]:
        """List available monitoring tool connectors"""
        return {
            "available_connectors": [
                {
                    "type": "datadog",
                    "name": "Datadog",
                    "status": "implemented",
                    "description": "Cloud monitoring and alerting platform",
                    "webhook_supported": True,
                    "api_supported": True,
                },
                {
                    "type": "azure_monitor",
                    "name": "Azure Monitor",
                    "status": "implemented",
                    "description": "Microsoft Azure monitoring and alerting service",
                    "webhook_supported": True,
                    "api_supported": False,
                },
                {
                    "type": "prometheus",
                    "name": "Prometheus Alertmanager",
                    "status": "implemented",
                    "description": "Open-source monitoring and alerting toolkit",
                    "webhook_supported": True,
                    "api_supported": False,
                },
                {
                    "type": "solarwinds",
                    "name": "SolarWinds Orion",
                    "status": "implemented",
                    "description": "Network and infrastructure monitoring platform",
                    "webhook_supported": False,
                    "api_supported": True,
                },
                {
                    "type": "opmanager",
                    "name": "ManageEngine OpManager",
                    "status": "implemented",
                    "description": "On\u2011premise network and infrastructure monitoring (ManageEngine OpManager)",
                    "webhook_supported": False,
                    "api_supported": True,
                },
                {
                    "type": "splunk",
                    "name": "Splunk",
                    "status": "implemented",
                    "description": "Log aggregation, SIEM, and operational intelligence platform",
                    "webhook_supported": True,
                    "api_supported": True,
                    "hec_supported": True,
                },
                {
                    "type": "zabbix",
                    "name": "Zabbix",
                    "status": "planned",
                    "description": "Enterprise monitoring solution",
                },
                {
                    "type": "manageengine",
                    "name": "ManageEngine",
                    "status": "planned",
                    "description": "IT management suite",
                },
            ]
        }

    def list_ticketing_connectors(self) -> Dict[str, Any]:
        """List available ticketing system connectors"""
        return {
            "available_connectors": [
                {
                    "type": "servicenow",
                    "name": "ServiceNow",
                    "status": "implemented",
                    "description": "IT service management platform",
                },
                {
                    "type": "zendesk",
                    "name": "Zendesk",
                    "status": "planned",
                    "description": "Customer service platform",
                },
                {
                    "type": "manageengine",
                    "name": "ManageEngine ServiceDesk",
                    "status": "planned",
                    "description": "IT service desk solution",
                },
                {
                    "type": "bmcremedy",
                    "name": "BMC Remedy",
                    "status": "planned",
                    "description": "ITSM platform",
                },
            ]
        }
