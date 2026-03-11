"""
Service type classification for runbook generation.

Uses phrase-level regex matching so that "server xyz is not responding" is
treated as a single contextual unit (subject + entity + predicate) rather than
isolated keyword hits.  Patterns are compiled once at import time (zero runtime
overhead beyond the first module load).
"""
import re
from typing import Optional, List, Tuple

from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compile(patterns: List[Tuple[str, int]]) -> List[Tuple[re.Pattern, int]]:
    """Compile a list of (regex_str, weight) tuples."""
    return [(re.compile(p, re.IGNORECASE), w) for p, w in patterns]


def _score(text: str, phrase_list: List[Tuple[re.Pattern, int]]) -> int:
    """Return cumulative score for all matching phrases in *text*."""
    return sum(w for pat, w in phrase_list if pat.search(text))


def _first_match(text: str, phrase_list: List[Tuple[re.Pattern, int]]) -> bool:
    """Return True if ANY phrase matches."""
    return any(pat.search(text) for pat, _ in phrase_list)


# ---------------------------------------------------------------------------
# Service-type phrase patterns
#
# Ordering inside each list: most-specific (highest weight) first so that the
# scoring reflects richer context.  Single-word catch-alls are kept at low
# weights (1) as a last-resort signal only.
# ---------------------------------------------------------------------------

# .{0,50} allows entity names ("server xyz", "host prod-db-01") between tokens
_SERVER_PHRASES = _compile([
    # "server <name> is not responding / unreachable / down / timed out"
    (r'\bserver\b.{0,50}\b(not\s+responding|unreachable|unresponsive|timed?\s*out|is\s+down|went\s+down|offline)\b', 8),
    (r'\b(host|node|vm|virtual\s+machine)\b.{0,50}\b(not\s+responding|unreachable|is\s+down|offline|unresponsive)\b', 8),
    # "cannot / unable to reach / connect / ssh to server <name>"
    (r'\b(cannot|can\'t|unable\s+to)\s+(reach|connect(\s+to)?|ping|ssh(\s+to)?|access)\b.{0,30}\b(server|host|node)\b', 7),
    # Resource saturation phrases
    (r'\b(high|elevated|critical|excessive)\s+(cpu|processor)\s*(usage|load|utilization)?\b', 7),
    (r'\b(cpu|processor)\s*(usage|load|utilization)?\b.{0,20}\b(high|critical|spiking|100\s*%|\d{2,3}\s*%)\b', 7),
    (r'\b(out\s+of\s+memory|oom\s+kill|memory\s+exhausted|memory\s+full|swap\s+full)\b', 7),
    (r'\b(high|elevated)\s+(memory|ram)\s*(usage|pressure)?\b', 6),
    (r'\b(disk|filesystem|volume|partition)\b.{0,30}\b(full|out\s+of\s+space|no\s+space\s+left|at\s+capacity)\b', 6),
    # Service/process crash
    (r'\b(service|process|daemon|application|app)\b.{0,30}\b(crashed?|died?|stopped|failed|not\s+running|keeps\s+restart)\b', 6),
    # Weak single-word fallbacks
    (r'\bserver\b', 1),
    (r'\bhost\b', 1),
    (r'\bnode\b', 1),
])

_STORAGE_PHRASES = _compile([
    (r'\b(nas|san|storage\s+array|storage\s+system|network\s+attached\s+storage|shared\s+storage)\b', 8),
    (r'\b(nfs|cifs|smb)\b.{0,20}\b(mount|share|volume|export)\b', 7),
    (r'\b(network\s+storage|external\s+storage|storage\s+network)\b', 7),
    (r'\b(storage\s+(capacity|quota|volume))\b.{0,20}\b(full|out\s+of\s+space|exhausted)\b', 6),
    (r'\b(nfs\s+mount|cifs\s+mount|network\s+share)\b', 5),
    (r'\bstorage\b', 1),
])

