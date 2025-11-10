"""Tests for Gmail collector configuration module.

This module tests configuration loading, validation, and security features.
"""

from pathlib import Path

import pytest

from tools._shared.exceptions import ConfigurationValidationError
from tools.gmail.src.collectors.gmail.config import (
    FilterCriteria,
    GmailRule,
    load_gmail_config,
    load_universal_keywords,
    validate_file_path_config,
    validate_gmail_action,
    validate_gmail_query_syntax,
    validate_scopes_list,
)


class TestFilterCriteria:
    """Test FilterCriteria dataclass."""

    def test_filter_criteria_defaults(self) -> None:
        """Test default FilterCriteria values."""
        filter_criteria = FilterCriteria()
        assert filter_criteria.max_age_days is None
        assert filter_criteria.include_keywords == []
        assert filter_criteria.exclude_keywords == []

    def test_filter_criteria_with_values(self) -> None:
        """Test FilterCriteria with specific values."""
        filter_criteria = FilterCriteria(
            max_age_days=30, include_keywords=["AI", "machine learning"], exclude_keywords=["spam"]
        )
        assert filter_criteria.max_age_days == 30
        assert len(filter_criteria.include_keywords) == 2
        assert len(filter_criteria.exclude_keywords) == 1


class TestGmailRule:
    """Test GmailRule dataclass."""

    def test_gmail_rule_required_fields(self) -> None:
        """Test GmailRule with required fields only."""
        rule = GmailRule(name="test-rule", query="from:test@example.com")
        assert rule.name == "test-rule"
        assert rule.query == "from:test@example.com"
        assert rule.actions == []
        assert rule.filters is None
        assert rule.save_attachments is True
        assert rule.max_messages == 100

    def test_gmail_rule_with_all_fields(self) -> None:
        """Test GmailRule with all fields specified."""
        filters = FilterCriteria(max_age_days=7)
        rule = GmailRule(
            name="important-emails",
            query="is:important",
            actions=["save", "archive"],
            filters=filters,
            save_attachments=False,
            max_messages=50,
        )
        assert rule.name == "important-emails"
        assert len(rule.actions) == 2
        # Add None check for mypy
        assert rule.filters is not None
        assert rule.filters.max_age_days == 7
        assert rule.save_attachments is False
        assert rule.max_messages == 50


class TestGmailQueryValidation:
    """Test Gmail query syntax validation."""

    def test_valid_simple_query(self) -> None:
        """Test validation of simple valid queries."""
        valid_queries = [
            "from:user@example.com",
            "to:recipient@example.com",
            "subject:important",
            "is:unread",
            "has:attachment",
            "label:work",
        ]
        for query in valid_queries:
            result = validate_gmail_query_syntax(query)
            assert result == query

    def test_valid_complex_query(self) -> None:
        """Test validation of complex queries."""
        query = "from:user@example.com subject:report after:2025/01/01 has:attachment"
        result = validate_gmail_query_syntax(query)
        assert result == query

    def test_query_with_operators(self) -> None:
        """Test queries with various Gmail operators."""
        valid_queries = [
            "from:user@example.com OR to:user@example.com",
            "subject:report -label:spam",
            "after:2025/01/01 before:2025/12/31",
            "larger:1M smaller:10M",
            "filename:report.pdf",
            "cc:user@example.com bcc:user@example.com",
        ]
        for query in valid_queries:
            result = validate_gmail_query_syntax(query)
            assert isinstance(result, str)

    def test_empty_query(self) -> None:
        """Test that empty query raises error."""
        with pytest.raises(ConfigurationValidationError):
            validate_gmail_query_syntax("")

    def test_query_with_html_injection(self) -> None:
        """Test that HTML injection in query is blocked."""
        malicious_queries = [
            "<script>alert('xss')</script>",
            "from:<script>user@example.com",
            "subject:test<iframe src='evil.com'>",
        ]
        for query in malicious_queries:
            with pytest.raises(ConfigurationValidationError):
                validate_gmail_query_syntax(query)

    def test_query_with_path_traversal(self) -> None:
        """Test that path traversal attempts are blocked."""
        with pytest.raises(ConfigurationValidationError):
            validate_gmail_query_syntax("from:../../../etc/passwd")

    def test_query_too_long(self) -> None:
        """Test that excessively long queries are truncated."""
        long_query = "from:" + "a" * 2000  # Exceeds Gmail limit
        result = validate_gmail_query_syntax(long_query)
        assert len(result) <= 1000

    def test_bare_email_without_operator(self) -> None:
        """Test that bare email addresses require operators."""
        with pytest.raises(ConfigurationValidationError) as exc_info:
            validate_gmail_query_syntax("user@example.com")
        assert "must be used with an operator" in str(exc_info.value)

    def test_invalid_operator(self) -> None:
        """Test that invalid operators are rejected."""
        with pytest.raises(ConfigurationValidationError) as exc_info:
            validate_gmail_query_syntax("invalid:value")
        assert "invalid operators" in str(exc_info.value)


