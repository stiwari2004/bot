"""
Output-driven variable extractor.

After each step executes, this service parses the command output and extracts
real values needed by subsequent steps.  No LLM — all deterministic parsers.

Flow:
  Step 1 runs "df -h"  → output parsed → mount_point=/var (95% full)
  Step 2 runs "du -sh /var/*" → output parsed → largest_dir=/var/log
  Step 3 runs "find /var/log ..." → real results, no placeholders

Extracted values accumulate in session.meta_data["resolved_inputs"] and are
substituted into every subsequent step before execution.
"""
import re
from typing import Any, Dict, List, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Individual parsers
# ---------------------------------------------------------------------------

def _parse_df(output: str) -> Dict[str, str]:
    """
    Parse 'df -h' / 'df --output=...' output.
    Returns the mount point with the highest usage percentage (skipping tmpfs/devtmpfs).
    Also returns disk_usage_pct for that mount.
    """
    best_mount: Optional[str] = None
    best_pct = 0

    for line in output.strip().splitlines():
        parts = line.split()
        # Standard df -h: Filesystem  Size  Used  Avail  Use%  Mounted-on
        if len(parts) < 6:
            continue
        fs = parts[0]
        pct_str = parts[4].rstrip("%")
        mount = parts[5]

        # Skip virtual / overlay filesystems
        if any(skip in fs.lower() for skip in ("tmpfs", "devtmpfs", "udev", "none", "overlay", "shm")):
            continue
        if mount in ("/dev", "/run", "/sys", "/proc"):
            continue

        try:
            pct = int(pct_str)
        except ValueError:
            continue

        if pct > best_pct:
            best_pct = pct
            best_mount = mount

    result: Dict[str, str] = {}
    if best_mount:
        result["mount_point"] = best_mount
        result["disk_usage_pct"] = str(best_pct)
        logger.info("OutputExtractor: df parsed → mount_point=%s (%s%%)", best_mount, best_pct)
    return result


def _parse_du(output: str) -> Dict[str, str]:
    """
    Parse 'du -sh <path>/*' output (assumed already sorted largest-first).
    Extracts the largest directory/file path as 'largest_dir'.
    """
    result: Dict[str, str] = {}
    for line in output.strip().splitlines():
        parts = line.split(None, 1)
        if len(parts) < 2:
            continue
        path = parts[1].strip()
        # Skip totals / current-dir markers
        if path in (".", "/", "") or path.endswith("/.") or path.endswith("/.."):
            continue
        result["largest_dir"] = path
        logger.info("OutputExtractor: du parsed → largest_dir=%s", path)
        break
    return result


def _parse_find_large_files(output: str) -> Dict[str, str]:
    """
    Parse 'find ... -size +N | xargs du -h | sort -rh' or similar output.
    Extracts the largest file path as 'largest_file', and a comma-separated
    list of all found paths as 'large_files'.
    """
    result: Dict[str, str] = {}
    files: List[str] = []
    for line in output.strip().splitlines():
        # Lines may be "<size>  <path>" (from du) or just "<path>" (from find)
        parts = line.split(None, 1)
        if len(parts) == 2:
            path = parts[1].strip()
        elif len(parts) == 1:
            path = parts[0].strip()
        else:
            continue
        if path and not path.startswith("#"):
            files.append(path)

    if files:
        result["largest_file"] = files[0]
        result["large_files"] = ",".join(files[:10])
        logger.info("OutputExtractor: find parsed → %d large files, top=%s", len(files), files[0])
    return result


def _parse_systemctl_failed(output: str) -> Dict[str, str]:
    """
    Parse 'systemctl list-units --state=failed' output.
    Extracts first failed service name as 'service_name'.
    """
    result: Dict[str, str] = {}
    for line in output.strip().splitlines():
        # Lines look like:  ● nginx.service  loaded failed failed  A high perf...
        m = re.search(r'(\S+\.service)', line)
        if m:
            result["service_name"] = m.group(1)
            logger.info("OutputExtractor: systemctl parsed → service_name=%s", m.group(1))
            break
    return result


def _parse_ps_top_cpu(output: str) -> Dict[str, str]:
    """
    Parse 'ps aux --sort=-%cpu' output.
    Extracts the top CPU-consuming process name and PID.
    """
    result: Dict[str, str] = {}
    lines = output.strip().splitlines()
    # Skip header
    for line in lines[1:]:
        parts = line.split(None, 10)
        if len(parts) >= 11:
            pid = parts[1]
            proc = parts[10].split()[0]  # just the binary name
            result["top_process"] = proc
            result["top_pid"] = pid
            logger.info("OutputExtractor: ps parsed → top_process=%s pid=%s", proc, pid)
            break
    return result


def _parse_hostname(output: str) -> Dict[str, str]:
    """Parse 'hostname' / 'hostname -f' output."""
    h = output.strip().splitlines()[0].strip() if output.strip() else ""
    if h:
        logger.info("OutputExtractor: hostname parsed → %s", h)
        return {"hostname": h, "server_name": h}
    return {}


def _parse_free_memory(output: str) -> Dict[str, str]:
    """
    Parse 'free -h' output.
    Extracts available memory as 'available_memory' and usage pct as 'memory_usage_pct'.
    """
    result: Dict[str, str] = {}
    for line in output.strip().splitlines():
        if line.lower().startswith("mem:"):
            parts = line.split()
            if len(parts) >= 7:
                result["total_memory"] = parts[1]
                result["used_memory"] = parts[2]
                result["available_memory"] = parts[6]
            elif len(parts) >= 3:
                result["total_memory"] = parts[1]
                result["used_memory"] = parts[2]
            # Approximate usage pct from used/total (strip units for rough calc)
            break
    if result:
        logger.info("OutputExtractor: free parsed → %s", result)
    return result


