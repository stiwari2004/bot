"""
Test script for billing system
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.tenant import Tenant
from app.models.tenant_billing_config import TenantBillingConfig
from app.services.billing.billing_tracker import BillingTracker
from app.services.billing.billing_calculator import BillingCalculator
from decimal import Decimal

print("=" * 80)
print("TESTING BILLING SYSTEM")
print("=" * 80)

db = SessionLocal()

try:
    # Get demo tenant
    tenant = db.query(Tenant).filter(Tenant.id == 1).first()
    if not tenant:
        print("✗ Demo tenant (ID=1) not found")
        sys.exit(1)
    
    print(f"\n✓ Tenant found: {tenant.name} (ID: {tenant.id})")
    
    # Check if billing config exists
    config = db.query(TenantBillingConfig).filter(
        TenantBillingConfig.tenant_id == tenant.id
    ).first()
    
    if config:
        print(f"\n✓ Billing config exists:")
        print(f"  Fixed monthly: ₹{config.fixed_monthly_cost}")
        print(f"  Per-node enabled: {config.per_node_enabled} (₹{config.per_node_cost}/node)")
        print(f"  Per-ticket-received: {config.per_ticket_received_enabled} (₹{config.per_ticket_received_cost}/ticket)")
        print(f"  Per-ticket-resolved: {config.per_ticket_resolved_enabled} (₹{config.per_ticket_resolved_cost}/ticket)")
        print(f"  Per-execution: {config.per_execution_enabled} (₹{config.per_execution_cost}/execution)")
    else:
        print(f"\n⚠ No billing config found (will use defaults)")
    
    # Test billing tracker
    print(f"\n2. TESTING BILLING TRACKER:")
    tracker = BillingTracker(db)
    
    # Get current usage
    usage = tracker.get_current_period_usage(tenant.id)
    if usage:
        print(f"  ✓ Current period usage:")
        print(f"    Tickets received: {usage.tickets_received}")
        print(f"    Tickets resolved: {usage.tickets_resolved}")
        print(f"    Execution sessions: {usage.execution_sessions}")
        print(f"    API calls: {usage.api_calls}")
        print(f"    LLM tokens: {usage.llm_tokens}K")
    else:
        print(f"  ⚠ No usage record for current period")
    
    # Count active nodes
    node_count = tracker.count_active_nodes(tenant.id)
    print(f"  ✓ Active nodes: {node_count}")
    
    # Test billing calculator
    print(f"\n3. TESTING BILLING CALCULATOR:")
    calculator = BillingCalculator(db)
    bill = calculator.calculate_monthly_bill(tenant.id)
    
    print(f"  ✓ Billing calculation:")
    print(f"    Fixed cost: ₹{bill['fixed_cost']}")
    print(f"    Node cost: ₹{bill['node_cost']} ({bill['node_count']} nodes)")
    print(f"    Ticket received cost: ₹{bill['ticket_received_cost']} ({bill['usage']['tickets_received']} tickets)")
    print(f"    Ticket resolved cost: ₹{bill['ticket_resolved_cost']} ({bill['usage']['tickets_resolved']} tickets)")
    print(f"    Execution cost: ₹{bill['execution_cost']} ({bill['usage']['execution_sessions']} executions)")
    print(f"    API call cost: ₹{bill['api_call_cost']} ({bill['usage']['api_calls']} calls)")
    print(f"    LLM token cost: ₹{bill['llm_token_cost']} ({bill['usage']['llm_tokens']}K tokens)")
    print(f"    ─────────────────────────────")
    print(f"    TOTAL: ₹{bill['total_cost']}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()


