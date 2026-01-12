"""
Linux Syslog Collector - Collect logs from Linux systems
"""
import json
import subprocess
import re
from typing import Dict, Any, Optional, List, Iterator
from datetime import datetime, timezone
from pathlib import Path
from app.core.logging import get_logger

logger = get_logger(__name__)


class LinuxSyslogCollector:
    """Collector for Linux syslog and system logs"""
    
    def __init__(self):
        # Common log file locations
        self.log_paths = {
            "syslog": "/var/log/syslog",
            "messages": "/var/log/messages",
            "auth": "/var/log/auth.log",
            "secure": "/var/log/secure",
            "kern": "/var/log/kern.log",
            "daemon": "/var/log/daemon.log",
            "application": "/var/log/application.log"
        }
    
    async def collect_syslog(
        self,
        log_type: str = "syslog",
        lines: int = 1000,
        host: Optional[str] = None,
        username: Optional[str] = None,
        ssh_key_path: Optional[str] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        Collect syslog entries from Linux system
        
        Args:
            log_type: Type of log (syslog, messages, auth, etc.)
            lines: Number of lines to read (tail -n)
            host: Remote host (optional, for remote collection via SSH)
            username: Username for SSH
            ssh_key_path: Path to SSH private key
            
        Yields:
            Dict with log entry data
        """
        try:
            if host:
                # Remote collection via SSH
                log_path = self.log_paths.get(log_type, f"/var/log/{log_type}")
                entries = await self._collect_remote(host, log_path, lines, username, ssh_key_path)
            else:
                # Local collection
                log_path = self.log_paths.get(log_type, f"/var/log/{log_type}")
                entries = await self._collect_local(log_path, lines)
            
            for entry in entries:
                yield entry
                
        except Exception as e:
            logger.error(f"Error collecting Linux syslog: {e}")
            yield {
                "error": str(e),
                "success": False
            }
    
    async def _collect_local(
        self,
        log_path: str,
        lines: int
    ) -> List[Dict[str, Any]]:
        """Collect logs from local Linux system"""
        try:
            path = Path(log_path)
            if not path.exists():
                logger.warning(f"Log file not found: {log_path}")
                return []
            
            # Use tail to get last N lines
            result = subprocess.run(
                ["tail", "-n", str(lines), str(log_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Error reading log file: {result.stderr}")
                return []
            
            entries = []
            for line in result.stdout.splitlines():
                normalized = self._parse_syslog_line(line)
                if normalized:
                    entries.append(normalized)
            
            return entries
            
        except Exception as e:
            logger.error(f"Error in local collection: {e}")
            return []
    
    async def _collect_remote(
        self,
        host: str,
        log_path: str,
        lines: int,
        username: Optional[str],
        ssh_key_path: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Collect logs from remote Linux system via SSH"""
        try:
            # Build SSH command
            ssh_cmd = ["ssh"]
            
            if ssh_key_path:
                ssh_cmd.extend(["-i", ssh_key_path])
            
            if username:
                ssh_cmd.append(f"{username}@{host}")
            else:
                ssh_cmd.append(host)
            
            # Remote command: tail the log file
            remote_cmd = f"tail -n {lines} {log_path}"
            ssh_cmd.append(remote_cmd)
            
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"SSH command failed: {result.stderr}")
                return []
            
            entries = []
            for line in result.stdout.splitlines():
                normalized = self._parse_syslog_line(line)
                if normalized:
                    entries.append(normalized)
            
            return entries
            
        except Exception as e:
            logger.error(f"Error in remote collection: {e}")
            return []
    
    def _parse_syslog_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a syslog line"""
        try:
            if not line.strip():
                return None
            
            # Standard syslog format: MMM DD HH:MM:SS hostname service: message
            # Example: Jan  8 12:34:56 server01 kernel: [12345.67] error message
            syslog_pattern = r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(\S+):\s+(.*)$'
            match = re.match(syslog_pattern, line)
            
            if match:
                timestamp_str, hostname, service, message = match.groups()
                timestamp = self._parse_timestamp(timestamp_str)
                
                # Determine log level from message
                level = self._extract_level(message)
                
                return {
                    "timestamp": timestamp.isoformat(),
                    "level": level,
                    "log_type": "syslog",
                    "message": message,
                    "hostname": hostname,
                    "service": service,
                    "raw_log": line
                }
            else:
                # Try to parse as JSON
                try:
                    parsed = json.loads(line)
                    if isinstance(parsed, dict):
                        return {
                            "timestamp": parsed.get("timestamp", datetime.now(timezone.utc).isoformat()),
                            "level": parsed.get("level", "INFO").upper(),
                            "log_type": parsed.get("type", "application"),
                            "message": parsed.get("message", line),
                            "raw_log": line,
                            "parsed_fields": parsed
                        }
                except json.JSONDecodeError:
                    pass
                
                # Fallback: treat as plain log
                return {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": "INFO",
                    "log_type": "application",
                    "message": line,
                    "raw_log": line
                }
            
        except Exception as e:
            logger.error(f"Error parsing syslog line: {e}")
            return None
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse syslog timestamp"""
        try:
            # Format: "Jan  8 12:34:56" or "Jan 08 12:34:56"
            # Add current year
            current_year = datetime.now().year
            full_timestamp = f"{current_year} {timestamp_str}"
            
            # Try different formats
            formats = [
                "%Y %b %d %H:%M:%S",
                "%Y %B %d %H:%M:%S"
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(full_timestamp, fmt)
                    return dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            
            # Fallback to current time
            return datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error parsing timestamp: {e}")
            return datetime.now(timezone.utc)
    
    def _extract_level(self, message: str) -> str:
        """Extract log level from message"""
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in ["error", "err", "failed", "failure", "critical"]):
            return "ERROR"
        elif any(keyword in message_lower for keyword in ["warn", "warning"]):
            return "WARN"
        elif any(keyword in message_lower for keyword in ["debug", "trace"]):
            return "DEBUG"
        else:
            return "INFO"
    
    async def collect_journald(
        self,
        unit: Optional[str] = None,
        lines: int = 1000,
        host: Optional[str] = None,
        username: Optional[str] = None,
        ssh_key_path: Optional[str] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        Collect logs from systemd journal (journalctl)
        
        Args:
            unit: Systemd unit name (optional)
            lines: Number of lines to read
            host: Remote host (optional)
            username: Username for SSH
            ssh_key_path: Path to SSH private key
            
        Yields:
            Dict with log entry data
        """
        try:
            if host:
                # Remote collection
                cmd = await self._build_journalctl_remote_cmd(host, unit, lines, username, ssh_key_path)
            else:
                # Local collection
                cmd = await self._build_journalctl_local_cmd(unit, lines)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"journalctl command failed: {result.stderr}")
                return
            
            # Parse journalctl output (JSON format)
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                
                try:
                    entry = json.loads(line)
                    normalized = self._normalize_journal_entry(entry)
                    if normalized:
                        yield normalized
                except json.JSONDecodeError:
                    # Try parsing as plain text
                    normalized = self._parse_syslog_line(line)
                    if normalized:
                        yield normalized
                        
        except Exception as e:
            logger.error(f"Error collecting journald logs: {e}")
    
    async def _build_journalctl_local_cmd(
        self,
        unit: Optional[str],
        lines: int
    ) -> List[str]:
        """Build journalctl command for local system"""
        cmd = ["journalctl", "-n", str(lines), "-o", "json"]
        if unit:
            cmd.extend(["-u", unit])
        return cmd
    
    async def _build_journalctl_remote_cmd(
        self,
        host: str,
        unit: Optional[str],
        lines: int,
        username: Optional[str],
        ssh_key_path: Optional[str]
    ) -> List[str]:
        """Build SSH command for remote journalctl"""
        ssh_cmd = ["ssh"]
        
        if ssh_key_path:
            ssh_cmd.extend(["-i", ssh_key_path])
        
        if username:
            ssh_cmd.append(f"{username}@{host}")
        else:
            ssh_cmd.append(host)
        
        remote_cmd = f"journalctl -n {lines} -o json"
        if unit:
            remote_cmd += f" -u {unit}"
        
        ssh_cmd.append(remote_cmd)
        return ssh_cmd
    
    def _normalize_journal_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize systemd journal entry"""
        try:
            # Map journal priority to log level
            priority = entry.get("PRIORITY", 6)
            level_mapping = {
                0: "CRITICAL",  # emerg
                1: "CRITICAL",  # alert
                2: "CRITICAL",  # crit
                3: "ERROR",     # err
                4: "WARN",      # warning
                5: "INFO",      # notice
                6: "INFO",      # info
                7: "DEBUG"      # debug
            }
            level = level_mapping.get(priority, "INFO")
            
            # Parse timestamp (microseconds since epoch)
            timestamp_us = entry.get("__REALTIME_TIMESTAMP")
            if timestamp_us:
                timestamp = datetime.fromtimestamp(int(timestamp_us) / 1000000, tz=timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)
            
            return {
                "timestamp": timestamp.isoformat(),
                "level": level,
                "log_type": "journald",
                "message": entry.get("MESSAGE", ""),
                "hostname": entry.get("_HOSTNAME"),
                "service": entry.get("_SYSTEMD_UNIT") or entry.get("SYSLOG_IDENTIFIER"),
                "pid": entry.get("_PID"),
                "priority": priority,
                "raw_log": json.dumps(entry)
            }
            
        except Exception as e:
            logger.error(f"Error normalizing journal entry: {e}")
            return None

