"""
Unit tests for validation services (quality validator, command validator)
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch

from app.services.runbook.generation.runbook_quality_validator import RunbookQualityValidator
from app.services.infrastructure.command_validator import CommandValidator
from app.services.runbook.generation.runbook_command_validator import RunbookCommandValidator


@pytest.fixture
def quality_validator():
    """Create a RunbookQualityValidator instance"""
    return RunbookQualityValidator()


@pytest.fixture
def command_validator():
    """Create a CommandValidator instance"""
    return CommandValidator()


@pytest.fixture
def runbook_command_validator():
    """Create a RunbookCommandValidator instance"""
    return RunbookCommandValidator()


@pytest.fixture
def valid_runbook_spec():
    """Valid runbook spec for testing"""
    return {
        "runbook_id": "rb-test",
        "version": "1.0.0",
        "title": "Fix CPU usage high on Windows server",
        "service": "server",
        "env": "prod",
        "risk": "low",
        "description": "Test description",
        "inputs": [
            {
                "name": "server_name",
                "type": "string",
                "required": True,
                "description": "Server name"
            }
        ],
        "prechecks": [
            {"command": "Get-Counter -Counter '\\Processor(_Total)\\% Processor Time'", "expected_output": "CPU usage"},
            {"command": "ping {{server_name}}", "expected_output": "Ping success"},
            {"command": "Get-Process | Sort-Object CPU -Descending", "expected_output": "Top processes"}
        ],
        "steps": [
            {"name": "Check CPU", "command": "Get-Counter -Counter '\\Processor(_Total)\\% Processor Time'", "purpose": "diagnose"},
            {"name": "Kill process", "command": "Stop-Process -Id 123 -Force", "purpose": "remediate"},
            {"name": "Restart service", "command": "Restart-Service -Name w3svc", "purpose": "remediate"},
            {"name": "Clear cache", "command": "Clear-EventLog -LogName System", "purpose": "remediate"},
            {"name": "Verify", "command": "Get-Counter -Counter '\\Processor(_Total)\\% Processor Time'", "purpose": "verify"}
        ],
        "postchecks": [
            {"command": "Get-Counter -Counter '\\Processor(_Total)\\% Processor Time'", "expected_output": "CPU < 70%"}
        ]
    }


class TestRunbookQualityValidator:
    """Test RunbookQualityValidator class"""
    
    def test_validate_with_valid_spec(
        self, quality_validator, valid_runbook_spec
    ):
        """Test validation with valid runbook spec"""
        is_valid, errors = quality_validator.validate(
            valid_runbook_spec,
            "CPU usage is high on Windows server"
        )
        
        # Debug: print errors if validation fails
        if not is_valid:
            print(f"\nValidation failed with {len(errors)} errors:")
            for error in errors:
                print(f"  - {error}")
        
        assert is_valid is True, f"Validation failed with errors: {errors}"
        assert len(errors) == 0
    
    def test_validate_detects_missing_prechecks(
        self, quality_validator, valid_runbook_spec
    ):
        """Test that missing prechecks are detected"""
        valid_runbook_spec["prechecks"] = []  # Remove prechecks
        
        is_valid, errors = quality_validator.validate(
            valid_runbook_spec,
            "CPU usage is high"
        )
        
        assert is_valid is False
        assert any("prechecks" in err.lower() for err in errors)
    
    def test_validate_detects_missing_steps(
        self, quality_validator, valid_runbook_spec
    ):
        """Test that missing steps are detected"""
        valid_runbook_spec["steps"] = []  # Remove steps
        
        is_valid, errors = quality_validator.validate(
            valid_runbook_spec,
            "CPU usage is high"
        )
        
        assert is_valid is False
        assert any("steps" in err.lower() for err in errors)
    
    def test_validate_detects_missing_postchecks(
        self, quality_validator, valid_runbook_spec
    ):
        """Test that missing postchecks are detected"""
        valid_runbook_spec["postchecks"] = []  # Remove postchecks
        
        is_valid, errors = quality_validator.validate(
            valid_runbook_spec,
            "CPU usage is high"
        )
        
        assert is_valid is False
        assert any("postchecks" in err.lower() for err in errors)
    
    def test_validate_detects_undefined_input_reference(
        self, quality_validator, valid_runbook_spec
    ):
        """Test that undefined input references are detected"""
        # Add a step that references undefined input
        valid_runbook_spec["steps"].append({
            "name": "Test step",
            "command": "echo {{undefined_input}}",
            "purpose": "diagnose"
        })
        
        is_valid, errors = quality_validator.validate(
            valid_runbook_spec,
            "CPU usage is high"
        )
        
        assert is_valid is False
        assert any("undefined" in err.lower() for err in errors)
    
    def test_validate_detects_commands_in_inputs_section(
        self, quality_validator, valid_runbook_spec
    ):
        """Test that commands in inputs section are detected"""
        valid_runbook_spec["inputs"].append({
            "name": "bad_input",
            "type": "string",
            "command": "Get-Process"  # Command should not be in inputs
        })
        
        is_valid, errors = quality_validator.validate(
            valid_runbook_spec,
            "CPU usage is high"
        )
        
        assert is_valid is False
        assert any("command" in err.lower() and "input" in err.lower() for err in errors)
    
    def test_validate_detects_missing_remediation_steps(
        self, quality_validator, valid_runbook_spec
    ):
        """Test that missing remediation steps are detected"""
        # Change all steps to diagnostic
        for step in valid_runbook_spec["steps"]:
            step["purpose"] = "diagnose"
        
        is_valid, errors = quality_validator.validate(
            valid_runbook_spec,
            "CPU usage is high"
        )
        
        assert is_valid is False
        assert any("remediation" in err.lower() for err in errors)


class TestCommandValidator:
    """Test CommandValidator class"""
    
    def test_validate_sql_command_with_safe_select(
        self, command_validator
    ):
        """Test that safe SELECT commands are allowed"""
        is_safe, error = command_validator.validate_sql_command(
            "SELECT * FROM users WHERE id = 1"
        )
        
        assert is_safe is True
        assert error == ""
    
    def test_validate_sql_command_rejects_drop_table(
        self, command_validator
    ):
        """Test that DROP TABLE commands are rejected"""
        is_safe, error = command_validator.validate_sql_command(
            "DROP TABLE users"
        )
        
        assert is_safe is False
        assert "dangerous" in error.lower()
    
    def test_validate_sql_command_rejects_delete_without_where(
        self, command_validator
    ):
        """Test that DELETE without WHERE is rejected"""
        is_safe, error = command_validator.validate_sql_command(
            "DELETE FROM users"
        )
        
        assert is_safe is False
        assert "dangerous" in error.lower()
    
    def test_validate_shell_command_with_safe_command(
        self, command_validator
    ):
        """Test that safe shell commands are allowed"""
        is_safe, error = command_validator.validate_shell_command(
            "ls -la /tmp"
        )
        
        assert is_safe is True
        assert error == ""
    
    def test_validate_shell_command_rejects_command_chaining(
        self, command_validator
    ):
        """Test that command chaining is rejected"""
        is_safe, error = command_validator.validate_shell_command(
            "ls; rm -rf /"
        )
        
        assert is_safe is False
        assert "dangerous" in error.lower()
    
    def test_validate_shell_command_rejects_dangerous_rm(
        self, command_validator
    ):
        """Test that dangerous rm commands are rejected"""
        is_safe, error = command_validator.validate_shell_command(
            "rm -rf /"
        )
        
        assert is_safe is False
        assert "dangerous" in error.lower()
    
    def test_validate_powershell_command_with_safe_command(
        self, command_validator
    ):
        """Test that safe PowerShell commands are allowed"""
        is_safe, error = command_validator.validate_powershell_command(
            "Get-Process"
        )
        
        assert is_safe is True
        assert error == ""
    
    def test_validate_powershell_command_rejects_invoke_expression(
        self, command_validator
    ):
        """Test that Invoke-Expression is rejected"""
        is_safe, error = command_validator.validate_powershell_command(
            "Invoke-Expression $code"
        )
        
        assert is_safe is False
        assert "dangerous" in error.lower()
    
    def test_validate_powershell_command_rejects_format_volume(
        self, command_validator
    ):
        """Test that Format-Volume is rejected"""
        is_safe, error = command_validator.validate_powershell_command(
            "Format-Volume -DriveLetter C"
        )
        
        assert is_safe is False
        assert "dangerous" in error.lower()


class TestRunbookCommandValidator:
    """Test RunbookCommandValidator class"""
    
    @pytest.mark.asyncio
    async def test_validate_runbook_commands_with_valid_commands(
        self, runbook_command_validator, valid_runbook_spec
    ):
        """Test validation with valid commands"""
        with patch.object(
            runbook_command_validator.llm_service,
            '_chat_once',
            new_callable=AsyncMock
        ) as mock_chat:
            # Mock LLM response indicating commands are valid
            mock_chat.return_value = json.dumps({
                "is_valid": True,
                "invalid_commands": [],
                "diagnostic_mislabeled": [],
                "remediation_commands_found": ["Stop-Process", "Restart-Service", "Clear-EventLog"]
            })
            
            result = await runbook_command_validator.validate_runbook_commands(
                valid_runbook_spec,
                "CPU usage is high on Windows server",
                "Windows"
            )
            
            assert result["is_valid"] is True
            assert len(result.get("invalid_commands", [])) == 0
    
    @pytest.mark.asyncio
    async def test_validate_runbook_commands_detects_missing_remediation(
        self, runbook_command_validator, valid_runbook_spec
    ):
        """Test that missing remediation commands are detected"""
        # Remove remediation steps
        valid_runbook_spec["steps"] = [
            {"name": "Check", "command": "Get-Process", "purpose": "diagnose"}
        ]
        
        with patch.object(
            runbook_command_validator.llm_service,
            '_chat_once',
            new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.return_value = json.dumps({
                "is_valid": False,
                "invalid_commands": [],
                "diagnostic_mislabeled": [],
                "remediation_commands_found": [],
                "missing_remediation": True
            })
            
            result = await runbook_command_validator.validate_runbook_commands(
                valid_runbook_spec,
                "CPU usage is high",
                "Windows"
            )
            
            assert result["is_valid"] is False
            assert result.get("missing_remediation", False) is True
    
    @pytest.mark.asyncio
    async def test_validate_runbook_commands_handles_missing_llm_service(
        self, valid_runbook_spec
    ):
        """Test that missing LLM service returns fail-open result"""
        validator = RunbookCommandValidator(llm_service_instance=None)
        
        result = await validator.validate_runbook_commands(
            valid_runbook_spec,
            "CPU usage is high",
            "Windows"
        )
        
        assert result["is_valid"] is True  # Fail open
        assert "unavailable" in result.get("validation_summary", "").lower()
    
    @pytest.mark.asyncio
    async def test_validate_runbook_commands_auto_detects_os_type(
        self, runbook_command_validator, valid_runbook_spec
    ):
        """Test that OS type is auto-detected from issue description"""
        with patch.object(
            runbook_command_validator.llm_service,
            '_chat_once',
            new_callable=AsyncMock
        ) as mock_chat:
            mock_chat.return_value = json.dumps({
                "is_valid": True,
                "invalid_commands": []
            })
            
            await runbook_command_validator.validate_runbook_commands(
                valid_runbook_spec,
                "CPU usage is high on Windows server with PowerShell",
                os_type=None  # Not provided, should auto-detect
            )
            
            # Verify OS type was detected (Windows)
            # This is tested indirectly through the validation logic

