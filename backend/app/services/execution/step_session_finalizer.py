"""
Handles session finalization and cleanup after all steps complete
"""
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.core.logging import get_logger

logger = get_logger(__name__)


class StepSessionFinalizer:
    """Handles session finalization and cleanup"""
    
    def __init__(self, event_service, ticket_status_service, resolution_verification_service, connection_service):
        self.event_service = event_service
        self.ticket_status_service = ticket_status_service
        self.resolution_verification_service = resolution_verification_service
        self.connection_service = connection_service
    
    async def finalize_session(
        self,
        db: Session,
        session: ExecutionSession,
        failed_steps: List[ExecutionStep]
    ) -> None:
        """
        Finalize execution session after all steps complete.
        
        Args:
            db: Database session
            session: Execution session
            failed_steps: List of failed steps
        """
        # Determine final status
        if failed_steps:
            failed_step_numbers = [s.step_number for s in failed_steps]
            # Check if any main steps failed
            main_steps_failed = any(s.step_type == "main" for s in failed_steps)
            if main_steps_failed:
                session.status = "failed"
                # Track failure for quarantine
                self._track_failure_for_quarantine(db, session, failed_steps)
            else:
                # Only diagnostic steps failed
                session.status = "completed_with_errors"
        else:
            failed_step_numbers = []
            session.status = "completed"

        # Learning loop: promote runbook as golden example when execution fully succeeds
        if session.status == "completed" and session.runbook_id:
            try:
                self._promote_golden_runbook(db, session)
            except Exception as e:
                logger.warning(f"Non-critical: failed to promote golden runbook: {e}")

        session.completed_at = datetime.now(timezone.utc)
        
        # Store execution pattern for learning
        try:
            from app.services.execution.execution_engine import ExecutionEngine
            engine = ExecutionEngine()
            await engine.store_execution_pattern(db, session)
        except Exception as e:
            logger.warning(f"Failed to store execution pattern: {e}")
        
        # Calculate duration
        if session.started_at:
            started = session.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            completed = session.completed_at
            if completed.tzinfo is None:
                completed = completed.replace(tzinfo=timezone.utc)
            duration = (completed - started).total_seconds() / 60
            session.total_duration_minutes = int(duration)
        
        # Commit session status before verification
        db.commit()
        db.refresh(session)
        
        # Perform final cleanup
        await self._perform_final_cleanup(db, session)
        
        # Publish session completion event
        await self._publish_session_completion(db, session, failed_steps, failed_step_numbers)
        
        # Verify resolution
        if session.ticket_id:
            issue_resolved = session.status == "completed"
            verification_result = await self.resolution_verification_service.verify_resolution(
                db, session.id, session.ticket_id
            )
            logger.info(f"Resolution verification: resolved={verification_result['resolved']}")
            
            if not verification_result.get('resolved'):
                self.ticket_status_service.update_ticket_on_execution_complete(
                    db, session.ticket_id, session.status, issue_resolved=issue_resolved
                )
        
        db.commit()
    
    async def _publish_session_completion(
        self,
        db: Session,
        session: ExecutionSession,
        failed_steps: List[ExecutionStep],
        failed_step_numbers: List[int]
    ) -> None:
        """Publish session completion event"""
        if not self.event_service:
            return
        
        try:
            event_payload = {
                "status": session.status,
                "total_steps": session.total_steps,
                "failed_steps": failed_step_numbers,
                "duration_minutes": session.total_duration_minutes,
            }
            if failed_steps:
                event_payload["failure_summary"] = [
                    {
                        "step_number": s.step_number,
                        "step_type": s.step_type,
                        "error": s.error[:200] if s.error else "Unknown error",
                    }
                    for s in failed_steps
                ]
            
            await self.event_service.publish_event(
                db,
                session=session,
                event_type="execution.session.completed",
                payload=event_payload,
            )
        except Exception as e:
            logger.warning(f"Failed to publish session.completed event: {e}")
    
    async def _perform_final_cleanup(
        self,
        db: Session,
        session: ExecutionSession
    ) -> None:
        """
        Perform final cleanup after all steps complete.
        This is the only place cleanup should happen - not before each step.
        """
        try:
            # Get connection config to determine connector type
            connection_config = await self.connection_service.get_connection_config(db, session, None)
            connector_type = connection_config.get("connector_type", "") if connection_config else ""
            
            # Only cleanup for Azure Bastion connector
            if connector_type == "azure_bastion":
                logger.info(f"Performing final Azure cleanup after all steps complete for session {session.id}")
                await self._cleanup_azure_resources(connection_config)
        except Exception as e:
            logger.warning(f"Error performing final cleanup for session {session.id}: {e}")
    
    async def _cleanup_azure_resources(self, connection_config: Dict[str, Any]) -> None:
        """Cleanup Azure resources after execution"""
        try:
            from app.services.infrastructure.azure_connector import AzureBastionConnector
            from azure.identity import ClientSecretCredential, DefaultAzureCredential
            from azure.mgmt.compute import ComputeManagementClient
            
            connector = AzureBastionConnector()
            
            # Get VM details from connection config
            resource_id = connection_config.get("resource_id") or connection_config.get("target_resource_id")
            if not resource_id:
                logger.warning("Cannot perform final cleanup - missing resource_id in connection config")
                return
            
            # Parse resource ID
            parts = resource_id.split("/")
            if len(parts) < 9:
                logger.warning("Cannot perform final cleanup - invalid resource_id format")
                return
            
            subscription_id = parts[parts.index("subscriptions") + 1]
            resource_group = parts[parts.index("resourceGroups") + 1]
            vm_name = parts[parts.index("virtualMachines") + 1]
            
            # Get credentials
            azure_creds = connection_config.get("azure_credentials") or {}
            tenant_id = azure_creds.get("tenant_id") or connection_config.get("tenant_id")
            client_id = azure_creds.get("client_id") or connection_config.get("client_id")
            client_secret = azure_creds.get("client_secret") or connection_config.get("client_secret")
            
            # Create credential and compute client
            if tenant_id and client_id and client_secret:
                credential = ClientSecretCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret
                )
            else:
                credential = DefaultAzureCredential()
            
            compute_client = ComputeManagementClient(credential, subscription_id)
            
            # Determine shell
            os_type = connection_config.get("os_type", "")
            shell = "PowerShell" if (os_type and "windows" in os_type.lower()) else "bash"
            
            # Perform cleanup
            cleanup_result = await connector._attempt_azure_cleanup(
                vm_name=vm_name,
                resource_group=resource_group,
                compute_client=compute_client,
                credential=credential,
                subscription_id=subscription_id,
                shell=shell
            )
            
            if cleanup_result.get("cleanup_success"):
                logger.info("Final cleanup successful")
            else:
                logger.warning(f"Final cleanup failed: {cleanup_result.get('error', 'Unknown')}")
        except Exception as cleanup_error:
            logger.warning(f"Final cleanup error: {cleanup_error}")
    
    def _promote_golden_runbook(self, db: Session, session: ExecutionSession) -> None:
        """
        Mark a runbook as a proven golden example after successful execution.
        Updates meta_data with golden_example=True and increments success_count.
        This makes the runbook rank higher in RAG retrieval for similar future incidents.
        """
        from app.models.runbook import Runbook
        import json as _json

        runbook = db.query(Runbook).filter(Runbook.id == session.runbook_id).first()
        if not runbook:
            return

        # Parse existing meta_data
        meta = {}
        if runbook.meta_data:
            try:
                meta = _json.loads(runbook.meta_data) if isinstance(runbook.meta_data, str) else runbook.meta_data
            except Exception:
                meta = {}

        # Update golden example markers
        meta["golden_example"] = True
        meta["success_count"] = meta.get("success_count", 0) + 1
        meta["last_successful_session"] = session.id
        if session.total_duration_minutes is not None:
            # Track resolution time for quality ranking
            prev_times = meta.get("resolution_times_minutes", [])
            prev_times.append(session.total_duration_minutes)
            meta["resolution_times_minutes"] = prev_times[-10:]  # Keep last 10
            meta["avg_resolution_minutes"] = sum(prev_times) / len(prev_times)

        runbook.meta_data = _json.dumps(meta)
        # db.commit() intentionally omitted — caller (finalize_session) commits after this returns

        logger.info(
            f"Promoted runbook {session.runbook_id} as golden example "
            f"(success_count={meta['success_count']}, session={session.id})"
        )

        # Re-index for search so future RAG retrieval favours this proven runbook
        try:
            import asyncio
            from app.services.runbook.generation.runbook_indexer import RunbookIndexer
            indexer = RunbookIndexer()

            async def _reindex():
                from app.core.database import SessionLocal
                reindex_db = SessionLocal()
                try:
                    await indexer.index_runbook_for_search(runbook, reindex_db)
                    logger.info(f"Re-indexed golden runbook {runbook.id} for search")
                except Exception as e:
                    logger.warning(f"Non-critical: re-index of golden runbook failed: {e}")
                finally:
                    reindex_db.close()

            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_reindex())
            else:
                loop.run_until_complete(_reindex())
        except Exception as e:
            logger.warning(f"Non-critical: could not schedule golden runbook re-index: {e}")

    def _track_failure_for_quarantine(
        self,
        db: Session,
        session: ExecutionSession,
        failed_steps: List[ExecutionStep]
    ) -> None:
        """Track execution failure for quarantine system"""
        try:
            if not session.runbook_id:
                logger.debug("Skipping quarantine tracking: session has no runbook_id")
                return

            from app.services.execution.quarantine_service import QuarantineService
            from app.services.runbook.versioning_service import VersioningService

            quarantine_service = QuarantineService()
            versioning_service = VersioningService()
            
            # Get current runbook version
            runbook_version_id = None
            current_version = versioning_service.get_current_version(
                db=db,
                runbook_id=session.runbook_id,
                tenant_id=session.tenant_id
            )
            if current_version:
                runbook_version_id = current_version.id
            
            # Get error details from first failed step
            first_failed_step = failed_steps[0] if failed_steps else None
            error_details = {
                "error": first_failed_step.error[:500] if first_failed_step and first_failed_step.error else "Unknown error",
                "step_number": first_failed_step.step_number if first_failed_step else None,
                "error_type": "execution_failure"
            }
            
            # Track failure (will auto-quarantine if threshold reached)
            quarantine_service.track_failure(
                db=db,
                runbook_id=session.runbook_id,
                runbook_version_id=runbook_version_id,
                session_id=session.id,
                error_details=error_details,
                tenant_id=session.tenant_id
            )
        except Exception as e:
            logger.warning(f"Failed to track failure for quarantine: {e}")