class TestGmailActionValidation:
    """Test Gmail action validation."""

    def test_valid_simple_actions(self) -> None:
        """Test validation of simple actions."""
        valid_actions = ["save", "archive", "mark_read", "delete", "delete_permanent"]
        for action in valid_actions:
            result = validate_gmail_action(action)
            assert result == action

    def test_valid_label_actions(self) -> None:
        """Test validation of label actions."""
        valid_actions = [
            "label:important",
            "label:work",
            "label:parent/child",  # Nested label
            "remove_label:spam",
        ]
        for action in valid_actions:
            result = validate_gmail_action(action)
            assert result == action

    def test_valid_forward_action(self) -> None:
        """Test validation of forward action."""
        action = "forward:user@example.com"
        result = validate_gmail_action(action)
        assert result == action

    def test_empty_action(self) -> None:
        """Test that empty action raises error."""
        with pytest.raises(ConfigurationValidationError):
            validate_gmail_action("")

    def test_invalid_action_name(self) -> None:
        """Test that invalid action names are rejected."""
        with pytest.raises(ConfigurationValidationError):
            validate_gmail_action("invalid_action")

    def test_invalid_label_format(self) -> None:
        """Test that invalid label formats are rejected."""
        with pytest.raises(ConfigurationValidationError):
            validate_gmail_action("label:invalid<>label")

    def test_invalid_forward_email(self) -> None:
        """Test that invalid forward email addresses are rejected."""
        with pytest.raises(ConfigurationValidationError):
            validate_gmail_action("forward:invalid-email")

    def test_action_too_long(self) -> None:
        """Test that excessively long actions are handled."""
        long_action = "label:" + "a" * 300
        result = validate_gmail_action(long_action)
        assert len(result) <= 200


class TestFilePathValidation:
    """Test file path configuration validation."""

    def test_valid_relative_path(self) -> None:
        """Test validation of valid relative paths."""
        valid_paths = ["data/gmail_token.json", "output/gmail", "settings/config.yaml"]
        for path in valid_paths:
            result = validate_file_path_config(path, "test path")
            assert isinstance(result, str)

    def test_valid_absolute_path(self) -> None:
        """Test validation of allowed absolute paths."""
        valid_paths = ["/tmp/test.json", "/home/user/data.json", "/Users/user/data.json"]
        for path in valid_paths:
            result = validate_file_path_config(path, "test path")
            assert isinstance(result, str)

    def test_empty_path(self) -> None:
        """Test that empty path raises error."""
        with pytest.raises(ConfigurationValidationError):
            validate_file_path_config("", "test path")

    def test_path_traversal_attempt(self) -> None:
        """Test that path traversal is blocked."""
        dangerous_paths = ["../../../etc/passwd", "data/../../sensitive", "~/.ssh/id_rsa", "${HOME}/secrets"]
        for path in dangerous_paths:
            with pytest.raises(ConfigurationValidationError):
                validate_file_path_config(path, "test path")

    def test_sensitive_system_path(self) -> None:
        """Test that sensitive system paths are blocked."""
        dangerous_paths = ["/etc/shadow", "/bin/bash", "/sbin/init", "/root/.ssh/id_rsa"]
        for path in dangerous_paths:
            with pytest.raises(ConfigurationValidationError):
                validate_file_path_config(path, "test path")


class TestOAuthScopesValidation:
    """Test OAuth scopes validation."""

    def test_valid_readonly_scope(self) -> None:
        """Test validation of readonly scope."""
        scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
        result = validate_scopes_list(scopes)
        assert result == scopes

    def test_valid_multiple_scopes(self) -> None:
        """Test validation of multiple valid scopes."""
        scopes = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.send",
        ]
        result = validate_scopes_list(scopes)
        assert result == scopes

    def test_empty_scopes_list(self) -> None:
        """Test that empty scopes list raises error."""
        with pytest.raises(ConfigurationValidationError):
            validate_scopes_list([])

    def test_invalid_scope_url(self) -> None:
        """Test that invalid scope URLs are rejected."""
        with pytest.raises(ConfigurationValidationError):
            validate_scopes_list(["https://evil.com/auth/scope"])

    def test_non_string_scope(self) -> None:
        """Test that non-string scopes are rejected."""
        with pytest.raises(ConfigurationValidationError):
            # Use list[Any] to allow mixed types for testing
            validate_scopes_list([123, "https://www.googleapis.com/auth/gmail.readonly"])  # type: ignore[list-item]


