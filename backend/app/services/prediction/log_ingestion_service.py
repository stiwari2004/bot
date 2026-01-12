"""
Log Ingestion Service - Collect logs from multiple sources
"""
import json
import asyncio
from typing import Dict, Any, Optional, List, AsyncIterator
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.models.log_entry import LogEntry

logger = get_logger(__name__)


class LogIngestionService:
    """Service for ingesting logs from various sources"""
    
    def __init__(self):
        pass
    
    async def ingest_from_file(
        self,
        file_path: str,
        source: str,
        tenant_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Ingest logs from a file
        
        Args:
            file_path: Path to log file
            source: Source identifier (application, infrastructure, etc.)
            tenant_id: Tenant ID
            db: Database session
            
        Returns:
            Dict with ingestion results
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }
            
            ingested_count = 0
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse and store log entry
                    result = await self._store_log_entry(
                        raw_log=line,
                        source=source,
                        tenant_id=tenant_id,
                        db=db
                    )
                    
                    if result:
                        ingested_count += 1
            
            return {
                "success": True,
                "ingested_count": ingested_count
            }
            
        except Exception as e:
            logger.error(f"Error ingesting from file: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def ingest_from_api(
        self,
        logs: List[Dict[str, Any]],
        source: str,
        tenant_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Ingest logs from API (monitoring tools, etc.)
        
        Args:
            logs: List of log dictionaries
            source: Source identifier
            tenant_id: Tenant ID
            db: Database session
            
        Returns:
            Dict with ingestion results
        """
        try:
            ingested_count = 0
            for log_data in logs:
                result = await self._store_log_entry(
                    raw_log=json.dumps(log_data) if isinstance(log_data, dict) else str(log_data),
                    source=source,
                    tenant_id=tenant_id,
                    parsed_fields=log_data if isinstance(log_data, dict) else None,
                    db=db
                )
                
                if result:
                    ingested_count += 1
            
            return {
                "success": True,
                "ingested_count": ingested_count
            }
            
        except Exception as e:
            logger.error(f"Error ingesting from API: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def ingest_stream(
        self,
        stream: AsyncIterator[str],
        source: str,
        tenant_id: int,
        db: Session
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Ingest logs from a streaming source (Kafka, WebSocket, etc.)
        
        Args:
            stream: Async iterator of log lines
            source: Source identifier
            tenant_id: Tenant ID
            db: Database session
            
        Yields:
            Dict with ingestion results for each log
        """
        try:
            async for log_line in stream:
                result = await self._store_log_entry(
                    raw_log=log_line,
                    source=source,
                    tenant_id=tenant_id,
                    db=db
                )
                
                yield {
                    "success": result is not None,
                    "log_entry": result
                }
                
        except Exception as e:
            logger.error(f"Error in stream ingestion: {e}")
            yield {
                "success": False,
                "error": str(e)
            }
    
    async def ingest_from_windows_eventlog(
        self,
        log_name: str = "Application",
        max_events: int = 1000,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        tenant_id: int = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Ingest logs from Windows Event Log
        
        Args:
            log_name: Event log name (Application, System, Security)
            max_events: Maximum events to collect
            host: Remote host (optional)
            username: Username for remote access
            password: Password for remote access
            tenant_id: Tenant ID
            db: Database session
            
        Returns:
            Dict with ingestion results
        """
        try:
            from app.services.prediction.windows_eventlog_collector import WindowsEventLogCollector
            
            collector = WindowsEventLogCollector()
            ingested_count = 0
            
            async for event in collector.collect_event_logs(
                log_name=log_name,
                max_events=max_events,
                host=host,
                username=username,
                password=password
            ):
                if event.get("error"):
                    continue
                
                result = await self._store_log_entry(
                    raw_log=json.dumps(event),
                    source=f"windows_eventlog_{log_name.lower()}" + (f"_{host}" if host else ""),
                    tenant_id=tenant_id,
                    parsed_fields=event,
                    db=db
                )
                
                if result:
                    ingested_count += 1
            
            return {
                "success": True,
                "ingested_count": ingested_count
            }
            
        except Exception as e:
            logger.error(f"Error ingesting Windows Event Log: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def ingest_from_linux_syslog(
        self,
        log_type: str = "syslog",
        lines: int = 1000,
        host: Optional[str] = None,
        username: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        tenant_id: int = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Ingest logs from Linux syslog
        
        Args:
            log_type: Type of log (syslog, messages, auth, etc.)
            lines: Number of lines to read
            host: Remote host (optional)
            username: Username for SSH
            ssh_key_path: Path to SSH private key
            tenant_id: Tenant ID
            db: Database session
            
        Returns:
            Dict with ingestion results
        """
        try:
            from app.services.prediction.linux_syslog_collector import LinuxSyslogCollector
            
            collector = LinuxSyslogCollector()
            ingested_count = 0
            
            async for entry in collector.collect_syslog(
                log_type=log_type,
                lines=lines,
                host=host,
                username=username,
                ssh_key_path=ssh_key_path
            ):
                if entry.get("error"):
                    continue
                
                result = await self._store_log_entry(
                    raw_log=entry.get("raw_log", json.dumps(entry)),
                    source=f"linux_syslog_{log_type}" + (f"_{host}" if host else ""),
                    tenant_id=tenant_id,
                    parsed_fields=entry,
                    db=db
                )
                
                if result:
                    ingested_count += 1
            
            return {
                "success": True,
                "ingested_count": ingested_count
            }
            
        except Exception as e:
            logger.error(f"Error ingesting Linux syslog: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def ingest_from_journald(
        self,
        unit: Optional[str] = None,
        lines: int = 1000,
        host: Optional[str] = None,
        username: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        tenant_id: int = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Ingest logs from systemd journal (journalctl)
        
        Args:
            unit: Systemd unit name (optional)
            lines: Number of lines to read
            host: Remote host (optional)
            username: Username for SSH
            ssh_key_path: Path to SSH private key
            tenant_id: Tenant ID
            db: Database session
            
        Returns:
            Dict with ingestion results
        """
        try:
            from app.services.prediction.linux_syslog_collector import LinuxSyslogCollector
            
            collector = LinuxSyslogCollector()
            ingested_count = 0
            
            async for entry in collector.collect_journald(
                unit=unit,
                lines=lines,
                host=host,
                username=username,
                ssh_key_path=ssh_key_path
            ):
                if entry.get("error"):
                    continue
                
                result = await self._store_log_entry(
                    raw_log=entry.get("raw_log", json.dumps(entry)),
                    source=f"journald" + (f"_{unit}" if unit else "") + (f"_{host}" if host else ""),
                    tenant_id=tenant_id,
                    parsed_fields=entry,
                    db=db
                )
                
                if result:
                    ingested_count += 1
            
            return {
                "success": True,
                "ingested_count": ingested_count
            }
            
        except Exception as e:
            logger.error(f"Error ingesting journald logs: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _store_log_entry(
        self,
        raw_log: str,
        source: str,
        tenant_id: int,
        parsed_fields: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> Optional[LogEntry]:
        """Store a log entry in the database"""
        try:
            # Extract basic information
            timestamp = datetime.now(timezone.utc)
            level = "INFO"
            log_type = "info"
            message = raw_log[:1000]  # Truncate if too long
            
            # Try to parse as JSON
            if parsed_fields is None:
                try:
                    parsed = json.loads(raw_log)
                    if isinstance(parsed, dict):
                        parsed_fields = parsed
                        level = parsed.get("level", level).upper()
                        log_type = parsed.get("type", log_type)
                        message = parsed.get("message", message)
                        if "timestamp" in parsed:
                            try:
                                timestamp = datetime.fromisoformat(parsed["timestamp"].replace("Z", "+00:00"))
                            except:
                                pass
                except json.JSONDecodeError:
                    pass
            
            # Create log entry
            log_entry = LogEntry(
                tenant_id=tenant_id,
                source=source,
                log_type=log_type,
                level=level,
                message=message,
                raw_log=raw_log,
                parsed_fields=parsed_fields,
                timestamp=timestamp
            )
            
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            
            return log_entry
            
        except Exception as e:
            logger.error(f"Error storing log entry: {e}")
            db.rollback()
            return None

