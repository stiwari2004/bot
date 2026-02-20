"""
ServiceNow-specific input extractor (structured metadata only).
CI and u_* custom fields. Description/title parsing is tool-agnostic (see text_extractor).
"""
from typing import Dict, Any
from app.models.ticket import Ticket
from app.services.runbook.input_extractors.base_extractor import BaseInputExtractor
from app.core.logging import get_logger

logger = get_logger(__name__)


class ServiceNowInputExtractor(BaseInputExtractor):
    """Extract from ServiceNow structured metadata only: CI (configuration_item) and u_* custom fields."""

    def extract(self, ticket: Ticket, runbook_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Extract from ServiceNow CI and custom fields. Text in description is handled by tool-agnostic extractor."""
        inputs = {}
        meta = ticket.meta_data or {}
        raw = ticket.raw_payload or {}
        
        # ServiceNow CI (Configuration Item) - most reliable
        ci = raw.get("configuration_item") or meta.get("ci") or raw.get("u_configuration_item") or meta.get("cmdb_ci")
        if ci:
            if isinstance(ci, dict):
                inputs["server_name"] = ci.get("name") or ci.get("host_name") or ci.get("fqdn")
                inputs["host_ip"] = ci.get("ip_address") or ci.get("u_ip_address") or ci.get("ip")
            elif isinstance(ci, str):
                inputs["server_name"] = ci
        
        # ServiceNow custom fields (u_* prefix)
        custom_field_mappings = {
            "u_vpn_service": "vpn_service_name",
            "u_vpn_service_name": "vpn_service_name",
            "u_interface": "interface",
            "u_network_interface": "interface",
            "u_host_ip": "host_ip",
            "u_gateway_ip": "gateway_ip",
            "u_gateway": "gateway_ip",
            "u_service_name": "service_name",
        }
        
        # Check both raw payload and metadata
        for sn_field, input_name in custom_field_mappings.items():
            value = raw.get(sn_field) or meta.get(sn_field)
            if value:
                inputs[input_name] = value

        logger.info(f"ServiceNow (structured) found {len(inputs)} inputs: {list(inputs.keys())}")
        return inputs
    
    def get_confidence(self, extracted: Dict[str, Any]) -> Dict[str, float]:
        """Return confidence scores for extracted inputs"""
        confidence = {}
        
        for key in extracted.keys():
            if key in ["server_name", "host_ip"]:
                confidence[key] = 0.95  # From CI - very reliable
            elif key == "vpn_service_name":
                confidence[key] = 0.8  # From custom field
            elif key == "interface":
                confidence[key] = 0.75  # From custom field or inferred
            elif key == "gateway_ip":
                confidence[key] = 0.8  # From custom field
            else:
                confidence[key] = 0.7  # Default confidence
        
        return confidence
    