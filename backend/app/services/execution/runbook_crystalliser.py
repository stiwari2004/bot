"""
Runbook Crystalliser — converts a proven execution trace into a reusable runbook.

Called after the human reviews the agent session, marks weeds, and clicks
"Save as Runbook".  Produces a YAML runbook that:

  1. Contains only non-weed steps
  2. De-parameterises specific values back into {{variable}} placeholders
  3. Documents HOW each placeholder is resolved (from which command's output)
  4. Stores the runbook via the existing RunbookRepository

The stored runbook is battle-tested — every step in it succeeded during the
agent's real execution on real infrastructure.
"""
import re
import yaml
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, ExecutionStep

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# De-parameterisation helpers
# ─────────────────────────────────────────────────────────────────────────────

# Maps a concrete value back to a template variable IF the value looks like
# something that was resolved from system output.  We do this by checking
# the resolved_inputs dict and substituting values back to {{variable}}.
def _deparameterise(command: str, resolved_inputs: Dict[str, str]) -> str:
    """
    Replace concrete resolved values back with {{variable}} placeholders.
    Longest values are replaced first to avoid partial replacements.
    """
    if not resolved_inputs:
        return command

    result = command
    # Sort by value length descending (replace longer strings first)
    for var, val in sorted(resolved_inputs.items(), key=lambda x: -len(str(x[1]))):
        val_str = str(val)
        if val_str and val_str in result:
            result = result.replace(val_str, f"{{{{{var}}}}}")
    return result


def _infer_extracts(command: str) -> Optional[str]:
    """
    Given a command, infer what variable name it extracts for subsequent steps.
    Returns the variable name or None.
    """
    cmd = command.strip().lower()
    cmd = re.sub(r'^(sudo\s+-S[^\s]*\s+|sudo\s+)', '', cmd)

    if re.match(r'df\b', cmd):
        return "mount_point"
    if re.match(r'du\b', cmd):
        return "largest_dir"
    if re.search(r'find\b.*-size', cmd):
        return "large_files"
    if re.search(r'systemctl\b.*failed', cmd):
        return "service_name"
    if re.match(r'ps\b.*aux', cmd):
        return "top_process"
    if re.match(r'hostname\b', cmd):
        return "hostname"
    if re.match(r'free\b', cmd):
        return "available_memory"
    return None


def _infer_smart_defaults(command: str) -> Dict[str, Any]:
    """
    Given a command, infer what smart defaults it uses for {{variables}}.
    Returns a dict of variable_name → default_value.
    """
    from app.services.execution.output_extractor import _SMART_DEFAULTS, _SMART_DEFAULT_PATTERNS
    defaults = {}
    for var in re.findall(r'\{\{(\w+)\}\}', command):
        if var in _SMART_DEFAULTS:
            defaults[var] = _SMART_DEFAULTS[var]
        else:
            for pattern, default in _SMART_DEFAULT_PATTERNS:
                if re.match(pattern, var):
                    defaults[var] = default
                    break
    return defaults


# ─────────────────────────────────────────────────────────────────────────────
# Crystalliser
# ─────────────────────────────────────────────────────────────────────────────

