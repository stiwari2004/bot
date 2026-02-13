"""
Remote servers scanner package: discover Linux/Windows servers, databases via SSH/WinRM.
Modular architecture: connectors, discoverers, parsers, orchestrator.
"""
from .orchestrator import scan_remote_servers

__all__ = ["scan_remote_servers"]
