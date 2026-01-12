"""
Long-term Predictor - Predict incidents in next 1-7 days
"""
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.services.prediction.feature_engineering import FeatureEngineeringService
from app.services.prediction.historical_analyzer import HistoricalAnalyzer

logger = get_logger(__name__)


class LongTermPredictor:
    """
    Long-term prediction model (days)
    Uses trend analysis and historical patterns
    """
    
    def __init__(self):
        self.feature_service = FeatureEngineeringService()
        self.historical_analyzer = HistoricalAnalyzer()
    
    async def predict(
        self,
        tenant_id: int,
        db: Session,
        time_horizon_days: int = 3
    ) -> Dict[str, Any]:
        """
        Predict incidents in the next time_horizon_days
        
        Args:
            tenant_id: Tenant ID
            db: Database session
            time_horizon_days: Prediction horizon (1-7 days)
            
        Returns:
            Dict with prediction results
        """
        try:
            # Get time-series features (last 7 days)
            ts_features = await self.feature_service.create_time_series_features(
                tenant_id=tenant_id,
                time_window_minutes=time_horizon_days * 24 * 60,
                window_size_minutes=60,  # 1-hour windows for long-term
                db=db
            )
            
            if not ts_features["success"]:
                return {
                    "success": False,
                    "error": ts_features.get("error", "Failed to create features")
                }
            
            features = ts_features.get("features", {})
            windows = ts_features.get("windows", [])
            
            # Calculate trends
            trends = self._calculate_trends(windows)
            
            # Get historical patterns
            historical_result = await self.historical_analyzer.identify_failure_sequences(
                tenant_id=tenant_id,
                days_back=30,
                db=db
            )
            
            # Analyze capacity trends
            capacity_analysis = await self._analyze_capacity_trends(
                tenant_id=tenant_id,
                db=db
            )
            
            # Calculate prediction confidence
            confidence = self._calculate_confidence(
                trends=trends,
                historical_data=historical_result,
                capacity_analysis=capacity_analysis
            )
            
            # Determine risk level
            risk_level = self._determine_risk_level(confidence, trends, capacity_analysis)
            
            # Predict incident type
            incident_type = self._predict_incident_type(trends, capacity_analysis)
            
            return {
                "success": True,
                "prediction_type": "long_term",
                "confidence_score": confidence,
                "risk_level": risk_level,
                "time_horizon_minutes": time_horizon_days * 24 * 60,
                "predicted_incident_type": incident_type,
                "trends": trends,
                "capacity_analysis": capacity_analysis
            }
            
        except Exception as e:
            logger.error(f"Error in long-term prediction: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_trends(self, windows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate long-term trends"""
        if len(windows) < 2:
            return {
                "error_trend": 0.0,
                "warning_trend": 0.0,
                "trend_direction": "stable"
            }
        
        error_counts = [w['error_count'] for w in windows]
        warning_counts = [w['warning_count'] for w in windows]
        
        # Calculate linear trend
        x = np.arange(len(error_counts))
        error_trend = np.polyfit(x, error_counts, 1)[0] if len(error_counts) > 1 else 0.0
        warning_trend = np.polyfit(x, warning_counts, 1)[0] if len(warning_counts) > 1 else 0.0
        
        # Determine trend direction
        if error_trend > 0.1:
            direction = "increasing"
        elif error_trend < -0.1:
            direction = "decreasing"
        else:
            direction = "stable"
        
        return {
            "error_trend": float(error_trend),
            "warning_trend": float(warning_trend),
            "trend_direction": direction,
            "error_avg": np.mean(error_counts),
            "error_max": max(error_counts),
            "error_min": min(error_counts),
            "trend_strength": abs(error_trend) / max(np.std(error_counts), 0.1) if len(error_counts) > 1 else 0.0
        }
    
    async def _analyze_capacity_trends(
        self,
        tenant_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """Analyze capacity and resource trends"""
        try:
            # Get resource features over last 7 days
            resource_features = await self.feature_service.create_resource_utilization_features(
                tenant_id=tenant_id,
                time_window_minutes=7 * 24 * 60,
                db=db
            )
            
            if not resource_features.get("success"):
                return {
                    "cpu_trend": None,
                    "memory_trend": None,
                    "capacity_warning": False
                }
            
            features = resource_features.get("features", {})
            
            capacity_warning = False
            if features.get("cpu_avg") and features.get("cpu_avg") > 80:
                capacity_warning = True
            if features.get("memory_avg") and features.get("memory_avg") > 80:
                capacity_warning = True
            
            return {
                "cpu_trend": features.get("cpu_trend"),
                "memory_trend": features.get("memory_trend"),
                "cpu_avg": features.get("cpu_avg"),
                "memory_avg": features.get("memory_avg"),
                "capacity_warning": capacity_warning
            }
            
        except Exception as e:
            logger.error(f"Error analyzing capacity trends: {e}")
            return {
                "cpu_trend": None,
                "memory_trend": None,
                "capacity_warning": False
            }
    
    def _calculate_confidence(
        self,
        trends: Dict[str, Any],
        historical_data: Dict[str, Any],
        capacity_analysis: Dict[str, Any]
    ) -> float:
        """Calculate prediction confidence"""
        confidence = 0.0
        
        # Trend strength (40% weight)
        trend_strength = trends.get("trend_strength", 0)
        if trend_strength > 0.5:
            confidence += 0.4
        elif trend_strength > 0.3:
            confidence += 0.3
        elif trend_strength > 0.1:
            confidence += 0.2
        
        # Trend direction (20% weight)
        if trends.get("trend_direction") == "increasing":
            confidence += 0.2
        
        # Historical patterns (20% weight)
        if historical_data.get("success") and historical_data.get("common_sequences"):
            common_seqs = historical_data.get("common_sequences", [])
            if common_seqs and common_seqs[0].get("frequency", 0) >= 3:
                confidence += 0.2
        
        # Capacity warnings (20% weight)
        if capacity_analysis.get("capacity_warning"):
            confidence += 0.2
        
        return min(1.0, confidence)
    
    def _determine_risk_level(
        self,
        confidence: float,
        trends: Dict[str, Any],
        capacity_analysis: Dict[str, Any]
    ) -> str:
        """Determine risk level"""
        # Adjust based on multiple factors
        trend_strength = trends.get("trend_strength", 0)
        capacity_warning = capacity_analysis.get("capacity_warning", False)
        
        if confidence >= 0.7 and (trend_strength > 0.5 or capacity_warning):
            return "high"
        elif confidence >= 0.5:
            return "medium"
        elif confidence >= 0.3:
            return "low"
        else:
            return "low"
    
    def _predict_incident_type(
        self,
        trends: Dict[str, Any],
        capacity_analysis: Dict[str, Any]
    ) -> str:
        """Predict incident type"""
        if capacity_analysis.get("capacity_warning"):
            return "capacity_exhaustion"
        elif trends.get("trend_direction") == "increasing" and trends.get("trend_strength", 0) > 0.3:
            return "error_trend_escalation"
        elif trends.get("error_avg", 0) > 10:
            return "sustained_high_error_rate"
        else:
            return "potential_incident"

