"""
Windows Event Log Collector - Collect logs from Windows systems
"""
import json
import subprocess
from typing import Dict, Any, Optional, List, Iterator
from datetime import datetime, timezone
from app.core.logging import get_logger

logger = get_logger(__name__)


class WindowsEventLogCollector:
    """Collector for Windows Event Logs"""
    
    def __init__(self):
        pass
    
    async def collect_event_logs(
        self,
        log_name: str = "Application",  # Application, System, Security, etc.
        max_events: int = 1000,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        Collect Windows Event Logs
        
        Args:
            log_name: Event log name (Application, System, Security, etc.)
            max_events: Maximum number of events to collect
            host: Remote host (optional, for remote collection)
            username: Username for remote access
            password: Password for remote access
            
        Yields:
            Dict with event log data
        """
        try:
            if host:
                # Remote collection via WinRM or PowerShell remoting
                events = await self._collect_remote(host, log_name, max_events, username, password)
            else:
                # Local collection
                events = await self._collect_local(log_name, max_events)
            
            for event in events:
                yield event
                
        except Exception as e:
            logger.error(f"Error collecting Windows Event Logs: {e}")
            yield {
                "error": str(e),
                "success": False
            }
    
    async def _collect_local(
        self,
        log_name: str,
        max_events: int
    ) -> List[Dict[str, Any]]:
        """Collect event logs from local Windows system"""
        try:
            # Use PowerShell Get-WinEvent
            ps_command = f"""
            Get-WinEvent -LogName '{log_name}' -MaxEvents {max_events} | 
            Select-Object TimeCreated, Id, LevelDisplayName, LogName, Message, MachineName, 
            ProviderName, UserId | 
            ConvertTo-Json -Depth 5
            """
            
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"PowerShell command failed: {result.stderr}")
                return []
            
            # Parse JSON output
            try:
                events_data = json.loads(result.stdout)
                if not isinstance(events_data, list):
                    events_data = [events_data]
                
                events = []
                for event in events_data:
                    normalized = self._normalize_event(event)
                    if normalized:
                        events.append(normalized)
                
                return events
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing PowerShell output: {e}")
                return []
                
        except Exception as e:
            logger.error(f"Error in local collection: {e}")
            return []
    
    async def _collect_remote(
        self,
        host: str,
        log_name: str,
        max_events: int,
        username: Optional[str],
        password: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Collect event logs from remote Windows system"""
        try:
            # Use PowerShell remoting (WinRM)
            ps_command = f"""
            $cred = $null
            if ('{username}' -and '{password}') {{
                $securePassword = ConvertTo-SecureString '{password}' -AsPlainText -Force
                $cred = New-Object System.Management.Automation.PSCredential('{username}', $securePassword)
            }}
            
            Invoke-Command -ComputerName '{host}' -Credential $cred -ScriptBlock {{
                param($logName, $maxEvents)
                Get-WinEvent -LogName $logName -MaxEvents $maxEvents | 
                Select-Object TimeCreated, Id, LevelDisplayName, LogName, Message, MachineName, 
                ProviderName, UserId | 
                ConvertTo-Json -Depth 5
            }} -ArgumentList '{log_name}', {max_events}
            """
            
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Remote PowerShell command failed: {result.stderr}")
                return []
            
            try:
                events_data = json.loads(result.stdout)
                if not isinstance(events_data, list):
                    events_data = [events_data]
                
                events = []
                for event in events_data:
                    normalized = self._normalize_event(event)
                    if normalized:
                        events.append(normalized)
                
                return events
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing remote PowerShell output: {e}")
                return []
                
        except Exception as e:
            logger.error(f"Error in remote collection: {e}")
            return []
    
    def _normalize_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize Windows Event Log entry"""
        try:
            # Map Windows Event Log levels to standard levels
            level_mapping = {
                "Error": "ERROR",
                "Warning": "WARN",
                "Information": "INFO",
                "Critical": "CRITICAL",
                "Verbose": "DEBUG"
            }
            
            level_display = event.get("LevelDisplayName", "Information")
            level = level_mapping.get(level_display, "INFO")
            
            # Parse timestamp
            time_created = event.get("TimeCreated")
            if isinstance(time_created, str):
                try:
                    timestamp = datetime.fromisoformat(time_created.replace("Z", "+00:00"))
                except:
                    timestamp = datetime.now(timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)
            
            return {
                "timestamp": timestamp.isoformat(),
                "level": level,
                "log_type": "windows_event",
                "message": event.get("Message", ""),
                "event_id": event.get("Id"),
                "log_name": event.get("LogName"),
                "provider": event.get("ProviderName"),
                "machine": event.get("MachineName"),
                "user_id": event.get("UserId"),
                "raw_event": event
            }
            
        except Exception as e:
            logger.error(f"Error normalizing event: {e}")
            return None
    
    async def collect_from_file(
        self,
        evtx_file_path: str
    ) -> Iterator[Dict[str, Any]]:
        """
        Collect events from an .evtx file
        
        Args:
            evtx_file_path: Path to .evtx file
            
        Yields:
            Dict with event log data
        """
        try:
            # Use PowerShell to read .evtx file
            ps_command = f"""
            Get-WinEvent -Path '{evtx_file_path}' | 
            Select-Object TimeCreated, Id, LevelDisplayName, LogName, Message, MachineName, 
            ProviderName, UserId | 
            ConvertTo-Json -Depth 5
            """
            
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Error reading .evtx file: {result.stderr}")
                return
            
            try:
                events_data = json.loads(result.stdout)
                if not isinstance(events_data, list):
                    events_data = [events_data]
                
                for event in events_data:
                    normalized = self._normalize_event(event)
                    if normalized:
                        yield normalized
                        
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing .evtx file output: {e}")
                
        except Exception as e:
            logger.error(f"Error collecting from .evtx file: {e}")

