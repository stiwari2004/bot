"""
Step execution utility functions - module-level helpers
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.services.execution.output_extractor import get_output_extractor
from app.core.logging import get_logger

logger = get_logger(__name__)

# Key used to persist resolved inputs in session.meta_data
_RESOLVED_INPUTS_KEY = "resolved_inputs"


def _get_resolved_inputs(session: ExecutionSession) -> dict:
    """Load the accumulated resolved inputs from session metadata."""
    meta = session.meta_data if isinstance(session.meta_data, dict) else {}
    return dict(meta.get(_RESOLVED_INPUTS_KEY) or {})


def _save_resolved_inputs(session: ExecutionSession, resolved: dict, db: Session) -> None:
    """Persist updated resolved inputs into session metadata."""
    from sqlalchemy.orm.attributes import flag_modified
    if not isinstance(session.meta_data, dict):
        session.meta_data = {}
    session.meta_data[_RESOLVED_INPUTS_KEY] = resolved
    flag_modified(session, "meta_data")
    db.add(session)


def _find_needed_vars(db: Session, session: ExecutionSession, from_step_number: int) -> list:
    """Collect all {{variable}} names still needed by steps not yet completed."""
    future_steps = (
        db.query(ExecutionStep)
        .filter(
            ExecutionStep.session_id == session.id,
            ExecutionStep.step_number >= from_step_number,
            ExecutionStep.completed == False,
        )
        .all()
    )
    needed = []
    extractor = get_output_extractor()
    for step in future_steps:
        for var in extractor.find_unresolved(step.command or ""):
            if var not in needed:
                needed.append(var)
    return needed


def _is_command_not_found_or_wrong_shell(error_text: Optional[str]) -> bool:
    """
    True if the failure is due to wrong command/shell (e.g. PowerShell on bash),
    not a real server/application failure. In that case we should continue to the
    next step instead of failing the run.
    """
    if not error_text:
        return False
    err = error_text.lower()
    if "command not found" in err or ": command not found" in err:
        return True
    if "not found" in err and ("bash:" in err or "line 1:" in err):
        return True
    # PowerShell cmdlets run in bash (e.g. Get-Counter, Select-Object)
    if "get-counter" in err or "select-object" in err:
        return True
    return False


def _get_next_step_with_branching(
    db: Session,
    session: ExecutionSession,
    current_step: ExecutionStep,
    step_succeeded: bool
) -> Optional[ExecutionStep]:
    """
    Get the next step to execute based on branching logic.

    Args:
        db: Database session
        session: Execution session
        current_step: Current step that just completed
        step_succeeded: Whether the current step succeeded

    Returns:
        Next ExecutionStep to execute, or None if no next step
    """
    # Check for branching logic in command_payload
    branching = current_step.command_payload or {}
    target_step_number = None

    if step_succeeded and branching.get("on_success") is not None:
        # Jump to on_success step
        target_step_number = branching.get("on_success")
        logger.info(
            f"Step {current_step.step_number} succeeded, branching to step {target_step_number} "
            f"(on_success)"
        )
    elif not step_succeeded and branching.get("on_failure") is not None:
        # Jump to on_failure step
        target_step_number = branching.get("on_failure")
        logger.info(
            f"Step {current_step.step_number} failed, branching to step {target_step_number} "
            f"(on_failure)"
        )

    if target_step_number is not None:
        # Find step by explicit step_number
        next_step = db.query(ExecutionStep).filter(
            ExecutionStep.session_id == session.id,
            ExecutionStep.step_number == target_step_number,
            ExecutionStep.completed == False
        ).first()

        if next_step:
            return next_step
        else:
            logger.warning(
                f"Branching target step {target_step_number} not found or already completed. "
                f"Falling back to sequential execution."
            )

    # Fall back to sequential execution (next step_number)
    next_step = db.query(ExecutionStep).filter(
        ExecutionStep.session_id == session.id,
        ExecutionStep.step_number == current_step.step_number + 1,
        ExecutionStep.completed == False
    ).first()

    return next_step
