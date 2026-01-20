from app.services.runbook.generation.runbook_quality_validator import RunbookQualityValidator


def _base_spec():
    """Create a fully valid runbook spec skeleton for testing."""
    return {
        "runbook_id": "rb-server-cpu",
        "version": "1.0.0",
        "title": "Fix CPU running hot",
        "service": "server",
        "env": "prod",
        "risk": "low",
        "description": "CPU utilization is high on the server.",
        "inputs": [
            {
                "name": "server_name",
                "type": "string",
                "required": True,
                "description": "Target server hostname",
            }
        ],
        "prechecks": [
            {
                "description": "Check CPU usage",
                "command": "Get-Counter -Counter '\\Processor(_Total)\\% Processor Time'",
                "expected_output": "CPU usage percent",
            },
            {
                "description": "Ping server",
                "command": "ping {{server_name}} -n 2",
                "expected_output": "Ping success",
            },
            {
                "description": "Check top processes",
                "command": "Get-Process | Sort-Object CPU -Descending | Select-Object -First 5",
                "expected_output": "Top CPU processes",
            },
        ],
        "steps": [
            {
                "name": "Measure CPU again",
                "type": "command",
                "command": "Get-Counter -Counter '\\Processor(_Total)\\% Processor Time'",
                "expected_output": "Current CPU usage",
                "purpose": "diagnose",
                "requires_metric": "cpu",
            },
            {
                "name": "Capture top PID",
                "type": "command",
                "command": "Get-Process | Sort-Object CPU -Descending | Select-Object -First 1",
                "expected_output": "Top CPU process",
                "purpose": "diagnose",
                "captures_variable": "top_cpu_pid",
            },
            {
                "name": "Kill runaway process",
                "type": "command",
                "command": "Stop-Process -Id {{top_cpu_pid}} -Force",
                "expected_output": "Process terminated",
                "purpose": "remediate",
                "depends_on": ["top_cpu_pid"],
            },
            {
                "name": "Restart IIS",
                "type": "command",
                "command": "Restart-Service -Name w3svc -Force",
                "expected_output": "IIS restarted",
                "purpose": "remediate",
            },
            {
                "name": "Clear system cache",
                "type": "command",
                "command": "Clear-EventLog -LogName System -Confirm:$false",
                "expected_output": "Log cleared",
                "purpose": "remediate",
            },
            {
                "name": "Verify CPU normal",
                "type": "command",
                "command": "Get-Counter -Counter '\\Processor(_Total)\\% Processor Time'",
                "expected_output": "CPU reduced",
                "purpose": "verify",
            },
        ],
        "postchecks": [
            {
                "description": "Final CPU check",
                "command": "Get-Counter -Counter '\\Processor(_Total)\\% Processor Time'",
                "expected_output": "CPU < 70%",
            }
        ],
    }


def _validate(spec):
    validator = RunbookQualityValidator()
    return validator.validate(spec, "CPU running hot on Windows server")


def test_missing_purpose_is_invalid():
    spec = _base_spec()
    spec["steps"][1].pop("purpose")
    is_valid, errors = _validate(spec)
    assert not is_valid
    assert any("missing the 'purpose' field" in err for err in errors)


def test_dependency_on_unknown_variable_fails():
    spec = _base_spec()
    spec["steps"][3]["depends_on"] = ["unknown_var"]
    is_valid, errors = _validate(spec)
    assert not is_valid
    assert any("references dependency 'unknown_var'" in err for err in errors)


def test_requires_minimum_remediation_steps():
    spec = _base_spec()
    # Downgrade two remediation steps to diagnostic to force failure
    # Base spec has 3 remediation steps (indices 2, 3, 4)
    # Change two of them to "diagnose" to reduce to 1 remediation step
    spec["steps"][2]["purpose"] = "diagnose"  # "Kill runaway process" -> diagnose
    spec["steps"][3]["purpose"] = "diagnose"  # "Restart IIS" -> diagnose
    # Now we have only 1 remediation step (step[4] "Clear system cache")
    # MIN_REMEDIATION_STEPS is 2, so this should fail
    is_valid, errors = _validate(spec)
    assert not is_valid
    assert any("must include at least 2 REMEDIATION actions" in err for err in errors)


def test_valid_spec_passes():
    spec = _base_spec()
    is_valid, errors = _validate(spec)
    
    # Debug: print errors if validation fails
    if not is_valid:
        print(f"\nValidation failed with {len(errors)} errors:")
        for error in errors:
            print(f"  - {error}")
    
    assert is_valid, f"Validation failed with errors: {errors}"
    assert errors == []

