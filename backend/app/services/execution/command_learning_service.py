"""
Command Learning Service - DB-driven command correction without hardcoded rules.
Saves execution failures to ExecutionCommandLearning and retrieves similar past fixes
for correction. Used with Perplexity for unknown patterns.
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.execution_command_learning import ExecutionCommandLearning
from app.core.logging import get_logger

logger = get_logger(__name__)


def _detect_os_from_connector(connector_type: str) -> str:
    """Detect os_type from connector (windows or linux)."""
    if connector_type in ("azure_bastion", "local", "winrm"):
        return "windows"
    elif connector_type in ("ssh", "gcp_iap"):
        return "linux"
    return "windows"


class CommandLearningService:
    """Saves failures and retrieves similar past fixes from DB."""

    def save_failure(
        self,
        db: Session,
        tenant_id: int,
        command: str,
        error_text: str,
        output_text: Optional[str] = None,
        connector_type: str = "local",
        session_id: Optional[int] = None,
        runbook_id: Optional[int] = None,
        step_number: Optional[int] = None,
        step_type: Optional[str] = None,
        connection_config: Optional[Dict[str, Any]] = None,
        issue_description: Optional[str] = None,
    ) -> Optional[int]:
        """
        Save a command failure to ExecutionCommandLearning for later refinement.
        Returns the learning record id if saved, None on error.
        """
        if not command or not command.strip():
            return None
        try:
            os_type = _detect_os_from_connector(connector_type)
            rec = ExecutionCommandLearning(
                tenant_id=tenant_id,
                session_id=session_id,
                runbook_id=runbook_id,
                step_number=step_number,
                step_type=step_type,
                command=(command or "").strip()[:2000],
                error_text=(error_text or "")[:4000] if error_text else None,
                output_text=(output_text or "")[:4000] if output_text else None,
                connector_type=connector_type,
                os_type=os_type,
                connection_config=connection_config,
                issue_description=(issue_description or "")[:2000] if issue_description else None,
            )
            db.add(rec)
            db.flush()
            learning_id = rec.id
            logger.info(
                f"Saved command failure to learning (id={learning_id}): "
                f"connector={connector_type}, os={os_type}"
            )
            return learning_id
        except Exception as e:
            logger.warning(f"Failed to save command failure to learning: {e}")
            return None

    def update_with_fix(
        self,
        db: Session,
        learning_id: int,
        fix_applied: str,
        fix_source: str,
        success_after_fix: bool,
    ) -> bool:
        """Update a learning record with the fix that was applied."""
        try:
            rec = db.query(ExecutionCommandLearning).filter(
                ExecutionCommandLearning.id == learning_id
            ).first()
            if not rec:
                logger.warning(f"Learning record {learning_id} not found for update")
                return False
            rec.fix_applied = (fix_applied or "")[:2000]
            rec.fix_source = (fix_source or "unknown")[:32]
            rec.success_after_fix = success_after_fix
            db.flush()
            logger.info(
                f"Updated learning {learning_id}: fix_source={fix_source}, "
                f"success_after_fix={success_after_fix}"
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to update learning {learning_id}: {e}")
            return False

    def find_similar_fix(
        self,
        db: Session,
        tenant_id: int,
        command: str,
        error_text: str,
        connector_type: str,
        limit: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """
        Find a similar past fix from DB. Prefer records with success_after_fix=True.
        Match by: same connector, same os, similar command (substring), similar error.
        Returns best match dict with fix_applied, fix_source, success_after_fix.
        """
        if not command or not command.strip():
            return None
        os_type = _detect_os_from_connector(connector_type)
        cmd_lower = (command or "").strip().lower()[:200]
        err_lower = (error_text or "").strip().lower()[:300]
        if not cmd_lower:
            return None
        try:
            # Get command base (first word or first 50 chars) for similarity
            cmd_base = cmd_lower.split()[0] if cmd_lower.split() else cmd_lower[:50]
            q = (
                db.query(ExecutionCommandLearning)
                .filter(
                    ExecutionCommandLearning.tenant_id == tenant_id,
                    ExecutionCommandLearning.connector_type == connector_type,
                    ExecutionCommandLearning.os_type == os_type,
                    ExecutionCommandLearning.fix_applied.isnot(None),
                    ExecutionCommandLearning.fix_applied != "",
                )
            )
            candidates = q.order_by(
                ExecutionCommandLearning.success_after_fix.desc().nullslast(),
                ExecutionCommandLearning.created_at.desc(),
            ).limit(limit * 2).all()
            best = None
            best_score = 0
            for rec in candidates:
                if not rec.fix_applied:
                    continue
                score = 0
                # Prefer success_after_fix
                if rec.success_after_fix:
                    score += 10
                # Command similarity: base command matches
                rec_cmd = (rec.command or "").lower()
                if cmd_base in rec_cmd or (rec_cmd.split()[0] == cmd_base if rec_cmd.split() else False):
                    score += 5
                if cmd_lower in rec_cmd or rec_cmd in cmd_lower:
                    score += 3
                # Error similarity
                rec_err = (rec.error_text or "").lower()
                if err_lower and rec_err:
                    err_words = set(err_lower.split())
                    rec_err_words = set(rec_err.split())
                    overlap = len(err_words & rec_err_words) / max(1, len(err_words))
                    score += int(overlap * 5)
                if score > best_score and score >= 5:
                    best_score = score
                    best = {
                        "fix_applied": rec.fix_applied,
                        "fix_source": rec.fix_source or "db_learning",
                        "success_after_fix": rec.success_after_fix or False,
                        "learning_id": rec.id,
                    }
            return best
        except Exception as e:
            logger.warning(f"Failed to find similar fix: {e}")
            return None

    def save_success(
        self,
        db: Session,
        tenant_id: int,
        command: str,
        output_text: Optional[str] = None,
        connector_type: str = "local",
        session_id: Optional[int] = None,
        runbook_id: Optional[int] = None,
        step_number: Optional[int] = None,
        step_type: Optional[str] = None,
        issue_description: Optional[str] = None,
    ) -> Optional[int]:
        """
        Save a successful remediation command to the learning store.
        Reuses ExecutionCommandLearning table: fix_applied=command, success_after_fix=True.
        These are later surfaced as known-good commands during runbook generation context building.
        """
        if not command or not command.strip():
            return None
        try:
            os_type = _detect_os_from_connector(connector_type)
            rec = ExecutionCommandLearning(
                tenant_id=tenant_id,
                session_id=session_id,
                runbook_id=runbook_id,
                step_number=step_number,
                step_type=step_type,
                command=(command or "").strip()[:2000],
                error_text=None,  # No error — this was a success
                output_text=(output_text or "")[:4000] if output_text else None,
                connector_type=connector_type,
                os_type=os_type,
                fix_applied=(command or "").strip()[:2000],  # Command itself is the proven fix
                fix_source="execution_success",
                success_after_fix=True,
                issue_description=(issue_description or "")[:2000] if issue_description else None,
            )
            db.add(rec)
            db.flush()
            learning_id = rec.id
            logger.info(
                f"Saved successful command to learning (id={learning_id}): "
                f"connector={connector_type}, os={os_type}, cmd={command[:60]}"
            )
            return learning_id
        except Exception as e:
            logger.warning(f"Failed to save command success to learning: {e}")
            return None

    def _keyword_overlap_score(self, issue_description: str, record_description: str) -> float:
        """Calculate keyword overlap score between two issue descriptions."""
        issue_words = set(issue_description.lower().split())
        rec_words = set((record_description or "").lower().split())
        return len(issue_words & rec_words) / max(1, len(issue_words))

    def get_known_good_commands(
        self,
        db: Session,
        tenant_id: int,
        issue_description: str,
        os_type: Optional[str] = None,
        limit: int = 8,
    ) -> list:
        """
        Retrieve commands known to work for similar issues.
        Used to build KAG context for runbook generation.
        Returns list of dicts: {command, issue_description, os_type}
        """
        if not issue_description:
            return []
        try:
            q = (
                db.query(ExecutionCommandLearning)
                .filter(
                    ExecutionCommandLearning.tenant_id == tenant_id,
                    ExecutionCommandLearning.success_after_fix == True,
                    ExecutionCommandLearning.fix_source == "execution_success",
                    ExecutionCommandLearning.command.isnot(None),
                )
            )
            if os_type:
                q = q.filter(ExecutionCommandLearning.os_type == os_type.lower())

            candidates = q.order_by(
                ExecutionCommandLearning.created_at.desc()
            ).limit(limit * 4).all()

            # Score by keyword overlap with issue_description
            scored = []
            for rec in candidates:
                overlap = self._keyword_overlap_score(issue_description, rec.issue_description or "")
                if overlap > 0 or not rec.issue_description:
                    scored.append((overlap, rec))

            scored.sort(key=lambda x: x[0], reverse=True)
            results = []
            seen_commands = set()
            for _, rec in scored[:limit]:
                cmd = (rec.command or "").strip()
                if cmd and cmd not in seen_commands:
                    seen_commands.add(cmd)
                    results.append({
                        "command": cmd,
                        "issue_description": rec.issue_description or "",
                        "os_type": rec.os_type or "",
                    })
            return results
        except Exception as e:
            logger.warning(f"Failed to get known good commands: {e}")
            return []

    def get_known_bad_commands(
        self,
        db: Session,
        tenant_id: int,
        issue_description: str,
        os_type: Optional[str] = None,
        limit: int = 5,
    ) -> list:
        """
        Retrieve commands known to fail for similar issues (no successful fix found).
        Used to build KAG context to steer LLM away from broken commands.
        Returns list of dicts: {command, error_text, issue_description}
        """
        if not issue_description:
            return []
        try:
            q = (
                db.query(ExecutionCommandLearning)
                .filter(
                    ExecutionCommandLearning.tenant_id == tenant_id,
                    ExecutionCommandLearning.error_text.isnot(None),
                    ExecutionCommandLearning.success_after_fix.isnot(True),
                    ExecutionCommandLearning.command.isnot(None),
                )
            )
            if os_type:
                q = q.filter(ExecutionCommandLearning.os_type == os_type.lower())

            candidates = q.order_by(
                ExecutionCommandLearning.created_at.desc()
            ).limit(limit * 4).all()

            scored = []
            for rec in candidates:
                overlap = self._keyword_overlap_score(issue_description, rec.issue_description or "")
                scored.append((overlap, rec))

            scored.sort(key=lambda x: x[0], reverse=True)
            results = []
            seen_commands = set()
            for _, rec in scored[:limit]:
                cmd = (rec.command or "").strip()
                if cmd and cmd not in seen_commands:
                    seen_commands.add(cmd)
                    results.append({
                        "command": cmd,
                        "error_text": (rec.error_text or "")[:200],
                        "issue_description": rec.issue_description or "",
                    })
            return results
        except Exception as e:
            logger.warning(f"Failed to get known bad commands: {e}")
            return []
