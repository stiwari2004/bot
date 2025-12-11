"""
Tenant billing configuration model
Allows super admin to configure flexible billing per tenant
"""
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class TenantBillingConfig(Base):
    """Billing configuration for each tenant"""
    __tablename__ = "tenant_billing_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Fixed Monthly Cost
    fixed_monthly_cost = Column(Numeric(10, 2), nullable=False, default=0.00, comment="Fixed monthly base cost")
    
    # Per-Node Configuration
    per_node_enabled = Column(Boolean, default=False, nullable=False, comment="Enable per-node billing")
    per_node_cost = Column(Numeric(10, 2), default=0.00, nullable=False, comment="Cost per node per month")
    node_count_override = Column(Integer, nullable=True, comment="Manual node count override (null = auto-calculate)")
    
    # Variable Costs - Ticket Based
    per_ticket_received_enabled = Column(Boolean, default=False, nullable=False, comment="Enable per-ticket-received billing")
    per_ticket_received_cost = Column(Numeric(10, 2), default=0.00, nullable=False, comment="Cost per ticket received")
    
    per_ticket_resolved_enabled = Column(Boolean, default=False, nullable=False, comment="Enable per-ticket-resolved billing")
    per_ticket_resolved_cost = Column(Numeric(10, 2), default=0.00, nullable=False, comment="Cost per ticket resolved")
    
    # Variable Costs - Execution Based
    per_execution_enabled = Column(Boolean, default=False, nullable=False, comment="Enable per-execution billing")
    per_execution_cost = Column(Numeric(10, 2), default=0.00, nullable=False, comment="Cost per execution session")
    
    # Variable Costs - API Based
    per_api_call_enabled = Column(Boolean, default=False, nullable=False, comment="Enable per-API-call billing")
    per_api_call_cost = Column(Numeric(10, 4), default=0.0000, nullable=False, comment="Cost per API call")
    
    # Variable Costs - LLM Based
    per_llm_token_enabled = Column(Boolean, default=False, nullable=False, comment="Enable per-LLM-token billing")
    per_llm_token_cost = Column(Numeric(10, 6), default=0.000000, nullable=False, comment="Cost per 1K LLM tokens")
    
    # Billing Period Configuration
    billing_cycle = Column(String(20), default="monthly", nullable=False, comment="Billing cycle: monthly, quarterly, annual")
    billing_day = Column(Integer, default=1, nullable=False, comment="Day of month to bill (1-28)")
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="billing_config")
    
    # Indexes
    __table_args__ = (
        Index('idx_billing_config_tenant', 'tenant_id'),
        Index('idx_billing_config_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<TenantBillingConfig(tenant_id={self.tenant_id}, fixed={self.fixed_monthly_cost}, per_node={self.per_node_cost if self.per_node_enabled else 0})>"


class TenantBillingUsage(Base):
    """Track usage metrics for billing calculation"""
    __tablename__ = "tenant_billing_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Period
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Usage Metrics
    tickets_received = Column(Integer, default=0, nullable=False, comment="Tickets received/created in period")
    tickets_resolved = Column(Integer, default=0, nullable=False, comment="Tickets resolved in period")
    execution_sessions = Column(Integer, default=0, nullable=False, comment="Execution sessions in period")
    api_calls = Column(Integer, default=0, nullable=False, comment="API calls in period")
    llm_tokens = Column(Integer, default=0, nullable=False, comment="LLM tokens consumed (in thousands)")
    
    # Node count (snapshot at period end)
    active_nodes = Column(Integer, default=0, nullable=False, comment="Active nodes at period end")
    
    # Calculated costs
    fixed_cost = Column(Numeric(10, 2), default=0.00, nullable=False)
    node_cost = Column(Numeric(10, 2), default=0.00, nullable=False)
    ticket_received_cost = Column(Numeric(10, 2), default=0.00, nullable=False)
    ticket_resolved_cost = Column(Numeric(10, 2), default=0.00, nullable=False)
    execution_cost = Column(Numeric(10, 2), default=0.00, nullable=False)
    api_call_cost = Column(Numeric(10, 2), default=0.00, nullable=False)
    llm_token_cost = Column(Numeric(10, 2), default=0.00, nullable=False)
    total_cost = Column(Numeric(10, 2), default=0.00, nullable=False)
    
    # Status
    status = Column(String(20), default="pending", nullable=False, comment="pending, calculated, invoiced, paid")
    invoice_number = Column(String(50), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_billing_usage_tenant_period', 'tenant_id', 'period_start', 'period_end'),
        Index('idx_billing_usage_status', 'status'),
    )
    
    def __repr__(self):
        return f"<TenantBillingUsage(tenant_id={self.tenant_id}, period={self.period_start.date()}, total={self.total_cost})>"


