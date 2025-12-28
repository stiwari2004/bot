"""
Type definitions for SolarWinds integration
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class SolarWindsAlert:
    """SolarWinds alert representation"""
    alert_id: str
    name: str
    message: str
    severity: str  # Critical, Error, Warning, Information
    state: str  # Active, Acknowledged, Resolved
    entity_type: str  # Node, Interface, etc.
    entity_name: str
    entity_id: str
    triggered_time: datetime
    acknowledged_time: Optional[datetime] = None
    resolved_time: Optional[datetime] = None
    custom_properties: Dict[str, Any] = None


@dataclass
class SolarWindsNode:
    """SolarWinds node/device representation"""
    node_id: str
    caption: str
    ip_address: str
    status: str  # Up, Down, Unknown
    node_type: str
    custom_properties: Dict[str, Any] = None


@dataclass
class SolarWindsConnectionConfig:
    """SolarWinds connection configuration"""
    api_base_url: str  # e.g., https://your-instance.solarwinds.com
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    oauth_token: Optional[str] = None
    oauth_token_expires: Optional[datetime] = None

