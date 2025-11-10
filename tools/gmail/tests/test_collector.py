"""Comprehensive tests for Gmail collector and authentication modules.

This module provides complete test coverage for:
- OAuth authentication (auth.py)
- Gmail API integration (collector.py)
- Message processing, filtering, and actions
- State management and error handling

Tests use mocked Gmail API calls - no real API requests are made.
"""

import base64
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

from tools._shared.exceptions import (
    AuthenticationFailureError,
    ContentProcessingError,
    InputValidationError,
    NetworkConnectionError,
)
from tools.gmail.src.collectors.gmail.auth import GmailAuthenticator
from tools.gmail.src.collectors.gmail.collector import GmailCollector
from tools.gmail.src.collectors.gmail.config import (
    FilterCriteria,
    GmailCollectorConfig,
    GmailRule,
)

# ============================================================================
# TEST HELPERS
# ============================================================================


def create_valid_token_data() -> dict[str, Any]:
    """Create valid token data with future expiry for testing."""
    return {
        "token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
        "expiry": (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat(),
    }


# ============================================================================
# AUTHENTICATION MODULE TESTS (auth.py)
# ============================================================================


class TestGmailAuthenticator:
    """Test OAuth authentication for Gmail API access."""

    def test_initialization_with_env_token_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test initialization with JSON token in GMAIL_TOKEN environment variable."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        auth = GmailAuthenticator(
            credentials_file_path=str(tmp_path / "nonexistent.json"),
            token_file_path=str(tmp_path / "token.json"),
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        assert hasattr(auth, "credentials")
        assert auth.credentials.token == "test_access_token"
        assert auth.credentials_file_path is None

    def test_initialization_with_env_token_base64(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test initialization with base64-encoded token in GMAIL_TOKEN."""
        token_data = create_valid_token_data()
        token_json = json.dumps(token_data)
        token_base64 = base64.b64encode(token_json.encode()).decode()
        monkeypatch.setenv("GMAIL_TOKEN", token_base64)

        auth = GmailAuthenticator(
            credentials_file_path=str(tmp_path / "nonexistent.json"),
            token_file_path=str(tmp_path / "token.json"),
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        assert hasattr(auth, "credentials")
        assert auth.credentials.token == "test_access_token"

    def test_initialization_with_invalid_json_token(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that invalid JSON token raises AuthenticationFailureError."""
        monkeypatch.setenv("GMAIL_TOKEN", "invalid json {{{")

        with pytest.raises((InputValidationError, AuthenticationFailureError)):
            GmailAuthenticator(
                credentials_file_path=str(tmp_path / "nonexistent.json"),
                token_file_path=str(tmp_path / "token.json"),
                scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            )

    def test_initialization_with_file_credentials(self, tmp_path: Path) -> None:
        """Test initialization with credentials file (fallback method)."""
        creds_file = tmp_path / "credentials.json"
        creds_data = {
            "installed": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "redirect_uris": ["http://localhost"],
            }
        }
        creds_file.write_text(json.dumps(creds_data))
        creds_file.chmod(0o600)

        auth = GmailAuthenticator(
            credentials_file_path=str(creds_file),
            token_file_path=str(tmp_path / "token.json"),
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        assert auth.credentials_file_path == creds_file

    def test_initialization_missing_credentials_file(self, tmp_path: Path) -> None:
        """Test that missing credentials file raises AuthenticationFailureError."""
        with pytest.raises(AuthenticationFailureError) as exc_info:
            GmailAuthenticator(
                credentials_file_path=str(tmp_path / "nonexistent.json"),
                token_file_path=str(tmp_path / "token.json"),
                scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            )
        assert "credentials not found" in str(exc_info.value).lower()

    def test_get_credentials_with_env_token(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting credentials when loaded from environment variable."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        auth = GmailAuthenticator(
            credentials_file_path=str(tmp_path / "nonexistent.json"),
            token_file_path=str(tmp_path / "token.json"),
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        creds = auth.get_credentials()
        assert creds.token == "test_access_token"

    def test_get_credentials_refresh_expired_token(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test automatic token refresh when expired."""
        # Create expired token
        token_data = create_valid_token_data()
        token_data["expiry"] = (datetime.now(tz=UTC) - timedelta(hours=1)).isoformat()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        auth = GmailAuthenticator(
            credentials_file_path=str(tmp_path / "nonexistent.json"),
            token_file_path=str(tmp_path / "token.json"),
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        # Mock the refresh method
        with patch.object(auth.credentials, "refresh") as mock_refresh:
            mock_refresh.return_value = None
            auth.credentials.token = "new_access_token"

            auth.get_credentials()
            mock_refresh.assert_called_once()

    def test_get_credentials_refresh_failure(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling of token refresh failure."""
        # Create expired token
        token_data = create_valid_token_data()
        token_data["expiry"] = (datetime.now(tz=UTC) - timedelta(hours=1)).isoformat()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        auth = GmailAuthenticator(
            credentials_file_path=str(tmp_path / "nonexistent.json"),
            token_file_path=str(tmp_path / "token.json"),
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        # Mock the refresh method to raise an error
        with patch.object(auth.credentials, "refresh") as mock_refresh:
            mock_refresh.side_effect = Exception("Refresh failed")

            with pytest.raises(AuthenticationFailureError) as exc_info:
                auth.get_credentials()
            assert "refresh" in str(exc_info.value).lower()

    def test_load_credentials_from_token_file(self, tmp_path: Path) -> None:
        """Test loading credentials from saved token file."""
        creds_file = tmp_path / "credentials.json"
        token_file = tmp_path / "token.json"

        creds_data = {
            "installed": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "redirect_uris": ["http://localhost"],
            }
        }
        creds_file.write_text(json.dumps(creds_data))
        creds_file.chmod(0o600)

        token_data = create_valid_token_data()
        token_file.write_text(json.dumps(token_data))

        auth = GmailAuthenticator(
            credentials_file_path=str(creds_file),
            token_file_path=str(token_file),
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        creds = auth._load_credentials_from_token_file()
        assert creds.token == "test_access_token"
        assert creds.refresh_token == "test_refresh_token"

    def test_load_credentials_from_corrupted_file(self, tmp_path: Path) -> None:
        """Test handling of corrupted token file."""
        creds_file = tmp_path / "credentials.json"
        token_file = tmp_path / "token.json"

        creds_data = {
            "installed": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "redirect_uris": ["http://localhost"],
            }
        }
        creds_file.write_text(json.dumps(creds_data))
        creds_file.chmod(0o600)

        token_file.write_text("invalid json {{{")

        auth = GmailAuthenticator(
            credentials_file_path=str(creds_file),
            token_file_path=str(token_file),
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        with pytest.raises(AuthenticationFailureError) as exc_info:
            auth._load_credentials_from_token_file()
        assert "corrupted" in str(exc_info.value).lower()

    def test_save_credentials_to_token_file(self, tmp_path: Path) -> None:
        """Test saving credentials to token file with secure permissions."""
        creds_file = tmp_path / "credentials.json"
        token_file = tmp_path / "token.json"

        creds_data = {
            "installed": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "redirect_uris": ["http://localhost"],
            }
        }
        creds_file.write_text(json.dumps(creds_data))
        creds_file.chmod(0o600)

        auth = GmailAuthenticator(
            credentials_file_path=str(creds_file),
            token_file_path=str(token_file),
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        # Create test credentials
        credentials = Credentials(
            token="test_token",
            refresh_token="test_refresh",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="test_client",
            client_secret="test_secret",
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        auth._save_credentials_to_token_file(credentials)

        # Verify file was created with secure permissions
        assert token_file.exists()
        file_mode = token_file.stat().st_mode & 0o777
        assert file_mode == 0o600

        # Verify content
        saved_data = json.loads(token_file.read_text())
        assert saved_data["token"] == "test_token"

    def test_validate_credential_file_permissions_secure(self, tmp_path: Path) -> None:
        """Test validation passes for secure file permissions."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text("{}")
        creds_file.chmod(0o600)

        token_file = tmp_path / "token.json"
        auth = GmailAuthenticator(
            credentials_file_path=str(creds_file),
            token_file_path=str(token_file),
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        # Should not raise
        auth._validate_credential_file_permissions(creds_file)

    def test_validate_credential_file_permissions_insecure(self, tmp_path: Path) -> None:
        """Test validation fails for insecure file permissions."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text("{}")
        creds_file.chmod(0o644)  # Insecure permissions

        with pytest.raises(AuthenticationFailureError) as exc_info:
            GmailAuthenticator(
                credentials_file_path=str(creds_file),
                token_file_path=str(tmp_path / "token.json"),
                scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            )
        assert "insecure permissions" in str(exc_info.value).lower()


# ============================================================================
# GMAIL COLLECTOR TESTS (collector.py)
# ============================================================================


class TestGmailCollectorInitialization:
    """Test Gmail collector initialization."""

    def test_initialization_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test successful collector initialization."""
        # Setup mock credentials
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        # Update config to use tmp_path
        sample_gmail_config.output_dir = str(tmp_path / "output")
        sample_gmail_config.token_file = str(tmp_path / "token.json")
        sample_gmail_config.credentials_file = str(tmp_path / "creds.json")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            assert collector.config == sample_gmail_config
            assert collector.service is not None
            assert Path(sample_gmail_config.output_dir).exists()

    def test_initialization_authentication_failure(
        self, tmp_path: Path, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test initialization failure when authentication fails."""
        sample_gmail_config.output_dir = str(tmp_path / "output")
        sample_gmail_config.credentials_file = str(tmp_path / "nonexistent.json")

        with pytest.raises(ContentProcessingError) as exc_info:
            GmailCollector(sample_gmail_config)
        assert "authentication failed" in str(exc_info.value).lower()

    def test_context_manager_support(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test collector works as context manager."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")
        sample_gmail_config.token_file = str(tmp_path / "token.json")
        sample_gmail_config.credentials_file = str(tmp_path / "creds.json")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            with GmailCollector(sample_gmail_config) as collector:
                assert collector is not None
            # Should exit cleanly


class TestGmailCollectorRetryLogic:
    """Test API retry logic with exponential backoff."""

    def test_execute_with_retry_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test successful API call without retries."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            api_call = Mock(return_value={"result": "success"})
            result = collector._execute_with_retry(api_call)

            assert result == {"result": "success"}
            api_call.assert_called_once()

    def test_execute_with_retry_transient_error_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test retry succeeds after transient error."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")
        sample_gmail_config.retry_base_delay = 0.01  # Speed up test

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            # First call fails with 429, second succeeds
            mock_response = Mock()
            mock_response.status = 429
            api_call = Mock(side_effect=[HttpError(mock_response, b"Rate limit"), {"result": "success"}])

            result = collector._execute_with_retry(api_call, max_retries=2)

            assert result == {"result": "success"}
            assert api_call.call_count == 2

    def test_execute_with_retry_all_retries_fail(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test all retries exhausted raises NetworkConnectionError."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")
        sample_gmail_config.retry_base_delay = 0.01

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            mock_response = Mock()
            mock_response.status = 503
            api_call = Mock(side_effect=HttpError(mock_response, b"Service unavailable"))

            with pytest.raises(NetworkConnectionError):
                collector._execute_with_retry(api_call, max_retries=2)

            assert api_call.call_count == 3  # Initial + 2 retries

    def test_execute_with_retry_non_transient_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test non-transient errors are not retried."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            # 400 is not a transient error
            mock_response = Mock()
            mock_response.status = 400
            api_call = Mock(side_effect=HttpError(mock_response, b"Bad request"))

            with pytest.raises(NetworkConnectionError):
                collector._execute_with_retry(api_call, max_retries=2)

            api_call.assert_called_once()  # Should not retry


class TestGmailMessageSearch:
    """Test Gmail message search functionality."""

    def test_search_messages_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test successful message search."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")
        sample_gmail_config.batch_size = 10

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Mock API response
            mock_list = MagicMock()
            mock_list.execute.return_value = {
                "messages": [{"id": "msg_1"}, {"id": "msg_2"}, {"id": "msg_3"}],
            }
            mock_service.users().messages().list.return_value = mock_list

            collector = GmailCollector(sample_gmail_config)
            message_ids = collector._search_messages("from:test@example.com", max_results=10)

            assert len(message_ids) == 3
            assert message_ids == ["msg_1", "msg_2", "msg_3"]

    def test_search_messages_pagination(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test message search with pagination."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")
        sample_gmail_config.batch_size = 2
        sample_gmail_config.rate_limit_seconds = 0.01

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Mock paginated responses
            page1_mock = MagicMock()
            page1_mock.execute.return_value = {
                "messages": [{"id": "msg_1"}, {"id": "msg_2"}],
                "nextPageToken": "token_page2",
            }

            page2_mock = MagicMock()
            page2_mock.execute.return_value = {
                "messages": [{"id": "msg_3"}],
            }

            mock_service.users().messages().list.side_effect = [page1_mock, page2_mock]

            collector = GmailCollector(sample_gmail_config)
            message_ids = collector._search_messages("from:test@example.com", max_results=5)

            assert len(message_ids) == 3
            assert message_ids == ["msg_1", "msg_2", "msg_3"]

    def test_search_messages_empty_results(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test search with no matching messages."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            mock_list = MagicMock()
            mock_list.execute.return_value = {}
            mock_service.users().messages().list.return_value = mock_list

            collector = GmailCollector(sample_gmail_config)
            message_ids = collector._search_messages("from:nonexistent@example.com", max_results=10)

            assert len(message_ids) == 0


class TestGmailMessageParsing:
    """Test Gmail message parsing and body extraction."""

    def test_get_message_details_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test successful message details retrieval."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Mock message response
            body_text = "Test email body"
            body_encoded = base64.urlsafe_b64encode(body_text.encode()).decode()

            mock_message = {
                "id": "msg_123",
                "threadId": "thread_123",
                "sizeEstimate": 1024,
                "snippet": "Test snippet",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "sender@example.com"},
                        {"name": "To", "value": "recipient@example.com"},
                        {"name": "Subject", "value": "Test Subject"},
                        {"name": "Date", "value": "Wed, 27 Oct 2025 10:00:00 +0000"},
                    ],
                    "mimeType": "text/plain",
                    "body": {"data": body_encoded},
                },
            }

            mock_get = MagicMock()
            mock_get.execute.return_value = mock_message
            mock_service.users().messages().get.return_value = mock_get

            collector = GmailCollector(sample_gmail_config)
            message_data = collector._get_message_details("msg_123")

            assert message_data is not None
            assert message_data["id"] == "msg_123"
            assert message_data["subject"] == "Test Subject"
            assert message_data["from"] == "sender@example.com"
            assert message_data["body"]["plain"] == body_text

    def test_extract_message_body_plain_text(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test extraction of plain text body."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            body_text = "Plain text body"
            body_encoded = base64.urlsafe_b64encode(body_text.encode()).decode()

            payload = {
                "mimeType": "text/plain",
                "headers": [{"name": "Content-Type", "value": "text/plain; charset=utf-8"}],
                "body": {"data": body_encoded},
            }

            result = collector._extract_message_body(payload)

            assert result["plain"] == body_text
            assert result["html"] == ""

    def test_extract_message_body_html(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test extraction of HTML body."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            html_body = "<html><body>HTML body</body></html>"
            html_encoded = base64.urlsafe_b64encode(html_body.encode()).decode()

            payload = {
                "mimeType": "text/html",
                "headers": [{"name": "Content-Type", "value": "text/html; charset=utf-8"}],
                "body": {"data": html_encoded},
            }

            result = collector._extract_message_body(payload)

            assert result["html"] == html_body
            assert result["plain"] == ""

    def test_extract_message_body_multipart(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test extraction of multipart message (plain + HTML)."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            plain_text = "Plain text version"
            html_text = "<html><body>HTML version</body></html>"

            plain_encoded = base64.urlsafe_b64encode(plain_text.encode()).decode()
            html_encoded = base64.urlsafe_b64encode(html_text.encode()).decode()

            payload = {
                "mimeType": "multipart/alternative",
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "headers": [{"name": "Content-Type", "value": "text/plain; charset=utf-8"}],
                        "body": {"data": plain_encoded},
                    },
                    {
                        "mimeType": "text/html",
                        "headers": [{"name": "Content-Type", "value": "text/html; charset=utf-8"}],
                        "body": {"data": html_encoded},
                    },
                ],
            }

            result = collector._extract_message_body(payload)

            assert result["plain"] == plain_text
            assert result["html"] == html_text


class TestGmailContentFiltering:
    """Test content filtering logic."""

    def test_should_process_message_include_keywords_match(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test message passes when include keywords match."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")
        sample_gmail_config.default_filters = FilterCriteria(include_keywords=["important", "urgent"])

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            rule = GmailRule(name="test", query="from:test@example.com")
            message_data = {
                "id": "msg_1",
                "subject": "This is an important message",
                "body": {"plain": "Please handle this urgently"},
                "date": datetime.now(tz=UTC),
            }

            should_process = collector._should_process_message(message_data, rule)
            assert should_process is True

    def test_should_process_message_exclude_keywords_match(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test message blocked when exclude keywords match."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")
        sample_gmail_config.default_filters = FilterCriteria(exclude_keywords=["spam", "unsubscribe"])

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            rule = GmailRule(name="test", query="from:test@example.com")
            message_data = {
                "id": "msg_1",
                "subject": "This is spam",
                "body": {"plain": "Click to unsubscribe"},
                "date": datetime.now(tz=UTC),
            }

            should_process = collector._should_process_message(message_data, rule)
            assert should_process is False

    def test_should_process_message_age_filter(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test message filtered by age."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")
        sample_gmail_config.default_filters = FilterCriteria(max_age_days=7)

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            rule = GmailRule(name="test", query="from:test@example.com")

            # Old message (should be filtered out)
            old_message = {
                "id": "msg_1",
                "subject": "Old message",
                "body": {"plain": "Old content"},
                "date": datetime.now(tz=UTC) - timedelta(days=30),
            }

            should_process = collector._should_process_message(old_message, rule)
            assert should_process is False

            # Recent message (should pass)
            recent_message = {
                "id": "msg_2",
                "subject": "Recent message",
                "body": {"plain": "Recent content"},
                "date": datetime.now(tz=UTC) - timedelta(days=2),
            }

            should_process = collector._should_process_message(recent_message, rule)
            assert should_process is True


class TestGmailMessageActions:
    """Test Gmail message actions (archive, label, forward, etc.)."""

    def test_archive_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test archiving message by removing INBOX label."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            mock_modify = MagicMock()
            mock_modify.execute.return_value = {"id": "msg_123"}
            mock_service.users().messages().modify.return_value = mock_modify

            collector = GmailCollector(sample_gmail_config)
            collector._archive_message("msg_123")

            # Verify modify was called with removeLabelIds
            mock_service.users().messages().modify.assert_called_once()
            call_args = mock_service.users().messages().modify.call_args
            assert call_args[1]["body"]["removeLabelIds"] == ["INBOX"]

    def test_mark_message_read(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test marking message as read."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            mock_modify = MagicMock()
            mock_modify.execute.return_value = {"id": "msg_123"}
            mock_service.users().messages().modify.return_value = mock_modify

            collector = GmailCollector(sample_gmail_config)
            collector._mark_message_read("msg_123")

            call_args = mock_service.users().messages().modify.call_args
            assert call_args[1]["body"]["removeLabelIds"] == ["UNREAD"]

    def test_add_label_to_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test adding label to message."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Mock label list
            mock_list = MagicMock()
            mock_list.execute.return_value = {"labels": [{"id": "Label_1", "name": "Important"}]}
            mock_service.users().labels().list.return_value = mock_list

            # Mock modify
            mock_modify = MagicMock()
            mock_modify.execute.return_value = {"id": "msg_123"}
            mock_service.users().messages().modify.return_value = mock_modify

            collector = GmailCollector(sample_gmail_config)
            collector._add_label_to_message("msg_123", "Important")

            call_args = mock_service.users().messages().modify.call_args
            assert call_args[1]["body"]["addLabelIds"] == ["Label_1"]

    def test_delete_message_trash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test moving message to trash."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            mock_trash = MagicMock()
            mock_trash.execute.return_value = {"id": "msg_123"}
            mock_service.users().messages().trash.return_value = mock_trash

            collector = GmailCollector(sample_gmail_config)
            collector._delete_message("msg_123", permanent=False)

            mock_service.users().messages().trash.assert_called_once()

    def test_delete_message_permanent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test permanently deleting message."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            mock_delete = MagicMock()
            mock_delete.execute.return_value = None
            mock_service.users().messages().delete.return_value = mock_delete

            collector = GmailCollector(sample_gmail_config)
            collector._delete_message("msg_123", permanent=True)

            mock_service.users().messages().delete.assert_called_once()


class TestGmailAttachmentHandling:
    """Test attachment extraction and security validation."""

    def test_validate_attachment_safety_dangerous_extension(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test dangerous file extensions are blocked."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            dangerous_files = ["malware.exe", "script.sh", "virus.bat", "payload.js"]
            for filename in dangerous_files:
                is_safe = collector._validate_attachment_safety(filename, 1024)
                assert is_safe is False

    def test_validate_attachment_safety_oversized(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test oversized attachments are blocked."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            # 200MB file (exceeds 100MB limit)
            is_safe = collector._validate_attachment_safety("largefile.zip", 200 * 1024 * 1024)
            assert is_safe is False

    def test_validate_attachment_safety_safe_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test safe attachments pass validation."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            safe_files = ["document.pdf", "image.jpg", "spreadsheet.xlsx", "archive.zip"]
            for filename in safe_files:
                is_safe = collector._validate_attachment_safety(filename, 1024 * 1024)  # 1MB
                assert is_safe is True


class TestGmailStateManagement:
    """Test state management and duplicate prevention."""

    def test_load_state_with_validation_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test successful state loading."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            # Create valid state
            state = {
                "processed_messages": {"msg_1": {"actions_applied": ["save"], "last_processed": "2025-10-27T10:00:00Z"}}
            }
            collector.state_manager.save_state(state)

            loaded_state = collector._load_state_with_validation()
            assert "processed_messages" in loaded_state
            assert "msg_1" in loaded_state["processed_messages"]

    def test_load_state_with_validation_invalid_structure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test handling of invalid state structure."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            # Save invalid state (list instead of dict)
            state_file = Path(sample_gmail_config.output_dir) / ".gmail_state.json"
            state_file.write_text("[]")

            loaded_state = collector._load_state_with_validation()
            # Should return initial state
            assert loaded_state["processed_messages"] == {}

    def test_cleanup_old_state_entries(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test cleanup of old state entries."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            # Create state with more than 10k entries
            processed_messages = {}
            for i in range(10500):
                processed_messages[f"msg_{i}"] = {
                    "actions_applied": ["save"],
                    "last_processed": f"2025-10-{27 - (i % 30):02d}T10:00:00Z",
                }

            cleaned = collector._cleanup_old_state_entries(processed_messages)
            assert len(cleaned) == 10000

    def test_calculate_state_hash_consistency(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test state hash calculation is consistent."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_build.return_value = MagicMock()

            collector = GmailCollector(sample_gmail_config)

            state = {"processed_messages": {"msg_1": {"actions_applied": ["save"]}}}

            hash1 = collector._calculate_state_hash(state)
            hash2 = collector._calculate_state_hash(state)

            assert hash1 == hash2


class TestGmailEmailSending:
    """Test email sending and forwarding functionality."""

    def test_send_email_plain_text(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test sending plain text email."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            mock_send = MagicMock()
            mock_send.execute.return_value = {"id": "sent_123"}
            mock_service.users().messages().send.return_value = mock_send

            collector = GmailCollector(sample_gmail_config)

            result = collector.send_email(to="recipient@example.com", subject="Test Subject", body="Test body content")

            assert result is True
            mock_service.users().messages().send.assert_called_once()

    def test_send_email_with_html(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test sending email with HTML content."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            mock_send = MagicMock()
            mock_send.execute.return_value = {"id": "sent_123"}
            mock_service.users().messages().send.return_value = mock_send

            collector = GmailCollector(sample_gmail_config)

            result = collector.send_email(
                to="recipient@example.com",
                subject="Test Subject",
                body="Plain text",
                html_body="<html><body>HTML content</body></html>",
            )

            assert result is True

    def test_forward_email(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_gmail_config: GmailCollectorConfig
    ) -> None:
        """Test forwarding email."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        sample_gmail_config.output_dir = str(tmp_path / "output")

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Mock get message
            body_text = "Original message body"
            body_encoded = base64.urlsafe_b64encode(body_text.encode()).decode()

            mock_message = {
                "id": "msg_123",
                "threadId": "thread_123",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "original@example.com"},
                        {"name": "Subject", "value": "Original Subject"},
                        {"name": "Date", "value": "Wed, 27 Oct 2025 10:00:00 +0000"},
                    ],
                    "body": {"data": body_encoded},
                },
            }

            mock_get = MagicMock()
            mock_get.execute.return_value = mock_message
            mock_service.users().messages().get.return_value = mock_get

            # Mock send
            mock_send = MagicMock()
            mock_send.execute.return_value = {"id": "sent_123"}
            mock_service.users().messages().send.return_value = mock_send

            collector = GmailCollector(sample_gmail_config)

            result = collector.forward_email(message_id="msg_123", to="forward@example.com", additional_body="FYI")

            assert result is True
            mock_service.users().messages().send.assert_called_once()


class TestGmailCollectorIntegration:
    """Integration tests for full collection workflow."""

    def test_collect_rule_full_workflow(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test complete collection workflow for a rule."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        config = GmailCollectorConfig(
            output_dir=str(tmp_path / "output"),
            token_file=str(tmp_path / "token.json"),
            credentials_file=str(tmp_path / "creds.json"),
            rate_limit_seconds=0.01,
            default_filters=FilterCriteria(),
            rules=[
                GmailRule(
                    name="test-rule",
                    query="from:test@example.com",
                    actions=["save"],
                    max_messages=2,
                )
            ],
        )

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Mock search
            mock_list = MagicMock()
            mock_list.execute.return_value = {"messages": [{"id": "msg_1"}, {"id": "msg_2"}]}
            mock_service.users().messages().list.return_value = mock_list

            # Mock get message
            body_text = "Test email body"
            body_encoded = base64.urlsafe_b64encode(body_text.encode()).decode()

            def create_mock_message(msg_id: str) -> dict[str, Any]:
                return {
                    "id": msg_id,
                    "threadId": f"thread_{msg_id}",
                    "sizeEstimate": 1024,
                    "snippet": "Test snippet",
                    "payload": {
                        "headers": [
                            {"name": "From", "value": "test@example.com"},
                            {"name": "To", "value": "recipient@example.com"},
                            {"name": "Subject", "value": f"Test Subject {msg_id}"},
                            {"name": "Date", "value": "Wed, 27 Oct 2025 10:00:00 +0000"},
                        ],
                        "mimeType": "text/plain",
                        "body": {"data": body_encoded},
                    },
                }

            mock_get = MagicMock()
            mock_get.execute.side_effect = [create_mock_message("msg_1"), create_mock_message("msg_2")]
            mock_service.users().messages().get.return_value = mock_get

            collector = GmailCollector(config)
            stats = collector.collect_rule(config.rules[0])

            assert stats["messages_processed"] == 2
            assert stats["messages_saved"] == 2
            assert stats["errors"] == 0

    def test_collect_all_rules(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test collecting from multiple rules."""
        token_data = create_valid_token_data()
        monkeypatch.setenv("GMAIL_TOKEN", json.dumps(token_data))

        config = GmailCollectorConfig(
            output_dir=str(tmp_path / "output"),
            token_file=str(tmp_path / "token.json"),
            credentials_file=str(tmp_path / "creds.json"),
            rate_limit_seconds=0.01,
            default_filters=FilterCriteria(),
            rules=[
                GmailRule(name="rule-1", query="from:test1@example.com", actions=["save"], max_messages=1),
                GmailRule(name="rule-2", query="from:test2@example.com", actions=["save"], max_messages=1),
            ],
        )

        with patch("tools.gmail.src.collectors.gmail.collector.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Mock search responses
            mock_list = MagicMock()
            mock_list.execute.side_effect = [
                {"messages": [{"id": "msg_1"}]},
                {"messages": [{"id": "msg_2"}]},
            ]
            mock_service.users().messages().list.return_value = mock_list

            # Mock get message
            body_encoded = base64.urlsafe_b64encode(b"Test body").decode()

            def create_message(msg_id: str) -> dict[str, Any]:
                return {
                    "id": msg_id,
                    "threadId": f"thread_{msg_id}",
                    "sizeEstimate": 1024,
                    "snippet": "Test",
                    "payload": {
                        "headers": [
                            {"name": "From", "value": "test@example.com"},
                            {"name": "Subject", "value": "Test"},
                            {"name": "Date", "value": "Wed, 27 Oct 2025 10:00:00 +0000"},
                        ],
                        "body": {"data": body_encoded},
                    },
                }

            mock_get = MagicMock()
            mock_get.execute.side_effect = [create_message("msg_1"), create_message("msg_2")]
            mock_service.users().messages().get.return_value = mock_get

            collector = GmailCollector(config)
            overall_stats = collector.collect_all_rules()

            assert overall_stats["rules_processed"] == 2
            assert overall_stats["total_messages_processed"] == 2
            assert overall_stats["total_messages_saved"] == 2
