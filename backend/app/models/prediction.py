"""
Prediction model for incident prediction
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class Prediction(Base):
    """Incident prediction"""
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_type = Column(String(50), nullable=False, index=True)  # short_term, medium_term, long_term
    predicted_incident_type = Column(String(100), nullable=True)
    confidence_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False, index=True)  # low, medium, high, critical
    time_horizon_minutes = Column(Integer, nullable=False)
    predicted_at = Column(DateTime(timezone=True), nullable=False, index=True)
    occurred = Column(Boolean, default=False)
    occurred_at = Column(DateTime(timezone=True), nullable=True)
    false_positive = Column(Boolean, default=False)
    prediction_metadata = Column("metadata", JSONB, nullable=True)  # Renamed to avoid SQLAlchemy conflict
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tenant = relationship("Tenant", backref="predictions")
    patterns = relationship("PredictionPattern", back_populates="prediction")
    
    def __repr__(self):
        return f"<Prediction(id={self.id}, type='{self.prediction_type}', risk='{self.risk_level}', confidence={self.confidence_score})>"


class PredictionPattern(Base):
    """Link between predictions and log patterns"""
    __tablename__ = "prediction_patterns"
    
    prediction_id = Column(Integer, ForeignKey("predictions.id", ondelete="CASCADE"), primary_key=True)
    pattern_id = Column(Integer, ForeignKey("log_patterns.id", ondelete="CASCADE"), primary_key=True)
    weight = Column(Float, nullable=False)
    
    # Relationships
    prediction = relationship("Prediction", back_populates="patterns")
    pattern = relationship("LogPattern", back_populates="predictions")
    
    def __repr__(self):
        return f"<PredictionPattern(prediction_id={self.prediction_id}, pattern_id={self.pattern_id}, weight={self.weight})>"


class PredictionModel(Base):
    """ML model metadata for predictions"""
    __tablename__ = "prediction_models"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    model_type = Column(String(50), nullable=False, index=True)  # short_term, medium_term, long_term
    model_version = Column(String(50), nullable=False)
    model_path = Column(String(500), nullable=True)
    training_data_count = Column(Integer, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    trained_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    model_metadata = Column("metadata", JSONB, nullable=True)  # Renamed to avoid SQLAlchemy conflict
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tenant = relationship("Tenant", backref="prediction_models")
    
    def __repr__(self):
        return f"<PredictionModel(id={self.id}, type='{self.model_type}', version='{self.model_version}')>"

