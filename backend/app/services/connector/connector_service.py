"""
Connector service for business logic: testing, discovery, command execution
"""
from app.services.connector.connector_testing_mixin import ConnectorTestingMixin
from app.services.connector.connector_discovery_mixin import ConnectorDiscoveryMixin
from app.services.connector.connector_command_mixin import ConnectorCommandMixin


class ConnectorService(ConnectorTestingMixin, ConnectorDiscoveryMixin, ConnectorCommandMixin):
    """Business logic for connector operations"""
