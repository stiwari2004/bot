"""
Scheduled Report model for automated report generation
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Text, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class ReportFrequency(str, enum.Enum):
    """Report frequency options"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class ReportFormat(str, enum.Enum):
    """Report format options"""
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"


class ReportType(str, enum.Enum):
    """Report type options"""
    OVERVIEW = "overview"
    TENANTS = "tenants"
    REVENUE = "revenue"
    USAGE = "usage"
    CUSTOM = "custom"


class ScheduledReport(Base):
    __tablename__ = "scheduled_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Report configuration
    report_type = Column(Enum(ReportType), nullable=False, default=ReportType.CUSTOM)
    format = Column(Enum(ReportFormat), nullable=False, default=ReportFormat.PDF)
    
    # Filters and parameters (stored as JSON)
    filters = Column(JSON, nullable=True, default=dict)
    # Example filters: {"date_range": {"start": "...", "end": "..."}, "tenants": [1,2,3], "plans": ["trial", "starter"]}
    
    # Scheduling
    frequency = Column(Enum(ReportFrequency), nullable=False)
    schedule_config = Column(JSON, nullable=True, default=dict)
    # Example schedule_config: {"day_of_week": 1, "day_of_month": 1, "time": "09:00", "timezone": "UTC"}
    
    # Recipients
    recipients = Column(JSON, nullable=False, default=list)
    # Example: ["admin@example.com", "manager@example.com"]
    
    # Status
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    
    # Owner
    created_by_id = Column(Integer, ForeignKey("super_admins.id"), nullable=False)
    created_by = relationship("SuperAdmin", foreign_keys=[created_by_id])
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<ScheduledReport(id={self.id}, name='{self.name}', frequency={self.frequency.value})>"
