"""
Log Pattern Extractor - Extract patterns from logs
"""
import re
from typing import Dict, Any, List, Optional
from collections import Counter
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.core.logging import get_logger
from app.models.log_entry import LogEntry
from app.models.log_pattern import LogPattern

logger = get_logger(__name__)


class LogPatternExtractor:
    """Service for extracting patterns from logs"""
    
    def __init__(self):
        # Common error patterns
        self.error_patterns = [
            (r'error:\s*(.+)', 'error_message'),
            (r'exception:\s*(.+)', 'exception'),
            (r'failed\s+to\s+(.+)', 'failure'),
            (r'timeout', 'timeout'),
            (r'connection\s+refused', 'connection_error'),
            (r'out\s+of\s+memory', 'memory_error'),
            (r'disk\s+full', 'disk_error'),
        ]
    
    async def extract_patterns(
        self,
        tenant_id: int,
        time_window_minutes: int = 60,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Extract patterns from recent logs
        
        Args:
            tenant_id: Tenant ID
            time_window_minutes: Time window to analyze
            db: Database session
            
        Returns:
            Dict with extracted patterns
        """
        try:
            # Get recent logs
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
            
            logs = db.query(LogEntry).filter(
                and_(
                    LogEntry.tenant_id == tenant_id,
                    LogEntry.timestamp >= cutoff_time
                )
            ).all()
            
            # Extract patterns
            error_patterns = []
            warning_patterns = []
            error_frequency = Counter()
            warning_frequency = Counter()
            
            for log in logs:
                if log.level == "ERROR" or log.level == "CRITICAL":
                    pattern = self._extract_pattern_signature(log.message)
                    error_patterns.append(pattern)
                    error_frequency[pattern] += 1
                elif log.level == "WARN":
                    pattern = self._extract_pattern_signature(log.message)
                    warning_patterns.append(pattern)
                    warning_frequency[pattern] += 1
            
            # Store patterns in database
            stored_patterns = []
            for pattern, frequency in error_frequency.most_common(20):
                stored = await self._store_pattern(
                    tenant_id=tenant_id,
                    pattern_signature=pattern,
                    pattern_type="error_pattern",
                    frequency=frequency,
                    db=db
                )
                if stored:
                    stored_patterns.append(stored)
            
            for pattern, frequency in warning_frequency.most_common(20):
                stored = await self._store_pattern(
                    tenant_id=tenant_id,
                    pattern_signature=pattern,
                    pattern_type="warning_pattern",
                    frequency=frequency,
                    db=db
                )
                if stored:
                    stored_patterns.append(stored)
            
            return {
                "success": True,
                "patterns_extracted": len(stored_patterns),
                "error_patterns": len(error_patterns),
                "warning_patterns": len(warning_patterns),
                "patterns": stored_patterns
            }
            
        except Exception as e:
            logger.error(f"Error extracting patterns: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_pattern_signature(self, message: str) -> str:
        """Extract a pattern signature from a log message"""
        # Normalize the message
        # Replace numbers with placeholders
        normalized = re.sub(r'\d+', 'N', message)
        # Replace UUIDs with placeholders
        normalized = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', 'UUID', normalized, flags=re.IGNORECASE)
        # Replace IP addresses with placeholders
        normalized = re.sub(r'\d+\.\d+\.\d+\.\d+', 'IP', normalized)
        # Replace file paths with placeholders
        normalized = re.sub(r'/[^\s]+', '/PATH', normalized)
        # Replace email addresses
        normalized = re.sub(r'[\w\.-]+@[\w\.-]+', 'EMAIL', normalized)
        
        # Take first 200 chars as signature
        return normalized[:200]
    
    async def _store_pattern(
        self,
        tenant_id: int,
        pattern_signature: str,
        pattern_type: str,
        frequency: int,
        db: Session
    ) -> Optional[LogPattern]:
        """Store or update a pattern in the database"""
        try:
            # Check if pattern exists
            pattern = db.query(LogPattern).filter(
                and_(
                    LogPattern.tenant_id == tenant_id,
                    LogPattern.pattern_signature == pattern_signature,
                    LogPattern.pattern_type == pattern_type
                )
            ).first()
            
            if pattern:
                # Update existing pattern
                pattern.frequency += frequency
                pattern.last_seen = datetime.now(timezone.utc)
            else:
                # Create new pattern
                pattern = LogPattern(
                    tenant_id=tenant_id,
                    pattern_signature=pattern_signature,
                    pattern_type=pattern_type,
                    frequency=frequency,
                    first_seen=datetime.now(timezone.utc),
                    last_seen=datetime.now(timezone.utc)
                )
                db.add(pattern)
            
            db.commit()
            db.refresh(pattern)
            
            return pattern
            
        except Exception as e:
            logger.error(f"Error storing pattern: {e}")
            db.rollback()
            return None
    
    async def detect_anomalies(
        self,
        tenant_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Detect anomalies in log patterns
        
        Args:
            tenant_id: Tenant ID
            db: Database session
            
        Returns:
            Dict with detected anomalies
        """
        try:
            # Get recent error rate
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
            
            recent_errors = db.query(func.count(LogEntry.id)).filter(
                and_(
                    LogEntry.tenant_id == tenant_id,
                    LogEntry.level.in_(["ERROR", "CRITICAL"]),
                    LogEntry.timestamp >= cutoff_time
                )).scalar() or 0
            
            # Get historical average (last 24 hours)
            historical_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            historical_errors = db.query(func.count(LogEntry.id)).filter(
                and_(
                    LogEntry.tenant_id == tenant_id,
                    LogEntry.level.in_(["ERROR", "CRITICAL"]),
                    LogEntry.timestamp >= historical_cutoff,
                    LogEntry.timestamp < cutoff_time
                )).scalar() or 0
            
            # Calculate average per hour
            historical_avg = historical_errors / 23  # 23 hours
            
            # Detect anomaly if current rate is 2x historical average
            is_anomaly = recent_errors > (historical_avg * 2)
            
            return {
                "success": True,
                "is_anomaly": is_anomaly,
                "current_error_rate": recent_errors,
                "historical_average": historical_avg,
                "anomaly_score": recent_errors / historical_avg if historical_avg > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return {
                "success": False,
                "error": str(e)
            }

