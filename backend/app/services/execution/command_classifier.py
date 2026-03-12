"""
Command classifier — safety gate for agentic and scripted execution.

Every command is classified before execution:

  Level 1 — SAFE        : read-only, auto-proceed
  Level 2 — CAUTION     : state-changing, show countdown + cancel window
  Level 3 — DESTRUCTIVE : irreversible, dry-run preview + explicit human approval
  Level 4 — BLOCKED     : never execute, alert immediately

Also derives the dry-run preview command for Level 3 so the human sees
exactly what would be affected before approving.
"""
import re
from dataclasses import dataclass, field
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ClassificationResult:
    level: int                        # 1 / 2 / 3 / 4
    label: str                        # SAFE / CAUTION / DESTRUCTIVE / BLOCKED
    reason: str                       # Human-readable explanation
    dry_run_command: Optional[str]    # For level 3: preview command to show human
    requires_approval: bool
    auto_proceed: bool
    countdown_seconds: int = 0        # For level 2: seconds before auto-proceed


# ─────────────────────────────────────────────────────────────────────────────
# Level 4 — BLOCKED patterns (check first, most important)
# ─────────────────────────────────────────────────────────────────────────────

_BLOCKED_PATTERNS = [
    # Wipe root filesystem
    (r'\brm\s+(-[^\s]*[rf][^\s]*\s+){0,3}/?(\s+|$)',
     "rm targeting root / is blocked"),
    (r'\brm\b.*\s+-[rf]*r[rf]*\s+/$',
     "recursive delete of / is blocked"),
    # dd wiping physical device
    (r'\bdd\b.+\bof=/dev/(sd|hd|vd|nvme|xvd|ssd)',
     "dd write to raw block device is blocked"),
    # chmod 777 on root
    (r'\bchmod\b.*-R.*777\s+/$',
     "chmod 777 on root is blocked"),
    # Touching credential/auth files
    (r'(/etc/(sudoers|passwd|shadow|group|gshadow|ssh/sshd_config))',
     "modification of auth/credential files is blocked"),
    (r'(authorized_keys|\.ssh/config)',
     "modification of SSH key files is blocked"),
    # Lateral SSH movement (ssh within a command that is already running on remote)
    (r';\s*ssh\s+|&&\s*ssh\s+|\|\s*ssh\s+',
     "lateral SSH from within a remote session is blocked"),
    # mkfs / disk format
    (r'\b(mkfs|fdisk|parted|wipefs|shred)\b',
     "disk formatting/wiping commands are blocked"),
    # iptables flush (could lock you out)
    (r'\biptables\s+-F\b|\biptables\s+--flush\b',
     "iptables flush is blocked — could break connectivity"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Level 3 — DESTRUCTIVE patterns + dry-run derivation
# ─────────────────────────────────────────────────────────────────────────────

_DESTRUCTIVE_PATTERNS = [
    (r'\brm\b',                          "rm deletes files permanently"),
    (r'\brmdir\b',                        "rmdir removes directories"),
    (r'\bfind\b.+\-delete\b',            "find -delete removes matched files"),
    (r'\bfind\b.+\-exec\s+rm\b',         "find -exec rm removes files"),
    (r'\btruncate\s+(-s\s+0|--size=0)\b',"truncate -s 0 wipes file content"),
    (r'>\s*/[a-zA-Z]',                   "output redirection overwrites a file"),
    (r'\bdd\b',                           "dd can overwrite data"),
    # SQL destructive
    (r'\b(DROP|DELETE\s+FROM|TRUNCATE\s+TABLE)\b',
     "destructive SQL operation"),
    # Package removal
    (r'\b(apt|yum|dnf|rpm)\b.+(remove|purge|erase)\b',
     "package removal"),
    # Kill -9
    (r'\bkill\s+-9\b|\bkill\s+-SIGKILL\b',
     "SIGKILL forcefully terminates a process"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Level 2 — CAUTION patterns
# ─────────────────────────────────────────────────────────────────────────────

_CAUTION_PATTERNS = [
    (r'\bsystemctl\s+(restart|stop|start|reload|disable|enable)\b',
     "systemctl modifies service state"),
    (r'\bservice\s+\w+\s+(restart|stop|start)\b',
     "service command modifies service state"),
    (r'\bkill\b',                                  "kill sends a signal to a process"),
    (r'\bjournalctl\s+--vacuum\b',                 "journalctl --vacuum removes old journal logs"),
    (r'\blogrotate\b',                              "logrotate rotates/compresses log files"),
    (r'\btruncate\b',                               "truncate reduces file size"),
    (r'\bsysctl\s+-w\b',                           "sysctl -w modifies kernel parameters"),
    (r'\b(apt|yum|dnf)\b.+(install|upgrade|update)\b',
     "package install/upgrade changes system state"),
    (r'\btimedatectl\b',                            "timedatectl changes system time"),
    (r'\buseradd\b|\busermod\b|\buserdel\b',        "user account modification"),
    (r'\bfirewall-cmd\b|\bufw\b',                   "firewall rule modification"),
    (r'\bnmcli\b|\bifconfig\b.*up\b|\bifconfig\b.*down\b',
     "network interface state change"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Dry-run derivation for Level 3
# ─────────────────────────────────────────────────────────────────────────────

def _derive_dry_run(command: str) -> Optional[str]:
    """
    Given a destructive command, derive a safe preview command that shows
    what WOULD be affected without making any changes.
    """
    cmd = command.strip()

    # find ... -delete  →  find ... (without -delete)
    preview = re.sub(r'\s+-delete\b', '', cmd)
    if preview != cmd:
        return preview.strip()

    # find ... -exec rm ... \;  →  find ... (without -exec rm part)
    preview = re.sub(r'\s+-exec\s+rm\b[^;]*;', '', cmd)
    if preview != cmd:
        return preview.strip()

    # rm FILE  →  ls -lah FILE
    m = re.match(r'^(?:sudo\s+)?rm\s+(-[^\s]+\s+)?(.+)$', cmd)
    if m:
        flags = m.group(1) or ""
        target = m.group(2)
        if "-r" in flags or "-R" in flags:
            return f"find {target} | head -50 && du -sh {target}"
        return f"ls -lah {target}"

    # truncate -s 0 FILE  →  ls -lh FILE
    m = re.match(r'^(?:sudo\s+)?truncate\s+(-s\s+0|--size=0)\s+(.+)$', cmd)
    if m:
        return f"ls -lh {m.group(2)}"

    # > FILE overwrite  →  show current file info
    m = re.search(r'>\s*(/[^\s|&;]+)', cmd)
    if m:
        return f"ls -lh {m.group(1)} && tail -5 {m.group(1)}"

    # SQL DROP/DELETE/TRUNCATE  →  SELECT equivalent
    if re.search(r'\bDROP\s+TABLE\s+(\w+)', cmd, re.IGNORECASE):
        tbl = re.search(r'\bDROP\s+TABLE\s+(\w+)', cmd, re.IGNORECASE).group(1)
        return f"SELECT COUNT(*) FROM {tbl};"
    if re.search(r'\bDELETE\s+FROM\s+(\w+)(.*)', cmd, re.IGNORECASE):
        m2 = re.search(r'\bDELETE\s+FROM\s+(\w+)(.*)', cmd, re.IGNORECASE)
        return f"SELECT COUNT(*) FROM {m2.group(1)}{m2.group(2)};"

    # dd  →  show source/destination info
    if re.match(r'^\s*dd\b', cmd):
        return "# dd dry-run: review source/destination carefully before approving"

    # Package removal
    m = re.match(r'^(?:sudo\s+)?(apt|yum|dnf|rpm)\b(.+)(remove|purge|erase)\s+(.+)$', cmd)
    if m:
        mgr = m.group(1)
        pkg = m.group(4)
        if mgr in ("apt", "apt-get"):
            return f"apt show {pkg} 2>/dev/null | head -10"
        return f"rpm -qi {pkg} 2>/dev/null | head -10"

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Public classifier
# ─────────────────────────────────────────────────────────────────────────────

class CommandClassifier:
    """Classifies shell commands by safety level before execution."""

    def classify(self, command: str) -> ClassificationResult:
        """
        Classify a command and return a ClassificationResult.
        Strips sudo / env prefixes for matching but preserves the original.
        """
        # Normalise for matching (lowercase, strip sudo prefix)
        normalised = command.strip()
        normalised = re.sub(
            r'^(echo\s+\S+\s+\|\s+sudo\s+-S[^\s]*\s+|sudo\s+-S\s+-p\s+\S+\s+|sudo\s+(-[^\s]+\s+)*)+',
            '', normalised, flags=re.IGNORECASE
        ).strip()
        check = normalised.lower()

        # ── Level 4: BLOCKED ─────────────────────────────────────────────────
        for pattern, reason in _BLOCKED_PATTERNS:
            if re.search(pattern, check, re.IGNORECASE):
                logger.warning("Command BLOCKED (level 4): %s | reason: %s", command[:80], reason)
                return ClassificationResult(
                    level=4,
                    label="BLOCKED",
                    reason=reason,
                    dry_run_command=None,
                    requires_approval=False,
                    auto_proceed=False,
                    countdown_seconds=0,
                )

        # ── Level 3: DESTRUCTIVE ─────────────────────────────────────────────
        for pattern, reason in _DESTRUCTIVE_PATTERNS:
            if re.search(pattern, check, re.IGNORECASE):
                dry_run = _derive_dry_run(normalised)
                logger.info("Command DESTRUCTIVE (level 3): %s | reason: %s", command[:80], reason)
                return ClassificationResult(
                    level=3,
                    label="DESTRUCTIVE",
                    reason=reason,
                    dry_run_command=dry_run,
                    requires_approval=True,
                    auto_proceed=False,
                    countdown_seconds=0,
                )

        # ── Level 2: CAUTION ─────────────────────────────────────────────────
        for pattern, reason in _CAUTION_PATTERNS:
            if re.search(pattern, check, re.IGNORECASE):
                logger.info("Command CAUTION (level 2): %s | reason: %s", command[:80], reason)
                return ClassificationResult(
                    level=2,
                    label="CAUTION",
                    reason=reason,
                    dry_run_command=None,
                    requires_approval=False,
                    auto_proceed=True,
                    countdown_seconds=10,
                )

        # ── Level 1: SAFE ────────────────────────────────────────────────────
        return ClassificationResult(
            level=1,
            label="SAFE",
            reason="Read-only or non-destructive command",
            dry_run_command=None,
            requires_approval=False,
            auto_proceed=True,
            countdown_seconds=0,
        )


# Singleton
_classifier: Optional[CommandClassifier] = None


def get_command_classifier() -> CommandClassifier:
    global _classifier
    if _classifier is None:
        _classifier = CommandClassifier()
    return _classifier
