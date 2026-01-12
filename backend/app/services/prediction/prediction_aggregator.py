"""
Prediction Aggregator - Combine predictions from multiple models
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.models.prediction import Prediction
from app.models.log_pattern import LogPattern

logger = get_logger(__name__)


class PredictionAggregator:
    """Service for aggregating predictions from multiple models"""
    
    def __init__(self):
        # Weights for different prediction types
        self.weights = {
            "short_term": 0.5,  # Higher weight for short-term (more immediate)
            "medium_term": 0.3,
            "long_term": 0.2
        }
    
    async def aggregate_predictions(
        self,
        predictions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate multiple predictions into a single risk assessment
        
        Args:
            predictions: List of prediction dictionaries
            
        Returns:
            Aggregated prediction result
        """
        try:
            if not predictions:
                return {
                    "success": False,
                    "error": "No predictions to aggregate"
                }
            
            # Calculate weighted confidence
            total_confidence = 0.0
            total_weight = 0.0
            risk_levels = []
            
            for pred in predictions:
                pred_type = pred.get("prediction_type", "medium_term")
                weight = self.weights.get(pred_type, 0.3)
                confidence = pred.get("confidence_score", 0.0)
                
                total_confidence += confidence * weight
                total_weight += weight
                risk_levels.append(pred.get("risk_level", "low"))
            
            # Normalize confidence
            if total_weight > 0:
                aggregated_confidence = total_confidence / total_weight
            else:
                aggregated_confidence = 0.0
            
            # Determine overall risk level
            risk_level = self._determine_risk_level(aggregated_confidence, risk_levels)
            
            # Calculate time horizon (use shortest)
            time_horizons = [p.get("time_horizon_minutes", 60) for p in predictions]
            min_horizon = min(time_horizons) if time_horizons else 60
            
            return {
                "success": True,
                "aggregated_confidence": aggregated_confidence,
                "risk_level": risk_level,
                "time_horizon_minutes": min_horizon,
                "prediction_count": len(predictions),
                "contributing_predictions": predictions
            }
            
        except Exception as e:
            logger.error(f"Error aggregating predictions: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _determine_risk_level(
        self,
        confidence: float,
        risk_levels: List[str]
    ) -> str:
        """Determine overall risk level from confidence and individual risk levels"""
        # Risk level hierarchy
        risk_hierarchy = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1
        }
        
        # Get highest risk level
        max_risk = max([risk_hierarchy.get(rl, 1) for rl in risk_levels], default=1)
        
        # Adjust based on confidence
        if confidence >= 0.8:
            if max_risk >= 3:
                return "critical"
            elif max_risk >= 2:
                return "high"
            else:
                return "medium"
        elif confidence >= 0.6:
            if max_risk >= 3:
                return "high"
            elif max_risk >= 2:
                return "medium"
            else:
                return "low"
        else:
            if max_risk >= 3:
                return "medium"
            else:
                return "low"
    
    async def create_prediction(
        self,
        tenant_id: int,
        prediction_type: str,
        confidence_score: float,
        risk_level: str,
        time_horizon_minutes: int,
        predicted_incident_type: Optional[str] = None,
        pattern_ids: Optional[List[int]] = None,
        db: Session = None
    ) -> Optional[Prediction]:
        """Create a prediction record"""
        try:
            prediction = Prediction(
                tenant_id=tenant_id,
                prediction_type=prediction_type,
                predicted_incident_type=predicted_incident_type,
                confidence_score=confidence_score,
                risk_level=risk_level,
                time_horizon_minutes=time_horizon_minutes,
                predicted_at=datetime.now(timezone.utc)
            )
            
            db.add(prediction)
            db.commit()
            db.refresh(prediction)
            
            # Link to patterns if provided
            if pattern_ids:
                from app.models.prediction import PredictionPattern
                for pattern_id in pattern_ids:
                    pattern_link = PredictionPattern(
                        prediction_id=prediction.id,
                        pattern_id=pattern_id,
                        weight=1.0 / len(pattern_ids)  # Equal weight
                    )
                    db.add(pattern_link)
                db.commit()
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error creating prediction: {e}")
            db.rollback()
            return None

