"""Configuration classes for Gmail collector.

This module defines typed configuration structures for Gmail collection settings.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from tools._shared.config import load_yaml_config
from tools._shared.exceptions import ConfigurationValidationError
from tools._shared.security import sanitize_text_content


def validate_gmail_query_syntax(query: str) -> str:
    """
    Validate Gmail query syntax and sanitize for security.

    Args:
        query: Gmail search query to validate

    Returns:
        Validated and sanitized query

    Raises:
        ConfigurationValidationError: If query contains dangerous patterns
    """
    if not query:
        raise ConfigurationValidationError("Gmail query cannot be empty")

    # Sanitize query content - Gmail's actual limit is 1000 characters
    sanitized_query = sanitize_text_content(query.strip(), max_length=1000)  # Gmail query limit

    # Check for potential injection patterns
    dangerous_patterns = [
        r'[<>"\\\n\r\t]',  # HTML/injection characters
        r"javascript:",  # JavaScript injection
        r"data:",  # Data URI injection
        r"\.\./",  # Path traversal
        r"<script",  # Script injection
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, sanitized_query, re.IGNORECASE):
            raise ConfigurationValidationError(
                f"Gmail query contains potentially dangerous pattern: {pattern}", {"query": sanitized_query[:100]}
            )

    # Validate Gmail-specific operators are reasonable
    valid_operators = {
        "from:",
        "to:",
        "subject:",
        "label:",
        "has:",
        "is:",
        "in:",
        "after:",
        "before:",
        "newer:",
        "older:",
        "category:",
        "size:",
        "larger:",
        "smaller:",
        "filename:",
        "cc:",
        "bcc:",
        "deliveredto:",
    }

    # Extract operators and validate
    operators_found = re.findall(r"(\w+:)", sanitized_query)
    invalid_operators = [op for op in operators_found if op not in valid_operators]

    if invalid_operators:
        raise ConfigurationValidationError(
            f"Gmail query contains invalid operators: {invalid_operators}", {"valid_operators": list(valid_operators)}
        )

    # Check for bare email addresses without operators
    email_pattern = r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
    potential_emails = re.findall(email_pattern, sanitized_query)

    for email in potential_emails:
        # Check if this email appears with a valid operator
        email_with_operator = False
        for operator in valid_operators:
            if f"{operator}{email}" in sanitized_query or f'{operator}"{email}"' in sanitized_query:
                email_with_operator = True
                break

        if not email_with_operator:
            raise ConfigurationValidationError(
                f"Email address '{email}' must be used with an operator (e.g., 'from:{email}', 'to:{email}')",
                {
                    "bare_email": email,
                    "suggestion": f"Use 'from:{email}' or 'to:{email}' instead",
                    "valid_operators": ["from:", "to:", "cc:", "bcc:", "deliveredto:"],
                },
            )

    return sanitized_query


def validate_gmail_action(action: str) -> str:
    """
    Validate Gmail rule action format.

    Args:
        action: Action string to validate

    Returns:
        Validated action string

    Raises:
        ConfigurationValidationError: If action format is invalid
    """
    if not action:
        raise ConfigurationValidationError("Action cannot be empty")

    # Sanitize action
    sanitized_action = sanitize_text_content(action.strip(), max_length=200)

    # Define valid action patterns
    valid_actions = [
        "save",  # Save message
        "archive",  # Archive message
        "mark_read",  # Mark as read
        "delete",  # Move to trash
        "delete_permanent",  # Permanently delete
    ]

    # Actions with parameters
    # Note: Label naming conventions:
    # - Use forward slashes (/) for nesting (e.g., "label:parent/child")
    # - Alphanumeric, underscore, dash, and slash characters are allowed
    # - Nested labels are created automatically by Gmail when using "/"
    valid_parametrized_actions = {
        "label:": r"^label:[a-zA-Z0-9_\-/]+$",  # Add label (use / for nesting, e.g., label:parent/child)
        "remove_label:": r"^remove_label:[a-zA-Z0-9_\-/]+$",  # Remove label
        "forward:": r"^forward:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",  # Forward to email
    }

    # Check if it's a simple action
    if sanitized_action in valid_actions:
        return sanitized_action

    # Check parametrized actions
    for action_prefix, pattern in valid_parametrized_actions.items():
        if sanitized_action.startswith(action_prefix):
            if re.match(pattern, sanitized_action):
                return sanitized_action
            else:
                raise ConfigurationValidationError(
                    f"Invalid {action_prefix} action format: {sanitized_action}", {"expected_pattern": pattern}
                )

    # If we get here, action is invalid
    all_valid = valid_actions + list(valid_parametrized_actions.keys())
    raise ConfigurationValidationError(f"Invalid action: {sanitized_action}", {"valid_actions": all_valid})


def validate_label_name(label_name: str) -> str:
    """
    Validate Gmail label name format.

    Gmail label naming rules:
    - Alphanumeric, dash, underscore, slash (for nesting)
    - No special characters like <, >, etc.
    - Max length: 100 characters
    - Case-insensitive (normalized to lowercase for consistency)

    Args:
        label_name: Label name to validate

    Returns:
        Validated and normalized label name

    Raises:
        ConfigurationValidationError: If label name is invalid
    """
    if not label_name:
        raise ConfigurationValidationError("Label name cannot be empty")

    # Sanitize label name
    sanitized = sanitize_text_content(label_name.strip(), max_length=100)

    # Gmail allows: alphanumeric, dash, underscore, slash (for nesting)
    if not re.match(r"^[a-zA-Z0-9_\-/]+$", sanitized):
        raise ConfigurationValidationError(
            f"Invalid label name: {sanitized}",
            {"allowed_chars": "letters, numbers, dash, underscore, slash (for nesting)"},
        )

    # Normalize to lowercase (Gmail labels are case-insensitive)
    return sanitized.lower()


def validate_file_path_config(file_path: str, path_type: str) -> str:
    """
    Validate file path configuration for security.

    Args:
        file_path: File path to validate
        path_type: Type of path (for error messages)

    Returns:
        Validated file path

    Raises:
        ConfigurationValidationError: If path is unsafe
    """
    if not file_path:
        raise ConfigurationValidationError(f"{path_type} path cannot be empty")

    # Sanitize path
    sanitized_path = sanitize_text_content(file_path.strip(), max_length=4096)

    # Check for path traversal attempts
    dangerous_patterns = ["../", "..\\", "~/", "$HOME", "${"]
    for pattern in dangerous_patterns:
        if pattern in sanitized_path:
            raise ConfigurationValidationError(
                f"{path_type} path contains dangerous pattern: {pattern}", {"path": sanitized_path}
            )

    # Ensure path is relative and reasonable
    try:
        path_obj = Path(sanitized_path)
        if path_obj.is_absolute():
            # Allow specific absolute paths that are safe
            allowed_absolute_prefixes = ["/tmp/", "/var/tmp/", "/home/", "/Users/"]
            if not any(str(path_obj).startswith(prefix) for prefix in allowed_absolute_prefixes):
                raise ConfigurationValidationError(
                    f"{path_type} absolute path not in allowed locations",
                    {"path": sanitized_path, "allowed_prefixes": allowed_absolute_prefixes},
                )

        # Check for dangerous absolute system paths
        dangerous_paths = ["/etc/", "/bin/", "/sbin/", "/usr/bin/", "/usr/sbin/", "/root/", "/boot/"]
        path_str = str(path_obj.resolve())
        for dangerous in dangerous_paths:
            if path_str.startswith(dangerous):
                raise ConfigurationValidationError(
                    f"{path_type} path attempts to access sensitive system directory", {"attempted_path": dangerous}
                )

    except Exception as path_error:
        raise ConfigurationValidationError(
            f"Invalid {path_type} path format: {path_error}", {"path": sanitized_path}
        ) from path_error

    return sanitized_path


def validate_scopes_list(scopes: list[str]) -> list[str]:
    """
    Validate Gmail OAuth scopes for security.

    Args:
        scopes: List of OAuth scopes

    Returns:
        Validated list of scopes

    Raises:
        ConfigurationValidationError: If scopes contain dangerous permissions
    """
    if not scopes:
        raise ConfigurationValidationError("OAuth scopes list cannot be empty")

    # Define allowed Gmail API scopes
    allowed_scopes = {
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.labels",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
    }

    validated_scopes = []
    for scope in scopes:
        if not isinstance(scope, str):
            raise ConfigurationValidationError(f"Scope must be string: {type(scope)}")

        sanitized_scope = sanitize_text_content(scope.strip(), max_length=200)

        if sanitized_scope not in allowed_scopes:
            raise ConfigurationValidationError(
                f"Invalid or dangerous OAuth scope: {sanitized_scope}", {"allowed_scopes": list(allowed_scopes)}
            )

        validated_scopes.append(sanitized_scope)

    return validated_scopes


@dataclass
class FilterCriteria:
    """Content filtering criteria for Gmail messages."""

    max_age_days: int | None = None
    include_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)


@dataclass
class GmailRule:
    """Configuration for a Gmail processing rule."""

    name: str
    query: str
    actions: list[str] = field(default_factory=list)  # e.g., ["archive", "save", "label:important"]
    filters: FilterCriteria | None = None
    save_attachments: bool = True
    max_messages: int = 100


@dataclass
class GmailLabelRule:
    """Configuration for a label-based trigger rule.

    Label rules monitor for manually applied labels and trigger actions
    when those labels are detected on emails.
    """

    name: str  # Descriptive name for the rule
    trigger_label: str  # Label to watch for (e.g., "to-archive")
    actions: list[str] = field(default_factory=list)  # Actions to perform when label detected
    remove_trigger: bool = True  # Remove trigger label after processing
    filters: FilterCriteria | None = None  # Optional content filtering
    save_attachments: bool = True  # Download attachments if "save" action included
    max_messages: int = 50  # Max messages to process per run (lower than query rules)


@dataclass
class GmailCollectorConfig:
    """Main configuration for Gmail collector.

    Filtering cascade (all levels UNION together):
    1. default_filters: Keywords from this config (all Gmail rules)
    2. rule.filters: Keywords for specific Gmail rule
    """

    output_dir: str
    token_file: str = "./data/gmail_token.json"
    credentials_file: str = "./data/gmail_credentials.json"
    rate_limit_seconds: float = 1.0
    default_filters: FilterCriteria = field(default_factory=FilterCriteria)
    rules: list[GmailRule] = field(default_factory=list)
    label_rules: list[GmailLabelRule] = field(default_factory=list)  # Label-based trigger rules

    # Gmail API settings
    scopes: list[str] = field(
        default_factory=lambda: [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.labels",
            "https://www.googleapis.com/auth/gmail.send",
        ]
    )
    batch_size: int = 50  # Recommended: 50 (values >100 may cause rate limiting)

    # Retry configuration for transient errors
    retry_base_delay: float = 1.0  # Base delay in seconds for exponential backoff
    retry_max_attempts: int = 3  # Maximum number of retry attempts

    # Attachment settings
    max_attachment_size: int = 25 * 1024 * 1024  # 25MB limit (Gmail's attachment size limit)


def load_gmail_config(config_path: str) -> GmailCollectorConfig:
    """
    Load Gmail collector configuration from YAML file with comprehensive security validation.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Parsed configuration object

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        ConfigurationValidationError: If configuration is invalid or insecure
    """
    try:
        raw_config = load_yaml_config(config_path)
    except Exception as load_error:
        raise ConfigurationValidationError(
            f"Failed to load Gmail configuration: {load_error}", {"config_path": config_path}
        ) from load_error

    # Parse default filters
    default_filters_data = raw_config.get("default_filters", {})
    default_filters = FilterCriteria(
        max_age_days=default_filters_data.get("max_age_days"),
        include_keywords=default_filters_data.get("include_keywords", []),
        exclude_keywords=default_filters_data.get("exclude_keywords", []),
    )

    # Parse Gmail rules with security validation
    rules = []
    for rule_index, rule_data in enumerate(raw_config.get("rules", [])):
        try:
            # Validate required fields
            if "name" not in rule_data:
                raise ConfigurationValidationError(f"Rule at index {rule_index} is missing required 'name' field")
            if "query" not in rule_data:
                raise ConfigurationValidationError(
                    f"Rule '{rule_data.get('name', 'unnamed')}' is missing required 'query' field"
                )

            # Sanitize and validate rule name
            rule_name = sanitize_text_content(rule_data["name"].strip(), max_length=100)
            if not rule_name:
                raise ConfigurationValidationError(f"Rule at index {rule_index} has empty name")

            # Validate Gmail query syntax
            validated_query = validate_gmail_query_syntax(rule_data["query"])

            # Validate actions
            validated_actions = []
            for action in rule_data.get("actions", []):
                validated_action = validate_gmail_action(action)
                validated_actions.append(validated_action)

            # Parse rule-specific filters if present
            rule_filters = None
            if "filters" in rule_data:
                filter_data = rule_data["filters"]
                rule_filters = FilterCriteria(
                    max_age_days=filter_data.get("max_age_days"),
                    include_keywords=filter_data.get("include_keywords", []),
                    exclude_keywords=filter_data.get("exclude_keywords", []),
                )

            # Validate numeric parameters
            max_messages = rule_data.get("max_messages", 100)
            if not isinstance(max_messages, int) or max_messages <= 0 or max_messages > 500:
                raise ConfigurationValidationError(
                    f"Rule '{rule_name}' max_messages must be positive integer <= 500 "
                    "(values >100 may cause rate limiting)",
                    {"current_value": max_messages},
                )

            rule_config = GmailRule(
                name=rule_name,
                query=validated_query,
                actions=validated_actions,
                filters=rule_filters,
                save_attachments=bool(rule_data.get("save_attachments", True)),
                max_messages=max_messages,
            )
            rules.append(rule_config)

        except ConfigurationValidationError:
            raise  # Re-raise configuration errors
        except Exception as rule_error:
            raise ConfigurationValidationError(
                f"Failed to parse rule at index {rule_index}: {rule_error}", {"rule_data": str(rule_data)[:200]}
            ) from rule_error

    # Parse label-based trigger rules with security validation
    label_rules = []
    for rule_index, rule_data in enumerate(raw_config.get("label_rules", [])):
        try:
            # Validate required fields
            if "name" not in rule_data:
                raise ConfigurationValidationError(
                    f"Label rule at index {rule_index} is missing required 'name' field"
                )
            if "trigger_label" not in rule_data:
                raise ConfigurationValidationError(
                    f"Label rule '{rule_data.get('name', 'unnamed')}' is missing required 'trigger_label' field"
                )

            # Sanitize and validate rule name
            rule_name = sanitize_text_content(rule_data["name"].strip(), max_length=100)
            if not rule_name:
                raise ConfigurationValidationError(f"Label rule at index {rule_index} has empty name")

            # Validate trigger label name
            validated_trigger_label = validate_label_name(rule_data["trigger_label"])

            # Validate actions
            validated_actions = []
            for action in rule_data.get("actions", []):
                validated_action = validate_gmail_action(action)
                validated_actions.append(validated_action)

            if not validated_actions:
                raise ConfigurationValidationError(
                    f"Label rule '{rule_name}' must have at least one action", {"rule_name": rule_name}
                )

            # Parse rule-specific filters if present
            rule_filters = None
            if "filters" in rule_data:
                filter_data = rule_data["filters"]
                rule_filters = FilterCriteria(
                    max_age_days=filter_data.get("max_age_days"),
                    include_keywords=filter_data.get("include_keywords", []),
                    exclude_keywords=filter_data.get("exclude_keywords", []),
                )

            # Validate numeric parameters
            max_messages = rule_data.get("max_messages", 50)
            if not isinstance(max_messages, int) or max_messages <= 0 or max_messages > 500:
                raise ConfigurationValidationError(
                    f"Label rule '{rule_name}' max_messages must be positive integer <= 500",
                    {"current_value": max_messages},
                )

            label_rule_config = GmailLabelRule(
                name=rule_name,
                trigger_label=validated_trigger_label,
                actions=validated_actions,
                remove_trigger=bool(rule_data.get("remove_trigger", True)),
                filters=rule_filters,
                save_attachments=bool(rule_data.get("save_attachments", True)),
                max_messages=max_messages,
            )
            label_rules.append(label_rule_config)

        except ConfigurationValidationError:
            raise  # Re-raise configuration errors
        except Exception as rule_error:
            raise ConfigurationValidationError(
                f"Failed to parse label rule at index {rule_index}: {rule_error}",
                {"rule_data": str(rule_data)[:200]},
            ) from rule_error

    # Build main configuration with security validation
    try:
        # Validate required main config fields
        if "output_dir" not in raw_config:
            raise ConfigurationValidationError("Missing required 'output_dir' field in Gmail configuration")

        # Validate and sanitize paths
        output_dir = sanitize_text_content(raw_config["output_dir"].strip(), max_length=4096)
        token_file = validate_file_path_config(raw_config.get("token_file", "./data/gmail_token.json"), "token file")
        credentials_file = validate_file_path_config(
            raw_config.get("credentials_file", "./data/gmail_credentials.json"), "credentials file"
        )

        # Validate rate limit
        rate_limit = raw_config.get("rate_limit_seconds", 1.0)
        if not isinstance(rate_limit, (int, float)) or rate_limit < 0.1 or rate_limit > 60:
            raise ConfigurationValidationError(
                "rate_limit_seconds must be a number between 0.1 and 60", {"current_value": rate_limit}
            )

        # Validate batch size
        batch_size = raw_config.get("batch_size", 50)
        if not isinstance(batch_size, int) or batch_size <= 0 or batch_size > 100:
            raise ConfigurationValidationError(
                "batch_size must be positive integer <= 100 (recommended: 50 to avoid rate limiting)",
                {"current_value": batch_size},
            )

        # Validate OAuth scopes
        scopes = raw_config.get(
            "scopes",
            [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/gmail.labels",
                "https://www.googleapis.com/auth/gmail.send",
            ],
        )
        validated_scopes = validate_scopes_list(scopes)

        config = GmailCollectorConfig(
            output_dir=output_dir,
            token_file=token_file,
            credentials_file=credentials_file,
            rate_limit_seconds=float(rate_limit),
            default_filters=default_filters,
            rules=rules,
            label_rules=label_rules,
            scopes=validated_scopes,
            batch_size=batch_size,
        )

        return config

    except ConfigurationValidationError:
        raise  # Re-raise configuration validation errors
    except Exception as config_error:
        raise ConfigurationValidationError(
            f"Failed to build Gmail configuration: {config_error}", {"config_file": config_path}
        ) from config_error