class TestUniversalKeywordsLoading:
    """Test loading of universal keywords from .keywords.yaml."""

    def test_load_missing_keywords_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading when .keywords.yaml doesn't exist."""
        monkeypatch.chdir("/tmp")
        result = load_universal_keywords()
        assert result == {"include_keywords": [], "exclude_keywords": []}

    def test_load_invalid_keywords_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test graceful handling of invalid keywords file."""
        keywords_file = tmp_path / ".keywords.yaml"
        keywords_file.write_text("invalid: yaml: content:")
        monkeypatch.chdir(tmp_path)

        result = load_universal_keywords()
        # Should return empty lists on error
        assert result == {"include_keywords": [], "exclude_keywords": []}


class TestGmailConfigLoading:
    """Test full Gmail configuration loading."""

    def test_load_minimal_config(self, tmp_path: Path) -> None:
        """Test loading minimal valid configuration."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
output_dir: "output/gmail"
rules:
  - name: "test-rule"
    query: "from:test@example.com"
        """
        )

        config = load_gmail_config(str(config_file))
        assert config.output_dir == "output/gmail"
        assert len(config.rules) == 1
        assert config.rules[0].name == "test-rule"

    def test_load_config_with_filters(self, tmp_path: Path) -> None:
        """Test loading configuration with filters."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
output_dir: "output/gmail"
default_filters:
  max_age_days: 30
  include_keywords: ["AI", "ML"]
  exclude_keywords: ["spam"]
rules:
  - name: "test-rule"
    query: "from:test@example.com"
    filters:
      max_age_days: 7
        """
        )

        config = load_gmail_config(str(config_file))
        assert config.default_filters.max_age_days == 30
        assert len(config.default_filters.include_keywords) == 2
        # Add None check for mypy
        assert config.rules[0].filters is not None
        assert config.rules[0].filters.max_age_days == 7

    def test_load_config_missing_file(self) -> None:
        """Test loading non-existent configuration file."""
        with pytest.raises(ConfigurationValidationError):
            load_gmail_config("/nonexistent/config.yaml")

    def test_load_config_missing_required_field(self, tmp_path: Path) -> None:
        """Test loading config missing required output_dir field."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
rules:
  - name: "test-rule"
    query: "from:test@example.com"
        """
        )

        with pytest.raises(ConfigurationValidationError) as exc_info:
            load_gmail_config(str(config_file))
        assert "output_dir" in str(exc_info.value)

    def test_load_config_invalid_rate_limit(self, tmp_path: Path) -> None:
        """Test that invalid rate limits are rejected."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
output_dir: "output/gmail"
rate_limit_seconds: -1
rules:
  - name: "test-rule"
    query: "from:test@example.com"
        """
        )

        with pytest.raises(ConfigurationValidationError):
            load_gmail_config(str(config_file))

    def test_load_config_invalid_batch_size(self, tmp_path: Path) -> None:
        """Test that invalid batch sizes are rejected."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
output_dir: "output/gmail"
batch_size: 200
rules:
  - name: "test-rule"
    query: "from:test@example.com"
        """
        )

        with pytest.raises(ConfigurationValidationError):
            load_gmail_config(str(config_file))

    def test_load_config_rule_missing_query(self, tmp_path: Path) -> None:
        """Test that rules without queries are rejected."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
output_dir: "output/gmail"
rules:
  - name: "test-rule"
    actions: ["save"]
        """
        )

        with pytest.raises(ConfigurationValidationError) as exc_info:
            load_gmail_config(str(config_file))
        assert "query" in str(exc_info.value)

    def test_load_config_rule_invalid_max_messages(self, tmp_path: Path) -> None:
        """Test that invalid max_messages values are rejected."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
output_dir: "output/gmail"
rules:
  - name: "test-rule"
    query: "from:test@example.com"
    max_messages: 1000
        """
        )

        with pytest.raises(ConfigurationValidationError):
            load_gmail_config(str(config_file))
