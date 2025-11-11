"""
Execution session model for tracking manual and orchestrated runbook execution.
"""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ExecutionSession(Base):
    __tablename__ = "execution_sessions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    runbook_id = Column(
        Integer, ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticket_id = Column(
        Integer, ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True, index=True
    )  # Link to ticket
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    issue_description = Column(Text, nullable=True)
    status = Column(
        String(20), default="pending"
    )  # pending, waiting_approval, in_progress, completed, failed, abandoned, escalated
    current_step = Column(Integer, default=0)  # Current step number
    waiting_for_approval = Column(Boolean, default=False)  # Whether waiting for human approval
    approval_step_number = Column(Integer, nullable=True)  # Step number waiting for approval
    transport_channel = Column(String(32), default="redis")
    last_event_seq = Column(String(64), nullable=True)
    assignment_retry_count = Column(Integer, default=0)
    sandbox_profile = Column(String(64), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total_duration_minutes = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tenant = relationship("Tenant")
    runbook = relationship("Runbook")
    user = relationship("User")
    ticket = relationship("Ticket", back_populates="execution_sessions")
    steps = relationship(
        "ExecutionStep", back_populates="session", cascade="all, delete-orphan"
    )
    feedback = relationship(
        "ExecutionFeedback", back_populates="session", uselist=False, cascade="all, delete-orphan"
    )
    events = relationship(
        "ExecutionEvent", back_populates="session", cascade="all, delete-orphan"
    )
    assignments = relationship(
        "AgentWorkerAssignment", back_populates="session", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_execution_sessions_runbook", "runbook_id"),
        Index("idx_execution_sessions_status", "status"),
        Index("idx_execution_sessions_tenant", "tenant_id"),
        Index("idx_execution_sessions_ticket", "ticket_id"),
        Index("idx_execution_sessions_waiting", "waiting_for_approval"),
    )

    def __repr__(self):
        return f"<ExecutionSession(id={self.id}, runbook_id={self.runbook_id}, status='{self.status}')>"


class ExecutionStep(Base):
    __tablename__ = "execution_steps"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer, ForeignKey("execution_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_number = Column(Integer, nullable=False)
    step_type = Column(String(20), nullable=True)  # precheck, main, postcheck
    command = Column(Text, nullable=True)
    rollback_command = Column(Text, nullable=True)  # Rollback command for this step
    requires_approval = Column(Boolean, default=False)  # Whether this step requires approval
    approved = Column(Boolean, nullable=True)  # Approval status (null = not yet reviewed)
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    sandbox_profile = Column(String(64), nullable=True)
    blast_radius = Column(String(32), nullable=True)
    approval_policy = Column(String(64), nullable=True)
    command_payload = Column(JSON, nullable=True)
    rollback_payload = Column(JSON, nullable=True)
    credentials_used = Column(JSON, nullable=True)
    completed = Column(Boolean, default=False)
    success = Column(Boolean, nullable=True)
    output = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("ExecutionSession", back_populates="steps")
    approver = relationship("User", foreign_keys=[approved_by])

    # Indexes
    __table_args__ = (
        Index("idx_execution_steps_session", "session_id"),
        Index("idx_execution_steps_approval", "requires_approval"),
    )

    def __repr__(self):
        return (
            f"<ExecutionStep(id={self.id}, session_id={self.session_id}, step_number={self.step_number})>"
        )


class ExecutionFeedback(Base):
    __tablename__ = "execution_feedback"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer, ForeignKey("execution_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
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
        Index("idx_execution_feedback_session", "session_id"),
    )

    def __repr__(self):
        return (
            f"<ExecutionFeedback(id={self.id}, session_id={self.session_id}, was_successful='{self.was_successful}')>"
        )


class ExecutionEvent(Base):
    __tablename__ = "execution_events"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer, ForeignKey("execution_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_number = Column(Integer, nullable=True)
    event_type = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    stream_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ExecutionSession", back_populates="events")

    __table_args__ = (
        Index("idx_execution_events_session", "session_id"),
        Index("idx_execution_events_type", "event_type"),
    )


class AgentWorkerAssignment(Base):
    __tablename__ = "agent_worker_assignments"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer, ForeignKey("execution_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    worker_id = Column(String(128), nullable=True)
    status = Column(String(32), default="pending")  # pending, acknowledged, failed, completed
    attempt = Column(Integer, default=0)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ExecutionSession", back_populates="assignments")

    __table_args__ = (
        Index("idx_worker_assignments_worker", "worker_id"),
        Index("idx_worker_assignments_status", "status"),
    )

