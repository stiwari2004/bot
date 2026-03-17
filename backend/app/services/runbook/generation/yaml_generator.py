"""
YAML generator for different service types
"""
from typing import Dict, Any, Tuple
from app.services.runbook.generation.yaml_service_mixin import YamlServiceMixin


class YamlGenerator(YamlServiceMixin):
    """Generates YAML runbooks for different service types.

    Service implementations in YamlServiceMixin:
      generate_server_yaml, generate_database_yaml, generate_web_application_yaml,
      generate_storage_yaml, generate_network_connectivity_yaml
    """

    def generate_yaml(self, service: str, issue: str, env: str, risk: str) -> Tuple[str, Dict[str, Any]]:
        """Dispatch to the appropriate service-specific generator."""
        dispatch = {
            "server": self.generate_server_yaml,
            "database": self.generate_database_yaml,
            "web": self.generate_web_application_yaml,
            "storage": self.generate_storage_yaml,
            "network": self.generate_network_connectivity_yaml,
        }
        generator = dispatch.get(service, self.generate_server_yaml)
        return generator(issue, env, risk)