_DATABASE_PHRASES = _compile([
    # Named DB engines are highly specific
    (r'\b(mysql|postgres|postgresql|oracle|mongodb|redis|sql\s+server|mariadb|cassandra|elasticsearch)\b', 8),
    (r'\b(database|db)\b.{0,40}\b(down|unreachable|not\s+responding|connection\s+refused|failed)\b', 7),
    (r'\b(slow\s+query|query\s+timeout|long[\s-]running\s+query|query\s+performance)\b', 6),
    (r'\b(deadlock|lock\s+wait|lock\s+timeout|blocking\s+query)\b', 6),
    (r'\b(connection\s+pool|too\s+many\s+connections|connection\s+(refused|timeout|failed))\b', 5),
    (r'\b(replication\s+lag|replica\s+lag|slave\s+lag|sync\s+delay|replication\s+error)\b', 6),
    (r'\b(transaction\s+log|tablespace)\b.{0,20}\b(full|out\s+of\s+space)\b', 6),
    # Low-weight fallbacks
    (r'\b(database|db)\b', 2),
    (r'\bsql\b', 1),
    (r'\bquery\b', 1),
])

_WEB_PHRASES = _compile([
    (r'\b(web\s+(server|application|app|service)|website)\b.{0,40}\b(down|not\s+responding|unreachable|slow|returning\s+error)\b', 8),
    (r'\bhttp\s*(?:status\s*)?(?:error\s*)?(?:code\s*)?(5[0-9]{2}|4[0-9]{2})\b', 7),
    (r'\b(nginx|apache|iis|tomcat|gunicorn|uwsgi)\b.{0,30}\b(down|crashed?|failed|error|not\s+responding)\b', 7),
    (r'\b(api|rest\s+api|endpoint)\b.{0,30}\b(slow|timeout|error|not\s+responding|returning\s+5\d{2})\b', 6),
    (r'\b(load\s+balancer)\b.{0,20}\b(down|failing|error|not\s+responding)\b', 6),
    (r'\b(ssl|tls|certificate)\b.{0,20}\b(expired?|invalid|error|mismatch)\b', 6),
    (r'\b(response\s+time|latency)\b.{0,20}\b(high|slow|degraded|elevated)\b', 5),
    # Low-weight fallbacks
    (r'\bweb\b', 1),
    (r'\bhttp\b', 1),
    (r'\bhttps\b', 1),
])

_NETWORK_PHRASES = _compile([
    (r'\b(network\s+(connectivity|outage|issue)|connectivity\s+(issue|problem|lost|failure))\b', 8),
    (r'\b(switch|router|firewall|access\s+point)\b.{0,40}\b(down|unreachable|not\s+responding|failed|offline)\b', 8),
    (r'\b(interface|port|link)\b.{0,20}\b(down|flapping|error|dropped|disconnected)\b', 7),
    (r'\b(bgp|ospf|eigrp|isis)\b.{0,30}\b(down|neighbor\s+lost|session\s+(dropped|reset)|not\s+established)\b', 7),
    (r'\b(vlan|subnet)\b.{0,20}\b(down|issue|not\s+working|unreachable)\b', 6),
    (r'\b(dns\s+resolution|name\s+resolution)\b.{0,20}\b(fail|error|not\s+working|timeout)\b', 7),
    (r'\bdns\b.{0,20}\b(fail|error|timeout|not\s+resolving)\b', 6),
    (r'\b(packet\s+loss|high\s+(latency|ping)|network\s+slow|bandwidth\s+(saturated|exhausted))\b', 6),
    (r'\b(cisco|juniper|palo\s+alto|fortinet|arista)\b', 5),
    (r'\b(vlan|spanning\s+tree|stp|bgp|ospf|eigrp|vxlan)\b', 4),
    # Low-weight fallbacks
    (r'\bnetwork\b', 1),
    (r'\bconnectivity\b', 1),
    (r'\blatency\b', 1),
    (r'\bpacket\b', 1),
])

# ---------------------------------------------------------------------------
# Issue-type phrase patterns (per service)
#
# Each issue maps to a list of (compiled_regex, weight) tuples ordered from
# most-specific to least-specific.  The caller checks these in order and
# returns the first issue type whose phrase patterns match.
# ---------------------------------------------------------------------------

