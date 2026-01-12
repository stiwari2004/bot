"""
Model Training Service - Train and retrain prediction models
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.core.logging import get_logger
from app.models.prediction import Prediction, PredictionModel
from app.models.log_entry import LogEntry
from app.models.ticket import Ticket
from app.services.prediction.feature_engineering import FeatureEngineeringService

logger = get_logger(__name__)


class ModelTrainingService:
    """Service for training and retraining prediction models"""
    
    def __init__(self):
        self.feature_service = FeatureEngineeringService()
    
    async def train_model(
        self,
        tenant_id: int,
        model_type: str,  # short_term, medium_term, long_term
        days_back: int = 30,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Train a prediction model from historical data
        
        Args:
            tenant_id: Tenant ID
            model_type: Type of model to train
            days_back: Number of days of historical data to use
            db: Database session
            
        Returns:
            Dict with training results
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            # Get historical incidents
            incidents = db.query(Ticket).filter(
                and_(
                    Ticket.tenant_id == tenant_id,
                    Ticket.created_at >= cutoff_date,
                    Ticket.status.in_(['resolved', 'closed'])
                )
            ).all()
            
            if len(incidents) < 5:
                return {
                    "success": False,
                    "error": f"Insufficient training data. Need at least 5 incidents, found {len(incidents)}"
                }
            
            # Prepare training data
            training_data = []
            labels = []
            
            for incident in incidents:
                # Get features before incident
                incident_time = incident.created_at
                pre_window_start = incident_time - timedelta(hours=1 if model_type == "short_term" else (6 if model_type == "medium_term" else 24))
                
                # Get logs before incident
                logs = db.query(LogEntry).filter(
                    and_(
                        LogEntry.tenant_id == tenant_id,
                        LogEntry.timestamp >= pre_window_start,
                        LogEntry.timestamp < incident_time
                    )
                ).all()
                
                if not logs:
                    continue
                
                # Extract features
                features = await self._extract_features_for_training(
                    logs=logs,
                    incident_time=incident_time,
                    model_type=model_type,
                    db=db
                )
                
                if features:
                    training_data.append(features)
                    labels.append(1)  # Positive example (incident occurred)
            
            # Add negative examples (no incident)
            negative_examples = await self._get_negative_examples(
                tenant_id=tenant_id,
                cutoff_date=cutoff_date,
                model_type=model_type,
                db=db
            )
            
            training_data.extend(negative_examples)
            labels.extend([0] * len(negative_examples))
            
            if len(training_data) < 10:
                return {
                    "success": False,
                    "error": f"Insufficient training data after feature extraction. Need at least 10 examples, found {len(training_data)}"
                }
            
            # Train simple model (for now, use statistical approach)
            # In production, this would train an LSTM/GRU for short_term, or other models
            model_metrics = self._train_statistical_model(training_data, labels)
            
            # Save model metadata
            model = PredictionModel(
                tenant_id=tenant_id,
                model_type=model_type,
                model_version=f"v{datetime.now().strftime('%Y%m%d%H%M%S')}",
                training_data_count=len(training_data),
                precision=model_metrics.get("precision", 0.0),
                recall=model_metrics.get("recall", 0.0),
                f1_score=model_metrics.get("f1_score", 0.0),
                trained_at=datetime.now(timezone.utc),
                is_active=True,
                metadata={
                    "positive_examples": len([l for l in labels if l == 1]),
                    "negative_examples": len([l for l in labels if l == 0]),
                    "training_date_range": {
                        "start": cutoff_date.isoformat(),
                        "end": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            db.add(model)
            db.commit()
            db.refresh(model)
            
            return {
                "success": True,
                "model_id": model.id,
                "model_version": model.model_version,
                "metrics": model_metrics,
                "training_samples": len(training_data)
            }
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _extract_features_for_training(
        self,
        logs: List[LogEntry],
        incident_time: datetime,
        model_type: str,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """Extract features for training"""
        try:
            if not logs:
                return None
            
            # Basic features
            error_count = len([l for l in logs if l.level in ['ERROR', 'CRITICAL']])
            warning_count = len([l for l in logs if l.level == 'WARN'])
            total_logs = len(logs)
            
            # Time-based features
            time_span = (incident_time - logs[0].timestamp).total_seconds() / 60  # minutes
            
            # Pattern features
            unique_services = len(set([l.service for l in logs if l.service]))
            
            return {
                "error_count": error_count,
                "warning_count": warning_count,
                "total_logs": total_logs,
                "error_rate": error_count / max(total_logs, 1),
                "warning_rate": warning_count / max(total_logs, 1),
                "time_span_minutes": time_span,
                "unique_services": unique_services,
                "logs_per_minute": total_logs / max(time_span, 1)
            }
            
        except Exception as e:
            logger.error(f"Error extracting training features: {e}")
            return None
    
    async def _get_negative_examples(
        self,
        tenant_id: int,
        cutoff_date: datetime,
        model_type: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Get negative examples (periods without incidents)"""
        try:
            # Get all incidents to find gaps
            incidents = db.query(Ticket).filter(
                and_(
                    Ticket.tenant_id == tenant_id,
                    Ticket.created_at >= cutoff_date
                )
            ).order_by(Ticket.created_at).all()
            
            negative_examples = []
            
            # Sample random time windows that don't overlap with incidents
            window_size = 60 if model_type == "short_term" else (360 if model_type == "medium_term" else 1440)
            
            for i in range(min(20, len(incidents) * 2)):  # Generate up to 20 negative examples
                # Pick a random time
                random_time = cutoff_date + timedelta(
                    days=np.random.uniform(0, (datetime.now(timezone.utc) - cutoff_date).days)
                )
                
                # Check if this time overlaps with any incident
                overlaps = False
                for incident in incidents:
                    incident_window_start = incident.created_at - timedelta(minutes=window_size)
                    incident_window_end = incident.created_at + timedelta(minutes=window_size)
                    if incident_window_start <= random_time <= incident_window_end:
                        overlaps = True
                        break
                
                if not overlaps:
                    # Get logs for this time window
                    window_start = random_time - timedelta(minutes=window_size)
                    logs = db.query(LogEntry).filter(
                        and_(
                            LogEntry.tenant_id == tenant_id,
                            LogEntry.timestamp >= window_start,
                            LogEntry.timestamp < random_time
                        )
                    ).all()
                    
                    if logs:
                        features = await self._extract_features_for_training(
                            logs=logs,
                            incident_time=random_time,
                            model_type=model_type,
                            db=db
                        )
                        if features:
                            negative_examples.append(features)
            
            return negative_examples
            
        except Exception as e:
            logger.error(f"Error getting negative examples: {e}")
            return []
    
    def _train_statistical_model(
        self,
        training_data: List[Dict[str, Any]],
        labels: List[int]
    ) -> Dict[str, Any]:
        """Train a simple statistical model"""
        try:
            # Convert to DataFrame
            df = pd.DataFrame(training_data)
            df['label'] = labels
            
            # Calculate thresholds based on training data
            positive_data = df[df['label'] == 1]
            negative_data = df[df['label'] == 0]
            
            if len(positive_data) == 0 or len(negative_data) == 0:
                return {
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1_score": 0.0
                }
            
            # Simple threshold-based classifier
            error_rate_threshold = positive_data['error_rate'].quantile(0.5)
            error_count_threshold = positive_data['error_count'].quantile(0.5)
            
            # Test on training data (simple validation)
            predictions = []
            for _, row in df.iterrows():
                pred = 1 if (
                    row['error_rate'] >= error_rate_threshold or
                    row['error_count'] >= error_count_threshold
                ) else 0
                predictions.append(pred)
            
            # Calculate metrics
            tp = sum([1 for p, l in zip(predictions, labels) if p == 1 and l == 1])
            fp = sum([1 for p, l in zip(predictions, labels) if p == 1 and l == 0])
            fn = sum([1 for p, l in zip(predictions, labels) if p == 0 and l == 1])
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            
            return {
                "precision": float(precision),
                "recall": float(recall),
                "f1_score": float(f1_score),
                "thresholds": {
                    "error_rate": float(error_rate_threshold),
                    "error_count": float(error_count_threshold)
                }
            }
            
        except Exception as e:
            logger.error(f"Error training statistical model: {e}")
            return {
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0
            }
    
    async def retrain_model(
        self,
        model_id: int,
        tenant_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """Retrain an existing model with new data"""
        try:
            model = db.query(PredictionModel).filter(
                and_(
                    PredictionModel.id == model_id,
                    PredictionModel.tenant_id == tenant_id
                )
            ).first()
            
            if not model:
                return {
                    "success": False,
                    "error": "Model not found"
                }
            
            # Deactivate old model
            model.is_active = False
            db.commit()
            
            # Train new model
            result = await self.train_model(
                tenant_id=tenant_id,
                model_type=model.model_type,
                days_back=30,
                db=db
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error retraining model: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_model_performance(
        self,
        model_id: int,
        tenant_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """Get model performance metrics"""
        try:
            model = db.query(PredictionModel).filter(
                and_(
                    PredictionModel.id == model_id,
                    PredictionModel.tenant_id == tenant_id
                )
            ).first()
            
            if not model:
                return {
                    "success": False,
                    "error": "Model not found"
                }
            
            # Get predictions from this model
            predictions = db.query(Prediction).filter(
                and_(
                    Prediction.tenant_id == tenant_id,
                    Prediction.prediction_type == model.model_type
                )
            ).all()
            
            # Calculate accuracy
            total = len(predictions)
            occurred = len([p for p in predictions if p.occurred])
            false_positives = len([p for p in predictions if p.false_positive])
            
            accuracy = (occurred / total * 100.0) if total > 0 else 0.0
            false_positive_rate = (false_positives / total * 100.0) if total > 0 else 0.0
            
            return {
                "success": True,
                "model_id": model.id,
                "model_version": model.model_version,
                "model_type": model.model_type,
                "precision": model.precision,
                "recall": model.recall,
                "f1_score": model.f1_score,
                "trained_at": model.trained_at.isoformat() if model.trained_at else None,
                "is_active": model.is_active,
                "predictions_count": total,
                "occurred_count": occurred,
                "false_positive_count": false_positives,
                "accuracy": accuracy,
                "false_positive_rate": false_positive_rate
            }
            
        except Exception as e:
            logger.error(f"Error getting model performance: {e}")
            return {
                "success": False,
                "error": str(e)
            }

