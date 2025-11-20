"""
Rollback service for execution steps
"""
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.services.infrastructure import get_connector
from app.core.logging import get_logger

logger = get_logger(__name__)


class RollbackService:
    """Handles rollback operations for execution steps"""
    
    def __init__(self, connection_service):
        self.connection_service = connection_service
    
    async def rollback_execution(
        self,
        db: Session,
        session: ExecutionSession
    ):
        """
        Rollback all executed steps in reverse order
        
        Executes rollback commands for all completed steps, starting from the last one
        """
        try:
            # Get all completed steps, ordered by step_number descending
            completed_steps = db.query(ExecutionStep).filter(
                ExecutionStep.session_id == session.id,
                ExecutionStep.completed == True,
                ExecutionStep.success == True  # Only rollback successful steps
            ).order_by(ExecutionStep.step_number.desc()).all()
            
            if not completed_steps:
                logger.info(f"No completed steps to rollback for session {session.id}")
                return
            
            logger.info(f"Starting rollback for session {session.id}: {len(completed_steps)} steps to rollback")
            
            # Get connection config (use same config as execution)
            connection_config = await self.connection_service.get_connection_config(db, session, completed_steps[0])
            connector_type = connection_config.get("connector_type", "local")
            connector = get_connector(connector_type)
            
            rollback_failed = False
            
            # Execute rollback commands in reverse order
            for step in completed_steps:
                if not step.rollback_command:
                    logger.warning(f"Step {step.step_number} has no rollback command, skipping")
                    continue
                
                try:
                    logger.info(f"Rolling back step {step.step_number}: {step.rollback_command[:50]}...")
                    
                    # Execute rollback command
                    result = await connector.execute_command(
                        command=step.rollback_command,
                        connection_config=connection_config,
                        timeout=30
                    )
                    
                    if not result["success"]:
                        logger.error(
                            f"Rollback failed for step {step.step_number}: {result.get('error', 'Unknown error')}"
                        )
                        rollback_failed = True
                        # Continue with other rollbacks even if one fails
                    else:
                        logger.info(f"Successfully rolled back step {step.step_number}")
                        
                except Exception as e:
                    logger.error(f"Exception during rollback of step {step.step_number}: {e}")
                    rollback_failed = True
                    # Continue with other rollbacks
            
            if rollback_failed:
                logger.warning(f"Some rollback commands failed for session {session.id}")
            else:
                logger.info(f"Successfully rolled back all steps for session {session.id}")
                
        except Exception as e:
            logger.error(f"Error during rollback execution: {e}")
            # Don't raise - rollback failure shouldn't prevent error reporting


