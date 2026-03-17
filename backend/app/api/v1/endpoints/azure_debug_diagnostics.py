"""
Azure connection diagnostic endpoint
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.services.execution.connection_service import ConnectionService
from app.services.infrastructure import get_connector
from app.api.v1.endpoints.azure_debug_vm import _parse_azure_resource_id, _get_azure_credentials

router = APIRouter()
logger = get_logger(__name__)


@router.post("/debug/test-azure-connection")
async def test_azure_connection(session_id: int, db: Session = Depends(get_db)):
    """Diagnostic endpoint to test Azure connectivity step by step"""
    try:
        session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        first_step = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session_id, ExecutionStep.step_number == 1
        ).first()
        if not first_step:
            raise HTTPException(status_code=404, detail=f"No first step found for session {session_id}")

        diagnostic = {
            "session_id": session_id,
            "step_1": {"found": True, "command": first_step.command},
            "step_2": {
                "connection_config": None, "connector_type": None,
                "has_resource_id": False, "has_azure_credentials": False, "error": None,
            },
            "step_3": {"connector_found": False, "connector_class": None, "error": None},
            "step_4": {"test_command_result": None, "error": None},
        }

        try:
            connection_service = ConnectionService()
            connection_config = await connection_service.get_connection_config(db, session, first_step)
            diagnostic["step_2"]["connection_config"] = {
                "keys": list(connection_config.keys()),
                "connector_type": connection_config.get("connector_type"),
            }
            diagnostic["step_2"]["connector_type"] = connection_config.get("connector_type")
            diagnostic["step_2"]["has_resource_id"] = bool(connection_config.get("resource_id"))
            diagnostic["step_2"]["has_azure_credentials"] = bool(connection_config.get("azure_credentials"))
        except Exception as e:
            diagnostic["step_2"]["error"] = str(e)
            return diagnostic

        try:
            connector_type = connection_config.get("connector_type", "local")
            connector = get_connector(connector_type)
            diagnostic["step_3"]["connector_found"] = True
            diagnostic["step_3"]["connector_class"] = type(connector).__name__
        except Exception as e:
            diagnostic["step_3"]["error"] = str(e)
            return diagnostic

        # Test command execution is disabled to prevent Azure Run Command conflicts.
        # Azure only allows one command at a time per VM.
        if connector_type == "azure_bastion":
            diagnostic["step_4"]["test_command_result"] = {
                "skipped": True,
                "reason": "Test command execution disabled to prevent Azure Run Command conflicts. Azure only allows one command at a time per VM.",
                "note": "If you need to test connectivity, execute a real step instead of using this diagnostic endpoint.",
            }

        return diagnostic
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in test_azure_connection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Diagnostic error: {str(e)}")
