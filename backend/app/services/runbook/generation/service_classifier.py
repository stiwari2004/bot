"""
Service type classification for runbook generation
"""
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class ServiceClassifier:
    """Service type detection using keyword matching"""
    
    async def detect_service_type(self, issue_description: str) -> str:
        """Detect service type using keyword matching only (LLM disabled due to inaccuracy)."""
        keyword_guess = self.keyword_classify_service_type(issue_description)
        logger.debug(f"Service detection: returning keyword={keyword_guess} (LLM classification disabled)")
        return keyword_guess
    
    def keyword_classify_service_type(self, issue_description: str) -> str:
        """Detect service type from issue description using enhanced keyword matching."""
        issue_lower = issue_description.lower()
        
        # Score each service type based on keyword matches
        scores = {
            'server': 0,
            'storage': 0,
            'database': 0,
            'web': 0,
            'network': 0
        }
        
        # Server keywords with weights (CPU, memory, general performance, local disk)
        server_patterns = {
            'server is': 3, 'server running': 3, 'server slow': 3, 'server performance': 3,
            'cpu usage': 3, 'high cpu': 3, 'cpu high': 3, 'cpu load': 3,
            'memory usage': 3, 'high memory': 3, 'memory high': 3, 'out of memory': 3,
            'server disk': 2, 'local disk': 2, 'server storage': 2,
            'performance issue': 2, 'slow server': 3, 'server timeout': 2,
            'resource': 1, 'server': 1, 'host': 1
        }
        
        # Storage keywords with weights (external storage systems)
        storage_patterns = {
            'nas': 3, 'san': 3, 'network storage': 3, 'network attached': 3,
            'storage array': 3, 'storage system': 3, 'shared storage': 3,
            'external storage': 3, 'storage network': 3,
            'nfs mount': 2, 'cifs mount': 2, 'network share': 2,
            'storage volume': 2, 'storage capacity': 2,
            'storage': 1  # Lower weight, can be ambiguous
        }
        
        # Database keywords with weights (specific DB issues)
        db_patterns = {
            'database': 3, 'db': 2, 'mysql': 3, 'postgres': 3, 'postgresql': 3,
            'oracle': 3, 'mongodb': 3, 'redis': 3, 'sql server': 3,
            'connection timeout': 2, 'query timeout': 2, 'slow query': 2,
            'connection pool': 2, 'deadlock': 2, 'transaction': 2,
            'sql': 1, 'query': 1
        }
        
        # Web application keywords with weights
        web_patterns = {
            'web server': 3, 'website': 3, 'web application': 3, 'web app': 3,
            'http error': 2, 'https error': 2, 'status code': 2, '404': 2, '500': 2,
            'api': 2, 'rest api': 2, 'endpoint': 2, 'response time': 2,
            'load balancer': 2, 'nginx': 2, 'apache': 2, 'iis': 2,
            'web': 1, 'http': 1, 'https': 1
        }
        
        # Network keywords with weights (enhanced for network devices)
        network_patterns = {
            'network connectivity': 3, 'network issue': 3, 'connection lost': 3,
            'ping': 2, 'traceroute': 2, 'dns': 2, 'dns resolution': 2,
            'firewall': 3, 'switch': 3, 'router': 3, 'load balancer': 3, 'access point': 3,
            'cisco': 2, 'juniper': 2, 'palo alto': 2, 'fortinet': 2, 'arista': 2,
            'ios': 2, 'nx-os': 2, 'junos': 2, 'ios-xe': 2, 'ios-xr': 2,
            'interface down': 3, 'port down': 3, 'interface error': 3, 'port error': 3,
            'vlan': 2, 'vlan down': 3, 'vlan issue': 3, 'spanning tree': 2, 'stp': 2,
            'routing': 2, 'bgp': 2, 'ospf': 2, 'eigrp': 2, 'static route': 2,
            'cable': 2, 'link down': 3, 'link error': 3, 'duplex': 2, 'speed': 2,
            'ip address': 2, 'subnet': 2, 'gateway': 2, 'default route': 2,
            'network': 1, 'connectivity': 1, 'packet loss': 2, 'latency': 2
        }
        
        # Calculate scores
        for pattern, weight in server_patterns.items():
            if pattern in issue_lower:
                scores['server'] += weight
                
        for pattern, weight in storage_patterns.items():
            if pattern in issue_lower:
                scores['storage'] += weight
                
        for pattern, weight in db_patterns.items():
            if pattern in issue_lower:
                scores['database'] += weight
                
        for pattern, weight in web_patterns.items():
            if pattern in issue_lower:
                scores['web'] += weight
                
        for pattern, weight in network_patterns.items():
            if pattern in issue_lower:
                scores['network'] += weight
        
        # Special handling: if "disk space" but no external storage indicators, it's server
        if 'disk space' in issue_lower or 'disk full' in issue_lower:
            if scores['storage'] < 2:  # No strong storage indicators
                scores['server'] += 3  # More likely server disk issue
                scores['storage'] = 0  # Suppress storage score
        
        # Return the service with highest score, default to server if tied
        max_score = max(scores.values())
        if max_score == 0:
            return "server"  # Default fallback (most common)
            
        for service, score in scores.items():
            if score == max_score:
                return service
                
        return "server"  # Final fallback
    
    def detect_issue_type(self, issue_description: str, service: str) -> str:
        """
        Detect the specific issue type within a service domain.
        Returns a structured issue type used for prompt injection, RAG filtering,
        and validation. Zero LLM cost — pure keyword matching.

        Examples:
          service=server, "disk space low"  → "low_disk"
          service=server, "high CPU usage"  → "high_cpu"
          service=database, "deadlock"      → "db_deadlock"
        """
        t = issue_description.lower()

        if service == "server":
            if any(k in t for k in ["high cpu", "cpu high", "cpu usage", "cpu load",
                                     "cpu spike", "cpu utilization", "processor usage",
                                     "100% cpu", "cpu 100"]):
                return "high_cpu"
            if any(k in t for k in ["out of memory", "oom", "memory high", "high memory",
                                     "memory usage", "memory pressure", "memory leak",
                                     "low memory", "available memory", "swap full"]):
                return "high_memory"
            if any(k in t for k in ["disk space", "disk full", "low disk", "disk usage",
                                     "no space left", "filesystem full", "out of disk",
                                     "disk capacity", "storage full", "running out of space"]):
                return "low_disk"
            if any(k in t for k in ["service down", "service failed", "service stopped",
                                     "daemon failed", "daemon stopped", "process crash",
                                     "process died", "application crash", "app crash",
                                     "service not running", "service unavailable"]):
                return "service_down"
            if any(k in t for k in ["unreachable", "not responding", "host down",
                                     "server down", "cannot connect", "connection refused",
                                     "ping failed", "server timeout", "host timeout"]):
                return "host_unreachable"
            return "server_performance"

        if service == "database":
            if any(k in t for k in ["slow query", "query slow", "query timeout",
                                     "long running query", "query performance", "slow sql"]):
                return "db_slow_query"
            if any(k in t for k in ["connection failed", "connection timeout", "cannot connect",
                                     "connection pool", "too many connections", "connection refused"]):
                return "db_connection_failure"
            if any(k in t for k in ["disk full", "transaction log full", "log full",
                                     "tablespace full", "no space", "disk space"]):
                return "db_disk_full"
            if any(k in t for k in ["deadlock", "lock wait", "lock timeout", "blocking query"]):
                return "db_deadlock"
            if any(k in t for k in ["replication", "replica lag", "slave lag", "sync delay",
                                     "replication error"]):
                return "db_replication_lag"
            return "db_general"

        if service == "web":
            if any(k in t for k in ["500", "502", "503", "504", "5xx", "internal server error",
                                     "bad gateway", "service unavailable", "gateway timeout"]):
                return "web_5xx"
            if any(k in t for k in ["slow response", "high latency", "response time",
                                     "performance", "slow api", "timeout"]):
                return "web_high_latency"
            if any(k in t for k in ["ssl", "certificate", "cert expired", "tls", "https error"]):
                return "web_cert_expired"
            if any(k in t for k in ["down", "unreachable", "not responding", "404",
                                     "connection refused", "web server down"]):
                return "web_service_down"
            return "web_general"

        if service == "network":
            if any(k in t for k in ["dns", "name resolution", "cannot resolve", "dns failure"]):
                return "dns_failure"
            if any(k in t for k in ["firewall", "blocked", "access denied", "port blocked",
                                     "traffic blocked"]):
                return "firewall_block"
            if any(k in t for k in ["interface down", "port down", "link down", "interface error",
                                     "nic down"]):
                return "interface_down"
            if any(k in t for k in ["latency", "packet loss", "slow network", "high ping"]):
                return "high_network_latency"
            if any(k in t for k in ["unreachable", "cannot connect", "connection lost",
                                     "network down", "no route"]):
                return "network_unreachable"
            return "network_general"

        if service == "storage":
            if any(k in t for k in ["stale", "hung mount", "frozen", "stale handle"]):
                return "stale_mount"
            if any(k in t for k in ["nfs", "cifs", "mount", "smb", "network share"]):
                return "nfs_mount_failure"
            if any(k in t for k in ["full", "capacity", "quota", "no space"]):
                return "storage_full"
            if any(k in t for k in ["access denied", "permission denied", "authentication failed"]):
                return "storage_access_denied"
            return "storage_general"

        return "general_issue"

    async def detect_os_type(self, issue_description: str) -> Optional[str]:
        """Detect OS type (Windows/Linux) from issue description."""
        issue_lower = issue_description.lower()
        
        # Windows indicators
        windows_keywords = [
            'windows', 'powershell', 'get-process', 'get-counter', 'get-service',
            'iis', 'wmi', 'win32', '.exe', 'c:\\', 'windows server'
        ]
        
        # Linux indicators
        linux_keywords = [
            'linux', 'ubuntu', 'centos', 'rhel', 'debian', 'systemctl', 'journalctl',
            'apt', 'yum', 'dnf', '/var/log', '/etc/', 'bash', 'shell script'
        ]
        
        windows_score = sum(1 for keyword in windows_keywords if keyword in issue_lower)
        linux_score = sum(1 for keyword in linux_keywords if keyword in issue_lower)
        
        if windows_score > linux_score and windows_score > 0:
            return "Windows"
        elif linux_score > windows_score and linux_score > 0:
            return "Linux"
        
        return None  # Could not detect OS type




