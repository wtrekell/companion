"""CLI command for sending emails via Gmail API."""

import argparse
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

from tools._shared.exceptions import InputValidationError, PathTraversalError
from tools._shared.security import sanitize_text_content, validate_email_address

from .collector import GmailCollector
from .config import load_gmail_config


def validate_email_list(email_list: str, field_name: str = "email list") -> list[str]:
    """
    Validate and parse comma-separated email list.

    Args:
        email_list: Comma-separated email addresses
        field_name: Name of the field for error messages

    Returns:
        List of validated email addresses

    Raises:
        InputValidationError: If any email is invalid
    """
    if not email_list:
        return []

    # Split by comma and validate each email
    emails = [email.strip() for email in email_list.split(",")]
    validated_emails = []

    for i, email in enumerate(emails):
        try:
            validated_email = validate_email_address(email, f"{field_name} item {i + 1}")
            validated_emails.append(validated_email)
        except InputValidationError as validation_error:
            # Re-raise with context about which email in the list failed
            raise InputValidationError(
                f"Invalid email in {field_name}: {validation_error.error_message}",
                invalid_input=validation_error.invalid_input,
                field_name=field_name,
            ) from validation_error

    return validated_emails


def validate_file_path_safe(file_path: str, field_name: str = "file path") -> Path:
    """
    Validate file path to prevent path traversal attacks.

    Args:
        file_path: File path to validate
        field_name: Name of the field for error messages

    Returns:
        Validated Path object

    Raises:
        PathTraversalError: If path traversal attempt detected
        InputValidationError: If path is invalid
    """
    if not file_path:
        raise InputValidationError(f"{field_name} cannot be empty", field_name=field_name)

    # Sanitize path input
    sanitized_path = sanitize_text_content(file_path.strip(), max_length=4096)  # Reasonable path limit

    # Create Path object
    path_obj = Path(sanitized_path)

    # Check for path traversal attempts using Path.resolve()
    try:
        resolved_path = path_obj.resolve()
    except (OSError, ValueError) as path_error:
        raise InputValidationError(
            f"Invalid {field_name}: {path_error}",
            invalid_input=sanitized_path[:100] + "..." if len(sanitized_path) > 100 else sanitized_path,
            field_name=field_name,
        ) from path_error

    # Get current working directory for relative path validation
    cwd = Path.cwd().resolve()

    # For relative paths, ensure resolved path is within expected base directory
    if not path_obj.is_absolute():
        try:
            # Check if resolved path is within current working directory
            resolved_path.relative_to(cwd)
        except ValueError as path_error:
            # Path escaped outside working directory
            raise PathTraversalError(
                f"Path traversal detected in {field_name}: resolved outside working directory",
                attempted_path=sanitized_path[:100] + "..." if len(sanitized_path) > 100 else sanitized_path,
            ) from path_error

    # Ensure resolved path is not in sensitive system directories
    sensitive_paths = [
        "/etc",
        "/bin",
        "/sbin",
        "/usr/bin",
        "/usr/sbin",
        "/root",
        "/boot",
        "/sys",
        "/proc",
        "/dev",
        "/run",
    ]
    path_str = str(resolved_path)
    for sensitive in sensitive_paths:
        if path_str.startswith(sensitive):
            raise PathTraversalError(f"Access to sensitive path denied: {field_name}", attempted_path=sensitive)

    return resolved_path


def create_send_parser() -> argparse.ArgumentParser:
    """
    Create argument parser for Gmail send command.

    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Send emails via Gmail API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  signal-gmail-send --to recipient@example.com --subject "Test" --body "Hello!"
  signal-gmail-send --to user@domain.com --subject "Important" --body "Message" --cc cc@domain.com
  signal-gmail-send --forward MESSAGE_ID --to recipient@example.com --additional-body "FYI:"
        """,
    )

    # Configuration
    parser.add_argument(
        "--config",
        type=str,
        default="tools/gmail/settings/gmail.yaml",
        help="Gmail configuration file path (default: tools/gmail/settings/gmail.yaml)",
    )

    # Email sending arguments
    send_group = parser.add_argument_group("Email Sending")
    send_group.add_argument("--to", type=str, required=True, help="Recipient email address")
    send_group.add_argument("--subject", type=str, help="Email subject line")
    send_group.add_argument("--body", type=str, help="Email body content")
    send_group.add_argument(
        "--from", dest="from_email", type=str, help="Sender email address (defaults to authenticated account)"
    )
    send_group.add_argument("--cc", type=str, help="CC recipients (comma-separated)")
    send_group.add_argument("--bcc", type=str, help="BCC recipients (comma-separated)")
    send_group.add_argument("--reply-to", type=str, help="Reply-to email address")

    # Forwarding arguments
    forward_group = parser.add_argument_group("Email Forwarding")
    forward_group.add_argument("--forward", type=str, metavar="MESSAGE_ID", help="Forward an existing message by ID")
    forward_group.add_argument("--additional-body", type=str, help="Additional text to add before forwarded content")

    # Input options
    input_group = parser.add_argument_group("Input Options")
    input_group.add_argument("--body-file", type=str, help="Read email body from file")

    # Options
    parser.add_argument("--dry-run", action="store_true", help="Show what would be sent without actually sending")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    return parser


