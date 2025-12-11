"""
Datadog-specific input extractor
Extracts inputs from Datadog alert metadata (tags, host, service, etc.)
"""
import re
from typing import Dict, Any
from app.models.ticket import Ticket
from app.services.runbook.input_extractors.base_extractor import BaseInputExtractor
from app.core.logging import get_logger

logger = get_logger(__name__)


class DatadogInputExtractor(BaseInputExtractor):
    """Extract inputs from Datadog alert metadata"""
    
    def extract(self, ticket: Ticket, runbook_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract inputs from Datadog ticket metadata.
        
        Datadog metadata typically contains:
        - tags: List of "key:value" strings
        - host: Hostname or IP
        - service: Service name
        - metric: Metric name
        - alert: Alert details
        """
        inputs = {}
        meta = ticket.meta_data or {}
        raw = ticket.raw_payload or {}
        
        # Parse Datadog tags (most reliable source)
        tags = raw.get("tags", []) or meta.get("tags", [])
        tag_dict = self._parse_tags(tags)
        
        # Extract host information
        host = raw.get("host") or tag_dict.get("host") or meta.get("host")
        if host:
            inputs["server_name"] = host
            # Try to extract IP from hostname or tags
            host_ip = self._extract_ip_from_host(host, tag_dict, raw, meta)
            if host_ip:
                inputs["host_ip"] = host_ip
        
        # Extract service information
        service = tag_dict.get("service") or raw.get("service") or meta.get("service")
        if service:
            # Map to common input names
            if "vpn" in service.lower():
                inputs["vpn_service_name"] = service
            else:
                # Generic service name
                inputs["service_name"] = service
        
        # Extract interface from tags
        interface = tag_dict.get("interface") or tag_dict.get("device") or tag_dict.get("net_interface")
        if interface:
            inputs["interface"] = interface
        
        # Extract gateway IP from tags or metadata
        gateway = tag_dict.get("gateway") or tag_dict.get("gateway_ip") or meta.get("gateway_ip")
        if gateway:
            inputs["gateway_ip"] = gateway
        
        # Extract VPN-specific information
        vpn_service = tag_dict.get("vpn_service") or meta.get("vpn_service_name")
        if vpn_service:
            inputs["vpn_service_name"] = vpn_service
        
        # Extract from alert message/description
        description = ticket.description or raw.get("text", "") or meta.get("message", "")
        if description:
            inputs.update(self._extract_from_description(description, runbook_spec))
        
        logger.info(f"Datadog extractor found {len(inputs)} inputs: {list(inputs.keys())}")
        return inputs
    
    def get_confidence(self, extracted: Dict[str, Any]) -> Dict[str, float]:
        """Return confidence scores for extracted inputs"""
        confidence = {}
        
        # Higher confidence for metadata fields, lower for patterns
        for key in extracted.keys():
            if key in ["server_name", "host_ip"]:
                confidence[key] = 0.9  # From host tag/metadata
            elif key == "vpn_service_name":
                confidence[key] = 0.8  # From service tag
            elif key == "interface":
                confidence[key] = 0.7  # May be inferred
            elif key == "gateway_ip":
                confidence[key] = 0.75  # From tags
            else:
                confidence[key] = 0.6  # Lower confidence for others
        
        return confidence
    
    def _parse_tags(self, tags: list) -> Dict[str, str]:
        """Parse Datadog tags into dictionary"""
        result = {}
        if not tags:
            return result
        
        for tag in tags:
            if isinstance(tag, str) and ":" in tag:
                key, value = tag.split(":", 1)
                result[key.strip()] = value.strip()
            elif isinstance(tag, dict):
                # Handle dict format tags
                for k, v in tag.items():
                    result[k] = str(v)
        
        return result
    
    def _extract_ip_from_host(self, host: str, tag_dict: Dict, raw: Dict, meta: Dict) -> str:
        """Extract IP address from host or metadata"""
        # Check if host is already an IP
        ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
        if re.match(ip_pattern, host):
            return host
        
        # Check tags for IP
        ip = tag_dict.get("ip") or tag_dict.get("ip_address") or tag_dict.get("host_ip")
        if ip:
            return ip
        
        # Check metadata
        ip = meta.get("ip") or meta.get("ip_address") or meta.get("host_ip")
        if ip:
            return ip
        
        # Check raw payload
        ip = raw.get("ip") or raw.get("ip_address") or raw.get("host_ip")
        if ip:
            return ip
        
        return None
    
    def _extract_from_description(self, description: str, runbook_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Extract inputs from description text using patterns"""
        inputs = {}
        
        # IP addresses
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        ips = re.findall(ip_pattern, description)
        if ips:
            # Check if host_ip is needed
            required = self._get_required_inputs(runbook_spec)
            if "host_ip" in required and "host_ip" not in inputs:
                inputs["host_ip"] = ips[0]
            elif "gateway_ip" in required and "gateway_ip" not in inputs and len(ips) > 1:
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




