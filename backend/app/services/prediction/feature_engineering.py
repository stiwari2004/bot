"""
Feature Engineering Service - Create features for ML models
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.core.logging import get_logger
from app.models.log_entry import LogEntry
from app.models.log_pattern import LogPattern
from app.models.ticket import Ticket

logger = get_logger(__name__)


class FeatureEngineeringService:
    """Service for creating features for ML models"""
    
    def __init__(self):
        pass
    
    async def create_time_series_features(
        self,
        tenant_id: int,
        time_window_minutes: int = 60,
        window_size_minutes: int = 5,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Create time-series features from logs
        
        Args:
            tenant_id: Tenant ID
            time_window_minutes: Time window to analyze
            window_size_minutes: Size of sliding windows
            db: Database session
            
        Returns:
            Dict with time-series features
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
            
            # Get logs
            logs = db.query(LogEntry).filter(
                and_(
                    LogEntry.tenant_id == tenant_id,
                    LogEntry.timestamp >= cutoff_time
                )
            ).order_by(LogEntry.timestamp).all()
            
            if not logs:
                return {
                    "success": False,
                    "error": "No logs found in time window"
                }
            
            # Convert to DataFrame
            log_data = []
            for log in logs:
                log_data.append({
                    "timestamp": log.timestamp,
                    "level": log.level,
                    "log_type": log.log_type,
                    "service": log.service
                })
            
            df = pd.DataFrame(log_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            # Create time windows
            windows = []
            window_start = df.index.min()
            window_end = df.index.max()
            
            current = window_start
            while current < window_end:
                window_df = df[(df.index >= current) & (df.index < current + timedelta(minutes=window_size_minutes))]
                
                if not window_df.empty:
                    windows.append({
                        "window_start": current,
                        "window_end": current + timedelta(minutes=window_size_minutes),
                        "error_count": len(window_df[window_df['level'].isin(['ERROR', 'CRITICAL'])]),
                        "warning_count": len(window_df[window_df['level'] == 'WARN']),
                        "info_count": len(window_df[window_df['level'] == 'INFO']),
                        "unique_services": window_df['service'].nunique() if 'service' in window_df.columns else 0,
                        "total_logs": len(window_df)
                    })
                
                current += timedelta(minutes=window_size_minutes)
            
            # Calculate trends
            if len(windows) > 1:
                error_counts = [w['error_count'] for w in windows]
                error_trend = self._calculate_trend(error_counts)
                warning_counts = [w['warning_count'] for w in windows]
                warning_trend = self._calculate_trend(warning_counts)
            else:
                error_trend = 0.0
                warning_trend = 0.0
            
            return {
                "success": True,
                "windows": windows,
                "features": {
                    "error_rate_trend": error_trend,
                    "warning_rate_trend": warning_trend,
                    "total_windows": len(windows),
                    "avg_errors_per_window": np.mean([w['error_count'] for w in windows]) if windows else 0,
                    "max_errors_per_window": max([w['error_count'] for w in windows]) if windows else 0,
                    "error_rate_increase": error_trend > 0.1,
                    "warning_to_error_ratio": np.mean([w['warning_count'] / max(w['error_count'], 1) for w in windows]) if windows else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating time-series features: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend (slope) of values"""
        if len(values) < 2:
            return 0.0
        
        try:
            x = np.arange(len(values))
            slope = np.polyfit(x, values, 1)[0]
            return float(slope)
        except:
            return 0.0
    
    async def create_pattern_features(
        self,
        tenant_id: int,
        pattern_ids: List[int],
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Create features from log patterns
        
        Args:
            tenant_id: Tenant ID
            pattern_ids: List of pattern IDs
            db: Database session
            
        Returns:
            Dict with pattern features
        """
        try:
            patterns = db.query(LogPattern).filter(
                and_(
                    LogPattern.tenant_id == tenant_id,
                    LogPattern.id.in_(pattern_ids)
                )
            ).all()
            
            if not patterns:
                return {
                    "success": False,
                    "error": "No patterns found"
                }
            
            features = {
                "pattern_count": len(patterns),
                "error_pattern_count": len([p for p in patterns if p.pattern_type == "error_pattern"]),
                "warning_pattern_count": len([p for p in patterns if p.pattern_type == "warning_pattern"]),
                "anomaly_pattern_count": len([p for p in patterns if p.pattern_type == "anomaly"]),
                "avg_frequency": np.mean([p.frequency for p in patterns]) if patterns else 0,
                "max_frequency": max([p.frequency for p in patterns]) if patterns else 0,
                "avg_confidence": np.mean([p.confidence_score or 0.0 for p in patterns]) if patterns else 0,
                "associated_incidents": sum([p.associated_incidents for p in patterns]),
                "recent_patterns": len([p for p in patterns if p.last_seen and (datetime.now(timezone.utc) - p.last_seen).total_seconds() < 3600])
            }
            
            return {
                "success": True,
                "features": features
            }
            
        except Exception as e:
            logger.error(f"Error creating pattern features: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_resource_utilization_features(
        self,
        tenant_id: int,
        time_window_minutes: int = 60,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Extract resource utilization features from logs
        
        Args:
            tenant_id: Tenant ID
            time_window_minutes: Time window
            db: Database session
            
        Returns:
            Dict with resource features
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
            
            logs = db.query(LogEntry).filter(
                and_(
                    LogEntry.tenant_id == tenant_id,
                    LogEntry.timestamp >= cutoff_time,
                    LogEntry.parsed_fields.isnot(None)
                )
            ).all()
            
            cpu_values = []
            memory_values = []
            disk_values = []
            
            for log in logs:
                if log.parsed_fields:
                    metrics = log.parsed_fields.get("metrics", {})
                    if "cpu" in metrics:
                        cpu_values.append(float(metrics["cpu"]))
                    if "memory" in metrics:
                        memory_values.append(float(metrics["memory"]))
                    if "disk" in metrics:
                        disk_values.append(float(metrics["disk"]))
            
            features = {
                "cpu_avg": np.mean(cpu_values) if cpu_values else None,
                "cpu_max": max(cpu_values) if cpu_values else None,
                "cpu_trend": self._calculate_trend(cpu_values[-10:]) if len(cpu_values) >= 10 else None,
                "memory_avg": np.mean(memory_values) if memory_values else None,
                "memory_max": max(memory_values) if memory_values else None,
                "memory_trend": self._calculate_trend(memory_values[-10:]) if len(memory_values) >= 10 else None,
                "disk_avg": np.mean(disk_values) if disk_values else None,
                "disk_max": max(disk_values) if disk_values else None,
                "resource_warnings": len([v for v in cpu_values if v > 80]) + len([v for v in memory_values if v > 80])
            }
            
            return {
                "success": True,
                "features": features
            }
            
        except Exception as e:
            logger.error(f"Error creating resource features: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_historical_pattern_features(
        self,
        tenant_id: int,
        current_patterns: List[str],
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Create features based on historical pattern-to-incident mappings
        
        Args:
            tenant_id: Tenant ID
            current_patterns: List of current pattern signatures
            db: Database session
            
        Returns:
            Dict with historical features
        """
        try:
            # Get patterns that have been associated with incidents
            patterns = db.query(LogPattern).filter(
                and_(
                    LogPattern.tenant_id == tenant_id,
                    LogPattern.pattern_signature.in_(current_patterns),
                    LogPattern.associated_incidents > 0
                )
            ).all()
            
            if not patterns:
                return {
                    "success": True,
                    "features": {
                        "historical_incident_count": 0,
                        "avg_incidents_per_pattern": 0,
                        "high_risk_patterns": 0
                    }
                }
            
            total_incidents = sum([p.associated_incidents for p in patterns])
            avg_incidents = total_incidents / len(patterns) if patterns else 0
            high_risk = len([p for p in patterns if p.associated_incidents >= 3])
            
            return {
                "success": True,
                "features": {
                    "historical_incident_count": total_incidents,
                    "avg_incidents_per_pattern": avg_incidents,
                    "high_risk_patterns": high_risk,
                    "pattern_incident_rate": total_incidents / len(current_patterns) if current_patterns else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating historical features: {e}")
            return {
                "success": False,
                "error": str(e)
            }

