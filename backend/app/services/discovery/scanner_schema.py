"""
Scanner output schema: payload shapes for agent vs jump-host modes.
Used by ingest API and gateway; agents/jump-host scanners send these structures.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --- L1 asset (from agent or VM manager) ---
class ScannerAssetPayload(BaseModel):
    """Single asset as reported by scanner/agent."""
    source: str = Field(..., description="e.g. discovered_via_connection, azure")
    source_native_id: str = Field(..., description="Stable ID from source")
    fingerprint: Optional[str] = Field(None, description="Hostname/FQDN or MAC; avoid port-set when possible")
    name: Optional[str] = None
    primary_ip: Optional[str] = None
    ips: List[str] = Field(default_factory=list)
    tags: Dict[str, str] = Field(default_factory=dict)


# --- L2 component ---
class ScannerComponentPayload(BaseModel):
    """Component (service endpoint) on an asset."""
    component_type: str = Field(..., description="e.g. postgres, redis, nginx")
    bind_address: Optional[str] = None
    port: Optional[int] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[str] = Field(None, description="high, medium, low")
    evidence: List[Dict[str, Any]] = Field(default_factory=list)


# --- L3 edge (connection) ---
class ScannerEdgePayload(BaseModel):
    """Outbound connection: from this asset/component to destination."""
    remote_addr: str = Field(..., description="IP or hostname")
    remote_port: Optional[int] = None
    from_component_type: Optional[str] = None
    edge_type: str = Field(default="tcp_connection")
    confidence: Optional[str] = None
    evidence: List[Dict[str, Any]] = Field(default_factory=list)


# --- Full payload from one agent (single host) ---
class AgentReportPayload(BaseModel):
    """
    Payload sent by agent for one host.
    Mode: agent (reports to gateway or directly to ingest).
    """
    asset: ScannerAssetPayload
    components: List[ScannerComponentPayload] = Field(default_factory=list)
    outbound_connections: List[ScannerEdgePayload] = Field(default_factory=list, alias="outbound_connections")
    run_id: Optional[int] = Field(None, description="If run was started by backend; else gateway assigns")

    class Config:
        populate_by_name = True


# --- Batch from jump-host scanner (multiple hosts) ---
class JumpHostBatchPayload(BaseModel):
    """
    Payload from jump-host scanner: multiple hosts in one batch.
    Mode: jump-host (scanner runs SSH/commands to targets, sends one batch per run).
    """
    run_id: Optional[int] = None
    hosts: List[AgentReportPayload] = Field(default_factory=list)
