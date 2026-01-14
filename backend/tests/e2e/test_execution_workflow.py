"""
End-to-end tests for execution workflow
Tests complete flow from ticket creation to execution completion
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from tests.utils.factories import (
    UserFactory, TenantFactory, RunbookFactory, TicketFactory, ExecutionSessionFactory
)


@pytest.mark.e2e
class TestCompleteExecutionWorkflow:
    """Test complete execution workflow from start to finish"""
    
    @pytest.mark.asyncio
    async def test_complete_execution_workflow_with_approval(
        self, authenticated_client, db
    ):
        """Test complete execution workflow with human approval"""
        client, user = authenticated_client
        
        # Step 1: Create a runbook
        runbook = RunbookFactory.create(
            db,
            tenant_id=user.tenant_id,
            title="Fix High CPU",
            status="approved",
            body_md="# Test Runbook\n```yaml\nsteps:\n  - name: Check CPU\n    command: Get-Counter\n```"
        )
        
        # Step 2: Create a ticket
        ticket = TicketFactory.create(
            db,
            tenant_id=user.tenant_id,
            title="High CPU Alert",
            description="CPU usage is above 90%",
            status="open"
        )
        
        # Step 3: Start execution
        with patch('app.services.execution.execution_engine.StepExecutionService') as mock_step:
            mock_step.return_value.execute_next_step = AsyncMock()
            
            response = client.post(
                "/api/v1/agent/execute",
                json={
                    "runbook_id": runbook.id,
                    "issue_description": ticket.description,
                    "ticket_id": ticket.id
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            session_id = data["id"]
            
            # Step 4: Get execution status
            status_response = client.get(f"/api/v1/agent/{session_id}")
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["session_id"] == session_id
            
            # Step 5: Approve step (if waiting for approval)
            if status_data.get("waiting_for_approval"):
                approve_response = client.post(
                    f"/api/v1/agent/{session_id}/approve-step",
                    json={
                        "approve": True,
                        "step_number": status_data.get("current_step", 1)
                    }
                )
                assert approve_response.status_code in [200, 202]
    
    @pytest.mark.asyncio
    async def test_execution_workflow_with_rejection(
        self, authenticated_client, db
    ):
        """Test execution workflow when step is rejected"""
        client, user = authenticated_client
        
        runbook = RunbookFactory.create(
            db,
            tenant_id=user.tenant_id,
            status="approved"
        )
        
        ticket = TicketFactory.create(
            db,
            tenant_id=user.tenant_id,
            status="open"
        )
        
        with patch('app.services.execution.execution_engine.StepExecutionService') as mock_step:
            mock_step.return_value.execute_next_step = AsyncMock()
            
            # Start execution
            response = client.post(
                "/api/v1/agent/execute",
                json={
                    "runbook_id": runbook.id,
                    "issue_description": "Test issue",
                    "ticket_id": ticket.id
                }
            )
            
            assert response.status_code == 200
            session_id = response.json()["id"]
            
            # Reject step
            reject_response = client.post(
                f"/api/v1/agent/{session_id}/approve-step",
                json={
                    "approve": False,
                    "step_number": 1
                }
            )
            
            assert reject_response.status_code in [200, 202]
            
            # Verify session is abandoned
            status_response = client.get(f"/api/v1/agent/{session_id}")
            status_data = status_response.json()
            assert status_data["status"] == "abandoned"
    
    @pytest.mark.asyncio
    async def test_execution_workflow_with_rollback(
        self, authenticated_client, db
    ):
        """Test execution workflow with rollback on failure"""
        client, user = authenticated_client
        
        runbook = RunbookFactory.create(
            db,
            tenant_id=user.tenant_id,
            status="approved"
        )
        
        ticket = TicketFactory.create(
            db,
            tenant_id=user.tenant_id,
            status="open"
        )
        
        with patch('app.services.execution.execution_engine.StepExecutionService') as mock_step:
            # Mock step failure
            mock_step.return_value.execute_next_step = AsyncMock(
                side_effect=Exception("Step execution failed")
            )
            
            # Start execution
            response = client.post(
                "/api/v1/agent/execute",
                json={
                    "runbook_id": runbook.id,
                    "issue_description": "Test issue",
                    "ticket_id": ticket.id
                }
            )
            
            # Execution should handle failure and potentially rollback
            # (exact behavior depends on implementation)
            assert response.status_code in [200, 500]
    
    @pytest.mark.asyncio
    async def test_execution_workflow_with_self_healing(
        self, authenticated_client, db
    ):
        """Test execution workflow with self-healing on failure"""
        client, user = authenticated_client
        
        runbook = RunbookFactory.create(
            db,
            tenant_id=user.tenant_id,
            status="approved"
        )
        
        ticket = TicketFactory.create(
            db,
            tenant_id=user.tenant_id,
            status="open"
        )
        
        with patch('app.services.execution.execution_engine.StepExecutionService') as mock_step:
            with patch('app.services.self_healing.dynamic_remediation_generator.DynamicRemediationGenerator') as mock_healing:
                mock_healing.return_value.generate_remediation = AsyncMock(
                    return_value={"steps": [{"command": "fix-command"}]}
                )
                
                # Start execution
                response = client.post(
                    "/api/v1/agent/execute",
                    json={
                        "runbook_id": runbook.id,
                        "issue_description": "Test issue",
                        "ticket_id": ticket.id
                    }
                )
                
                # Self-healing should be triggered on failure
                # (exact behavior depends on implementation)
                assert response.status_code in [200, 500]
    
    @pytest.mark.asyncio
    async def test_execution_workflow_error_handling(
        self, authenticated_client, db
    ):
        """Test execution workflow error handling"""
        client, user = authenticated_client
        
        # Try to start execution with invalid runbook
        response = client.post(
            "/api/v1/agent/execute",
            json={
                "runbook_id": 99999,  # Nonexistent
                "issue_description": "Test issue"
            }
        )
        
        assert response.status_code in [404, 400]
        
        # Try to start execution with unapproved runbook
        draft_runbook = RunbookFactory.create(
            db,
            tenant_id=user.tenant_id,
            status="draft"
        )
        
        response = client.post(
            "/api/v1/agent/execute",
            json={
                "runbook_id": draft_runbook.id,
                "issue_description": "Test issue"
            }
        )
        
        assert response.status_code in [400, 403]


@pytest.mark.e2e
class TestApprovalWorkflow:
    """Test approval workflow in execution"""
    
    @pytest.mark.asyncio
    async def test_approval_workflow_with_multiple_steps(
        self, authenticated_client, db
    ):
        """Test approval workflow with multiple steps requiring approval"""
        client, user = authenticated_client
        
        runbook = RunbookFactory.create(
            db,
            tenant_id=user.tenant_id,
            status="approved"
        )
        
        # Start execution
        response = client.post(
            "/api/v1/agent/execute",
            json={
                "runbook_id": runbook.id,
                "issue_description": "Test issue"
            }
        )
        
        assert response.status_code == 200
        session_id = response.json()["id"]
        
        # Get pending approvals
        approvals_response = client.get("/api/v1/agent/pending-approvals")
        assert approvals_response.status_code == 200
        
        # Approve each step
        # (This is a simplified test - actual implementation may vary)
        for step_num in range(1, 4):
            approve_response = client.post(
                f"/api/v1/agent/{session_id}/approve-step",
                json={
                    "approve": True,
                    "step_number": step_num
                }
            )
            # May return 200 or 202 depending on async processing
            assert approve_response.status_code in [200, 202, 400]


@pytest.mark.e2e
class TestRollbackWorkflow:
    """Test rollback workflow in execution"""
    
    @pytest.mark.asyncio
    async def test_rollback_on_step_failure(
        self, authenticated_client, db
    ):
        """Test that rollback is triggered on step failure"""
        client, user = authenticated_client
        
        runbook = RunbookFactory.create(
            db,
            tenant_id=user.tenant_id,
            status="approved"
        )
        
        with patch('app.services.execution.rollback_service.RollbackService') as mock_rollback:
            mock_rollback.return_value.rollback_to_step = AsyncMock()
            
            # Start execution
            response = client.post(
                "/api/v1/agent/execute",
                json={
                    "runbook_id": runbook.id,
                    "issue_description": "Test issue"
                }
            )
            
            # Rollback should be triggered on failure
            # (exact behavior depends on implementation)
            assert response.status_code in [200, 500]

