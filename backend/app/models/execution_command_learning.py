"""
Execution Command Learning model.
Stores learned (command, error, fix) from failures for refinement without hardcoded rules.
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


class ExecutionCommandLearning(Base):
    __tablename__ = "execution_command_learnings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    session_id = Column(
        Integer,
        ForeignKey("execution_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    runbook_id = Column(
        Integer,
        ForeignKey("runbooks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    step_number = Column(Integer, nullable=True)
    step_type = Column(String(20), nullable=True)

    command = Column(Text, nullable=False)
    error_text = Column(Text, nullable=True)
    output_text = Column(Text, nullable=True)
    connector_type = Column(String(32), nullable=True)
    os_type = Column(String(32), nullable=True)

    fix_applied = Column(Text, nullable=True)
    fix_source = Column(String(32), nullable=True)
    success_after_fix = Column(Boolean, nullable=True)

    connection_config = Column(JSON, nullable=True)
    issue_description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tenant = relationship("Tenant")
    session = relationship("ExecutionSession")
    runbook = relationship("Runbook")

    __table_args__ = (
        Index("idx_execution_command_learnings_tenant", "tenant_id"),
        Index("idx_execution_command_learnings_connector", "connector_type"),
        Index("idx_execution_command_learnings_os", "os_type"),
        Index("idx_execution_command_learnings_success", "success_after_fix"),
        Index("idx_execution_command_learnings_created", "created_at"),
    )

    def __repr__(self):
        return (
            f"<ExecutionCommandLearning(id={self.id}, "
            f"connector={self.connector_type}, os={self.os_type})>"
        )
