"""
Unit tests for POML parser (no TOML; XML-like POML only).
"""
import pytest
from pathlib import Path

from app.services.poml_parser import (
    parse_poml,
    parse_poml_file,
    POMLParseError,
)


class TestParsePoml:
    """Test parse_poml with string content."""

    def test_minimal_poml_returns_system_and_user(self):
        content = """
        <poml>
          <system>You are a helper.</system>
          <user>Hello.</user>
        </poml>
        """
        result = parse_poml(content, {})
        assert result["system"] == "You are a helper."
        assert result["user"] == "Hello."

    def test_variable_substitution(self):
        content = """
        <poml>
          <system>Service: {service}</system>
          <user>Issue: {issue_description}. Env: {env}</user>
        </poml>
        """
        variables = {
            "service": "server",
            "issue_description": "CPU high",
            "env": "prod",
        }
        result = parse_poml(content, variables)
        assert result["system"] == "Service: server"
        assert "Issue: CPU high" in result["user"]
        assert "Env: prod" in result["user"]

    def test_missing_variable_becomes_empty(self):
        content = """
        <poml>
          <user>Hello {name}.</user>
        </poml>
        """
        result = parse_poml(content, {})
        assert result["user"] == "Hello ."

    def test_literal_placeholders_server_and_database(self):
        content = """
        <poml>
          <system>Use __SERVER_NAME__ in commands.</system>
          <user>DB: __DATABASE_NAME__</user>
        </poml>
        """
        result = parse_poml(content, {})
        assert result["system"] == "Use {{server_name}} in commands."
        assert result["user"] == "DB: {{database_name}}"

    def test_user_template_element_accepted(self):
        content = """
        <poml>
          <system>System here.</system>
          <user_template>User here with {x}.</user_template>
        </poml>
        """
        result = parse_poml(content, {"x": "value"})
        assert result["system"] == "System here."
        assert result["user"] == "User here with value."

    def test_empty_elements_ok(self):
        content = """
        <poml>
          <system></system>
          <user>Only user.</user>
        </poml>
        """
        result = parse_poml(content, {})
        assert result["system"] == ""
        assert result["user"] == "Only user."

    def test_cdata_style_content(self):
        content = """
        <poml>
          <system><![CDATA[Use step and quotes in text.]]></system>
          <user>User part.</user>
        </poml>
        """
        result = parse_poml(content, {})
        assert "Use step and quotes in text." in result["system"]
        assert result["user"] == "User part."

    def test_empty_content_raises(self):
        with pytest.raises(POMLParseError, match="empty"):
            parse_poml("")
        with pytest.raises(POMLParseError, match="empty"):
            parse_poml("   ")

    def test_invalid_xml_raises(self):
        with pytest.raises(POMLParseError, match="Invalid POML XML"):
            parse_poml("<poml><system>No close tag")

    def test_root_not_poml_raises(self):
        with pytest.raises(POMLParseError, match="root element must be"):
            parse_poml("<other><system>x</system></other>")


class TestParsePomlFile:
    """Test parse_poml_file with disk path."""

    def test_file_not_found_raises(self, tmp_path):
        path = tmp_path / "missing.poml"
        with pytest.raises(FileNotFoundError, match="not found"):
            parse_poml_file(path, {})

    def test_load_real_file(self, tmp_path):
        path = tmp_path / "test.poml"
        path.write_text(
            '<poml><system>From file.</system><user>User {v}.</user></poml>',
            encoding="utf-8",
        )
        result = parse_poml_file(path, {"v": "X"})
        assert result["system"] == "From file."
        assert result["user"] == "User X."
