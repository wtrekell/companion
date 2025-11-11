"""Minimal security utilities for content collectors.

For personal use on local machine + GitHub Actions.
Just filesystem safety - no SSRF, injection, or validation theater.
"""


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename to be safe for filesystem use.

    Args:
        filename: Original filename
        max_length: Maximum allowed filename length

    Returns:
        Sanitized filename safe for filesystem use
    """
    if not filename:
        return "unnamed_file"

    # Remove or replace dangerous filesystem characters
    dangerous_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*", "\0"]
    sanitized = filename
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "_")

    # Remove control characters
    sanitized = "".join(char for char in sanitized if ord(char) >= 32)

    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(" .")

    if not sanitized:
        sanitized = "unnamed_file"

    # Truncate if too long while preserving extension
    if len(sanitized) > max_length:
        if "." in sanitized:
            name, extension = sanitized.rsplit(".", 1)
            max_name_length = max_length - len(extension) - 1
            if max_name_length > 0:
                sanitized = f"{name[:max_name_length]}.{extension}"
            else:
                sanitized = sanitized[:max_length]
        else:
            sanitized = sanitized[:max_length]

    return sanitized


# Backwards compatibility stubs - no validation needed for personal use
def sanitize_text_content(content: str, max_length: int | None = None) -> str:
    """Passthrough - no sanitization needed."""
    if not content:
        return ""
    if max_length and len(content) > max_length:
        return content[:max_length]
    return content


def validate_email_address(email: str, field_name: str = "email") -> str:
    """Basic email check."""
    email = email.strip()
    if not email or "@" not in email:
        raise ValueError(f"Invalid {field_name}: must contain @")
    return email


def validate_url_for_ssrf(url: str, allow_private_ips: bool = False) -> bool:
    """Passthrough - no SSRF protection needed."""
    return True


def validate_input_length(input_value: str, max_length: int, field_name: str = "input") -> str:
    """Simple truncation."""
    if input_value and len(input_value) > max_length:
        return input_value[:max_length]
    return input_value if input_value else ""


def validate_domain_name(domain: str) -> bool:
    """Passthrough."""
    return bool(domain and domain.strip())


def extract_domain_from_url(url: str) -> str | None:
    """Simple domain extraction."""
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
        return parsed.hostname
    except Exception:
        return None


def escape_markdown_special_chars(text: str) -> str:
    """Passthrough."""
    return text if text else ""


def is_safe_redirect_url(url: str, allowed_domains: set[str] | None = None) -> bool:
    """Passthrough."""
    return True
