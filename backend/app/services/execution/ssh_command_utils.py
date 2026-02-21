"""
SSH command utilities for on-prem execution.
When using SSH connector, the connector connects to target_host from connection_config.
Runbook commands should be the raw shell command - no 'ssh host "..."' wrapper.
"""


def strip_ssh_wrapper(command: str) -> str:
    """
    If command is 'ssh host "cmd"', return just 'cmd'.
    Connector handles connection; avoids double-SSH and quoting issues.
    """
    if not command or not command.strip():
        return command
    c = command.strip()
    if not c.lower().startswith("ssh "):
        return command
    first_quote = c.find('"')
    if first_quote < 0:
        return command
    last_quote = c.rfind('"')
    if last_quote <= first_quote:
        return command
    inner = c[first_quote + 1 : last_quote].replace('\\"', '"').strip()
    return inner if inner else command
