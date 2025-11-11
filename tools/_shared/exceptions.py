"""Exception types for content collectors.

Simplified for personal use - 4 basic types.
"""

from typing import Any


class CollectorError(Exception):
    """Base exception for all collector errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None, **kwargs: Any):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        # Store any extra kwargs for backward compatibility
        for key, value in kwargs.items():
            setattr(self, key, value)


class ConfigError(CollectorError):
    """Configuration or validation errors."""

    pass


class AuthError(CollectorError):
    """Authentication failures."""

    pass


class NetworkError(CollectorError):
    """Network and API errors."""

    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        super().__init__(message, context, **kwargs)
        self.retry_after = retry_after


# Backwards compatibility aliases
SignalCollectorError = CollectorError
ConfigurationValidationError = ConfigError
AuthenticationFailureError = AuthError
RateLimitExceededError = NetworkError
ContentProcessingError = CollectorError
StateManagementError = CollectorError
NetworkConnectionError = NetworkError
SecurityError = CollectorError
SSRFError = CollectorError
PathTraversalError = CollectorError
InputValidationError = ConfigError
ConfigurationInjectionError = ConfigError
