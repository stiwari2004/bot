"""
Tool-agnostic text extractor.
Extracts runbook inputs (host_ip, server_name, etc.) from plain ticket text.
Used for all ticket sources (ServiceNow, Zendesk, Jira, ManageEngine, api_poll, etc.).
"""
import re
from typing import Dict, Any, List


def _get_all_input_names(runbook_spec: Dict[str, Any]) -> List[str]:
    """Return list of input names declared in runbook spec."""
    inputs = runbook_spec.get("inputs", [])
    if not isinstance(inputs, list):
        return []
    return [inp.get("name") for inp in inputs if isinstance(inp, dict) and inp.get("name")]


def extract_inputs_from_text(text: str, runbook_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract runbook input values from arbitrary ticket text (title, description, etc.).
    Tool-agnostic: same logic for ServiceNow, Zendesk, Jira, ManageEngine, or any source.

    Args:
        text: Combined ticket text (e.g. title + description + any meta string values).
        runbook_spec: Parsed runbook YAML with "inputs" section.

    Returns:
        Dict of input name -> value for host_ip, server_name, gateway_ip, vpn_service_name, interface, database_name.
    """
    if not (text and text.strip()):
        return {}
    inputs: Dict[str, Any] = {}
    all_inputs = _get_all_input_names(runbook_spec)

    # IP addresses
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    ips = re.findall(ip_pattern, text)
    if ips:
        if "host_ip" in all_inputs:
            inputs["host_ip"] = ips[0]
        if "gateway_ip" in all_inputs and len(ips) > 1:
            inputs["gateway_ip"] = ips[1]

    # Server/host name: "Host: name", "Server: name", FQDN, or name next to IP
    if "server_name" in all_inputs:
        for prefix in ("host", "server", "node", "ci", "machine", "target"):
            m = re.search(rf'\b{prefix}\s*[:\-=]\s*([a-zA-Z0-9_.-]+)\b', text, re.IGNORECASE)
            if m:
                inputs["server_name"] = m.group(1).strip()
                break
        if "server_name" not in inputs:
            hostname_pattern = r'\b([a-z0-9][a-z0-9_.-]*\.(?:[a-z0-9-]+\.)*[a-z]{2,})\b'
            hostnames = re.findall(hostname_pattern, text, re.IGNORECASE)
            if hostnames:
                inputs["server_name"] = min(hostnames, key=len)
            else:
                adj = re.search(
                    r'\b([a-z0-9][a-z0-9_.-]{2,})\s+[\d.]+\d|\b[\d.]+\d\s+([a-z0-9][a-z0-9_.-]{2,})\b',
                    text, re.IGNORECASE
                )
                if adj:
                    inputs["server_name"] = (adj.group(1) or adj.group(2) or "").strip()
                else:
                    simple = re.search(
                        r'\b(server[_-]?[0-9]+|host[_-]?[0-9]+|srv[0-9]+|node[0-9]*)\b',
                        text, re.IGNORECASE
                    )
                    if simple:
                        inputs["server_name"] = simple.group(1)

    # VPN/service names
    if "vpn_service_name" in all_inputs:
        service_pattern = r'\b(openvpn|strongswan|networkmanager|wireguard|network-manager|networkmanager-l2tp)\b'
        services = re.findall(service_pattern, text, re.IGNORECASE)
        if services:
            inputs["vpn_service_name"] = services[0]

    # Interface names
    if "interface" in all_inputs:
        interface_pattern = r'\b(eth\d+|ens\d+|enp\d+s\d+|wlan\d+|tun\d+|tap\d+)\b'
        interfaces = re.findall(interface_pattern, text, re.IGNORECASE)
        if interfaces:
            inputs["interface"] = interfaces[0]

    # Database names
    if "database_name" in all_inputs:
        db_pattern = r'\b(database|db)[\s:]+([a-z0-9_-]+)\b'
        db_matches = re.findall(db_pattern, text, re.IGNORECASE)
        if db_matches:
            inputs["database_name"] = db_matches[0][1]

    return inputs
