"""Pytest configuration and fixtures for Gmail collector tests.

This module provides shared fixtures and configuration for all Gmail collector tests.
"""

import json
import tempfile
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture  # type: ignore[misc]
def mock_gmail_service() -> MagicMock:
    """Create a mock Gmail API service."""
    service = MagicMock()

    # Mock users() method chain
    service.users.return_value = MagicMock()
    service.users().messages.return_value = MagicMock()
    service.users().messages().list.return_value = MagicMock()
    service.users().messages().get.return_value = MagicMock()
    service.users().messages().modify.return_value = MagicMock()
    service.users().messages().send.return_value = MagicMock()
    service.users().messages().trash.return_value = MagicMock()
    service.users().messages().delete.return_value = MagicMock()
    service.users().messages().attachments.return_value = MagicMock()
    service.users().labels.return_value = MagicMock()
    service.users().labels().list.return_value = MagicMock()
    service.users().labels().create.return_value = MagicMock()

    return service


@pytest.fixture  # type: ignore[misc]
def sample_gmail_config() -> Any:
    """Create a sample Gmail collector configuration."""
    from tools.gmail.src.collectors.gmail.config import FilterCriteria, GmailCollectorConfig, GmailRule

    return GmailCollectorConfig(
        output_dir="output/gmail/test",
        token_file="data/test_gmail_token.json",
        credentials_file="data/test_gmail_credentials.json",
        rate_limit_seconds=0.1,
        default_filters=FilterCriteria(max_age_days=30, include_keywords=["test"], exclude_keywords=["spam"]),
        rules=[
            GmailRule(
                name="test-rule",
                query="from:test@example.com",
                actions=["save", "archive"],
                filters=FilterCriteria(max_age_days=7, include_keywords=["important"]),
                save_attachments=True,
                max_messages=10,
            )
        ],
    )


@pytest.fixture  # type: ignore[misc]
def sample_message_data() -> dict[str, Any]:
    """Create sample Gmail message data for testing."""
    return {
        "id": "test_message_123",
        "threadId": "thread_123",
        "payload": {
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Subject", "value": "Test Email"},
                {"name": "Date", "value": "Wed, 27 Oct 2025 10:00:00 +0000"},
            ],
            "body": {"data": "VGVzdCBlbWFpbCBib2R5"},  # Base64 encoded "Test email body"
        },
        "snippet": "Test email snippet",
        "sizeEstimate": 1024,
    }


@pytest.fixture  # type: ignore[misc]
def sample_processed_message_data() -> dict[str, Any]:
    """Create sample processed message data."""
    return {
        "id": "test_message_123",
        "thread_id": "thread_123",
        "subject": "Test Email",
        "from": "sender@example.com",
        "to": "recipient@example.com",
        "date": datetime.now(tz=UTC),
        "body": {"plain": "Test email body", "html": "<p>Test email body</p>"},
        "headers": {
            "from": "sender@example.com",
            "to": "recipient@example.com",
            "subject": "Test Email",
        },
        "size_estimate": 1024,
        "snippet": "Test email snippet",
        "raw_message": {},
    }


@pytest.fixture  # type: ignore[misc]
def temp_output_dir() -> Generator[Path, None, None]:
    """Create a temporary output directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture  # type: ignore[misc]
def temp_config_file(temp_output_dir: Path) -> Path:
    """Create a temporary Gmail configuration file."""
    config_content = {
        "output_dir": str(temp_output_dir),
        "token_file": str(temp_output_dir / "gmail_token.json"),
        "credentials_file": str(temp_output_dir / "gmail_credentials.json"),
        "rate_limit_seconds": 0.1,
        "default_filters": {"max_age_days": 30, "include_keywords": [], "exclude_keywords": []},
        "rules": [
            {
                "name": "test-rule",
                "query": "from:test@example.com",
                "actions": ["save"],
                "max_messages": 10,
                "save_attachments": False,
            }
        ],
    }

    config_file = temp_output_dir / "test_gmail_config.yaml"
    with open(config_file, "w") as f:
        import yaml

        yaml.dump(config_content, f)

    return config_file


@pytest.fixture  # type: ignore[misc]
def mock_credentials() -> Any:
    """Create mock OAuth2 credentials."""
    from google.oauth2.credentials import Credentials

    return Credentials(
        token="test_access_token",
        refresh_token="test_refresh_token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="test_client_id",
        client_secret="test_client_secret",
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )


@pytest.fixture  # type: ignore[misc]
def mock_authenticator(mock_credentials: Any) -> Mock:
    """Create a mock Gmail authenticator."""
    mock_auth = Mock()
    mock_auth.get_credentials.return_value = mock_credentials
    return mock_auth


@pytest.fixture  # type: ignore[misc]
def sample_state_data() -> dict[str, Any]:
    """Create sample state data for testing."""
    return {
        "processed_messages": {
            "msg_123": {"actions_applied": ["save"], "last_processed": "2025-10-27T10:00:00Z"},
            "msg_456": {"actions_applied": ["save", "archive"], "last_processed": "2025-10-26T10:00:00Z"},
        },
        "version": "1.0",
    }


@pytest.fixture  # type: ignore[misc]
def temp_state_file(temp_output_dir: Path, sample_state_data: dict[str, Any]) -> Path:
    """Create a temporary state file."""
    state_file = temp_output_dir / "gmail_state.json"
    with open(state_file, "w") as f:
        json.dump(sample_state_data, f)
    return state_file


@pytest.fixture  # type: ignore[misc]
def mock_http_response() -> type:
    """Create a mock HTTP response."""

    class MockResponse:
        def __init__(self, status: int = 200, data: dict[str, Any] | None = None) -> None:
            self.status = status
            self.data = data or {}

        def execute(self) -> dict[str, Any]:
            return self.data

    return MockResponse


@pytest.fixture  # type: ignore[misc]
def sample_gmail_labels() -> dict[str, Any]:
    """Create sample Gmail label data."""
    return {
        "labels": [
            {"id": "Label_1", "name": "Important", "type": "user"},
            {"id": "Label_2", "name": "Work", "type": "user"},
            {"id": "INBOX", "name": "INBOX", "type": "system"},
            {"id": "UNREAD", "name": "UNREAD", "type": "system"},
        ]
    }


@pytest.fixture(autouse=True)  # type: ignore[misc]
def clean_test_environment(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Clean test environment before each test."""
    # Clear sensitive environment variables
    monkeypatch.delenv("GMAIL_TOKEN", raising=False)
    monkeypatch.delenv("GMAIL_CREDENTIALS", raising=False)

    yield

    # Cleanup after test
    pass
