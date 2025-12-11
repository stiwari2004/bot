"""
ServiceNow-specific input extractor
Extracts inputs from ServiceNow incident metadata (CI fields, custom fields, etc.)
"""
import re
from typing import Dict, Any
from app.models.ticket import Ticket
from app.services.runbook.input_extractors.base_extractor import BaseInputExtractor
from app.core.logging import get_logger

logger = get_logger(__name__)


class ServiceNowInputExtractor(BaseInputExtractor):
    """Extract inputs from ServiceNow incident metadata"""
    
    def extract(self, ticket: Ticket, runbook_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract inputs from ServiceNow ticket metadata.
        
        ServiceNow metadata typically contains:
        - configuration_item: CI object with name, ip_address, etc.
        - u_* fields: Custom fields
        - cmdb_ci: Configuration item reference
        """
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
        
        # Extract from description/notes
        description = ticket.description or raw.get("description", "") or raw.get("comments", "") or meta.get("description", "")
        if description:
            inputs.update(self._extract_from_description(description, runbook_spec))
        
        # Extract from short_description
        short_desc = ticket.title or raw.get("short_description", "") or meta.get("short_description", "")
        if short_desc:
            inputs.update(self._extract_from_description(short_desc, runbook_spec))
        
        logger.info(f"ServiceNow extractor found {len(inputs)} inputs: {list(inputs.keys())}")
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
    
    def _extract_from_description(self, description: str, runbook_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Extract inputs from description text using patterns"""
        inputs = {}
        
        # IP addresses
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        ips = re.findall(ip_pattern, description)
        if ips:
            required = self._get_required_inputs(runbook_spec)
            all_inputs = self._get_all_inputs(runbook_spec)
            
            if "host_ip" in all_inputs and "host_ip" not in inputs:
                inputs["host_ip"] = ips[0]
            if "gateway_ip" in all_inputs and "gateway_ip" not in inputs and len(ips) > 1:
                inputs["gateway_ip"] = ips[1]
        
        # Service names
        service_pattern = r'\b(openvpn|strongswan|networkmanager|wireguard|network-manager)\b'
        services = re.findall(service_pattern, description, re.IGNORECASE)
        if services:
            if "vpn_service_name" in self._get_all_inputs(runbook_spec):
                inputs["vpn_service_name"] = services[0]
        
        # Interface names
        interface_pattern = r'\b(eth\d+|ens\d+|enp\d+s\d+|wlan\d+|tun\d+|tap\d+)\b'
        interfaces = re.findall(interface_pattern, description, re.IGNORECASE)
        if interfaces:
            if "interface" in self._get_all_inputs(runbook_spec):
                inputs["interface"] = interfaces[0]
        
        return inputs




