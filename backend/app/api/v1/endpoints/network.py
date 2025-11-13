"""
Network inventory and metadata endpoints.
"""
from typing import Dict, List

from fastapi import APIRouter, HTTPException

router = APIRouter()

_NETWORK_CLUSTERS: List[Dict[str, str]] = [
    {
        "id": "core-campus-a",
        "name": "Campus Core - Building A",
        "description": "Core aggregation switches for Building A campus segment",
        "vendor": "Cisco",
        "management_host": "core-a.example.net",
        "transport": "ssh",
        "default_prompt": "core-a#",
    },
    {
        "id": "core-datacenter-1",
        "name": "Datacenter Spine Cluster 1",
        "description": "Spine switches inside primary DC",
        "vendor": "Juniper",
        "management_host": "dc1-spine.example.net",
        "transport": "ssh",
        "default_prompt": "dc1-spine>",
    },
]

_CLUSTER_DEVICES: Dict[str, List[Dict[str, str]]] = {
    "core-campus-a": [
        {
            "id": "edge-a-01",
            "name": "Edge Switch A-01",
            "vendor": "Cisco",
            "model": "Catalyst 9300",
            "role": "access",
            "mgmt_ip": "10.50.10.21",
        },
        {
            "id": "edge-a-02",
            "name": "Edge Switch A-02",
            "vendor": "Cisco",
            "model": "Catalyst 9300",
            "role": "access",
            "mgmt_ip": "10.50.10.22",
        },
    ],
    "core-datacenter-1": [
        {
            "id": "leaf-dc1-11",
            "name": "Leaf Switch DC1-11",
            "vendor": "Juniper",
            "model": "QFX5120",
            "role": "leaf",
            "mgmt_ip": "10.80.10.31",
        },
        {
            "id": "leaf-dc1-12",
            "name": "Leaf Switch DC1-12",
            "vendor": "Juniper",
            "model": "QFX5120",
            "role": "leaf",
            "mgmt_ip": "10.80.10.32",
        },
    ],
}


@router.get("/clusters", tags=["network"])
async def list_clusters():
    """Return known network clusters that can be connected to."""
    return {"clusters": _NETWORK_CLUSTERS}


@router.get("/clusters/{cluster_id}/devices", tags=["network"])
async def list_cluster_devices(cluster_id: str):
    """Return network devices that belong to a specific cluster."""
    if cluster_id not in _CLUSTER_DEVICES:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return {"cluster_id": cluster_id, "devices": _CLUSTER_DEVICES[cluster_id]}


