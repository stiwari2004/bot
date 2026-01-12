"""
Short-term Predictor - Predict incidents in next 5-30 minutes
"""
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.services.prediction.feature_engineering import FeatureEngineeringService
from app.services.prediction.historical_analyzer import HistoricalAnalyzer
from app.services.prediction.log_pattern_extractor import LogPatternExtractor

logger = get_logger(__name__)


class ShortTermPredictor:
    """
    Short-term prediction model (minutes)
    Uses time-series analysis and pattern matching
    """
    
    def __init__(self):
        self.feature_service = FeatureEngineeringService()
        self.historical_analyzer = HistoricalAnalyzer()
        self.pattern_extractor = LogPatternExtractor()
    
    async def predict(
        self,
        tenant_id: int,
        db: Session,
        time_horizon_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Predict incidents in the next time_horizon_minutes
        
        Args:
            tenant_id: Tenant ID
            db: Database session
            time_horizon_minutes: Prediction horizon (5-30 minutes)
            
        Returns:
            Dict with prediction results
        """
        try:
            # Get recent time-series features (last 15 minutes)
            ts_features = await self.feature_service.create_time_series_features(
                tenant_id=tenant_id,
                time_window_minutes=15,
                window_size_minutes=1,  # 1-minute windows for short-term
                db=db
            )
            
            if not ts_features["success"]:
                return {
                    "success": False,
                    "error": ts_features.get("error", "Failed to create features")
                }
            
            features = ts_features.get("features", {})
            
            # Detect anomalies
            anomaly_result = await self.pattern_extractor.detect_anomalies(
                tenant_id=tenant_id,
                db=db
            )
            
            # Get current patterns
            pattern_result = await self.pattern_extractor.extract_patterns(
                tenant_id=tenant_id,
                time_window_minutes=15,
                db=db
            )
            
            # Calculate prediction confidence
            confidence = self._calculate_confidence(
                features=features,
                anomaly_result=anomaly_result,
                pattern_count=pattern_result.get("patterns_extracted", 0)
            )
            
            # Determine risk level
            risk_level = self._determine_risk_level(confidence, features, anomaly_result)
            
            # Predict incident type
            incident_type = self._predict_incident_type(features, anomaly_result)
            
            return {
                "success": True,
                "prediction_type": "short_term",
                "confidence_score": confidence,
                "risk_level": risk_level,
                "time_horizon_minutes": time_horizon_minutes,
                "predicted_incident_type": incident_type,
                "features_used": {
                    "error_rate_trend": features.get("error_rate_trend", 0),
                    "error_rate_increase": features.get("error_rate_increase", False),
                    "anomaly_detected": anomaly_result.get("is_anomaly", False),
                    "anomaly_score": anomaly_result.get("anomaly_score", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in short-term prediction: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_confidence(
        self,
        features: Dict[str, Any],
        anomaly_result: Dict[str, Any],
        pattern_count: int
    ) -> float:
        """Calculate prediction confidence"""
        confidence = 0.0
        
        # Anomaly detection (40% weight)
        if anomaly_result.get("is_anomaly"):
            anomaly_score = anomaly_result.get("anomaly_score", 1.0)
            confidence += min(0.4, (anomaly_score - 1.0) * 0.2)  # Scale anomaly score
        
        # Error rate trend (30% weight)
        error_trend = features.get("error_rate_trend", 0)
        if error_trend > 0:
            confidence += min(0.3, error_trend * 0.1)
        
        # Error rate increase flag (20% weight)
        if features.get("error_rate_increase"):
            confidence += 0.2
        
        # Pattern count (10% weight)
        if pattern_count > 5:
            confidence += min(0.1, pattern_count * 0.01)
        
        return min(1.0, confidence)
    
    def _determine_risk_level(
        self,
        confidence: float,
        features: Dict[str, Any],
        anomaly_result: Dict[str, Any]
    ) -> str:
        """Determine risk level"""
        if confidence >= 0.8:
            return "critical"
        elif confidence >= 0.6:
            return "high"
        elif confidence >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _predict_incident_type(
        self,
        features: Dict[str, Any],
        anomaly_result: Dict[str, Any]
    ) -> str:
        """Predict the type of incident"""
        if anomaly_result.get("is_anomaly"):
            anomaly_score = anomaly_result.get("anomaly_score", 1.0)
            if anomaly_score > 3.0:
                return "critical_error_spike"
            elif anomaly_score > 2.0:
                return "error_rate_spike"
            else:
                return "elevated_error_rate"
        
        error_trend = features.get("error_rate_trend", 0)
        if error_trend > 0.5:
            return "increasing_errors"
        
        return "potential_incident"