_ISSUE_PHRASES: dict = {
    "server": [
        # (issue_type, phrase_patterns)
        ("host_unreachable", _compile([
            # "server <entity> is not responding / unreachable / timed out"
            (r'\bserver\b.{0,50}\b(not\s+responding|unreachable|unresponsive|timed?\s*out|is\s+down|went\s+down|offline)\b', 10),
            (r'\b(host|node)\b.{0,50}\b(not\s+responding|unreachable|is\s+down|offline)\b', 9),
            # "cannot reach / connect / ping server"
            (r'\b(cannot|can\'t|unable\s+to)\s+(reach|connect(\s+to)?|ping|ssh(\s+to)?)\b.{0,30}\b(server|host|node)\b', 8),
            # "ping / ssh to host failed"
            (r'\b(ping|ssh)\b.{0,30}\b(failed?|timing\s+out|not\s+working|unreachable)\b', 7),
            # Simple phrase fallbacks
            (r'\b(unreachable|not\s+responding|host\s+down|server\s+down|connection\s+refused|ping\s+failed?|server\s+timeout)\b', 4),
        ])),
        ("high_cpu", _compile([
            (r'\b(high|elevated|critical|excessive)\s+(cpu|processor)\s*(usage|load|utilization)?\b', 10),
            (r'\b(cpu|processor)\s*(usage|load|utilization)\b.{0,20}\b(high|critical|100\s*%|spiking)\b', 10),
            (r'\bserver\b.{0,40}\b(cpu|processor)\b.{0,20}\b(high|maxed|spiking|100\s*%)\b', 9),
            (r'\b(cpu\s+spike|cpu\s+high|high\s+cpu|cpu\s+usage|cpu\s+load|processor\s+usage)\b', 5),
        ])),
        ("high_memory", _compile([
            (r'\b(memory|ram)\b.{0,30}\b(high|full|exhausted|out\s+of|leak|pressure|saturated)\b', 10),
            (r'\bhigh\s+(memory|ram)\s*(usage|consumption|pressure)?\b', 10),
            (r'\b(out\s+of\s+memory|oom\s+kill|memory\s+exhausted|swap\s+full|low\s+available\s+memory)\b', 9),
            (r'\b(out\s+of\s+memory|oom|memory\s+high|high\s+memory|memory\s+usage|memory\s+leak|swap\s+full)\b', 5),
        ])),
        ("low_disk", _compile([
            (r'\b(disk|filesystem|volume|partition)\b.{0,30}\b(full|out\s+of\s+space|no\s+space\s+left|at\s+capacity|running\s+low)\b', 10),
            (r'\bserver\b.{0,40}\b(disk|storage)\b.{0,20}\b(full|low|out\s+of\s+space)\b', 9),
            (r'\b(disk\s+space|disk\s+full|low\s+disk|no\s+space\s+left|filesystem\s+full|running\s+out\s+of\s+space|disk\s+usage)\b', 5),
        ])),
        ("service_down", _compile([
            (r'\b(service|daemon|process|application|app)\b.{0,30}\b(down|stopped|failed|crashed?|not\s+running|unavailable|keeps\s+restarting)\b', 10),
            (r'\b(service\s+down|service\s+failed|service\s+stopped|process\s+crash|application\s+crash|app\s+crash|service\s+unavailable)\b', 6),
        ])),
    ],
    "database": [
        ("db_slow_query", _compile([
            (r'\b(slow|long[\s-]running|hung)\s+(query|sql|transaction)\b', 10),
            (r'\bquery\b.{0,20}\b(slow|timeout|taking\s+too\s+long|not\s+returning)\b', 9),
            (r'\b(slow\s+query|query\s+slow|query\s+timeout|long\s+running\s+query|query\s+performance)\b', 5),
        ])),
        ("db_connection_failure", _compile([
            (r'\b(database|db)\b.{0,30}\b(connection\s+(refused|failed|timeout)|cannot\s+connect|unreachable)\b', 10),
            (r'\b(connection\s+pool|too\s+many\s+connections|max\s+connections)\b', 8),
            (r'\b(connection\s+failed|connection\s+timeout|cannot\s+connect|connection\s+pool|too\s+many\s+connections|connection\s+refused)\b', 5),
        ])),
        ("db_disk_full", _compile([
            (r'\b(transaction\s+log|tablespace|db\s+disk|data\s+directory)\b.{0,20}\b(full|out\s+of\s+space)\b', 10),
            (r'\b(disk\s+full|transaction\s+log\s+full|log\s+full|tablespace\s+full|no\s+space)\b', 5),
        ])),
        ("db_deadlock", _compile([
            (r'\b(deadlock\s+detected|lock\s+(wait|timeout|contention)|blocking\s+query)\b', 10),
            (r'\b(deadlock|lock\s+wait|lock\s+timeout|blocking\s+query)\b', 5),
        ])),
        ("db_replication_lag", _compile([
            (r'\b(replication|replica|slave)\b.{0,20}\b(lag|delay|behind|error|broken)\b', 10),
            (r'\b(replication\s+lag|replica\s+lag|slave\s+lag|sync\s+delay|replication\s+error)\b', 5),
        ])),
    ],
    "web": [
        ("web_5xx", _compile([
            (r'\bhttp\s*(?:status\s*)?(?:error\s*)?(?:code\s*)?(5[0-9]{2})\b', 10),
            (r'\b(internal\s+server\s+error|bad\s+gateway|service\s+unavailable|gateway\s+timeout|5xx)\b', 9),
            (r'\b(500|502|503|504|5xx|internal\s+server\s+error|bad\s+gateway|service\s+unavailable|gateway\s+timeout)\b', 5),
        ])),
        ("web_high_latency", _compile([
            (r'\b(response\s+time|api\s+latency|request\s+time)\b.{0,20}\b(high|slow|elevated|degraded)\b', 10),
            (r'\b(slow\s+(response|api|website|page)|high\s+latency|timeout)\b', 7),
            (r'\b(slow\s+response|high\s+latency|response\s+time|slow\s+api|timeout)\b', 5),
        ])),
        ("web_cert_expired", _compile([
            (r'\b(ssl|tls|certificate)\b.{0,20}\b(expired?|invalid|error|mismatch|not\s+trusted)\b', 10),
            (r'\b(ssl|certificate|cert\s+expired|tls|https\s+error)\b', 4),
        ])),
        ("web_service_down", _compile([
            (r'\b(web\s+(server|application|app|service)|website)\b.{0,30}\b(down|not\s+responding|unreachable|offline)\b', 10),
            (r'\b(down|unreachable|not\s+responding|404|connection\s+refused|web\s+server\s+down)\b', 4),
        ])),
    ],
    "network": [
        ("dns_failure", _compile([
            (r'\bdns\b.{0,30}\b(fail|error|timeout|not\s+resolving|resolution\s+fail)\b', 10),
            (r'\b(name\s+resolution|dns\s+resolution)\b.{0,20}\b(fail|error|not\s+working|timeout)\b', 9),
            (r'\b(dns|name\s+resolution|cannot\s+resolve|dns\s+failure)\b', 4),
        ])),
        ("firewall_block", _compile([
            (r'\bfirewall\b.{0,30}\b(blocking?|dropping?|denying?|rules?\s+(preventing|blocking))\b', 10),
            (r'\b(traffic|connection|port)\b.{0,20}\b(blocked?|denied?|dropped?|filtered?)\b', 8),
            (r'\b(firewall|blocked|access\s+denied|port\s+blocked|traffic\s+blocked)\b', 4),
        ])),
        ("interface_down", _compile([
            (r'\b(interface|port|link|nic|ethernet)\b.{0,20}\b(down|flapping|disconnected|dropped|error)\b', 10),
            (r'\b(interface\s+down|port\s+down|link\s+down|interface\s+error|nic\s+down)\b', 5),
        ])),
        ("high_network_latency", _compile([
            (r'\b(network|link|wan|circuit)\b.{0,20}\b(latency|packet\s+loss|slow|saturated)\b', 10),
            (r'\b(high\s+latency|packet\s+loss|slow\s+network|high\s+ping)\b', 6),
            (r'\b(latency|packet\s+loss|slow\s+network|high\s+ping)\b', 4),
        ])),
        ("network_unreachable", _compile([
            (r'\b(network|subnet|segment)\b.{0,30}\b(unreachable|down|not\s+reachable|connectivity\s+lost)\b', 10),
            (r'\b(cannot\s+connect|connection\s+lost|no\s+route|network\s+down|network\s+outage)\b', 7),
            (r'\b(unreachable|cannot\s+connect|connection\s+lost|network\s+down|no\s+route)\b', 4),
        ])),
    ],
    "storage": [
        ("stale_mount", _compile([
            (r'\b(stale\s+(nfs|mount|file\s+handle)|hung\s+mount|frozen\s+mount)\b', 10),
            (r'\b(stale|hung\s+mount|frozen|stale\s+handle)\b', 4),
        ])),
        ("nfs_mount_failure", _compile([
            (r'\b(nfs|cifs|smb)\b.{0,20}\b(mount\s+(failed?|error|not\s+working)|unmounted|disconnected)\b', 10),
            (r'\b(mount|network\s+share)\b.{0,20}\b(failed?|error|not\s+accessible|unavailable)\b', 8),
            (r'\b(nfs|cifs|mount|smb|network\s+share)\b', 4),
        ])),
        ("storage_full", _compile([
            (r'\b(storage|volume|share|nas|san)\b.{0,20}\b(full|out\s+of\s+space|at\s+capacity|quota\s+exceeded)\b', 10),
            (r'\b(full|capacity|quota|no\s+space)\b', 3),
        ])),
        ("storage_access_denied", _compile([
            (r'\b(storage|share|volume)\b.{0,20}\b(access\s+denied|permission\s+denied|authentication\s+failed|unauthorized)\b', 10),
            (r'\b(access\s+denied|permission\s+denied|authentication\s+failed)\b', 4),
        ])),
    ],
}


