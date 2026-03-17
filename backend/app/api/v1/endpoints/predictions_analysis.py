"""
Predictions — analysis, history, patterns, and model endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, ConfigDict, Field

from app.core.database import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.models.prediction import Prediction
from app.models.log_pattern import LogPattern
from app.core.logging import get_logger

try:
    from app.services.prediction.prediction_aggregator import PredictionAggregator
except ImportError:
    PredictionAggregator = None

logger = get_logger(__name__)
router = APIRouter()


class PredictionResponse(BaseModel):
    success: bool
    predictions: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class TrainModelRequest(BaseModel):
    """model_config avoids Pydantic protected namespace warning for model_type."""
    model_config = ConfigDict(protected_namespaces=())
    model_type: str
    days_back: int = Field(default=30, ge=7, le=90)


@router.post("/analyze", response_model=PredictionResponse)
async def analyze_logs(
    time_window_minutes: int = Query(default=60, ge=1, le=1440),
    include_short_term: bool = Query(default=True),
    include_medium_term: bool = Query(default=True),
    include_long_term: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Analyze logs and generate predictions using all prediction models"""
    try:
        from app.services.prediction.short_term_predictor import ShortTermPredictor
        from app.services.prediction.medium_term_predictor import MediumTermPredictor
        from app.services.prediction.long_term_predictor import LongTermPredictor

        predictions = []
        aggregator = PredictionAggregator()

        async def _run_predictor(predictor, predict_kwargs, pred_type):
            try:
                result = await predictor.predict(**predict_kwargs)
                if result.get("success") and result.get("confidence_score", 0) > 0.3:
                    pred = await aggregator.create_prediction(
                        tenant_id=current_user.tenant_id,
                        prediction_type=pred_type,
                        confidence_score=result["confidence_score"],
                        risk_level=result["risk_level"],
                        time_horizon_minutes=result["time_horizon_minutes"],
                        predicted_incident_type=result.get("predicted_incident_type"),
                        db=db
                    )
                    if pred:
                        predictions.append({
                            "id": pred.id,
                            "prediction_type": pred.prediction_type,
                            "confidence_score": pred.confidence_score,
                            "risk_level": pred.risk_level,
                            "time_horizon_minutes": pred.time_horizon_minutes,
                            "predicted_incident_type": pred.predicted_incident_type,
                            "predicted_at": pred.predicted_at.isoformat() if pred.predicted_at else None
                        })
            except Exception as e:
                logger.warning(f"{pred_type} prediction failed: {e}")

        if include_short_term:
            await _run_predictor(
                ShortTermPredictor(),
                {"tenant_id": current_user.tenant_id, "db": db, "time_horizon_minutes": 30},
                "short_term"
            )
        if include_medium_term:
            await _run_predictor(
                MediumTermPredictor(),
                {"tenant_id": current_user.tenant_id, "db": db, "time_horizon_hours": 6},
                "medium_term"
            )
        if include_long_term:
            await _run_predictor(
                LongTermPredictor(),
                {"tenant_id": current_user.tenant_id, "db": db, "time_horizon_days": 3},
                "long_term"
            )

        aggregated_result = None
        if len(predictions) > 1:
            prediction_dicts = [
                {k: p[k] for k in ("prediction_type", "confidence_score", "risk_level", "time_horizon_minutes")}
                for p in predictions
            ]
            aggregated_result = await aggregator.aggregate_predictions(prediction_dicts)

        return PredictionResponse(
            success=True,
            predictions=predictions + ([{"aggregated": aggregated_result}] if aggregated_result else [])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current", response_model=PredictionResponse)
async def get_current_predictions(
    risk_level: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current active predictions"""
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        query = db.query(Prediction).filter(
            Prediction.tenant_id == current_user.tenant_id,
            Prediction.predicted_at >= cutoff_time,
            Prediction.occurred == False
        )
        if risk_level:
            query = query.filter(Prediction.risk_level == risk_level)
        predictions = query.order_by(Prediction.predicted_at.desc()).limit(50).all()
        return PredictionResponse(success=True, predictions=[
            {
                "id": p.id, "prediction_type": p.prediction_type,
                "predicted_incident_type": p.predicted_incident_type,
                "confidence_score": p.confidence_score, "risk_level": p.risk_level,
                "time_horizon_minutes": p.time_horizon_minutes,
                "predicted_at": p.predicted_at.isoformat() if p.predicted_at else None
            }
            for p in predictions
        ])
    except Exception as e:
        logger.error(f"Error getting current predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=PredictionResponse)
async def get_prediction_history(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get prediction history"""
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        predictions = db.query(Prediction).filter(
            Prediction.tenant_id == current_user.tenant_id,
            Prediction.predicted_at >= cutoff_time
        ).order_by(Prediction.predicted_at.desc()).limit(100).all()
        return PredictionResponse(success=True, predictions=[
            {
                "id": p.id, "prediction_type": p.prediction_type,
                "predicted_incident_type": p.predicted_incident_type,
                "confidence_score": p.confidence_score, "risk_level": p.risk_level,
                "time_horizon_minutes": p.time_horizon_minutes,
                "predicted_at": p.predicted_at.isoformat() if p.predicted_at else None,
                "occurred": p.occurred,
                "occurred_at": p.occurred_at.isoformat() if p.occurred_at else None,
                "false_positive": p.false_positive
            }
            for p in predictions
        ])
    except Exception as e:
        logger.error(f"Error getting prediction history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns", response_model=Dict[str, Any])
async def get_patterns(
    pattern_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detected log patterns"""
    try:
        query = db.query(LogPattern).filter(LogPattern.tenant_id == current_user.tenant_id)
        if pattern_type:
            query = query.filter(LogPattern.pattern_type == pattern_type)
        patterns = query.order_by(LogPattern.frequency.desc()).limit(50).all()
        return {"success": True, "patterns": [
            {
                "id": p.id, "pattern_signature": p.pattern_signature,
                "pattern_type": p.pattern_type, "frequency": p.frequency,
                "first_seen": p.first_seen.isoformat() if p.first_seen else None,
                "last_seen": p.last_seen.isoformat() if p.last_seen else None,
                "associated_incidents": p.associated_incidents,
                "confidence_score": p.confidence_score
            }
            for p in patterns
        ]}
    except Exception as e:
        logger.error(f"Error getting patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train-model")
async def train_model(
    body: TrainModelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Train a prediction model"""
    try:
        from app.services.prediction.model_training_service import ModelTrainingService
        if body.model_type not in ("short_term", "medium_term", "long_term"):
            raise HTTPException(status_code=400, detail="model_type must be one of: short_term, medium_term, long_term")
        result = await ModelTrainingService().train_model(
            tenant_id=current_user.tenant_id, model_type=body.model_type,
            days_back=body.days_back, db=db
        )
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Training failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error training model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models(
    model_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List prediction models"""
    try:
        from app.models.prediction import PredictionModel
        query = db.query(PredictionModel).filter(PredictionModel.tenant_id == current_user.tenant_id)
        if model_type:
            query = query.filter(PredictionModel.model_type == model_type)
        models = query.order_by(PredictionModel.trained_at.desc()).limit(20).all()
        return {"success": True, "models": [
            {
                "id": m.id, "model_type": m.model_type, "model_version": m.model_version,
                "precision": m.precision, "recall": m.recall, "f1_score": m.f1_score,
                "training_data_count": m.training_data_count,
                "trained_at": m.trained_at.isoformat() if m.trained_at else None,
                "is_active": m.is_active
            }
            for m in models
        ]}
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/map-patterns")
async def map_patterns_to_incidents(
    days_back: int = Body(default=30, ge=7, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Map log patterns to historical incidents"""
    try:
        from app.services.prediction.historical_analyzer import HistoricalAnalyzer
        return await HistoricalAnalyzer().map_patterns_to_incidents(
            tenant_id=current_user.tenant_id, days_back=days_back, db=db
        )
    except Exception as e:
        logger.error(f"Error mapping patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))
