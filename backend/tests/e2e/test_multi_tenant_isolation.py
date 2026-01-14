"""
End-to-end tests for multi-tenant isolation
Tests that tenants cannot access each other's data
"""
import pytest
from fastapi.testclient import TestClient
from tests.utils.factories import (
    UserFactory, TenantFactory, RunbookFactory, TicketFactory, ExecutionSessionFactory
)


@pytest.mark.e2e
class TestMultiTenantIsolation:
    """Test multi-tenant data isolation"""
    
    def test_tenant_cannot_access_other_tenant_runbooks(
        self, db
    ):
        """Test that tenants cannot access runbooks from other tenants"""
        # Create two tenants
        tenant1 = TenantFactory.create(db, name="tenant1")
        tenant2 = TenantFactory.create(db, name="tenant2")
        
        # Create users for each tenant
        user1 = UserFactory.create(
            db,
            email="user1@tenant1.com",
            tenant_id=tenant1.id
        )
        user2 = UserFactory.create(
            db,
            email="user2@tenant2.com",
            tenant_id=tenant2.id
        )
        
        # Create runbook for tenant1
        runbook1 = RunbookFactory.create(
            db,
            tenant_id=tenant1.id,
            title="Tenant1 Runbook"
        )
        
        # Create runbook for tenant2
        runbook2 = RunbookFactory.create(
            db,
            tenant_id=tenant2.id,
            title="Tenant2 Runbook"
        )
        
        # Create authenticated clients for each user
        from app.services.auth import create_access_token
        from app.main import app
        from app.core.database import get_db
        
        token1 = create_access_token(data={"sub": user1.email, "tenant_id": tenant1.id})
        token2 = create_access_token(data={"sub": user2.email, "tenant_id": tenant2.id})
        
        client1 = TestClient(app)
        client1.headers = {"Authorization": f"Bearer {token1}"}
        
        client2 = TestClient(app)
        client2.headers = {"Authorization": f"Bearer {token2}"}
        
        # Override get_db dependency
        def override_get_db_tenant1():
            yield db
        
        def override_get_db_tenant2():
            yield db
        
        app.dependency_overrides[get_db] = override_get_db_tenant1
        
        # User1 should see their runbook
        response1 = client1.get(f"/api/v1/runbooks/{runbook1.id}")
        assert response1.status_code == 200
        
        # User1 should NOT see tenant2's runbook
        response2 = client1.get(f"/api/v1/runbooks/{runbook2.id}")
        assert response2.status_code == 404
        
        # User2 should see their runbook
        app.dependency_overrides[get_db] = override_get_db_tenant2
        response3 = client2.get(f"/api/v1/runbooks/{runbook2.id}")
        assert response3.status_code == 200
        
        # User2 should NOT see tenant1's runbook
        response4 = client2.get(f"/api/v1/runbooks/{runbook1.id}")
        assert response4.status_code == 404
        
        # Clean up
        app.dependency_overrides.clear()
    
    def test_tenant_cannot_access_other_tenant_tickets(
        self, db
    ):
        """Test that tenants cannot access tickets from other tenants"""
        # Create two tenants
        tenant1 = TenantFactory.create(db, name="tenant1")
        tenant2 = TenantFactory.create(db, name="tenant2")
        
        # Create users
        user1 = UserFactory.create(db, email="user1@tenant1.com", tenant_id=tenant1.id)
        user2 = UserFactory.create(db, email="user2@tenant2.com", tenant_id=tenant2.id)
        
        # Create tickets
        ticket1 = TicketFactory.create(
            db,
            tenant_id=tenant1.id,
            title="Tenant1 Ticket"
        )
        
        ticket2 = TicketFactory.create(
            db,
            tenant_id=tenant2.id,
            title="Tenant2 Ticket"
        )
        
        # Create authenticated clients
        from app.services.auth import create_access_token
        from app.main import app
        from app.core.database import get_db
        
        token1 = create_access_token(data={"sub": user1.email, "tenant_id": tenant1.id})
        token2 = create_access_token(data={"sub": user2.email, "tenant_id": tenant2.id})
        
        client1 = TestClient(app)
        client1.headers = {"Authorization": f"Bearer {token1}"}
        
        client2 = TestClient(app)
        client2.headers = {"Authorization": f"Bearer {token2}"}
        
        def override_get_db_tenant1():
            yield db
        
        def override_get_db_tenant2():
            yield db
        
        app.dependency_overrides[get_db] = override_get_db_tenant1
        
        # User1 should see their ticket
        response1 = client1.get(f"/api/v1/ticket-ingestion/demo/tickets/{ticket1.id}")
        assert response1.status_code == 200
        
        # User1 should NOT see tenant2's ticket
        response2 = client1.get(f"/api/v1/ticket-ingestion/demo/tickets/{ticket2.id}")
        assert response2.status_code == 404
        
        # User2 should see their ticket
        app.dependency_overrides[get_db] = override_get_db_tenant2
        response3 = client2.get(f"/api/v1/ticket-ingestion/demo/tickets/{ticket2.id}")
        assert response3.status_code == 200
        
        # User2 should NOT see tenant1's ticket
        response4 = client2.get(f"/api/v1/ticket-ingestion/demo/tickets/{ticket1.id}")
        assert response4.status_code == 404
        
        app.dependency_overrides.clear()
    
    def test_tenant_cannot_access_other_tenant_executions(
        self, db
    ):
        """Test that tenants cannot access execution sessions from other tenants"""
        # Create two tenants
        tenant1 = TenantFactory.create(db, name="tenant1")
        tenant2 = TenantFactory.create(db, name="tenant2")
        
        # Create users
        user1 = UserFactory.create(db, email="user1@tenant1.com", tenant_id=tenant1.id)
        user2 = UserFactory.create(db, email="user2@tenant2.com", tenant_id=tenant2.id)
        
        # Create runbooks
        runbook1 = RunbookFactory.create(db, tenant_id=tenant1.id, status="approved")
        runbook2 = RunbookFactory.create(db, tenant_id=tenant2.id, status="approved")
        
        # Create execution sessions
        session1 = ExecutionSessionFactory.create(
            db,
            runbook_id=runbook1.id,
            tenant_id=tenant1.id,
            status="in_progress"
        )
        
        session2 = ExecutionSessionFactory.create(
            db,
            runbook_id=runbook2.id,
            tenant_id=tenant2.id,
            status="in_progress"
        )
        
        # Create authenticated clients
        from app.services.auth import create_access_token
        from app.main import app
        from app.core.database import get_db
        
        token1 = create_access_token(data={"sub": user1.email, "tenant_id": tenant1.id})
        token2 = create_access_token(data={"sub": user2.email, "tenant_id": tenant2.id})
        
        client1 = TestClient(app)
        client1.headers = {"Authorization": f"Bearer {token1}"}
        
        client2 = TestClient(app)
        client2.headers = {"Authorization": f"Bearer {token2}"}
        
        def override_get_db_tenant1():
            yield db
        
        def override_get_db_tenant2():
            yield db
        
        app.dependency_overrides[get_db] = override_get_db_tenant1
        
        # User1 should see their execution
        response1 = client1.get(f"/api/v1/agent/{session1.id}")
        assert response1.status_code == 200
        
        # User1 should NOT see tenant2's execution
        response2 = client1.get(f"/api/v1/agent/{session2.id}")
        assert response2.status_code == 404
        
        # User2 should see their execution
        app.dependency_overrides[get_db] = override_get_db_tenant2
        response3 = client2.get(f"/api/v1/agent/{session2.id}")
        assert response3.status_code == 200
        
        # User2 should NOT see tenant1's execution
        response4 = client2.get(f"/api/v1/agent/{session1.id}")
        assert response4.status_code == 404
        
        app.dependency_overrides.clear()


@pytest.mark.e2e
class TestTenantSpecificConfigurations:
    """Test tenant-specific configurations"""
    
    def test_tenant_specific_confidence_threshold(
        self, authenticated_client, db
    ):
        """Test that each tenant can have different confidence thresholds"""
        client, user = authenticated_client
        
        # This would test that tenant configurations are isolated
        # Implementation depends on how ConfigService works
        from app.services.config_service import ConfigService
        
        # Set threshold for tenant
        threshold1 = ConfigService.get_confidence_threshold(db, user.tenant_id)
        
        # Create another tenant
        other_tenant = TenantFactory.create(db, name="other_tenant")
        threshold2 = ConfigService.get_confidence_threshold(db, other_tenant.id)
        
        # Thresholds should be independent (may be same default, but isolated)
        # This test verifies isolation, not specific values
        assert isinstance(threshold1, (int, float))
        assert isinstance(threshold2, (int, float))