def validate_send_arguments(args: argparse.Namespace) -> None:
    """
    Validate command line arguments for sending with security checks.

    Args:
        args: Parsed command line arguments

    Raises:
        SystemExit: If validation fails
    """
    try:
        # Validate recipient email address (required for all modes)
        if not args.to:
            raise InputValidationError("Recipient email address (--to) is required", field_name="to")
        args.to = validate_email_address(args.to, "recipient email")

        # Validate optional email addresses
        if args.from_email:
            args.from_email = validate_email_address(args.from_email, "sender email")

        if args.cc:
            validated_cc = validate_email_list(args.cc, "CC recipients")
            args.cc = ",".join(validated_cc)

        if args.bcc:
            validated_bcc = validate_email_list(args.bcc, "BCC recipients")
            args.bcc = ",".join(validated_bcc)

        if args.reply_to:
            args.reply_to = validate_email_address(args.reply_to, "reply-to email")

        # Validate forwarding vs regular sending requirements
        if args.forward:
            # Forwarding mode - validate message ID format
            if not args.forward or not isinstance(args.forward, str):
                raise InputValidationError("Message ID for forwarding is required", field_name="forward")
            # Sanitize message ID (Gmail message IDs are alphanumeric)
            args.forward = sanitize_text_content(args.forward.strip(), max_length=100)
            if not re.match(r"^[a-zA-Z0-9_-]+$", args.forward):
                raise InputValidationError("Invalid message ID format", field_name="forward")
        else:
            # Regular sending mode - need subject and body
            if not args.subject:
                raise InputValidationError("Subject is required for sending new emails", field_name="subject")

            # Sanitize subject
            args.subject = sanitize_text_content(args.subject, max_length=998)  # RFC 2822 limit

            if not args.body and not args.body_file:
                raise InputValidationError("Either --body or --body-file is required", field_name="body")

            if args.body and args.body_file:
                raise InputValidationError("Cannot specify both --body and --body-file", field_name="body")

        # Sanitize additional body content if present
        if args.additional_body:
            args.additional_body = sanitize_text_content(args.additional_body, max_length=50000)  # Reasonable limit

    except (InputValidationError, PathTraversalError) as validation_error:
        print(f"Validation Error: {validation_error.error_message}", file=sys.stderr)
        sys.exit(1)


def read_body_content(args: argparse.Namespace) -> str:
    """
    Read email body content from arguments or file with security validation.

    Args:
        args: Parsed command line arguments

    Returns:
        Sanitized email body content

    Raises:
        SystemExit: If file reading fails or security validation fails
    """
    try:
        if args.body:
            # Sanitize direct body content
            return sanitize_text_content(args.body, max_length=100000)  # Reasonable email body limit

        if args.body_file:
            # Validate file path for security
            secure_path = validate_file_path_safe(args.body_file, "body file")

            if not secure_path.exists():
                raise InputValidationError(f"Body file not found: {secure_path}", field_name="body_file")

            # Check file is actually a file (not directory)
            if not secure_path.is_file():
                raise InputValidationError(
                    f"Body file path is not a regular file: {secure_path}", field_name="body_file"
                )

            # Check file size is reasonable (prevent memory exhaustion)
            file_size = secure_path.stat().st_size
            max_file_size = 10 * 1024 * 1024  # 10MB limit
            if file_size > max_file_size:
                raise InputValidationError(
                    f"Body file too large: {file_size} bytes (max {max_file_size})", field_name="body_file"
                )

            # Read and sanitize file content
            file_content = secure_path.read_text(encoding="utf-8", errors="replace")
            return sanitize_text_content(file_content, max_length=100000)

        return ""

    except (InputValidationError, PathTraversalError) as security_error:
        print(f"Security Error: {security_error.error_message}", file=sys.stderr)
        sys.exit(1)
    except OSError as file_error:
        print(f"File Error: Unable to read body file - {file_error}", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError as decode_error:
        print(f"Encoding Error: Body file contains invalid UTF-8 content - {decode_error}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main CLI entry point for Gmail sending."""
    # Load environment variables
    load_dotenv()

    # Parse arguments
    parser = create_send_parser()
    args = parser.parse_args()

    # Validate arguments
    validate_send_arguments(args)

    try:
        # Load configuration
        if args.verbose:
            print(f"Loading configuration from: {args.config}")

        config = load_gmail_config(args.config)

        # Initialize collector
        if args.verbose:
            print("Initializing Gmail collector...")

        collector = GmailCollector(config)

        if args.forward:
            # Forward existing message
            if args.verbose:
                print(f"Forwarding message {args.forward} to {args.to}")

            if args.dry_run:
                print("DRY RUN: Would forward message")
                print(f"  Message ID: {args.forward}")
                print(f"  To: {args.to}")
                if args.additional_body:
                    print(f"  Additional body: {args.additional_body}")
                if args.from_email:
                    print(f"  From: {args.from_email}")
                return

            success = collector.forward_email(
                message_id=args.forward, to=args.to, additional_body=args.additional_body, from_email=args.from_email
            )

            if success:
                print("Email forwarded successfully")
            else:
                print("Failed to forward email", file=sys.stderr)
                sys.exit(1)

        else:
            # Send new message
            body_content = read_body_content(args)

            if args.verbose:
                print(f"Sending email to {args.to}")
                print(f"Subject: {args.subject}")

            if args.dry_run:
                print("DRY RUN: Would send email")
                print(f"  To: {args.to}")
                print(f"  Subject: {args.subject}")
                print(f"  Body: {body_content[:100]}{'...' if len(body_content) > 100 else ''}")
                if args.from_email:
                    print(f"  From: {args.from_email}")
                if args.cc:
                    print(f"  CC: {args.cc}")
                if args.bcc:
                    print(f"  BCC: {args.bcc}")
                if args.reply_to:
                    print(f"  Reply-To: {args.reply_to}")
                return

            success = collector.send_email(
                to=args.to,
                subject=args.subject,
                body=body_content,
                from_email=args.from_email,
                cc=args.cc,
                bcc=args.bcc,
                reply_to=args.reply_to,
            )

            if success:
                print("Email sent successfully")
            else:
                print("Failed to send email", file=sys.stderr)
                sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
