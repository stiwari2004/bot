"""
Runbook Crystalliser — converts a proven execution trace into a reusable runbook.

Called after the human reviews the agent session, marks weeds, and clicks
"Save as Runbook".  Produces a YAML runbook that:

  1. Contains only successful non-weed execute-phase steps
  2. Generalises device-specific values back into {{variable}} placeholders
     so the runbook is reusable across any server with the same issue
  3. Documents what each placeholder means and its smart default
  4. Stores the runbook via RunbookRepository

Generalisation strategy (two passes):
  Pass 1 — Path/value deparameterisation:
    Re-runs all output parsers on the full step trace (diagnose + execute)
    to rediscover concrete values (mount points, largest dirs, service names,
    etc.) and replace them with {{variable}} tokens.
  Pass 2 — Pattern deparameterisation:
    Replaces hard-coded numeric/size literals in commands with {{variable}}
    tokens (e.g. "--vacuum-size=500M" → "--vacuum-size={{vacuum_size}}").
"""
import re
import yaml
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, ExecutionStep

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Pass 1 — rediscover concrete values from step outputs
# ─────────────────────────────────────────────────────────────────────────────

def _build_discovered_inputs(all_steps: List[ExecutionStep]) -> Dict[str, str]:
    """
    Re-run every output parser on the full step trace to recover the
    concrete values the agent discovered, regardless of whether {{variables}}
    were used during execution.  Diagnose steps are included because they
    often produce the values used by later execute steps.
    """
    from app.services.execution.output_extractor import (
        _detect_command_type,
        _parse_df, _parse_du, _parse_find_large_files,
        _parse_systemctl_failed, _parse_ps_top_cpu,
        _parse_free_memory, _parse_netstat_ports, _parse_hostname,
    )

    parsers = {
        "df":               _parse_df,
        "du":               _parse_du,
        "find_large":       _parse_find_large_files,
        "systemctl_failed": _parse_systemctl_failed,
        "ps_top_cpu":       _parse_ps_top_cpu,
        "hostname":         _parse_hostname,
        "free_memory":      _parse_free_memory,
        "netstat":          _parse_netstat_ports,
    }

    discovered: Dict[str, str] = {}
    for step in all_steps:
        if not step.output or not step.command:
            continue
        cmd_type = _detect_command_type(step.command)
        parser = parsers.get(cmd_type or "")
        if parser:
            extracted = parser(step.output)
            discovered.update(extracted)
            if extracted:
                logger.debug(
                    "Crystalliser: discovered from step %d (%s) → %s",
                    step.step_number, cmd_type, list(extracted.keys()),
                )

    return discovered