def _parse_netstat_ports(output: str) -> Dict[str, str]:
    """
    Parse 'ss -tlnp' / 'netstat -tlnp' output.
    Extracts first listening port as 'port'.
    """
    result: Dict[str, str] = {}
    for line in output.strip().splitlines():
        # ss: LISTEN  0  128  0.0.0.0:8080  ...
        m = re.search(r':(\d{2,5})\s', line)
        if m and "listen" in line.lower():
            result["port"] = m.group(1)
            logger.info("OutputExtractor: netstat parsed → port=%s", m.group(1))
            break
    return result


# ---------------------------------------------------------------------------
# Command-type detection
# ---------------------------------------------------------------------------

def _detect_command_type(command: str) -> Optional[str]:
    """Classify a command so we know which parser to use."""
    cmd = command.strip().lower()
    # Strip sudo / env prefixes
    cmd = re.sub(r'^(sudo\s+-\S+\s+)*sudo\s+', '', cmd)
    cmd = re.sub(r'^(echo\s+\S+\s+\|\s+sudo\s+-S[^\s]*\s+)', '', cmd)

    if re.match(r'df\b', cmd):
        return "df"
    if re.match(r'du\b', cmd):
        return "du"
    if re.search(r'\bfind\b.*\-size\b|\bfind\b.*\bdu\b', cmd):
        return "find_large"
    if re.search(r'\bsystemctl\b.*\bfail', cmd):
        return "systemctl_failed"
    if re.match(r'ps\b.*aux|top\b', cmd):
        return "ps_top_cpu"
    if re.match(r'hostname\b', cmd):
        return "hostname"
    if re.match(r'free\b', cmd):
        return "free_memory"
    if re.match(r'(ss|netstat)\b', cmd):
        return "netstat"
    return None


# ---------------------------------------------------------------------------
# Smart defaults: last-resort fallbacks for known variable patterns
# ---------------------------------------------------------------------------

_SMART_DEFAULTS: Dict[str, str] = {
    "tmp_retention_days": "7",
    "log_retention_days": "30",
    "backup_retention_days": "30",
    "retention_days": "30",
    "disk_threshold": "80",
    "cpu_threshold": "80",
    "memory_threshold": "80",
    "vacuum_size": "500M",
    "max_log_size": "100M",
    "mount_point": "/",         # safest fallback if df parse fails
    "filesystem": "/",
}

# Pattern-based defaults (regex on var name)
_SMART_DEFAULT_PATTERNS: List[tuple] = [
    (r'.*_days$',      "30"),
    (r'.*_threshold$', "80"),
    (r'.*_size$',      "500M"),
    (r'.*_limit$',     "100"),
]


def _smart_default(var_name: str) -> Optional[str]:
    """Return a smart default for a variable if we know a sensible value."""
    if var_name in _SMART_DEFAULTS:
        return _SMART_DEFAULTS[var_name]
    for pattern, default in _SMART_DEFAULT_PATTERNS:
        if re.match(pattern, var_name):
            return default
    return None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

class OutputExtractor:
    """
    Parses step output and extracts values for subsequent steps.
    Called after every successful step.  Values accumulate in session context.
    """

    def extract_from_output(
        self,
        command: str,
        output: str,
        needed_vars: List[str],
    ) -> Dict[str, str]:
        """
        Parse `output` from `command` and return a dict of resolved variables.
        Only extracts values that are actually needed by future steps.

        Args:
            command:     The command that was just run (used to choose parser).
            output:      The stdout from that command.
            needed_vars: Variable names still unresolved (from future step commands).

        Returns:
            Dict of variable_name → resolved_value.
        """
        if not output or not output.strip():
            return {}

        cmd_type = _detect_command_type(command)
        if cmd_type is None:
            return {}

        parsers = {
            "df":               _parse_df,
            "du":               _parse_du,
            "find_large":       _parse_find_large_files,
            "systemctl_failed": _parse_systemctl_failed,
            "ps_top_cpu":       _parse_ps_top_cpu,
            "hostname":         _parse_hostname,
            "free_memory":      _parse_free_memory,
            "netstat":          _parse_netstat_ports,
        }

        parser = parsers.get(cmd_type)
        if parser is None:
            return {}

        extracted = parser(output)
        # Only return values that are actually needed
        return {k: v for k, v in extracted.items() if k in needed_vars}

    def apply_smart_defaults(self, needed_vars: List[str]) -> Dict[str, str]:
        """
        For any variable that still can't be resolved from system output,
        return a sensible default if we know one.
        """
        defaults: Dict[str, str] = {}
        for var in needed_vars:
            d = _smart_default(var)
            if d is not None:
                defaults[var] = d
                logger.info("OutputExtractor: smart default → %s=%s", var, d)
        return defaults

    @staticmethod
    def substitute(command: str, resolved: Dict[str, Any]) -> str:
        """
        Replace all {{variable}} placeholders in `command` with resolved values.
        Any placeholder that still has no resolved value is left as-is
        (it will be attempted again at the next step, or caught at execution).
        """
        def replacer(m: re.Match) -> str:
            var = m.group(1).strip()
            val = resolved.get(var)
            if val is not None:
                return str(val)
            return m.group(0)  # leave unresolved placeholder intact

        return re.sub(r'\{\{\s*(\w+)\s*\}\}', replacer, command)

    @staticmethod
    def find_unresolved(command: str) -> List[str]:
        """Return list of variable names still unresolved in a command."""
        return re.findall(r'\{\{\s*(\w+)\s*\}\}', command)


# Singleton
_extractor: Optional[OutputExtractor] = None


def get_output_extractor() -> OutputExtractor:
    global _extractor
    if _extractor is None:
        _extractor = OutputExtractor()
    return _extractor