class RunbookCrystalliser:
    """
    Converts a successful agent execution trace into a stored runbook.
    """

    async def crystallise(
        self,
        db: Session,
        session: ExecutionSession,
        weed_step_numbers: List[int],
        runbook_title: str,
        tenant_id: int,
        created_by_user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Build and store the runbook from the agent's execution trace.

        Args:
            db:                  DB session
            session:             The completed agent ExecutionSession
            weed_step_numbers:   Step numbers the human marked as weeds (excluded)
            runbook_title:       Title for the new runbook
            tenant_id:           Tenant to store it under
            created_by_user_id:  Optional user who triggered the crystallisation

        Returns:
            { "runbook_id": int, "runbook_title": str, "steps_included": int,
              "steps_excluded": int }
        """
        # Load all steps
        steps: List[ExecutionStep] = (
            db.query(ExecutionStep)
            .filter(ExecutionStep.session_id == session.id)
            .order_by(ExecutionStep.step_number)
            .all()
        )

        session_meta = session.meta_data or {}
        resolved_inputs: Dict[str, str] = session_meta.get("resolved_inputs") or {}
        agent_summary: str = session_meta.get("agent_summary") or ""

        # Filter: keep only successful, non-weed steps
        kept_steps = []
        excluded = 0
        for step in steps:
            payload = step.command_payload or {}
            is_weed = (
                step.step_number in weed_step_numbers
                or payload.get("weed") is True
            )
            if is_weed or not step.success:
                excluded += 1
                logger.info(
                    "Crystalliser: excluding step %d (%s)",
                    step.step_number,
                    "weed" if is_weed else "failed",
                )
                continue
            kept_steps.append(step)

        if not kept_steps:
            raise ValueError(
                "No successful non-weed steps to crystallise into a runbook."
            )

        # Build the runbook YAML structure
        runbook_steps = []
        inputs_needed: Dict[str, Any] = {}

        for step in kept_steps:
            raw_command = step.command or ""

            # De-parameterise: replace concrete values back to {{variables}}
            templ_command = _deparameterise(raw_command, resolved_inputs)

            # Collect any {{variables}} in the template command as declared inputs
            for var in re.findall(r'\{\{(\w+)\}\}', templ_command):
                if var not in inputs_needed:
                    defaults = _infer_smart_defaults(templ_command)
                    inputs_needed[var] = {
                        "name": var,
                        "required": var not in defaults,
                        "default": defaults.get(var),
                        "description": f"Resolved from system during initial execution",
                    }

            step_entry: Dict[str, Any] = {
                "name": (step.command_payload or {}).get("reasoning") or f"Step {step.step_number}",
                "command": templ_command,
            }

            # Document extraction metadata (how does this step feed later steps)
            extracts = _infer_extracts(raw_command)
            if extracts:
                step_entry["extracts"] = extracts

            # Smart defaults used
            smart = _infer_smart_defaults(templ_command)
            if smart:
                step_entry["default_inputs"] = smart

            # Mark state-changing steps as requiring approval
            from app.services.execution.command_classifier import get_command_classifier
            clf = get_command_classifier()
            classification = clf.classify(raw_command)
            if classification.level >= 3:
                step_entry["requires_approval"] = True
            elif classification.level == 2:
                step_entry["caution"] = classification.reason

            runbook_steps.append(step_entry)

        # Determine service type and OS from session metadata
        ticket_info = {}
        if session.ticket_id:
            from app.models.ticket import Ticket
            ticket = db.query(Ticket).filter(Ticket.id == session.ticket_id).first()
            if ticket:
                ticket_info = {
                    "service": ticket.service or "general",
                    "os_type": (ticket.meta_data or {}).get("os_type") or "linux",
                    "issue_type": (ticket.meta_data or {}).get("issue_type") or "general",
                }

        # Build full runbook spec
        runbook_spec = {
            "title": runbook_title,
            "description": (
                f"Auto-generated from successful agent execution. "
                f"Original issue: {agent_summary or 'See session metadata.'}"
            ),
            "service": ticket_info.get("service", "general"),
            "os_type": ticket_info.get("os_type", "linux"),
            "issue_type": ticket_info.get("issue_type", "general"),
            "source": "agent_crystallised",
            "crystallised_from_session": session.id,
            "crystallised_at": datetime.now(timezone.utc).isoformat(),
            "inputs": list(inputs_needed.values()),
            "prechecks": [],
            "steps": runbook_steps,
            "postchecks": [],
        }

        # Render to YAML
        runbook_yaml = yaml.dump(
            runbook_spec,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        runbook_body = f"```yaml\n{runbook_yaml}\n```"

        # Store via RunbookRepository
        from app.repositories.runbook_repository import RunbookRepository
        repo = RunbookRepository(db)
        runbook = repo.create(
            tenant_id=tenant_id,
            title=runbook_title,
            body_md=runbook_body,
            service=ticket_info.get("service", "general"),
            issue_type=ticket_info.get("issue_type", "general"),
            os_type=ticket_info.get("os_type", "linux"),
            meta_data={
                "source": "agent_crystallised",
                "session_id": session.id,
                "agent_summary": agent_summary,
                "approved": True,   # proven by real execution
                "created_by_user_id": created_by_user_id,
            },
        )

        # Mark session as crystallised
        from sqlalchemy.orm.attributes import flag_modified
        session.meta_data["crystallised"] = True
        session.meta_data["crystallised_runbook_id"] = runbook.id
        flag_modified(session, "meta_data")
        db.commit()

        logger.info(
            "Crystallised runbook id=%d '%s' from session %d (%d steps, %d excluded)",
            runbook.id, runbook_title, session.id, len(kept_steps), excluded,
        )

        return {
            "runbook_id": runbook.id,
            "runbook_title": runbook_title,
            "steps_included": len(kept_steps),
            "steps_excluded": excluded,
        }


# Singleton
_crystalliser: Optional[RunbookCrystalliser] = None


def get_runbook_crystalliser() -> RunbookCrystalliser:
    global _crystalliser
    if _crystalliser is None:
        _crystalliser = RunbookCrystalliser()
    return _crystalliser
