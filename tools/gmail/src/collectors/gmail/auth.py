"""OAuth2 authentication utilities for Gmail API access.

This module handles OAuth2 flow, token storage, and refresh for Gmail API access.
"""

import base64
import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from tools._shared.exceptions import AuthenticationFailureError, InputValidationError
from tools._shared.security import sanitize_text_content


class GmailAuthenticator:
    """Handles OAuth2 authentication for Gmail API access."""

    def __init__(self, credentials_file_path: str, token_file_path: str, scopes: list[str]):
        """
        Initialize Gmail authenticator.

        Args:
            credentials_file_path: Path to OAuth2 credentials JSON file
            token_file_path: Path to store/load access tokens
            scopes: List of OAuth2 scopes to request

        Raises:
            AuthenticationFailureError: If authentication cannot be set up
        """
        self.scopes = scopes
        self.token_file_path = Path(token_file_path)

        # FIRST: Try environment variable (existing working method)
        gmail_token = os.getenv("GMAIL_TOKEN")
        if gmail_token:
            try:
                # Validate token format before processing
                sanitized_token = sanitize_text_content(gmail_token, max_length=100000)  # Reasonable max for tokens

                # Proper token validation - try both formats securely
                token_data = None

                # Try JSON first (most common format)
                try:
                    token_data = json.loads(sanitized_token)
                except json.JSONDecodeError:
                    # Try base64 decode if direct JSON fails
                    try:
                        # Validate base64 format more securely
                        if len(sanitized_token) > 20 and all(
                            c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
                            for c in sanitized_token.strip()
                        ):
                            decoded_bytes = base64.b64decode(sanitized_token)
                            token_data = json.loads(decoded_bytes)
                        else:
                            raise InputValidationError(
                                "Invalid token format - not valid base64", field_name="GMAIL_TOKEN"
                            )
                    except (ValueError, json.JSONDecodeError) as decode_error:
                        raise InputValidationError(
                            "GMAIL_TOKEN format is invalid - must be valid JSON or base64-encoded JSON",
                            field_name="GMAIL_TOKEN",
                        ) from decode_error

                if not token_data:
                    raise InputValidationError(
                        "GMAIL_TOKEN could not be parsed as valid token data", field_name="GMAIL_TOKEN"
                    )

                # Create credentials directly from token - use token's original scopes
                token_scopes = token_data.get("scopes", scopes)
                creds: Credentials = Credentials.from_authorized_user_info(token_data, token_scopes)
                self.credentials = creds
                self.credentials_file_path = None  # Not needed
                return

            except InputValidationError:
                raise  # Re-raise specific validation errors
            except Exception as token_error:
                # Don't chain exception - prevents credential leakage
                raise AuthenticationFailureError(
                    "GMAIL_TOKEN validation failed - check token format and ensure valid OAuth2 credentials",
                    {
                        "error_type": type(token_error).__name__,
                        "error_hint": "Verify token is valid base64-encoded JSON with required OAuth2 fields",
                    },
                ) from None  # Note: 'from None' explicitly breaks exception chain

        # FALLBACK: File-based flow (only if no env var)
        self.credentials_file_path = Path(credentials_file_path)

        if not self.credentials_file_path.exists():
            raise AuthenticationFailureError(
                "Gmail credentials not found. Set GMAIL_TOKEN environment variable or provide valid credentials file",
                {"expected_location": str(credentials_file_path)},
            )

        # Validate credential file permissions for security
        self._validate_credential_file_permissions(self.credentials_file_path)

        # Ensure token directory exists
        self.token_file_path.parent.mkdir(parents=True, exist_ok=True)

    def get_credentials(self, force_refresh: bool = False) -> Credentials:
        """
        Get valid OAuth2 credentials, refreshing or re-authenticating as needed.

        Args:
            force_refresh: Force re-authentication even if valid token exists

        Returns:
            Valid OAuth2 credentials

        Raises:
            AuthenticationFailureError: If authentication fails
        """
        # If credentials already loaded from environment variable
        if hasattr(self, "credentials"):
            if self.credentials.expired and self.credentials.refresh_token:
                try:
                    self.credentials.refresh(Request())
                except Exception as refresh_error:
                    raise AuthenticationFailureError(
                        "Failed to refresh Gmail credentials - token may be expired or invalid",
                        {"error_type": type(refresh_error).__name__},
                    ) from refresh_error
            return self.credentials

        # File-based flow
        credentials = None

        # Load existing token if available and not forcing refresh
        if not force_refresh and self.token_file_path.exists():
            try:
                credentials = self._load_credentials_from_token_file()
            except Exception:
                # If loading fails, we'll re-authenticate
                credentials = None

        # If no valid credentials, run OAuth flow
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    self._refresh_credentials(credentials)
                except Exception:
                    # If refresh fails, re-authenticate
                    credentials = self._run_oauth_flow()
            else:
                credentials = self._run_oauth_flow()

            # Save the credentials for future runs
            self._save_credentials_to_token_file(credentials)

        return credentials

    def _load_credentials_from_token_file(self) -> Credentials:
        """
        Load credentials from saved token file.

        Returns:
            Loaded credentials

        Raises:
            AuthenticationFailureError: If token file is invalid
        """
        try:
            with open(self.token_file_path, encoding="utf-8") as token_file:
                token_data = json.load(token_file)

            credentials: Credentials = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=token_data.get("scopes"),
            )

            return credentials

        except (OSError, json.JSONDecodeError, KeyError) as load_error:
            raise AuthenticationFailureError(
                "Failed to load stored credentials - file may be corrupted or have invalid permissions",
                {"file_path": str(self.token_file_path), "error_type": type(load_error).__name__},
            ) from load_error

    def _save_credentials_to_token_file(self, credentials: Credentials) -> None:
        """
        Save credentials to token file with secure permissions.

        Uses os.open() with explicit mode 0o600 for atomic secure creation.

        Args:
            credentials: Credentials to save

        Raises:
            AuthenticationFailureError: If saving fails
        """
        try:
            token_data = {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes,
            }

            # Use os.open() with explicit mode 0o600 for atomic secure creation
            # This prevents a race condition between file creation and chmod
            fd = os.open(self.token_file_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode=0o600)

            try:
                with os.fdopen(fd, "w", encoding="utf-8") as token_file:
                    json.dump(token_data, token_file, indent=2)
            except Exception:
                # If fdopen or write fails, close the fd manually
                os.close(fd)
                raise

            # Validate the saved file permissions
            self._validate_credential_file_permissions(self.token_file_path)

        except OSError as save_error:
            raise AuthenticationFailureError(
                "Failed to save credentials to file - check directory permissions",
                {"file_path": str(self.token_file_path), "error_type": type(save_error).__name__},
            ) from save_error

    def _refresh_credentials(self, credentials: Credentials) -> None:
        """
        Refresh expired credentials using refresh token.

        Args:
            credentials: Expired credentials to refresh

        Raises:
            AuthenticationFailureError: If refresh fails
        """
        try:
            credentials.refresh(Request())
        except Exception as refresh_error:
            raise AuthenticationFailureError(
                "Failed to refresh Gmail credentials - may need to re-authenticate",
                {"error_type": type(refresh_error).__name__},
            ) from refresh_error

    def _run_oauth_flow(self) -> Credentials:
        """
        Run OAuth2 flow to get new credentials.

        Returns:
            New valid credentials

        Raises:
            AuthenticationFailureError: If OAuth flow fails
        """
        try:
            flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_file_path), self.scopes)

            # Use local server flow for better user experience
            credentials: Credentials = flow.run_local_server(port=0)

            return credentials

        except Exception as oauth_error:
            raise AuthenticationFailureError(
                "OAuth2 authentication flow failed - check credentials file and network connectivity",
                {
                    "error_type": type(oauth_error).__name__,
                    "credentials_file": str(self.credentials_file_path),
                    "scopes_count": len(self.scopes),
                },
            ) from oauth_error

    def _validate_credential_file_permissions(self, file_path: Path) -> None:
        """
        Validate that credential file has secure permissions.

        Args:
            file_path: Path to credential file to validate

        Raises:
            AuthenticationFailureError: If file permissions are insecure
        """
        try:
            file_stat = file_path.stat()
            file_mode = file_stat.st_mode & 0o777

            # Check that file is readable only by owner (0o600 or more restrictive)
            if file_mode & 0o077:  # Check if group or others have any permissions
                raise AuthenticationFailureError(
                    f"Credential file has insecure permissions: {oct(file_mode)}. "
                    "File should be readable only by owner (0o600).",
                    {"file_path": str(file_path), "current_permissions": oct(file_mode)},
                )

        except OSError as perm_error:
            raise AuthenticationFailureError(
                "Failed to validate credential file permissions",
                {"file_path": str(file_path), "error_type": type(perm_error).__name__},
            ) from perm_error
