"""
Log Normalizer - Parse and standardize logs from different sources
"""
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.core.logging import get_logger

logger = get_logger(__name__)


class LogNormalizer:
    """Service for normalizing logs from different sources"""
    
    def __init__(self):
        # Common log level patterns
        self.level_patterns = {
            "DEBUG": re.compile(r'\b(debug|DEBUG|dbg|DBG)\b', re.IGNORECASE),
            "INFO": re.compile(r'\b(info|INFO|information|INFORMATION)\b', re.IGNORECASE),
            "WARN": re.compile(r'\b(warn|WARN|warning|WARNING)\b', re.IGNORECASE),
            "ERROR": re.compile(r'\b(error|ERROR|err|ERR|exception|EXCEPTION)\b', re.IGNORECASE),
            "CRITICAL": re.compile(r'\b(critical|CRITICAL|fatal|FATAL|panic|PANIC)\b', re.IGNORECASE),
        }
        
        # Common timestamp patterns
        self.timestamp_patterns = [
            re.compile(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?'),  # ISO format
            re.compile(r'\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}'),  # Date format
            re.compile(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]'),  # Bracket format
        ]
    
    def normalize(
        self,
        raw_log: str,
        source: str,
        parsed_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Normalize a log entry
        
        Args:
            raw_log: Raw log line
            source: Source identifier
            parsed_fields: Optional pre-parsed fields
            
        Returns:
            Normalized log dictionary
        """
        try:
            # If already parsed, use those fields
            if parsed_fields:
                normalized = {
                    "timestamp": self._extract_timestamp(parsed_fields.get("timestamp") or raw_log),
                    "level": self._extract_level(parsed_fields.get("level") or raw_log),
                    "message": parsed_fields.get("message", raw_log),
                    "source": source,
                    "service": parsed_fields.get("service"),
                    "environment": parsed_fields.get("environment"),
                    "metadata": {k: v for k, v in parsed_fields.items() if k not in ["timestamp", "level", "message", "service", "environment"]}
                }
            else:
                # Try to parse as JSON first
                try:
                    parsed = json.loads(raw_log)
                    if isinstance(parsed, dict):
                        return self.normalize(raw_log, source, parsed)
                except json.JSONDecodeError:
                    pass
                
                # Parse plain text log
                normalized = {
                    "timestamp": self._extract_timestamp(raw_log),
                    "level": self._extract_level(raw_log),
                    "message": self._extract_message(raw_log),
                    "source": source,
                    "service": None,
                    "environment": None,
                    "metadata": {}
                }
            
            # Extract error patterns
            normalized["error_patterns"] = self._extract_error_patterns(normalized["message"])
            
            # Extract metrics if present
            normalized["metrics"] = self._extract_metrics(normalized["message"])
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing log: {e}")
            return {
                "timestamp": datetime.now(),
                "level": "INFO",
                "message": raw_log,
                "source": source,
                "error": str(e)
            }
    
    def _extract_timestamp(self, text: str) -> datetime:
        """Extract timestamp from log text"""
        # Try patterns
        for pattern in self.timestamp_patterns:
            match = pattern.search(text)
            if match:
                try:
                    ts_str = match.group(1) if match.groups() else match.group(0)
                    # Try to parse
                    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d %H:%M:%S"]:
                        try:
                            return datetime.strptime(ts_str, fmt)
                        except:
                            continue
                except:
                    pass
        
        # Default to now
        return datetime.now()
    
    def _extract_level(self, text: str) -> str:
        """Extract log level from text"""
        for level, pattern in self.level_patterns.items():
            if pattern.search(text):
                return level
        return "INFO"  # Default
    
    def _extract_message(self, text: str) -> str:
        """Extract message from log text"""
        # Remove timestamp if present
        for pattern in self.timestamp_patterns:
            text = pattern.sub("", text).strip()
        
        # Remove level if at start
        for level in ["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]:
            if text.startswith(level):
                text = text[len(level):].strip()
        
        return text[:1000]  # Truncate if too long
    
    def _extract_error_patterns(self, message: str) -> List[str]:
        """Extract error patterns from message"""
        patterns = []
        
        # Stack trace pattern
        if "Traceback" in message or "at " in message:
            patterns.append("stack_trace")
        
        # Connection error
        if any(keyword in message.lower() for keyword in ["connection", "timeout", "refused", "reset"]):
            patterns.append("connection_error")
        
        # Authentication error
        if any(keyword in message.lower() for keyword in ["unauthorized", "forbidden", "authentication", "auth"]):
            patterns.append("auth_error")
        
        # Resource error
        if any(keyword in message.lower() for keyword in ["out of memory", "disk full", "no space"]):
            patterns.append("resource_error")
        
        return patterns
    
    def _extract_metrics(self, message: str) -> Dict[str, float]:
        """Extract numeric metrics from message"""
        metrics = {}
        
        # CPU, memory, disk patterns
        cpu_match = re.search(r'cpu[:\s]+(\d+\.?\d*)%?', message, re.IGNORECASE)
        if cpu_match:
            try:
                metrics["cpu"] = float(cpu_match.group(1))
            except:
                pass
        
        memory_match = re.search(r'memory[:\s]+(\d+\.?\d*)\s*(MB|GB|%)?', message, re.IGNORECASE)
        if memory_match:
            try:
                metrics["memory"] = float(memory_match.group(1))
            except:
                pass
        
        return metrics

