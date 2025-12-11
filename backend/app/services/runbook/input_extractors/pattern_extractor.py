"""
Pattern-based input extractor (fallback)
Extracts inputs using regex patterns from ticket description/title
"""
import re
from typing import Dict, Any
from app.models.ticket import Ticket
from app.services.runbook.input_extractors.base_extractor import BaseInputExtractor
from app.core.logging import get_logger

logger = get_logger(__name__)


class PatternInputExtractor(BaseInputExtractor):
    """Extract inputs using pattern matching (fallback method)"""
    
    def extract(self, ticket: Ticket, runbook_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract inputs using regex patterns from ticket text.
        This is a fallback method when source-specific extractors don't find values.
        """
        inputs = {}
        
        # Combine all text sources
        text = f"{ticket.title or ''} {ticket.description or ''}"
        if ticket.meta_data and isinstance(ticket.meta_data, dict):
            # Add metadata text fields
            for key, value in ticket.meta_data.items():
                if isinstance(value, str):
                    text += f" {value}"
        
        if not text.strip():
            return inputs
        
        all_inputs = self._get_all_inputs(runbook_spec)
        
        # IP addresses
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        ips = re.findall(ip_pattern, text)
        if ips:
            if "host_ip" in all_inputs and "host_ip" not in inputs:
                inputs["host_ip"] = ips[0]
            if "gateway_ip" in all_inputs and "gateway_ip" not in inputs and len(ips) > 1:
                inputs["gateway_ip"] = ips[1]
        
        # Service names (VPN services)
        vpn_service_pattern = r'\b(openvpn|strongswan|networkmanager|wireguard|network-manager|networkmanager-l2tp)\b'
        vpn_services = re.findall(vpn_service_pattern, text, re.IGNORECASE)
        if vpn_services and "vpn_service_name" in all_inputs:
            inputs["vpn_service_name"] = vpn_services[0]
        
        # Interface names
        interface_pattern = r'\b(eth\d+|ens\d+|enp\d+s\d+|wlan\d+|tun\d+|tap\d+)\b'
        interfaces = re.findall(interface_pattern, text, re.IGNORECASE)
        if interfaces and "interface" in all_inputs:
            inputs["interface"] = interfaces[0]
        
        # Server/host names (FQDN or hostname patterns)
        hostname_pattern = r'\b([a-z0-9-]+\.(?:[a-z0-9-]+\.)*[a-z]{2,})\b'
        hostnames = re.findall(hostname_pattern, text, re.IGNORECASE)
        if hostnames and "server_name" in all_inputs:
            # Prefer shorter hostnames (likely server names)
            hostname = min(hostnames, key=len)
            inputs["server_name"] = hostname
        
        # Database names
        db_pattern = r'\b(database|db)[\s:]+([a-z0-9_-]+)\b'
        db_matches = re.findall(db_pattern, text, re.IGNORECASE)
        if db_matches and "database_name" in all_inputs:
            inputs["database_name"] = db_matches[0][1]
        
        logger.info(f"Pattern extractor found {len(inputs)} inputs: {list(inputs.keys())}")
        return inputs
    
    def get_confidence(self, extracted: Dict[str, Any]) -> Dict[str, float]:
        """Return confidence scores for pattern-extracted inputs (lower confidence)"""
        # Pattern matching has lower confidence than metadata extraction
        return {key: 0.6 for key in extracted.keys()}