class ServiceClassifier:
    """Service type and issue type detection using phrase-level regex matching."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def detect_service_type(self, issue_description: str) -> str:
        """Detect service type via phrase matching (LLM disabled — zero cost)."""
        result = self.classify_service_type(issue_description)
        logger.debug(f"Service detection (phrase-match): {result}")
        return result

    def classify_service_type(self, issue_description: str) -> str:
        """
        Score each service type by summing weights of all matching phrase
        patterns.  Phrases capture subject + predicate together so that
        "server xyz is not responding" scores as one high-confidence server
        signal rather than loose keyword hits.
        """
        scores = {
            "server":   _score(issue_description, _SERVER_PHRASES),
            "storage":  _score(issue_description, _STORAGE_PHRASES),
            "database": _score(issue_description, _DATABASE_PHRASES),
            "web":      _score(issue_description, _WEB_PHRASES),
            "network":  _score(issue_description, _NETWORK_PHRASES),
        }

        # Special case: local disk issue + no strong external-storage signals → server
        t = issue_description.lower()
        if re.search(r'\b(disk\s+space|disk\s+full)\b', t, re.IGNORECASE):
            if scores["storage"] < 4:
                scores["server"] += 3
                scores["storage"] = 0

        logger.debug(f"Service scores: {scores}")

        max_score = max(scores.values())
        if max_score == 0:
            return "server"  # Default — most common CI type

        # Return first (insertion-order) service with the top score
        for service, score in scores.items():
            if score == max_score:
                return service

        return "server"

    # Keep old method name for backwards compat
    def keyword_classify_service_type(self, issue_description: str) -> str:
        return self.classify_service_type(issue_description)

    def detect_issue_type(self, issue_description: str, service: str) -> str:
        """
        Detect the specific issue type within a service domain.

        Uses phrase-level regex patterns ordered from most-specific to
        least-specific.  Returns the first matching issue type.
        Zero LLM cost.

        Examples:
          service=server, "server prod-01 is not responding" → "host_unreachable"
          service=server, "high CPU usage on web01"         → "high_cpu"
          service=database, "deadlock detected in orders DB" → "db_deadlock"
        """
        issue_patterns = _ISSUE_PHRASES.get(service, [])
        for issue_type, phrase_list in issue_patterns:
            if _first_match(issue_description, phrase_list):
                logger.debug(f"Issue type matched: {issue_type} (service={service})")
                return issue_type

        # Default fallbacks per service
        _defaults = {
            "server":   "server_performance",
            "database": "db_general",
            "web":      "web_general",
            "network":  "network_general",
            "storage":  "storage_general",
        }
        return _defaults.get(service, "general_issue")

    async def detect_os_type(self, issue_description: str) -> Optional[str]:
        """Detect OS type (Windows/Linux) from issue description."""
        _WINDOWS = _compile([
            (r'\b(windows\s+server|windows\s+\d+|win\s*\d+)\b', 4),
            (r'\b(powershell|get-process|get-counter|get-service|iis|wmi|win32|\.exe|c:\\\\|event\s+viewer)\b', 3),
            (r'\bwindows\b', 2),
        ])
        _LINUX = _compile([
            (r'\b(ubuntu|centos|rhel|debian|fedora|suse|amazon\s+linux)\b', 4),
            (r'\b(systemctl|journalctl|apt[\s-]get|yum\s+install|dnf\s+install|/var/log|/etc/|bash\s+script)\b', 3),
            (r'\blinux\b', 2),
        ])

        windows_score = _score(issue_description, _WINDOWS)
        linux_score = _score(issue_description, _LINUX)

        if windows_score > linux_score and windows_score > 0:
            return "Windows"
        if linux_score > windows_score and linux_score > 0:
            return "Linux"
        return None
