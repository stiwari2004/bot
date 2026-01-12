"""
Predictions API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.models.prediction import Prediction
from app.models.log_entry import LogEntry
from app.models.log_pattern import LogPattern
from app.services.prediction.log_ingestion_service import LogIngestionService
from app.services.prediction.log_pattern_extractor import LogPatternExtractor
from app.services.prediction.prediction_aggregator import PredictionAggregator
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Pydantic models
class LogIngestionRequest(BaseModel):
    logs: List[Dict[str, Any]]
    source: str

class WindowsEventLogRequest(BaseModel):
    log_name: str = "Application"
    max_events: int = 1000
    host: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

class LinuxSyslogRequest(BaseModel):
    log_type: str = "syslog"
    lines: int = 1000
    host: Optional[str] = None
    username: Optional[str] = None
    ssh_key_path: Optional[str] = None

class JournaldRequest(BaseModel):
    unit: Optional[str] = None
    lines: int = 1000
    host: Optional[str] = None
    username: Optional[str] = None
    ssh_key_path: Optional[str] = None

class PredictionResponse(BaseModel):
    success: bool
    predictions: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

@router.post("/ingest", response_model=Dict[str, Any])
async def ingest_logs(
    request: LogIngestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ingest logs from API"""
    try:
        ingestion_service = LogIngestionService()
        result = await ingestion_service.ingest_from_api(
            logs=request.logs,
            source=request.source,
            tenant_id=current_user.tenant_id,
            db=db
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error ingesting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        
        # Short-term prediction (5-30 minutes)
        if include_short_term:
            try:
                short_term_predictor = ShortTermPredictor()
                short_result = await short_term_predictor.predict(
                    tenant_id=current_user.tenant_id,
                    db=db,
                    time_horizon_minutes=30
                )
                
                if short_result.get("success") and short_result.get("confidence_score", 0) > 0.3:
                    prediction = await aggregator.create_prediction(
                        tenant_id=current_user.tenant_id,
                        prediction_type="short_term",
                        confidence_score=short_result["confidence_score"],
                        risk_level=short_result["risk_level"],
                        time_horizon_minutes=short_result["time_horizon_minutes"],
                        predicted_incident_type=short_result.get("predicted_incident_type"),
                        db=db
                    )
                    
                    if prediction:
                        predictions.append({
                            "id": prediction.id,
                            "prediction_type": prediction.prediction_type,
                            "confidence_score": prediction.confidence_score,
                            "risk_level": prediction.risk_level,
                            "time_horizon_minutes": prediction.time_horizon_minutes,
                            "predicted_incident_type": prediction.predicted_incident_type,
                            "predicted_at": prediction.predicted_at.isoformat() if prediction.predicted_at else None
                        })
            except Exception as e:
                logger.warning(f"Short-term prediction failed: {e}")
        
        # Medium-term prediction (1-24 hours)
        if include_medium_term:
            try:
                medium_term_predictor = MediumTermPredictor()
                medium_result = await medium_term_predictor.predict(
                    tenant_id=current_user.tenant_id,
                    db=db,
                    time_horizon_hours=6
                )
                
                if medium_result.get("success") and medium_result.get("confidence_score", 0) > 0.3:
                    prediction = await aggregator.create_prediction(
                        tenant_id=current_user.tenant_id,
                        prediction_type="medium_term",
                        confidence_score=medium_result["confidence_score"],
                        risk_level=medium_result["risk_level"],
                        time_horizon_minutes=medium_result["time_horizon_minutes"],
                        predicted_incident_type=medium_result.get("predicted_incident_type"),
                        db=db
                    )
                    
                    if prediction:
                        predictions.append({
                            "id": prediction.id,
                            "prediction_type": prediction.prediction_type,
                            "confidence_score": prediction.confidence_score,
                            "risk_level": prediction.risk_level,
                            "time_horizon_minutes": prediction.time_horizon_minutes,
                            "predicted_incident_type": prediction.predicted_incident_type,
                            "predicted_at": prediction.predicted_at.isoformat() if prediction.predicted_at else None
                        })
            except Exception as e:
                logger.warning(f"Medium-term prediction failed: {e}")
        
        # Long-term prediction (1-7 days)
        if include_long_term:
            try:
                long_term_predictor = LongTermPredictor()
                long_result = await long_term_predictor.predict(
                    tenant_id=current_user.tenant_id,
                    db=db,
                    time_horizon_days=3
                )
                
                if long_result.get("success") and long_result.get("confidence_score", 0) > 0.3:
                    prediction = await aggregator.create_prediction(
                        tenant_id=current_user.tenant_id,
                        prediction_type="long_term",
                        confidence_score=long_result["confidence_score"],
                        risk_level=long_result["risk_level"],
                        time_horizon_minutes=long_result["time_horizon_minutes"],
                        predicted_incident_type=long_result.get("predicted_incident_type"),
                        db=db
                    )
                    
                    if prediction:
                        predictions.append({
                            "id": prediction.id,
                            "prediction_type": prediction.prediction_type,
                            "confidence_score": prediction.confidence_score,
                            "risk_level": prediction.risk_level,
                            "time_horizon_minutes": prediction.time_horizon_minutes,
                            "predicted_incident_type": prediction.predicted_incident_type,
                            "predicted_at": prediction.predicted_at.isoformat() if prediction.predicted_at else None
                        })
            except Exception as e:
                logger.warning(f"Long-term prediction failed: {e}")
        
        # Aggregate predictions if multiple
        aggregated_result = None
        if len(predictions) > 1:
            prediction_dicts = [
                {
                    "prediction_type": p["prediction_type"],
                    "confidence_score": p["confidence_score"],
                    "risk_level": p["risk_level"],
                    "time_horizon_minutes": p["time_horizon_minutes"]
                }
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
        # Get predictions from last 24 hours
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        query = db.query(Prediction).filter(
            Prediction.tenant_id == current_user.tenant_id,
            Prediction.predicted_at >= cutoff_time,
            Prediction.occurred == False
        )
        
        if risk_level:
            query = query.filter(Prediction.risk_level == risk_level)
        
        predictions = query.order_by(Prediction.predicted_at.desc()).limit(50).all()
        
        return PredictionResponse(
            success=True,
            predictions=[
                {
                    "id": p.id,
                    "prediction_type": p.prediction_type,
                    "predicted_incident_type": p.predicted_incident_type,
                    "confidence_score": p.confidence_score,
                    "risk_level": p.risk_level,
                    "time_horizon_minutes": p.time_horizon_minutes,
                    "predicted_at": p.predicted_at.isoformat() if p.predicted_at else None
                }
                for p in predictions
            ]
        )
        
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
        
        return PredictionResponse(
            success=True,
            predictions=[
                {
                    "id": p.id,
                    "prediction_type": p.prediction_type,
                    "predicted_incident_type": p.predicted_incident_type,
                    "confidence_score": p.confidence_score,
                    "risk_level": p.risk_level,
                    "time_horizon_minutes": p.time_horizon_minutes,
                    "predicted_at": p.predicted_at.isoformat() if p.predicted_at else None,
                    "occurred": p.occurred,
                    "occurred_at": p.occurred_at.isoformat() if p.occurred_at else None,
                    "false_positive": p.false_positive
                }
                for p in predictions
            ]
        )
        
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
        query = db.query(LogPattern).filter(
            LogPattern.tenant_id == current_user.tenant_id
        )
        
        if pattern_type:
            query = query.filter(LogPattern.pattern_type == pattern_type)
        
        patterns = query.order_by(LogPattern.frequency.desc()).limit(50).all()
        
        return {
            "success": True,
            "patterns": [
                {
                    "id": p.id,
                    "pattern_signature": p.pattern_signature,
                    "pattern_type": p.pattern_type,
                    "frequency": p.frequency,
                    "first_seen": p.first_seen.isoformat() if p.first_seen else None,
                    "last_seen": p.last_seen.isoformat() if p.last_seen else None,
                    "associated_incidents": p.associated_incidents,
                    "confidence_score": p.confidence_score
                }
                for p in patterns
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/train-model")
async def train_model(
    model_type: str = Body(..., description="Model type: short_term, medium_term, or long_term"),
    days_back: int = Body(default=30, ge=7, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Train a prediction model"""
    try:
        from app.services.prediction.model_training_service import ModelTrainingService
        
        if model_type not in ["short_term", "medium_term", "long_term"]:
            raise HTTPException(status_code=400, detail="model_type must be one of: short_term, medium_term, long_term")
        
        training_service = ModelTrainingService()
        result = await training_service.train_model(
            tenant_id=current_user.tenant_id,
            model_type=model_type,
            days_back=days_back,
            db=db
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
        
        query = db.query(PredictionModel).filter(
            PredictionModel.tenant_id == current_user.tenant_id
        )
        
        if model_type:
            query = query.filter(PredictionModel.model_type == model_type)
        
        models = query.order_by(PredictionModel.trained_at.desc()).limit(20).all()
        
        return {
            "success": True,
            "models": [
                {
                    "id": m.id,
                    "model_type": m.model_type,
                    "model_version": m.model_version,
                    "precision": m.precision,
                    "recall": m.recall,
                    "f1_score": m.f1_score,
                    "training_data_count": m.training_data_count,
                    "trained_at": m.trained_at.isoformat() if m.trained_at else None,
                    "is_active": m.is_active
                }
                for m in models
            ]
        }
        
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
        
        analyzer = HistoricalAnalyzer()
        result = await analyzer.map_patterns_to_incidents(
            tenant_id=current_user.tenant_id,
            days_back=days_back,
            db=db
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error mapping patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest/windows-eventlog")
async def ingest_windows_eventlog(
    request: WindowsEventLogRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ingest logs from Windows Event Log"""
    try:
        ingestion_service = LogIngestionService()
        result = await ingestion_service.ingest_from_windows_eventlog(
            log_name=request.log_name,
            max_events=request.max_events,
            host=request.host,
            username=request.username,
            password=request.password,
            tenant_id=current_user.tenant_id,
            db=db
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error ingesting Windows Event Log: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest/linux-syslog")
async def ingest_linux_syslog(
    request: LinuxSyslogRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ingest logs from Linux syslog"""
    try:
        ingestion_service = LogIngestionService()
        result = await ingestion_service.ingest_from_linux_syslog(
            log_type=request.log_type,
            lines=request.lines,
            host=request.host,
            username=request.username,
            ssh_key_path=request.ssh_key_path,
            tenant_id=current_user.tenant_id,
            db=db
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error ingesting Linux syslog: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest/journald")
async def ingest_journald(
    request: JournaldRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ingest logs from systemd journal (journalctl)"""
    try:
        ingestion_service = LogIngestionService()
        result = await ingestion_service.ingest_from_journald(
            unit=request.unit,
            lines=request.lines,
            host=request.host,
            username=request.username,
            ssh_key_path=request.ssh_key_path,
            tenant_id=current_user.tenant_id,
            db=db
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error ingesting journald logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

