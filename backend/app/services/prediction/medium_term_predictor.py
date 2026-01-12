"""
Medium-term Predictor - Predict incidents in next 1-24 hours
"""
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.services.prediction.feature_engineering import FeatureEngineeringService
from app.services.prediction.historical_analyzer import HistoricalAnalyzer
from app.services.prediction.log_pattern_extractor import LogPatternExtractor

logger = get_logger(__name__)


class MediumTermPredictor:
    """
    Medium-term prediction model (hours)
    Uses statistical analysis and pattern matching
    """
    
    def __init__(self):
        self.feature_service = FeatureEngineeringService()
        self.historical_analyzer = HistoricalAnalyzer()
        self.pattern_extractor = LogPatternExtractor()
    
    async def predict(
        self,
        tenant_id: int,
        db: Session,
        time_horizon_hours: int = 6
    ) -> Dict[str, Any]:
        """
        Predict incidents in the next time_horizon_hours
        
        Args:
            tenant_id: Tenant ID
            db: Database session
            time_horizon_hours: Prediction horizon (1-24 hours)
            
        Returns:
            Dict with prediction results
        """
        try:
            # Get time-series features (last 6 hours)
            ts_features = await self.feature_service.create_time_series_features(
                tenant_id=tenant_id,
                time_window_minutes=time_horizon_hours * 60,
                window_size_minutes=15,  # 15-minute windows for medium-term
                db=db
            )
            
            if not ts_features["success"]:
                return {
                    "success": False,
                    "error": ts_features.get("error", "Failed to create features")
                }
            
            features = ts_features.get("features", {})
            
            # Get pattern features
            pattern_result = await self.pattern_extractor.extract_patterns(
                tenant_id=tenant_id,
                time_window_minutes=time_horizon_hours * 60,
                db=db
            )
            
            pattern_ids = [p.id for p in pattern_result.get("patterns", [])]
            pattern_features = await self.feature_service.create_pattern_features(
                tenant_id=tenant_id,
                pattern_ids=pattern_ids,
                db=db
            )
            
            # Get resource utilization features
            resource_features = await self.feature_service.create_resource_utilization_features(
                tenant_id=tenant_id,
                time_window_minutes=time_horizon_hours * 60,
                db=db
            )
            
            # Get historical pattern features
            current_patterns = [p.pattern_signature for p in pattern_result.get("patterns", [])]
            historical_features = await self.feature_service.create_historical_pattern_features(
                tenant_id=tenant_id,
                current_patterns=current_patterns,
                db=db
            )
            
            # Calculate statistical indicators
            stats = self._calculate_statistical_indicators(
                ts_features=features,
                pattern_features=pattern_features.get("features", {}) if pattern_features.get("success") else {},
                resource_features=resource_features.get("features", {}) if resource_features.get("success") else {},
                historical_features=historical_features.get("features", {}) if historical_features.get("success") else {}
            )
            
            # Calculate confidence
            confidence = self._calculate_confidence(stats)
            
            # Determine risk level
            risk_level = self._determine_risk_level(confidence, stats)
            
            # Predict incident type
            incident_type = self._predict_incident_type(stats)
            
            return {
                "success": True,
                "prediction_type": "medium_term",
                "confidence_score": confidence,
                "risk_level": risk_level,
                "time_horizon_minutes": time_horizon_hours * 60,
                "predicted_incident_type": incident_type,
                "statistical_indicators": stats
            }
            
        except Exception as e:
            logger.error(f"Error in medium-term prediction: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_statistical_indicators(
        self,
        ts_features: Dict[str, Any],
        pattern_features: Dict[str, Any],
        resource_features: Dict[str, Any],
        historical_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate statistical indicators"""
        indicators = {
            "error_rate_trend": ts_features.get("error_rate_trend", 0),
            "error_rate_increase": ts_features.get("error_rate_increase", False),
            "avg_errors_per_window": ts_features.get("avg_errors_per_window", 0),
            "max_errors_per_window": ts_features.get("max_errors_per_window", 0),
            "pattern_incident_rate": historical_features.get("pattern_incident_rate", 0),
            "high_risk_patterns": historical_features.get("high_risk_patterns", 0),
            "resource_warnings": resource_features.get("resource_warnings", 0),
            "cpu_trend": resource_features.get("cpu_trend"),
            "memory_trend": resource_features.get("memory_trend")
        }
        
        # Calculate composite scores
        indicators["error_severity_score"] = (
            indicators["avg_errors_per_window"] * 0.3 +
            indicators["max_errors_per_window"] * 0.7
        )
        
        indicators["pattern_risk_score"] = (
            indicators["pattern_incident_rate"] * 0.6 +
            (indicators["high_risk_patterns"] / 10.0) * 0.4
        )
        
        return indicators
    
    def _calculate_confidence(self, stats: Dict[str, Any]) -> float:
        """Calculate prediction confidence from statistical indicators"""
        confidence = 0.0
        
        # Error severity (30% weight)
        error_severity = stats.get("error_severity_score", 0)
        if error_severity > 10:
            confidence += 0.3
        elif error_severity > 5:
            confidence += 0.2
        elif error_severity > 2:
            confidence += 0.1
        
        # Pattern risk (30% weight)
        pattern_risk = stats.get("pattern_risk_score", 0)
        if pattern_risk > 0.5:
            confidence += 0.3
        elif pattern_risk > 0.3:
            confidence += 0.2
        elif pattern_risk > 0.1:
            confidence += 0.1
        
        # Error rate trend (20% weight)
        if stats.get("error_rate_increase"):
            confidence += 0.2
        
        # Resource warnings (10% weight)
        resource_warnings = stats.get("resource_warnings", 0)
        if resource_warnings > 5:
            confidence += 0.1
        elif resource_warnings > 2:
            confidence += 0.05
        
        # Historical pattern association (10% weight)
        if stats.get("pattern_incident_rate", 0) > 0.3:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _determine_risk_level(
        self,
        confidence: float,
        stats: Dict[str, Any]
    ) -> str:
        """Determine risk level"""
        # Adjust based on severity
        error_severity = stats.get("error_severity_score", 0)
        pattern_risk = stats.get("pattern_risk_score", 0)
        
        if confidence >= 0.7 and (error_severity > 10 or pattern_risk > 0.5):
            return "critical"
        elif confidence >= 0.6:
            return "high"
        elif confidence >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _predict_incident_type(self, stats: Dict[str, Any]) -> str:
        """Predict incident type from statistical indicators"""
        error_severity = stats.get("error_severity_score", 0)
        pattern_risk = stats.get("pattern_risk_score", 0)
        resource_warnings = stats.get("resource_warnings", 0)
        
        if resource_warnings > 5:
            return "resource_exhaustion"
        elif pattern_risk > 0.5:
            return "pattern_based_incident"
        elif error_severity > 10:
            return "error_escalation"
        elif stats.get("error_rate_increase"):
            return "increasing_error_rate"
        else:
            return "potential_incident"

