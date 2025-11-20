"""
Service type classification for runbook generation
"""
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
        
        # Network keywords with weights
        network_patterns = {
            'network connectivity': 3, 'network issue': 3, 'connection lost': 3,
            'ping': 2, 'traceroute': 2, 'dns': 2, 'dns resolution': 2,
            'firewall': 2, 'switch': 2, 'router': 2, 'cable': 2,
            'ip address': 2, 'subnet': 2, 'vlan': 2, 'routing': 2,
            'network': 1, 'connectivity': 1
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




