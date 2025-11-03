"""
Execution session model for tracking manual runbook execution
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ExecutionSession(Base):
    __tablename__ = "execution_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    runbook_id = Column(Integer, ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    issue_description = Column(Text, nullable=True)
    status = Column(String(20), default="in_progress")  # in_progress, completed, failed, abandoned
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total_duration_minutes = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tenant = relationship("Tenant")
    runbook = relationship("Runbook")
    user = relationship("User")
    steps = relationship("ExecutionStep", back_populates="session", cascade="all, delete-orphan")
    feedback = relationship("ExecutionFeedback", back_populates="session", uselist=False, cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_execution_sessions_runbook', 'runbook_id'),
        Index('idx_execution_sessions_status', 'status'),
        Index('idx_execution_sessions_tenant', 'tenant_id'),
    )
    
    def __repr__(self):
        return f"<ExecutionSession(id={self.id}, runbook_id={self.runbook_id}, status='{self.status}')>"


class ExecutionStep(Base):
    __tablename__ = "execution_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("execution_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    step_type = Column(String(20), nullable=True)  # precheck, main, postcheck
    command = Column(Text, nullable=True)
    completed = Column(Boolean, default=False)
    success = Column(Boolean, nullable=True)
    output = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("ExecutionSession", back_populates="steps")
    
    # Indexes
    __table_args__ = (
        Index('idx_execution_steps_session', 'session_id'),
    )
    
    def __repr__(self):
        return f"<ExecutionStep(id={self.id}, session_id={self.session_id}, step_number={self.step_number})>"


class ExecutionFeedback(Base):
    __tablename__ = "execution_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("execution_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    was_successful = Column(Boolean, nullable=False)
    issue_resolved = Column(Boolean, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5
    feedback_text = Column(Text, nullable=True)
    suggestions = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("ExecutionSession", back_populates="feedback")
    
    # Indexes
    __table_args__ = (
        Index('idx_execution_feedback_session', 'session_id'),
    )
    
    def __repr__(self):
        return f"<ExecutionFeedback(id={self.id}, session_id={self.session_id}, was_successful='{self.was_successful}')>"


