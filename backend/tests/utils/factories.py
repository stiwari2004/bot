"""
Test data factories for creating test objects
"""
from datetime import datetime, timezone
from app.models.user import User
from app.models.tenant import Tenant
from app.models.runbook import Runbook
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.ticket import Ticket
from app.services.auth import get_password_hash


class UserFactory:
    """Factory for creating test users"""
    
    @staticmethod
    def create(
        db,
        email: str = "test@example.com",
        password: str = "testpassword123",
        tenant_id: int = 1,
        role: str = "user",
        is_active: bool = True,
        **kwargs
    ) -> User:
        """Create a test user in the database"""
        user = User(
            email=email,
            password_hash=get_password_hash(password),
            tenant_id=tenant_id,
            full_name=kwargs.get("full_name", "Test User"),
            role=role,
            is_active=is_active,
            failed_login_attempts=kwargs.get("failed_login_attempts", 0),
            locked_until=kwargs.get("locked_until", None),
            **{k: v for k, v in kwargs.items() if k not in ["full_name", "failed_login_attempts", "locked_until"]}
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


class TenantFactory:
    """Factory for creating test tenants"""
    
    @staticmethod
    def create(
        db,
        name: str = None,
        description: str = "Test tenant",
        is_active: bool = True,
        **kwargs
    ) -> Tenant:
        """Create a test tenant in the database"""
        # Generate unique name if not provided to avoid conflicts
        if name is None:
            import random
            import string
            name = f"test_tenant_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"
        
        # Check if tenant with this name already exists
        existing = db.query(Tenant).filter(Tenant.name == name).first()
        if existing:
            # If exists, generate a new unique name
            import random
            import string
            name = f"test_tenant_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"
        
        tenant = Tenant(
            name=name,
            description=description,
            is_active=is_active,
            **kwargs
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        return tenant


class RunbookFactory:
    """Factory for creating test runbooks"""
    
    @staticmethod
    def create(
        db,
        tenant_id: int = 1,
        title: str = "Test Runbook",
        status: str = "approved",
        is_active: str = "active",
        body_md: str = "# Test Runbook\nTest content",
        **kwargs
    ) -> Runbook:
        """Create a test runbook in the database"""
        import json
        
        runbook = Runbook(
            tenant_id=tenant_id,
            title=title,
            status=status,
            is_active=is_active,
            body_md=body_md,
            meta_data=json.dumps(kwargs.get("meta_data", {
                "service": "server",
                "env": "prod",
                "risk": "low"
            })),
            confidence=kwargs.get("confidence", 0.85),
            **{k: v for k, v in kwargs.items() if k not in ["meta_data", "confidence"]}
        )
        db.add(runbook)
        db.commit()
        db.refresh(runbook)
        return runbook


class ExecutionSessionFactory:
    """Factory for creating test execution sessions"""
    
    @staticmethod
    def create(
        db,
        runbook_id: int,
        tenant_id: int = 1,
        status: str = "pending",
        ticket_id: int = None,
        **kwargs
    ) -> ExecutionSession:
        """Create a test execution session in the database"""
        session = ExecutionSession(
            runbook_id=runbook_id,
            tenant_id=tenant_id,
            status=status,
            ticket_id=ticket_id,
            current_step=kwargs.get("current_step", 0),
            waiting_for_approval=kwargs.get("waiting_for_approval", False),
            approval_step_number=kwargs.get("approval_step_number", None),
            **{k: v for k, v in kwargs.items() if k not in ["current_step", "waiting_for_approval", "approval_step_number"]}
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session


class ExecutionStepFactory:
    """Factory for creating test execution steps"""
    
    @staticmethod
    def create(
        db,
        session_id: int,
        step_number: int = 1,
        step_type: str = "main",
        command: str = "echo 'test command'",
        requires_approval: bool = False,
        **kwargs
    ) -> ExecutionStep:
        """Create a test execution step in the database"""
        step = ExecutionStep(
            session_id=session_id,
            step_number=step_number,
            step_type=step_type,
            command=command,
            requires_approval=requires_approval,
            **kwargs
        )
        db.add(step)
        db.commit()
        db.refresh(step)
        return step


class TicketFactory:
    """Factory for creating test tickets"""
    
    @staticmethod
    def create(
        db,
        tenant_id: int = 1,
        title: str = "Test Ticket",
        description: str = "Test ticket description",
        status: str = "open",
        source: str = "test",
        severity: str = "medium",
        environment: str = "prod",
        **kwargs
    ) -> Ticket:
        """Create a test ticket in the database"""
        ticket = Ticket(
            tenant_id=tenant_id,
            title=title,
            description=description,
            status=status,
            source=source,
            severity=severity,
            environment=environment,
            **kwargs
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket

