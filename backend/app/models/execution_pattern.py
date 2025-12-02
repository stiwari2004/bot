"""
ExecutionPattern model for tracking reusable execution, resolution, and rollback patterns.
"""
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Numeric,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class ExecutionPattern(Base):
    """
    Stores successful execution / resolution / rollback patterns that can be
    reused for future recommendations.

    This is intentionally generic and JSON-based so we can evolve the schema
    without migrations for every new signal.
    """

    __tablename__ = "execution_patterns"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # execution | resolution | rollback
    pattern_type = Column(String(50), nullable=False)

    runbook_id = Column(
        Integer, ForeignKey("runbooks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ticket_id = Column(
        Integer, ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id = Column(
        Integer,
        ForeignKey("execution_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Normalized / canonical representation of the issue text used for search
    issue_signature = Column(Text, nullable=True)

    # High-level context (environment, service, severity, region, tags, etc.)
    context = Column(JSONB, nullable=True)

    # Detailed pattern payload: steps, commands, outputs, decision points, etc.
    pattern_data = Column(JSONB, nullable=False, default=dict)

    # Aggregate effectiveness metrics
    success_rate = Column(Numeric(5, 2), nullable=False, default=0.0)
    usage_count = Column(Integer, nullable=False, default=0)

    # Quality control fields (Module 6)
    is_deprecated = Column(String(10), nullable=False, default='false')  # 'true', 'false', 'pending'
    quality_score = Column(Numeric(5, 2), nullable=True)  # Calculated quality score (0-100)
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)

    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships (kept loose to avoid heavy joins by default)
    runbook = relationship("Runbook", backref="execution_patterns")
    ticket = relationship("Ticket", backref="execution_patterns")
    session = relationship("ExecutionSession", backref="execution_patterns")

    __table_args__ = (
        Index("idx_execution_patterns_type", "pattern_type"),
        # Full-text search index using to_tsvector (standard PostgreSQL full-text search)
        # This will be created via raw SQL in database initialization
        Index("idx_execution_patterns_context", "context", postgresql_using="gin"),
        Index("idx_execution_patterns_success", "success_rate"),
        Index("idx_execution_patterns_deprecated", "is_deprecated"),
        Index("idx_execution_patterns_quality", "quality_score"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExecutionPattern(id={self.id}, "
            f"type='{self.pattern_type}', "
            f"runbook_id={self.runbook_id}, "
            f"success_rate={self.success_rate}, "
            f"usage_count={self.usage_count})>"
        )