def _deparameterise_values(command: str, discovered: Dict[str, str]) -> str:
    """
    Replace concrete discovered values with {{variable}} placeholders.
    Longest values substituted first to avoid partial-match bugs.
    """
    if not discovered:
        return command

    result = command
    for var, val in sorted(discovered.items(), key=lambda x: -len(str(x[1]))):
        val_str = str(val)
        if len(val_str) > 1 and not val_str.startswith("{{") and val_str in result:
            result = result.replace(val_str, f"{{{{{var}}}}}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Pass 2 — pattern-based deparameterisation for numeric/size literals
# ─────────────────────────────────────────────────────────────────────────────

# Each entry: (compiled_regex, replacement_template, var_name, default_value, description)
_PARAM_PATTERNS: List[Tuple[re.Pattern, str, str, str, str]] = [
    (
        re.compile(r'(--vacuum-size=)\d+[KMGTkmgt]?[Bb]?', re.IGNORECASE),
        r'\g<1>{{vacuum_size}}',
        'vacuum_size', '500M',
        'Max size for journalctl vacuum (e.g. 500M, 1G)',
    ),
    (
        re.compile(r'(--vacuum-time=)\d+\w+', re.IGNORECASE),
        r'\g<1>{{vacuum_time}}',
        'vacuum_time', '2weeks',
        'Max age for journalctl vacuum (e.g. 2weeks, 30days)',
    ),
    (
        re.compile(r'(-mtime\s+\+)\d+'),
        r'\g<1>{{retention_days}}',
        'retention_days', '30',
        'Age threshold in days for file cleanup',
    ),
    (
        re.compile(r'(-mtime\s+-)\d+'),
        r'\g<1>{{recent_days}}',
        'recent_days', '1',
        'Recency threshold in days',
    ),
    (
        re.compile(r'(-size\s+\+)\d+[kKmMgG]'),
        r'\g<1>{{min_file_size}}',
        'min_file_size', '100M',
        'Minimum file size to target (e.g. 100M, 1G)',
    ),
    (
        re.compile(r'(rotate\s+)\d+', re.IGNORECASE),
        r'\g<1>{{log_rotate_count}}',
        'log_rotate_count', '5',
        'Number of rotated log files to keep',
    ),
    (
        re.compile(r'(maxsize\s+)\d+[MmGg]', re.IGNORECASE),
        r'\g<1>{{max_log_size}}',
        'max_log_size', '100M',
        'Maximum log file size before rotation',
    ),
]


def _deparameterise_patterns(command: str) -> Tuple[str, Dict[str, Any]]:
    """
    Apply pattern-based deparameterisation for size/numeric literals.
    Returns (rewritten_command, {var_name: default_value}).
    """
    result = command
    new_inputs: Dict[str, Any] = {}
    for pattern, replacement, var_name, default, _desc in _PARAM_PATTERNS:
        if pattern.search(result):
            result = pattern.sub(replacement, result)
            new_inputs[var_name] = default
    return result, new_inputs


# ─────────────────────────────────────────────────────────────────────────────
# Discovery precheck templates
# ─────────────────────────────────────────────────────────────────────────────

# Each entry declares which {{variables}} it produces, the command to run,
# and the `extracts` hint consumed by the step execution engine.
# Order matters: mount_point must be discovered before largest_dir.
_DISCOVERY_PRECHECKS: List[Dict[str, Any]] = [
    {
        "vars":     {"mount_point", "disk_usage_pct"},
        "name":     "Identify the full filesystem",
        "command":  "df -h",
        "extracts": "mount_point",
    },
    {
        "vars":     {"largest_dir"},
        "name":     "Find the largest directory on the filesystem",
        "command":  "du -sh {{mount_point}}/* 2>/dev/null | sort -rh | head -10",
        "extracts": "largest_dir",
    },
    {
        "vars":     {"large_files", "largest_file"},
        "name":     "Find large files consuming disk space",
        "command":  "find {{mount_point}} -maxdepth 5 -size +100M -type f 2>/dev/null | head -20",
        "extracts": "large_files",
    },
    {
        "vars":     {"service_name"},
        "name":     "List failed system services",
        "command":  "systemctl list-units --state=failed --no-pager",
        "extracts": "service_name",
    },
    {
        "vars":     {"top_process", "top_pid"},
        "name":     "Identify top CPU-consuming process",
        "command":  "ps aux --sort=-%cpu | head -5",
        "extracts": "top_process",
    },
    {
        "vars":     {"available_memory"},
        "name":     "Check available memory",
        "command":  "free -h",
        "extracts": "available_memory",
    },
]


_DISK_VARS = {"mount_point", "disk_usage_pct", "largest_dir", "large_files", "largest_file"}

# Regex matching read-only / diagnostic commands that belong in postchecks,
# not in the remediation steps list.
_READ_ONLY_RE = re.compile(
    r'^(sudo\s+)?(df|du|free|ps\s+aux|top|uptime|systemctl\s+status|cat\s+/proc|'
    r'hostname|uname|iostat|vmstat|netstat|ss\s+-|lsof)\b',
    re.IGNORECASE,
)


def _is_read_only(command: str) -> bool:
    return bool(_READ_ONLY_RE.match(command.strip()))


def _step_name(payload: Dict[str, Any], command: str, step_number: int) -> str:
    """
    Derive a concise step name.  Uses the first sentence of the LLM's
    reasoning if it is short enough; otherwise falls back to the command verb.
    """
    reasoning = (payload.get("reasoning") or "").strip()
    # Take only the first sentence
    first = re.split(r'(?<=[.!?])\s', reasoning, maxsplit=1)[0].strip()
    # Accept it only if it is short and doesn't look like a meta-comment
    meta_keywords = ("system requested", "verification", "final read-only", "step 7")
    if first and len(first) <= 120 and not any(kw in first.lower() for kw in meta_keywords):
        return first
    # Fall back: derive from the command itself
    cmd = re.sub(r'^sudo\s+', '', command.strip())
    verb = cmd.split()[0] if cmd.split() else "step"
    return f"Run {verb} (step {step_number})"


def _build_discovery_prechecks(inputs_needed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Return the minimal ordered set of discovery prechecks needed to populate
    every {{variable}} referenced by the execute steps.

    Handles transitive dependencies: if largest_dir is needed its precheck
    uses {{mount_point}}, so df -h must also be added even if mount_point
    is not directly in inputs_needed.
    """
    var_names = set(inputs_needed.keys())

    # Expand: any disk-space variable implies mount_point must be discovered first
    if var_names & _DISK_VARS:
        var_names.add("mount_point")

    result = []
    for spec in _DISCOVERY_PRECHECKS:
        if spec["vars"] & var_names:
            result.append({
                "name":     spec["name"],
                "command":  spec["command"],
                "extracts": spec["extracts"],
            })
    return result


def _build_verification_postchecks(inputs_needed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Return postchecks that re-run the primary metric command to confirm
    the remediation worked.
    """
    postchecks = []
    if inputs_needed.keys() & _DISK_VARS:
        postchecks.append({
            "name":    "Verify disk space has been freed",
            "command": "df -h",
        })
    if "available_memory" in inputs_needed:
        postchecks.append({
            "name":    "Verify memory after remediation",
            "command": "free -h",
        })
    if "service_name" in inputs_needed:
        postchecks.append({
            "name":    "Verify service status after remediation",
            "command": "systemctl status {{service_name}}",
        })
    return postchecks


# ─────────────────────────────────────────────────────────────────────────────
# Helpers shared with other modules
# ─────────────────────────────────────────────────────────────────────────────

def _infer_extracts(command: str) -> Optional[str]:
    """Given a command, infer what variable it produces for downstream steps."""
    cmd = re.sub(r'^(sudo\s+)', '', command.strip().lower())
    if re.match(r'df\b', cmd):    return "mount_point"
    if re.match(r'du\b', cmd):    return "largest_dir"
    if re.search(r'find\b.*-size', cmd): return "large_files"
    if re.search(r'systemctl\b.*failed', cmd): return "service_name"
    if re.match(r'ps\b.*aux', cmd): return "top_process"
    if re.match(r'hostname\b', cmd): return "hostname"
    if re.match(r'free\b', cmd):  return "available_memory"
    return None


def _input_description(var: str) -> str:
    """Human-readable description for a known variable name."""
    descriptions = {
        "mount_point":       "Filesystem mount point with the highest disk usage",
        "largest_dir":       "Directory consuming the most space under mount_point",
        "large_files":       "Comma-separated paths of large files found",
        "largest_file":      "Single largest file path found",
        "service_name":      "Name of the failed or problematic service",
        "top_process":       "Name of the top CPU-consuming process",
        "top_pid":           "PID of the top CPU-consuming process",
        "hostname":          "Server hostname",
        "available_memory":  "Available memory reported by free -h",
        "disk_usage_pct":    "Current disk usage percentage",
        "vacuum_size":       "Max size for journalctl vacuum (e.g. 500M, 1G)",
        "vacuum_time":       "Max age for journalctl vacuum (e.g. 2weeks)",
        "retention_days":    "Age threshold in days for file cleanup",
        "min_file_size":     "Minimum file size to target (e.g. 100M)",
        "log_rotate_count":  "Number of rotated log files to keep",
        "max_log_size":      "Maximum log file size before rotation",
    }
    return descriptions.get(var, f"Value of {var} resolved at runtime")


def _smart_default(var: str) -> Optional[str]:
    """Safe default value for a known variable."""
    from app.services.execution.output_extractor import _SMART_DEFAULTS, _SMART_DEFAULT_PATTERNS
    if var in _SMART_DEFAULTS:
        return _SMART_DEFAULTS[var]
    for pattern, default in _SMART_DEFAULT_PATTERNS:
        if re.match(pattern, var):
            return default
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Crystalliser
# ─────────────────────────────────────────────────────────────────────────────

class RunbookCrystalliser:
    """
    Converts a successful agent execution trace into a stored, generalised runbook.
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
        # ── Load all steps (diagnose + execute) ───────────────────────────────
        all_steps: List[ExecutionStep] = (
            db.query(ExecutionStep)
            .filter(ExecutionStep.session_id == session.id)
            .order_by(ExecutionStep.step_number)
            .all()
        )

        session_meta = session.meta_data or {}
        agent_summary: str = session_meta.get("agent_summary") or ""

        # ── Rediscover concrete values from the full trace ────────────────────
        # Use ALL steps (including diagnose weeds) — diagnosis often produces
        # the values (mount points, dirs) referenced by execute steps.
        discovered = _build_discovered_inputs(all_steps)

        # Merge with anything tracked during execution (may be empty)
        tracked = session_meta.get("resolved_inputs") or {}
        discovered.update(tracked)

        logger.info(
            "Crystalliser: discovered inputs from session %d: %s",
            session.id, list(discovered.keys()),
        )

        # ── Select steps to keep ──────────────────────────────────────────────
        kept_steps = []
        excluded = 0
        for step in all_steps:
            payload = step.command_payload or {}
            is_weed = step.step_number in weed_step_numbers or payload.get("weed") is True
            is_diagnose = payload.get("phase") == "diagnose"

            if is_weed or is_diagnose or not step.success:
                excluded += 1
                logger.info(
                    "Crystalliser: excluding step %d (%s)",
                    step.step_number,
                    "weed" if is_weed else "diagnose" if is_diagnose else "failed",
                )
                continue
            kept_steps.append(step)

        if not kept_steps:
            raise ValueError("No successful execute-phase steps to crystallise into a runbook.")

        # ── Build generalised runbook steps ───────────────────────────────────
        runbook_steps = []
        inputs_needed: Dict[str, Any] = {}
        seen_commands: set = set()  # for deduplication

        from app.services.execution.command_classifier import get_command_classifier
        clf = get_command_classifier()

        for step in kept_steps:
            payload = step.command_payload or {}
            raw_command = step.command or ""

            # Pass 1: replace discovered concrete values with {{variables}}
            templ_command = _deparameterise_values(raw_command, discovered)

            # Pass 2: replace hard-coded numeric/size literals
            templ_command, pattern_inputs = _deparameterise_patterns(templ_command)

            # Skip pure read-only / diagnostic commands — they belong in
            # postchecks, not in the remediation steps list.
            if _is_read_only(templ_command):
                logger.debug(
                    "Crystalliser: skipping read-only step %d (%s) — will appear in postchecks",
                    step.step_number, templ_command[:60],
                )
                continue

            # Deduplicate: if the same command has already been added, skip it.
            if templ_command in seen_commands:
                logger.debug(
                    "Crystalliser: deduplicating step %d (command already in runbook)",
                    step.step_number,
                )
                continue
            seen_commands.add(templ_command)

            # Collect declared inputs from all {{variables}} present
            for var in re.findall(r'\{\{(\w+)\}\}', templ_command):
                if var not in inputs_needed:
                    default = _smart_default(var) or pattern_inputs.get(var)
                    inputs_needed[var] = {
                        "name":        var,
                        "required":    default is None,
                        "default":     default,
                        "description": _input_description(var),
                    }

            step_entry: Dict[str, Any] = {
                "name":    _step_name(payload, templ_command, step.step_number),
                "command": templ_command,
            }

            extracts = _infer_extracts(raw_command)
            if extracts:
                step_entry["extracts"] = extracts

            classification = clf.classify(raw_command)
            if classification.level >= 3:
                step_entry["requires_approval"] = True
            elif classification.level == 2:
                step_entry["caution"] = classification.reason

            runbook_steps.append(step_entry)

        if not runbook_steps:
            raise ValueError(
                "No remediation steps remain after filtering read-only and duplicate commands."
            )

        # ── Ticket metadata ───────────────────────────────────────────────────
        ticket_info: Dict[str, str] = {}
        if session.ticket_id:
            from app.models.ticket import Ticket
            ticket = db.query(Ticket).filter(Ticket.id == session.ticket_id).first()
            if ticket:
                ticket_info = {
                    "service":    ticket.service or "general",
                    "os_type":    (ticket.meta_data or {}).get("os_type") or "linux",
                    "issue_type": (ticket.meta_data or {}).get("issue_type") or "general",
                }

        # ── Build discovery prechecks & verification postchecks ──────────────
        # Prechecks run on the new server BEFORE the remediation steps,
        # discovering real values (mount_point, largest_dir, etc.) so that
        # every {{variable}} in the execute steps gets substituted with the
        # actual path/value for that server — not the original server's values.
        discovery_prechecks = _build_discovery_prechecks(inputs_needed)
        verification_postchecks = _build_verification_postchecks(inputs_needed)

        logger.info(
            "Crystalliser: adding %d discovery prechecks, %d verification postchecks",
            len(discovery_prechecks), len(verification_postchecks),
        )

        # ── Assemble runbook spec ─────────────────────────────────────────────
        runbook_spec = {
            "title":       runbook_title,
            "description": (
                f"Auto-generated from successful agent execution. "
                f"Original issue: {agent_summary or 'See session metadata.'}"
            ),
            "service":    ticket_info.get("service", "general"),
            "os_type":    ticket_info.get("os_type", "linux"),
            "issue_type": ticket_info.get("issue_type", "general"),
            "source":     "agent_crystallised",
            "crystallised_from_session": session.id,
            "crystallised_at": datetime.now(timezone.utc).isoformat(),
            "inputs":     list(inputs_needed.values()),
            "prechecks":  discovery_prechecks,
            "steps":      runbook_steps,
            "postchecks": verification_postchecks,
        }

        runbook_body = "```yaml\n" + yaml.dump(
            runbook_spec,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        ) + "```"

        # ── Persist ───────────────────────────────────────────────────────────
        import json as _json
        from app.repositories.runbook_repository import RunbookRepository
        from sqlalchemy.orm.attributes import flag_modified

        repo = RunbookRepository(db)
        runbook = repo.create(
            tenant_id=tenant_id,
            title=runbook_title,
            body_md=runbook_body,
            status="approved",
            meta_data=_json.dumps({
                "source":              "agent_crystallised",
                "session_id":          session.id,
                "agent_summary":       agent_summary,
                "approved":            True,
                "created_by_user_id":  created_by_user_id,
                "service":             ticket_info.get("service", "general"),
                "issue_type":          ticket_info.get("issue_type", "general"),
                "os_type":             ticket_info.get("os_type", "linux"),
                "discovered_inputs":   discovered,
            }),
        )

        session.meta_data["crystallised"] = True
        session.meta_data["crystallised_runbook_id"] = runbook.id
        flag_modified(session, "meta_data")
        db.commit()

        logger.info(
            "Crystallised runbook id=%d '%s' from session %d "
            "(%d steps kept, %d excluded, %d inputs generalised)",
            runbook.id, runbook_title, session.id,
            len(kept_steps), excluded, len(inputs_needed),
        )

        return {
            "runbook_id":       runbook.id,
            "runbook_title":    runbook_title,
            "steps_included":   len(kept_steps),
            "steps_excluded":   excluded,
            "inputs_declared":  len(inputs_needed),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_crystalliser: Optional[RunbookCrystalliser] = None


def get_runbook_crystalliser() -> RunbookCrystalliser:
    global _crystalliser
    if _crystalliser is None:
        _crystalliser = RunbookCrystalliser()
    return _crystalliser
