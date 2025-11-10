"""Shared utilities for signal collectors."""

from .config import get_env_var, load_yaml_config
from .exceptions import (
    AuthenticationFailureError,
    ConfigurationInjectionError,
    ConfigurationValidationError,
    ContentProcessingError,
    InputValidationError,
    NetworkConnectionError,
    PathTraversalError,
    RateLimitExceededError,
    SecurityError,
    SignalCollectorError,
    SSRFError,
    StateManagementError,
)
from .filters import apply_content_filter, matches_keywords
from .http_client import RateLimitedHttpClient
from .output import ensure_folder_structure, update_existing_file, write_markdown_file
from .security import (
    extract_domain_from_url,
    is_safe_redirect_url,
    sanitize_filename,
    sanitize_text_content,
    validate_domain_name,
    validate_input_length,
    validate_url_for_ssrf,
)
from .storage import JsonStateManager, SqliteStateManager

__all__ = [
    "get_env_var",
    "load_yaml_config",
    "apply_content_filter",
    "matches_keywords",
    "RateLimitedHttpClient",
    "ensure_folder_structure",
    "update_existing_file",
    "write_markdown_file",
    # Security utilities
    "extract_domain_from_url",
    "is_safe_redirect_url",
    "sanitize_filename",
    "sanitize_text_content",
    "validate_domain_name",
    "validate_input_length",
    "validate_url_for_ssrf",
    # Exception types
    "AuthenticationFailureError",
    "ConfigurationInjectionError",
    "ConfigurationValidationError",
    "ContentProcessingError",
    "InputValidationError",
    "NetworkConnectionError",
    "PathTraversalError",
    "RateLimitExceededError",
    "SecurityError",
    "SignalCollectorError",
    "SSRFError",
    "StateManagementError",
    # Storage managers
    "JsonStateManager",
    "SqliteStateManager",
]
