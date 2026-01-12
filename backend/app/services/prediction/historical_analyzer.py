"""
Historical Analyzer - Map log patterns to past incidents
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from app.core.logging import get_logger
from app.models.log_entry import LogEntry
from app.models.log_pattern import LogPattern
from app.models.ticket import Ticket
from app.models.execution_session import ExecutionSession

logger = get_logger(__name__)


class HistoricalAnalyzer:
    """Service for analyzing historical incidents and their precursors"""
    
    def __init__(self):
        # Time window before incident to analyze (in minutes)
        self.pre_incident_window_minutes = 60
    
    async def map_patterns_to_incidents(
        self,
        tenant_id: int,
        days_back: int = 30,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Map log patterns to past incidents
        
        Args:
            tenant_id: Tenant ID
            days_back: Number of days to look back
            db: Database session
            
        Returns:
            Dict with pattern-to-incident mappings
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            # Get resolved tickets (incidents)
            incidents = db.query(Ticket).filter(
                and_(
                    Ticket.tenant_id == tenant_id,
                    Ticket.created_at >= cutoff_date,
                    Ticket.status.in_(['resolved', 'closed'])
                )
            ).order_by(Ticket.created_at.desc()).all()
            
            mappings = []
            
            for incident in incidents:
                # Get logs before incident
                incident_time = incident.created_at
                pre_window_start = incident_time - timedelta(minutes=self.pre_incident_window_minutes)
                
                pre_incident_logs = db.query(LogEntry).filter(
                    and_(
                        LogEntry.tenant_id == tenant_id,
                        LogEntry.timestamp >= pre_window_start,
                        LogEntry.timestamp < incident_time
                    )
                ).all()
                
                # Extract patterns from pre-incident logs
                pattern_signatures = set()
                for log in pre_incident_logs:
                    if log.level in ['ERROR', 'CRITICAL', 'WARN']:
                        # Create pattern signature
                        signature = self._extract_pattern_signature(log.message)
                        pattern_signatures.add(signature)
                
                # Update pattern associations
                for signature in pattern_signatures:
                    pattern = db.query(LogPattern).filter(
                        and_(
                            LogPattern.tenant_id == tenant_id,
                            LogPattern.pattern_signature == signature
                        )
                    ).first()
                    
                    if pattern:
                        pattern.associated_incidents += 1
                        if not pattern.last_seen or pattern.last_seen < incident_time:
                            pattern.last_seen = incident_time
                    else:
                        # Create new pattern
                        pattern = LogPattern(
                            tenant_id=tenant_id,
                            pattern_signature=signature,
                            pattern_type="error_pattern" if any(log.level in ['ERROR', 'CRITICAL'] for log in pre_incident_logs if signature in log.message) else "warning_pattern",
                            frequency=1,
                            first_seen=incident_time,
                            last_seen=incident_time,
                            associated_incidents=1
                        )
                        db.add(pattern)
                    
                    mappings.append({
                        "pattern_signature": signature,
                        "incident_id": incident.id,
                        "incident_title": incident.title,
                        "incident_time": incident_time.isoformat(),
                        "pattern_type": pattern.pattern_type
                    })
                
                db.commit()
            
            return {
                "success": True,
                "incidents_analyzed": len(incidents),
                "patterns_found": len(set([m["pattern_signature"] for m in mappings])),
                "mappings": mappings
            }
            
        except Exception as e:
            logger.error(f"Error mapping patterns to incidents: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def identify_failure_sequences(
        self,
        tenant_id: int,
        days_back: int = 30,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Identify common failure sequences leading to incidents
        
        Args:
            tenant_id: Tenant ID
            days_back: Number of days to look back
            db: Database session
            
        Returns:
            Dict with common failure sequences
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            # Get incidents
            incidents = db.query(Ticket).filter(
                and_(
                    Ticket.tenant_id == tenant_id,
                    Ticket.created_at >= cutoff_date,
                    Ticket.status.in_(['resolved', 'closed'])
                )
            ).order_by(Ticket.created_at.desc()).limit(50).all()
            
            sequences = []
            
            for incident in incidents:
                incident_time = incident.created_at
                pre_window_start = incident_time - timedelta(minutes=self.pre_incident_window_minutes)
                
                # Get logs in sequence
                logs = db.query(LogEntry).filter(
                    and_(
                        LogEntry.tenant_id == tenant_id,
                        LogEntry.timestamp >= pre_window_start,
                        LogEntry.timestamp < incident_time
                    )
                ).order_by(LogEntry.timestamp).all()
                
                # Extract sequence of error patterns
                sequence = []
                for log in logs:
                    if log.level in ['ERROR', 'CRITICAL']:
                        signature = self._extract_pattern_signature(log.message)
                        if signature not in sequence:  # Avoid duplicates
                            sequence.append(signature)
                
                if sequence:
                    sequences.append({
                        "incident_id": incident.id,
                        "sequence": sequence,
                        "sequence_length": len(sequence),
                        "incident_time": incident_time.isoformat()
                    })
            
            # Find common sequences
            sequence_counts = {}
            for seq_data in sequences:
                seq_key = tuple(seq_data["sequence"])
                if seq_key not in sequence_counts:
                    sequence_counts[seq_key] = {
                        "count": 0,
                        "incidents": []
                    }
                sequence_counts[seq_key]["count"] += 1
                sequence_counts[seq_key]["incidents"].append(seq_data["incident_id"])
            
            # Sort by frequency
            common_sequences = sorted(
                [
                    {
                        "sequence": list(seq_key),
                        "frequency": data["count"],
                        "incident_count": len(data["incidents"]),
                        "incident_ids": data["incidents"]
                    }
                    for seq_key, data in sequence_counts.items()
                ],
                key=lambda x: x["frequency"],
                reverse=True
            )
            
            return {
                "success": True,
                "total_sequences": len(sequences),
                "unique_sequences": len(sequence_counts),
                "common_sequences": common_sequences[:10]  # Top 10
            }
            
        except Exception as e:
            logger.error(f"Error identifying failure sequences: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def calculate_pattern_confidence(
        self,
        pattern_id: int,
        db: Session = None
    ) -> float:
        """
        Calculate confidence score for a pattern based on historical data
        
        Args:
            pattern_id: Pattern ID
            db: Database session
            
        Returns:
            Confidence score (0.0-1.0)
        """
        try:
            pattern = db.query(LogPattern).filter(LogPattern.id == pattern_id).first()
            
            if not pattern:
                return 0.0
            
            # Base confidence on:
            # 1. Number of associated incidents (more = higher confidence)
            # 2. Frequency (more occurrences = higher confidence)
            # 3. Recency (more recent = higher confidence)
            
            incident_score = min(1.0, pattern.associated_incidents / 10.0)  # Cap at 10 incidents
            frequency_score = min(1.0, pattern.frequency / 100.0)  # Cap at 100 occurrences
            
            recency_score = 0.5  # Default
            if pattern.last_seen:
                days_since = (datetime.now(timezone.utc) - pattern.last_seen).days
                if days_since <= 7:
                    recency_score = 1.0
                elif days_since <= 30:
                    recency_score = 0.7
                elif days_since <= 90:
                    recency_score = 0.5
                else:
                    recency_score = 0.3
            
            # Weighted average
            confidence = (
                incident_score * 0.5 +
                frequency_score * 0.3 +
                recency_score * 0.2
            )
            
            # Update pattern confidence
            pattern.confidence_score = confidence
            db.commit()
            
            return confidence
            
        except Exception as e:
            logger.error(f"Error calculating pattern confidence: {e}")
            db.rollback()
            return 0.0
    
    def _extract_pattern_signature(self, message: str) -> str:
        """Extract pattern signature from message"""
        import re
        
        # Normalize the message
        normalized = re.sub(r'\d+', 'N', message)
        normalized = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', 'UUID', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\d+\.\d+\.\d+\.\d+', 'IP', normalized)
        normalized = re.sub(r'/[^\s]+', '/PATH', normalized)
        normalized = re.sub(r'[\w\.-]+@[\w\.-]+', 'EMAIL', normalized)
        
        return normalized[:200]

