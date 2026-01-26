"""
Background scheduler for executing scheduled reports
"""
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.reporting.scheduled_report_service import ScheduledReportService
from app.core.logging import get_logger

logger = get_logger(__name__)


class ReportScheduler:
    """Background scheduler for executing scheduled reports"""
    
    _task: asyncio.Task = None
    _running: bool = False
    
    @classmethod
    async def start(cls, check_interval: int = 60):
        """
        Start the report scheduler
        
        Args:
            check_interval: How often to check for due reports (in seconds)
        """
        if cls._running:
            logger.warning("Report scheduler is already running")
            return
        
        cls._running = True
        cls._task = asyncio.create_task(cls._scheduler_loop(check_interval))
        logger.info(f"Report scheduler started (check interval: {check_interval}s)")
    
    @classmethod
    async def stop(cls):
        """Stop the report scheduler"""
        cls._running = False
        if cls._task:
            cls._task.cancel()
            try:
                await cls._task
            except asyncio.CancelledError:
                pass
        logger.info("Report scheduler stopped")
    
    @classmethod
    async def _scheduler_loop(cls, check_interval: int):
        """Main scheduler loop"""
        while cls._running:
            try:
                await cls._check_and_execute_reports()
            except Exception as e:
                logger.error(f"Error in report scheduler loop: {e}", exc_info=True)
            
            # Wait before next check
            try:
                await asyncio.sleep(check_interval)
            except asyncio.CancelledError:
                break
    
    @classmethod
    async def _check_and_execute_reports(cls):
        """Check for reports due for execution and execute them"""
        db = SessionLocal()
        try:
            service = ScheduledReportService(db)
            due_reports = service.get_reports_due_for_execution()
            
            if not due_reports:
                return
            
            logger.info(f"Found {len(due_reports)} scheduled report(s) due for execution")
            
            for report in due_reports:
                try:
                    logger.info(f"Executing scheduled report: {report.name} (ID: {report.id})")
                    # Execute in thread pool to avoid blocking
                    success = await asyncio.to_thread(
                        service.execute_scheduled_report,
                        report.id
                    )
                    
                    if success:
                        logger.info(f"Successfully executed scheduled report: {report.name} (ID: {report.id})")
                    else:
                        logger.warning(f"Failed to execute scheduled report: {report.name} (ID: {report.id})")
                        
                except Exception as e:
                    logger.error(
                        f"Error executing scheduled report {report.id} ({report.name}): {e}",
                        exc_info=True
                    )
                    
        except Exception as e:
            logger.error(f"Error checking for scheduled reports: {e}", exc_info=True)
        finally:
            db.close()
    
    @classmethod
    async def execute_now(cls, report_id: int) -> bool:
        """
        Manually execute a scheduled report immediately
        
        Args:
            report_id: ID of the scheduled report to execute
            
        Returns:
            True if execution was successful, False otherwise
        """
        db = SessionLocal()
        try:
            service = ScheduledReportService(db)
            success = await asyncio.to_thread(
                service.execute_scheduled_report,
                report_id
            )
            return success
        except Exception as e:
            logger.error(f"Error manually executing report {report_id}: {e}", exc_info=True)
            return False
        finally:
            db.close()
