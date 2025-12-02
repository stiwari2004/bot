"""
Unit tests for CommandValidator - Command injection protection
"""
import pytest
from app.services.infrastructure.command_validator import CommandValidator


@pytest.fixture
def validator():
    """Create a CommandValidator instance"""
    return CommandValidator()


class TestSQLCommandValidation:
    """Test SQL command validation"""
    
    def test_valid_sql_command(self, validator):
        """Test that valid SQL commands pass"""
        is_valid, _ = validator.validate_sql_command("SELECT * FROM users WHERE id = 1")
        assert is_valid is True
        is_valid, _ = validator.validate_sql_command("UPDATE users SET name = 'test' WHERE id = 1")
        assert is_valid is True
        is_valid, _ = validator.validate_sql_command("INSERT INTO users (name) VALUES ('test')")
        assert is_valid is True
    
    def test_sql_injection_detected(self, validator):
        """Test that SQL injection attempts are detected"""
        is_valid, _ = validator.validate_sql_command("SELECT * FROM users; DROP TABLE users;")
        assert is_valid is False
        is_valid, _ = validator.validate_sql_command("SELECT * FROM users WHERE id = 1; DELETE FROM users;")
        assert is_valid is False
        is_valid, _ = validator.validate_sql_command("'; DROP TABLE users; --")
        assert is_valid is False
    
    def test_sql_command_chaining_detected(self, validator):
        """Test that command chaining is detected"""
        is_valid, _ = validator.validate_sql_command("SELECT * FROM users; SELECT * FROM orders")
        assert is_valid is False
        is_valid, _ = validator.validate_sql_command("SELECT * FROM users; UPDATE users SET name = 'test'")
        assert is_valid is False


class TestShellCommandValidation:
    """Test shell command validation"""
    
    def test_valid_shell_command(self, validator):
        """Test that valid shell commands pass"""
        is_valid, _ = validator.validate_shell_command("ls -la")
        assert is_valid is True
        is_valid, _ = validator.validate_shell_command("cat /etc/passwd")
        assert is_valid is True
        # Note: "ps aux | grep python" will fail due to pipe character
        # This is expected behavior for security
    
    def test_dangerous_shell_commands_detected(self, validator):
        """Test that dangerous shell commands are detected"""
        is_valid, _ = validator.validate_shell_command("rm -rf /")
        assert is_valid is False
        is_valid, _ = validator.validate_shell_command("; rm -rf /")
        assert is_valid is False
        is_valid, _ = validator.validate_shell_command("&& rm -rf /")
        assert is_valid is False
        is_valid, _ = validator.validate_shell_command("| rm -rf /")
        assert is_valid is False
    
    def test_command_chaining_detected(self, validator):
        """Test that command chaining is detected"""
        is_valid, _ = validator.validate_shell_command("ls; rm -rf /")
        assert is_valid is False
        is_valid, _ = validator.validate_shell_command("cat file && rm file")
        assert is_valid is False
        is_valid, _ = validator.validate_shell_command("ls | rm")
        assert is_valid is False


class TestPowerShellCommandValidation:
    """Test PowerShell command validation"""
    
    def test_valid_powershell_command(self, validator):
        """Test that valid PowerShell commands pass"""
        is_valid, _ = validator.validate_powershell_command("Get-Process")
        assert is_valid is True
        is_valid, _ = validator.validate_powershell_command("Get-Service -Name w3svc")
        assert is_valid is True
        is_valid, _ = validator.validate_powershell_command("Get-EventLog -LogName System")
        assert is_valid is True
    
    def test_dangerous_powershell_commands_detected(self, validator):
        """Test that dangerous PowerShell commands are detected"""
        is_valid, _ = validator.validate_powershell_command("Remove-Item -Path C:\\ -Recurse -Force")
        assert is_valid is False
        is_valid, _ = validator.validate_powershell_command("; Remove-Item -Path C:\\ -Recurse -Force")
        assert is_valid is False
        is_valid, _ = validator.validate_powershell_command("Invoke-Expression 'rm -rf /'")
        assert is_valid is False
    
    def test_command_chaining_detected(self, validator):
        """Test that command chaining is detected"""
        is_valid, _ = validator.validate_powershell_command("Get-Process; Remove-Item -Path C:\\ -Recurse")
        assert is_valid is False
        is_valid, _ = validator.validate_powershell_command("Get-Service && Remove-Item -Path C:\\")
        assert is_valid is False


class TestCommandSanitization:
    """Test command sanitization"""
    
    def test_whitespace_handling(self, validator):
        """Test that whitespace is handled correctly"""
        is_valid, _ = validator.validate_shell_command("  ls -la  ")
        assert is_valid is True
        is_valid, _ = validator.validate_sql_command("  SELECT * FROM users  ")
        assert is_valid is True
    
    def test_empty_commands(self, validator):
        """Test that empty commands are rejected"""
        is_valid, _ = validator.validate_shell_command("")
        assert is_valid is False
        is_valid, _ = validator.validate_sql_command("")
        assert is_valid is False
        is_valid, _ = validator.validate_powershell_command("")
        assert is_valid is False
    
    def test_comment_handling(self, validator):
        """Test that comments are handled correctly"""
        # SQL comments should be allowed in some contexts but chaining should be detected
        is_valid, _ = validator.validate_sql_command("SELECT * FROM users -- comment")
        assert is_valid is True
        is_valid, _ = validator.validate_sql_command("SELECT * FROM users; -- DROP TABLE users")
        assert is_valid is False

