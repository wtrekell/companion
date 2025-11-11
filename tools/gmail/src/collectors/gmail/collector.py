"""Gmail collector for Signal system.

This module provides Gmail content collection functionality using the Gmail API.
"""

import base64
import email.utils
import logging
import random
import time
from datetime import UTC, datetime
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from tools._shared.exceptions import (
    AuthenticationFailureError,
    ContentProcessingError,
    NetworkConnectionError,
    StateManagementError,
)
from tools._shared.filters import apply_content_filter
from tools._shared.output import ensure_folder_structure, write_markdown_file
from tools._shared.security import sanitize_filename
from tools._shared.storage import JsonStateManager

from .auth import GmailAuthenticator
from .config import GmailCollectorConfig, GmailRule


class GmailCollector:
    """Gmail content collector using Gmail API.

    Supports context manager protocol for proper resource cleanup:
        with GmailCollector(config) as collector:
            stats = collector.collect_all_rules()
    """

    # Dangerous file extensions that should never be saved
    DANGEROUS_EXTENSIONS = {
        ".exe",
        ".bat",
        ".sh",
        ".cmd",
        ".com",
        ".scr",
        ".vbs",
        ".js",
        ".jar",
        ".msi",
        ".app",
        ".deb",
        ".rpm",
        ".dll",
        ".so",
        ".dylib",
        ".ps1",
        ".psm1",
    }

    def __init__(self, config: GmailCollectorConfig):
        """
        Initialize Gmail collector.

        Args:
            config: Gmail collector configuration

        Raises:
            CollectionError: If initialization fails
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Ensure output directory exists for state file
        # State file is stored in output directory to be tracked by git (not in data/ which is gitignored)
        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.state_manager = JsonStateManager(str(output_dir / ".gmail_state.json"))

        try:
            # Initialize authenticator
            self.authenticator = GmailAuthenticator(config.credentials_file, config.token_file, config.scopes)

            # Get credentials and build service
            credentials = self.authenticator.get_credentials()
            self.service = build("gmail", "v1", credentials=credentials)

        except AuthenticationFailureError as auth_error:
            raise ContentProcessingError(
                f"Gmail authentication failed: {auth_error}", {"original_error": str(auth_error)}
            ) from auth_error
        except Exception as init_error:
            raise ContentProcessingError(
                f"Failed to initialize Gmail collector: {init_error}", {"original_error": str(init_error)}
            ) from init_error

    def __enter__(self) -> "GmailCollector":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and cleanup resources."""
        self.close()

    def close(self) -> None:
        """Clean up resources (primarily for context manager support)."""
        # Gmail API service doesn't require explicit cleanup
        # This method is provided for future enhancements and consistency
        pass

    def _execute_with_retry(
        self, api_call_func: Any, max_retries: int | None = None, base_delay: float | None = None
    ) -> Any:
        """
        Execute API call with exponential backoff retry logic.

        Args:
            api_call_func: Function that makes the API call
            max_retries: Maximum number of retry attempts (defaults to config value)
            base_delay: Base delay in seconds for exponential backoff (defaults to config value)

        Returns:
            Result of the API call

        Raises:
            NetworkConnectionError: If all retry attempts fail
        """
        # Use config values if not overridden
        if max_retries is None:
            max_retries = self.config.retry_max_attempts
        if base_delay is None:
            base_delay = self.config.retry_base_delay

        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return api_call_func()
            except HttpError as api_error:
                last_error = api_error
                status_code = api_error.resp.status

                # Check if this is a transient error that should be retried
                if status_code in (429, 500, 502, 503, 504):
                    if attempt < max_retries:
                        # Exponential backoff with jitter
                        delay = base_delay * (2**attempt) + random.uniform(0, 1)
                        self.logger.warning(
                            f"API call failed with status {status_code}, retrying in {delay:.1f}s "
                            f"(attempt {attempt + 1}/{max_retries + 1})"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        self.logger.error(f"API call failed after {max_retries + 1} attempts with status {status_code}")
                        break
                else:
                    # Non-transient error, don't retry
                    self.logger.error(f"API call failed with non-retryable status {status_code}: {api_error}")
                    break
            except Exception as unexpected_error:
                last_error = unexpected_error
                self.logger.error(f"Unexpected error in API call: {unexpected_error}")
                break

        # All retries failed
        raise NetworkConnectionError(
            f"API call failed after {max_retries + 1} attempts",
            {"original_error": str(last_error), "failed_attempts": max_retries + 1},
        ) from last_error

    def collect_all_rules(self) -> dict[str, Any]:
        """
        Collect emails from all configured rules (both query-based and label-based).

        Returns:
            Dictionary containing collection statistics for all rule types

        Raises:
            ContentProcessingError: If collection fails
        """
        overall_stats: dict[str, Any] = {
            "rules_processed": 0,
            "label_rules_processed": 0,
            "total_messages_processed": 0,
            "total_messages_saved": 0,
            "total_messages_skipped": 0,
            "total_actions_applied": 0,
            "total_actions_failed": 0,
            "total_trigger_labels_removed": 0,
            "total_errors": 0,
            "rule_stats": [],
            "label_rule_stats": [],
        }

        # Process query-based rules
        for rule in self.config.rules:
            try:
                rule_stats = self.collect_rule(rule)
                overall_stats["rules_processed"] += 1
                overall_stats["total_messages_processed"] += rule_stats["messages_processed"]
                overall_stats["total_messages_saved"] += rule_stats["messages_saved"]
                overall_stats["total_messages_skipped"] += rule_stats["messages_skipped"]
                overall_stats["total_actions_applied"] += rule_stats["actions_applied"]
                overall_stats["total_actions_failed"] += rule_stats["actions_failed"]
                overall_stats["total_errors"] += rule_stats["errors"]
                overall_stats["rule_stats"].append({"rule": rule.name, **rule_stats})

                # Rate limiting between rules
                time.sleep(self.config.rate_limit_seconds)

            except Exception as rule_error:
                overall_stats["total_errors"] += 1
                overall_stats["rule_stats"].append(
                    {
                        "rule": rule.name,
                        "messages_processed": 0,
                        "messages_saved": 0,
                        "messages_skipped": 0,
                        "actions_applied": 0,
                        "actions_failed": 0,
                        "errors": 1,
                        "error_message": str(rule_error),
                    }
                )

        # Process label-based trigger rules
        if self.config.label_rules:
            self.logger.info(f"\n{'=' * 60}")
            self.logger.info("Processing label-based trigger rules")
            self.logger.info(f"{'=' * 60}\n")

            label_rules_stats = self.collect_label_rules()
            overall_stats["label_rules_processed"] = label_rules_stats["label_rules_processed"]
            overall_stats["total_messages_processed"] += label_rules_stats["total_messages_processed"]
            overall_stats["total_messages_saved"] += label_rules_stats["total_messages_saved"]
            overall_stats["total_messages_skipped"] += label_rules_stats["total_messages_skipped"]
            overall_stats["total_actions_applied"] += label_rules_stats["total_actions_applied"]
            overall_stats["total_actions_failed"] += label_rules_stats["total_actions_failed"]
            overall_stats["total_trigger_labels_removed"] = label_rules_stats["total_trigger_labels_removed"]
            overall_stats["total_errors"] += label_rules_stats["total_errors"]
            overall_stats["label_rule_stats"] = label_rules_stats["label_rule_stats"]

        return overall_stats

    def collect_rule(self, rule: GmailRule) -> dict[str, Any]:
        """
        Collect emails for a specific rule.

        Args:
            rule: Gmail rule configuration

        Returns:
            Dictionary containing collection statistics for this rule

        Raises:
            ContentProcessingError: If rule collection fails
        """
        stats = {
            "messages_processed": 0,
            "messages_saved": 0,
            "messages_skipped": 0,
            "actions_applied": 0,
            "actions_failed": 0,
            "errors": 0,
        }

        try:
            # Use atomic state update to prevent race conditions
            def process_messages_with_state_update() -> dict[str, Any]:
                # Load current state using atomic operation with integrity validation
                current_state = self._load_state_with_validation()
                processed_messages = current_state.get("processed_messages", {})

                # Migration: Convert old format (list) to new format (dict)
                if isinstance(processed_messages, list):
                    processed_messages = {msg_id: {"actions_applied": ["save"]} for msg_id in processed_messages}

                # Clean up old messages (older than 90 days)
                processed_messages = self._cleanup_old_state_entries(processed_messages)

                # Search for messages
                message_ids = self._search_messages(rule.query, rule.max_messages)
                self.logger.debug(
                    f"Rule '{rule.name}': Found {len(message_ids)} messages matching query '{rule.query}'"
                )

                for message_id in message_ids:
                    try:
                        stats["messages_processed"] += 1

                        # Reload state before processing each message to prevent race conditions
                        # This ensures we have the latest state in case another process modified it
                        current_state_check = self._load_state_with_validation()
                        processed_messages_check = current_state_check.get("processed_messages", {})
                        if isinstance(processed_messages_check, list):
                            # Migration: Convert old format (list) to new format (dict)
                            processed_messages_check = {
                                msg_id: {"actions_applied": ["save"]} for msg_id in processed_messages_check
                            }

                        # Get current message record from reloaded state
                        message_record = processed_messages_check.get(message_id, {"actions_applied": []})

                        # Determine what actions still need to be done
                        pending_actions = [
                            a for a in rule.actions if a not in message_record.get("actions_applied", [])
                        ]

                        # Skip if no actions needed
                        if not pending_actions:
                            stats["messages_skipped"] += 1
                            continue

                        # Get message details
                        message_data = self._get_message_details(message_id)
                        if not message_data:
                            self.logger.debug(f"Message {message_id}: Failed to get message details")
                            stats["messages_skipped"] += 1
                            continue

                        # Log message metadata for debugging
                        self.logger.debug(
                            f"Message {message_id}: Subject='{message_data.get('subject', '')}', "
                            f"From='{message_data.get('from', '')}', Date={message_data.get('date')}"
                        )

                        # Apply content filtering (only if we're going to save)
                        if "save" in pending_actions:
                            should_process = self._should_process_message(message_data, rule)
                            self.logger.debug(f"Message {message_id}: Content filter result={should_process}")
                            if not should_process:
                                stats["messages_skipped"] += 1
                                continue

                        # Apply all pending actions
                        applied_actions = []

                        # Handle "save" action
                        if "save" in pending_actions:
                            if self._process_message(message_data, rule):
                                stats["messages_saved"] += 1
                                applied_actions.append("save")

                        # Handle other actions (archive, label, etc.)
                        other_actions = [a for a in pending_actions if a != "save"]
                        if other_actions:
                            successful_other_actions = self._apply_rule_actions(message_id, other_actions)
                            applied_actions.extend(successful_other_actions)

                            # Track failed actions
                            failed_actions = len(other_actions) - len(successful_other_actions)
                            stats["actions_failed"] += failed_actions

                        # Update state with completed actions
                        if applied_actions:
                            message_record["actions_applied"].extend(applied_actions)
                            stats["actions_applied"] += len(applied_actions)

                        # Add timestamp for state cleanup sorting
                        message_record["last_processed"] = datetime.now(tz=UTC).isoformat()

                        # Track state update for this message in both the check and main state
                        processed_messages_check[message_id] = message_record
                        processed_messages[message_id] = message_record

                        # Checkpoint save every 10 messages
                        if stats["messages_processed"] % 10 == 0:
                            checkpoint_state = {"processed_messages": processed_messages}
                            try:
                                self.state_manager.update_state(checkpoint_state)
                                self.logger.info(
                                    f"Checkpoint: Saved state after {stats['messages_processed']} messages"
                                )
                            except Exception as checkpoint_error:
                                self.logger.warning(f"Checkpoint save failed: {checkpoint_error}")

                        # Rate limiting between messages
                        time.sleep(self.config.rate_limit_seconds)

                    except Exception as message_error:
                        stats["errors"] += 1
                        self.logger.error(f"Error processing message {message_id}: {message_error}")

                # Prepare state updates for atomic write
                return {"processed_messages": processed_messages}

            # Perform state update atomically with message-level merging
            # This prevents race conditions where concurrent processes could have their updates overwritten
            state_updates = process_messages_with_state_update()
            if state_updates and "processed_messages" in state_updates:
                # Use message-level merge instead of dict replacement to prevent lost updates
                # Standard update_state() would replace entire "processed_messages" dict,
                # potentially overwriting messages added by concurrent processes
                import fcntl

                lock_file_path = self.state_manager.state_file_path.with_suffix(".lock")

                try:
                    with open(lock_file_path, "w") as lock_file:
                        # Acquire exclusive lock to prevent concurrent modifications
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

                        # Load current state within lock
                        current_state = self.state_manager.load_state()
                        current_processed = current_state.get("processed_messages", {})

                        # Merge at message level - preserves concurrent updates
                        current_processed.update(state_updates["processed_messages"])
                        current_state["processed_messages"] = current_processed

                        # Save merged state
                        self.state_manager.save_state(current_state)
                        # Lock automatically released when file closed

                except OSError as lock_error:
                    self.logger.error(f"Failed to acquire lock for final state update: {lock_error}")
                    # Fall back to standard update if lock fails
                    self.state_manager.update_state(state_updates)

        except Exception as rule_error:
            raise ContentProcessingError(
                f"Failed to collect emails for rule '{rule.name}'", {"original_error": str(rule_error)}
            ) from rule_error

        return stats

    def collect_label_rules(self) -> dict[str, Any]:
        """
        Collect emails from all configured label-based trigger rules.

        Label rules monitor for manually applied labels and trigger actions
        when those labels are detected on emails.

        Returns:
            Dictionary containing collection statistics

        Raises:
            ContentProcessingError: If collection fails
        """
        overall_stats: dict[str, Any] = {
            "label_rules_processed": 0,
            "total_messages_processed": 0,
            "total_messages_saved": 0,
            "total_messages_skipped": 0,
            "total_actions_applied": 0,
            "total_actions_failed": 0,
            "total_trigger_labels_removed": 0,
            "total_errors": 0,
            "label_rule_stats": [],
        }

        for label_rule in self.config.label_rules:
            try:
                rule_stats = self.collect_label_rule(label_rule)
                overall_stats["label_rules_processed"] += 1
                overall_stats["total_messages_processed"] += rule_stats["messages_processed"]
                overall_stats["total_messages_saved"] += rule_stats["messages_saved"]
                overall_stats["total_messages_skipped"] += rule_stats["messages_skipped"]
                overall_stats["total_actions_applied"] += rule_stats["actions_applied"]
                overall_stats["total_actions_failed"] += rule_stats["actions_failed"]
                overall_stats["total_trigger_labels_removed"] += rule_stats["trigger_labels_removed"]
                overall_stats["total_errors"] += rule_stats["errors"]
                overall_stats["label_rule_stats"].append({"rule": label_rule.name, **rule_stats})

                # Rate limiting between label rules
                time.sleep(self.config.rate_limit_seconds)

            except Exception as rule_error:
                overall_stats["total_errors"] += 1
                overall_stats["label_rule_stats"].append(
                    {
                        "rule": label_rule.name,
                        "messages_processed": 0,
                        "messages_saved": 0,
                        "messages_skipped": 0,
                        "actions_applied": 0,
                        "actions_failed": 0,
                        "trigger_labels_removed": 0,
                        "errors": 1,
                        "error_message": str(rule_error),
                    }
                )

        return overall_stats

    def collect_label_rule(self, label_rule: Any) -> dict[str, Any]:
        """
        Collect emails for a specific label-based trigger rule.

        Args:
            label_rule: GmailLabelRule configuration

        Returns:
            Dictionary containing collection statistics for this label rule

        Raises:
            ContentProcessingError: If label rule collection fails
        """
        stats = {
            "messages_processed": 0,
            "messages_saved": 0,
            "messages_skipped": 0,
            "actions_applied": 0,
            "actions_failed": 0,
            "trigger_labels_removed": 0,
            "errors": 0,
        }

        try:
            self.logger.info(f"Processing label rule: {label_rule.name}")
            self.logger.info(f"  Watching for label: {label_rule.trigger_label}")

            # Build query to search for messages with trigger label
            query = f"label:{label_rule.trigger_label}"

            # Search for messages
            message_ids = self._search_messages(query, label_rule.max_messages)
            self.logger.info(f"  Found {len(message_ids)} messages with label '{label_rule.trigger_label}'")

            if not message_ids:
                return stats

            # Load current state
            current_state = self._load_state_with_validation()
            processed_messages = current_state.get("processed_messages", {})

            # Ensure dict format
            if isinstance(processed_messages, list):
                processed_messages = {msg_id: {"actions_applied": ["save"]} for msg_id in processed_messages}

            # Process each message
            for message_id in message_ids:
                try:
                    stats["messages_processed"] += 1

                    # Use label-rule-specific state key to track separately from query rules
                    state_key = f"label_rule:{label_rule.name}:{message_id}"

                    # Check if already processed by THIS label rule
                    message_record = processed_messages.get(state_key, {"actions_applied": []})

                    # Determine what actions still need to be done
                    pending_actions = [
                        a for a in label_rule.actions if a not in message_record.get("actions_applied", [])
                    ]

                    # Skip if no actions needed
                    if not pending_actions:
                        stats["messages_skipped"] += 1
                        continue

                    # Get message details
                    message_data = self._get_message_details(message_id)
                    if not message_data:
                        self.logger.debug(f"Message {message_id}: Failed to get message details")
                        stats["messages_skipped"] += 1
                        continue

                    self.logger.debug(
                        f"Message {message_id}: Subject='{message_data.get('subject', '')}', "
                        f"From='{message_data.get('from', '')}'"
                    )

                    # Apply content filtering if configured
                    if label_rule.filters and "save" in pending_actions:
                        # Create a temporary rule object with label_rule's filters for filtering
                        temp_rule = type(
                            "TempRule",
                            (),
                            {
                                "filters": label_rule.filters,
                                "name": label_rule.name,
                            },
                        )()
                        should_process = self._should_process_message(message_data, temp_rule)
                        self.logger.debug(f"Message {message_id}: Content filter result={should_process}")
                        if not should_process:
                            stats["messages_skipped"] += 1
                            continue

                    # Process the message (apply actions)
                    success = self._process_label_triggered_message(message_data, label_rule, pending_actions, stats)

                    if success:
                        # Update state with completed actions
                        message_record["actions_applied"].extend(pending_actions)
                        message_record["last_processed"] = datetime.now(tz=UTC).isoformat()
                        message_record["label_rule"] = label_rule.name
                        processed_messages[state_key] = message_record

                        stats["actions_applied"] += len(pending_actions)

                    # Rate limiting between messages
                    time.sleep(self.config.rate_limit_seconds)

                except Exception as message_error:
                    stats["errors"] += 1
                    self.logger.error(f"Error processing message {message_id}: {message_error}")

            # Save final state
            state_updates = {"processed_messages": processed_messages}
            self.state_manager.update_state(state_updates)

        except Exception as rule_error:
            raise ContentProcessingError(
                f"Failed to collect emails for label rule '{label_rule.name}'", {"original_error": str(rule_error)}
            ) from rule_error

        return stats

    def _process_label_triggered_message(
        self, message_data: dict[str, Any], label_rule: Any, pending_actions: list[str], stats: dict[str, Any]
    ) -> bool:
        """
        Process a message triggered by a label detection.

        Args:
            message_data: Email message data
            label_rule: GmailLabelRule configuration
            pending_actions: List of actions to apply
            stats: Statistics dictionary to update

        Returns:
            True if processed successfully
        """
        message_id = message_data["id"]
        applied_actions = []

        try:
            # Handle "save" action
            if "save" in pending_actions:
                # Create output directory for this label rule
                output_dir = Path(self.config.output_dir) / sanitize_filename(label_rule.name)
                output_dir.mkdir(parents=True, exist_ok=True)

                # Save message as markdown
                try:
                    markdown_content = self._create_markdown_content(message_data)
                    filename = sanitize_filename(f"{message_data.get('subject', 'no_subject')}_{message_id}.md")
                    output_path = output_dir / filename

                    frontmatter = {
                        "title": message_data.get("subject", "No Subject"),
                        "from": message_data.get("from", "Unknown"),
                        "to": message_data.get("to", "Unknown"),
                        "date": message_data.get("date", "Unknown"),
                        "source": "gmail",
                        "rule": label_rule.name,
                        "message_id": message_id,
                        "thread_id": message_data.get("thread_id", ""),
                        "size_estimate": message_data.get("size_estimate", 0),
                        "collected_date": datetime.now(tz=UTC).isoformat(),
                    }

                    write_markdown_file(str(output_path), markdown_content, frontmatter)
                    self.logger.info(f"  Saved: {filename}")
                    stats["messages_saved"] += 1
                    applied_actions.append("save")

                    # Save attachments if configured
                    if label_rule.save_attachments:
                        self._save_attachments(message_data, output_dir, message_id)

                except Exception as save_error:
                    self.logger.error(f"Failed to save message {message_id}: {save_error}")
                    stats["actions_failed"] += 1

            # Handle other actions (archive, label, forward, etc.)
            other_actions = [a for a in pending_actions if a != "save"]
            if other_actions:
                successful_other_actions = self._apply_rule_actions(message_id, other_actions)
                applied_actions.extend(successful_other_actions)

                # Track failed actions
                failed_actions = len(other_actions) - len(successful_other_actions)
                stats["actions_failed"] += failed_actions

            # Remove trigger label if configured
            if label_rule.remove_trigger:
                try:
                    self._remove_label_from_message(message_id, label_rule.trigger_label)
                    self.logger.info(f"  Removed trigger label: {label_rule.trigger_label}")
                    stats["trigger_labels_removed"] += 1
                except Exception as remove_error:
                    self.logger.warning(f"  Failed to remove trigger label: {remove_error}")

            return len(applied_actions) > 0

        except Exception as process_error:
            self.logger.error(f"Error processing label-triggered message {message_id}: {process_error}")
            return False

    def _search_messages(self, query: str, max_results: int) -> list[str]:
        """
        Search for messages using Gmail query syntax with pagination support.

        Args:
            query: Gmail search query
            max_results: Maximum number of results to return

        Returns:
            List of message IDs

        Raises:
            NetworkConnectionError: If search fails
        """
        message_ids = []
        next_page_token = None
        total_fetched = 0

        try:
            while total_fetched < max_results:
                # Calculate how many to fetch in this batch
                batch_size = min(self.config.batch_size, max_results - total_fetched)

                # Build request parameters
                request_params = {"userId": "me", "q": query, "maxResults": batch_size}

                if next_page_token:
                    request_params["pageToken"] = next_page_token

                # Execute the search request with retry logic
                # Capture request_params in lambda by using default argument
                result = self._execute_with_retry(
                    lambda params=request_params: self.service.users().messages().list(**params).execute()
                )

                # Extract message IDs from this page
                messages = result.get("messages", [])
                for message in messages:
                    message_ids.append(message["id"])
                    total_fetched += 1

                # Check if there are more pages
                next_page_token = result.get("nextPageToken")
                if not next_page_token or not messages:
                    # No more pages or no messages in this page
                    break

                # Rate limiting between pages
                time.sleep(self.config.rate_limit_seconds)

            return message_ids

        except HttpError as api_error:
            raise NetworkConnectionError(
                f"Gmail API search failed for query: {query}",
                {"original_error": str(api_error), "total_fetched": total_fetched},
            ) from api_error

    def _get_message_details(self, message_id: str) -> dict[str, Any] | None:
        """
        Get detailed message information.

        Args:
            message_id: Gmail message ID

        Returns:
            Dictionary containing message details, or None if error

        Raises:
            NetworkConnectionError: If message retrieval fails
        """
        try:
            message = self._execute_with_retry(
                lambda: self.service.users().messages().get(userId="me", id=message_id, format="full").execute()
            )

            # Extract headers
            headers = {}
            for header in message["payload"].get("headers", []):
                headers[header["name"].lower()] = header["value"]

            # Extract body (now returns dict with 'plain' and 'html' keys)
            body_content = self._extract_message_body(message["payload"])

            # Parse date
            date_str = headers.get("date", "")
            try:
                parsed_date = email.utils.parsedate_to_datetime(date_str)
            except Exception:
                parsed_date = datetime.now(tz=UTC)

            message_data = {
                "id": message_id,
                # thread_id is stored for future enhancements (e.g., threading support, conversation tracking)
                "thread_id": message.get("threadId"),
                "subject": headers.get("subject", ""),
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "date": parsed_date,
                "body": body_content,  # Now a dict with 'plain' and 'html' keys
                "headers": headers,
                "size_estimate": message.get("sizeEstimate", 0),
                "snippet": message.get("snippet", ""),
                "raw_message": message,
            }

            return message_data

        except HttpError as api_error:
            raise NetworkConnectionError(
                f"Failed to get message details for {message_id}", {"original_error": str(api_error)}
            ) from api_error

    def _extract_message_body(self, payload: dict[str, Any]) -> dict[str, str]:
        """
        Extract text and HTML body from message payload.

        Args:
            payload: Gmail message payload

        Returns:
            Dictionary with 'plain' and 'html' keys containing extracted content
        """
        # Memory and recursion limits to prevent email bombs
        max_total_body_size = 10 * 1024 * 1024  # 10MB limit
        max_recursion_depth = 50

        plain_parts = []
        html_parts = []
        total_plain_size = 0
        total_html_size = 0

        def get_charset_from_headers(part: dict[str, Any]) -> str:
            """
            Extract charset from Content-Type header using RFC-compliant parsing.

            Uses Python's email.message.Message for proper header parsing instead of
            manual string manipulation, which is vulnerable to malformed headers.

            Args:
                part: Gmail message part with headers

            Returns:
                Charset string, defaults to 'utf-8' if not found or on parsing errors
            """
            import codecs

            headers = part.get("headers", [])

            # Build a Message object for RFC-compliant header parsing
            msg = Message()
            for header in headers:
                name = header.get("name", "")
                value = header.get("value", "")
                if name and value:
                    msg[name] = value

            # Use Message.get_content_charset() for proper charset extraction
            # This handles quoted values, parameters, and malformed headers correctly
            charset = msg.get_content_charset(failobj="utf-8")
            charset_str = str(charset)

            # Validate charset name to prevent injection or invalid codec errors
            try:
                codecs.lookup(charset_str)
                return charset_str
            except LookupError:
                # Invalid charset, fall back to utf-8
                self.logger.warning(f"Invalid charset '{charset_str}' specified, falling back to utf-8")
                return "utf-8"

        def extract_parts(part: dict[str, Any], depth: int = 0) -> None:
            nonlocal total_plain_size, total_html_size

            # Check recursion depth to prevent stack overflow
            if depth > max_recursion_depth:
                self.logger.warning("Maximum recursion depth reached in email parts")
                return

            if "parts" in part:
                for subpart in part["parts"]:
                    extract_parts(subpart, depth + 1)
            else:
                mime_type = part.get("mimeType", "")
                if mime_type in ("text/plain", "text/html"):
                    if "data" in part.get("body", {}):
                        data = part["body"]["data"]
                        charset = get_charset_from_headers(part)

                        # Decode with proper charset
                        try:
                            decoded_bytes = base64.urlsafe_b64decode(data)
                            # Try the specified charset first
                            try:
                                decoded_data = decoded_bytes.decode(charset)
                            except (UnicodeDecodeError, LookupError):
                                # Fall back to UTF-8 if charset fails
                                try:
                                    decoded_data = decoded_bytes.decode("utf-8")
                                except UnicodeDecodeError:
                                    # Last resort: UTF-8 with replacement
                                    decoded_data = decoded_bytes.decode("utf-8", errors="replace")

                            # Check size limits before appending
                            if decoded_data:
                                if mime_type == "text/plain":
                                    if total_plain_size + len(decoded_data) > max_total_body_size:
                                        self.logger.warning("Plain text body size limit reached, truncating")
                                        return
                                    plain_parts.append(decoded_data)
                                    total_plain_size += len(decoded_data)
                                elif mime_type == "text/html":
                                    if total_html_size + len(decoded_data) > max_total_body_size:
                                        self.logger.warning("HTML body size limit reached, truncating")
                                        return
                                    html_parts.append(decoded_data)
                                    total_html_size += len(decoded_data)
                        except Exception as decode_error:
                            self.logger.warning(f"Failed to decode message part: {decode_error}")

        extract_parts(payload)

        return {
            "plain": "\n\n".join(plain_parts) if plain_parts else "",
            "html": "\n\n".join(html_parts) if html_parts else "",
        }

    def _should_process_message(self, message_data: dict[str, Any], rule: GmailRule) -> bool:
        """
        Check if message should be processed based on filters.

        Args:
            message_data: Message details
            rule: Gmail rule configuration

        Returns:
            True if message should be processed
        """
        message_id = message_data.get("id", "unknown")
        self.logger.debug(f"Message {message_id}: Starting content filter evaluation for rule '{rule.name}'")

        # Cascade and UNION filters from both levels
        # Level 1: Global keywords (from gmail.yaml default_filters)
        # Level 2: Rule keywords (from rule-specific filters)
        # Both levels are merged together (UNION)

        # Collect keywords from all levels
        include_keywords_sets = []
        exclude_keywords_sets = []

        # Global/default filters (Level 1)
        if self.config.default_filters:
            if self.config.default_filters.include_keywords:
                include_keywords_sets.append(set(self.config.default_filters.include_keywords))
            if self.config.default_filters.exclude_keywords:
                exclude_keywords_sets.append(set(self.config.default_filters.exclude_keywords))

        # Rule-specific filters (Level 2)
        if rule.filters:
            if rule.filters.include_keywords:
                include_keywords_sets.append(set(rule.filters.include_keywords))
            if rule.filters.exclude_keywords:
                exclude_keywords_sets.append(set(rule.filters.exclude_keywords))

        # UNION all keywords from all levels (remove duplicates)
        all_include_keywords = list(set.union(*include_keywords_sets)) if include_keywords_sets else []
        all_exclude_keywords = list(set.union(*exclude_keywords_sets)) if exclude_keywords_sets else []

        # Determine max_age_days (most specific wins: rule > default)
        max_age_days = None
        if rule.filters and rule.filters.max_age_days is not None:
            max_age_days = rule.filters.max_age_days
        elif self.config.default_filters and self.config.default_filters.max_age_days is not None:
            max_age_days = self.config.default_filters.max_age_days

        filter_criteria = {
            "max_age_days": max_age_days,
            "include_keywords": all_include_keywords,
            "exclude_keywords": all_exclude_keywords,
        }

        self.logger.info(
            f"Message {message_id}: Cascaded filters "
            f"(Global: {len(self.config.default_filters.include_keywords or [])} include, "
            f"{len(self.config.default_filters.exclude_keywords or [])} exclude | "
            f"Rule: {len(rule.filters.include_keywords or []) if rule.filters else 0} include, "
            f"{len(rule.filters.exclude_keywords or []) if rule.filters else 0} exclude) "
            f"→ Final: {len(all_include_keywords)} include, {len(all_exclude_keywords)} exclude"
        )

        # Prepare content data for filtering
        body_content = message_data.get("body", {})
        # Use HTML content if available, otherwise use plain text
        if isinstance(body_content, dict):
            text_content = body_content.get("html", "") or body_content.get("plain", "")
        else:
            # Handle legacy format for backward compatibility
            text_content = body_content if isinstance(body_content, str) else ""

        content_data = {
            "title": message_data.get("subject", ""),
            "text": text_content,
            "created_date": message_data.get("date"),
        }
        self.logger.info(
            f"Message {message_id}: Content data prepared - title='{content_data['title']}', "
            f"date={content_data['created_date']}, "
            f"body_length={len(content_data['text']) if content_data['text'] else 0}"
        )  # DEBUG

        result = apply_content_filter(content_data, filter_criteria)
        self.logger.debug(f"Message {message_id}: apply_content_filter result={result}")
        return result

    def _process_message(self, message_data: dict[str, Any], rule: GmailRule) -> bool:
        """
        Process and save a Gmail message.

        Args:
            message_data: Message details
            rule: Gmail rule configuration

        Returns:
            True if message was saved successfully
        """
        try:
            # Create output directory
            output_dir = ensure_folder_structure(self.config.output_dir, "gmail", rule.name)

            # Generate filename
            date_str = message_data["date"].strftime("%Y-%m-%d")
            subject = message_data.get("subject", "no_subject")
            # Clean subject for filename
            safe_subject = "".join(c for c in subject if c.isalnum() or c in (" ", "-", "_")).strip()
            safe_subject = safe_subject.replace(" ", "_")[:50]  # Limit length
            filename = f"{date_str}_{safe_subject}_{message_data['id']}.md"

            # Create markdown content
            markdown_content = self._create_markdown_content(message_data)

            # Create metadata
            metadata = {
                "title": message_data.get("subject", ""),
                "from": message_data.get("from", ""),
                "to": message_data.get("to", ""),
                "date": message_data["date"],
                "source": "gmail",
                "rule": rule.name,
                "message_id": message_data["id"],
                "thread_id": message_data.get("thread_id", ""),
                "size_estimate": message_data.get("size_estimate", 0),
                "collected_date": datetime.now().isoformat(),
            }

            # Write markdown file
            output_file_path = output_dir / filename
            write_markdown_file(str(output_file_path), markdown_content, metadata)

            # Save attachments if configured
            if rule.save_attachments:
                self._save_attachments(message_data, output_dir, message_data["id"])

            return True

        except (AuthenticationFailureError, StateManagementError) as critical_error:
            # Re-raise critical exceptions that should halt collection
            raise critical_error
        except Exception as process_error:
            # Log and gracefully handle content-specific errors
            self.logger.error(f"Error processing message {message_data['id']}: {process_error}")
            return False

    def _create_markdown_content(self, message_data: dict[str, Any]) -> str:
        """
        Create markdown content from message data.

        Args:
            message_data: Message details

        Returns:
            Formatted markdown content
        """
        content_parts = []

        # Add message headers
        content_parts.append("## Email Details")
        content_parts.append(f"**From:** {message_data.get('from', '')}")
        content_parts.append(f"**To:** {message_data.get('to', '')}")
        content_parts.append(f"**Date:** {message_data['date'].isoformat()}")
        content_parts.append(f"**Subject:** {message_data.get('subject', '')}")
        content_parts.append("")

        # Add snippet if available
        if message_data.get("snippet"):
            content_parts.append("## Snippet")
            content_parts.append(message_data["snippet"])
            content_parts.append("")

        # Add body content
        content_parts.append("## Message Body")
        body_data = message_data.get("body", {})

        # Handle new dict format and legacy string format
        if isinstance(body_data, dict):
            # Prefer plain text for markdown output (HTML would need conversion)
            body_text = body_data.get("plain", "")
            if not body_text and body_data.get("html", ""):
                # If only HTML is available, add a note
                content_parts.append("*Note: Message contains HTML content*")
                # You could optionally include raw HTML or convert it
                body_text = body_data.get("html", "")
        else:
            # Handle legacy string format
            body_text = body_data if isinstance(body_data, str) else ""

        if body_text:
            content_parts.append(body_text)
        else:
            content_parts.append("*No body content available*")

        return "\n".join(content_parts)

    def _save_attachments(self, message_data: dict[str, Any], output_dir: Path, message_id: str) -> None:
        """
        Save email attachments to disk.

        Args:
            message_data: Message details
            output_dir: Directory to save attachments
            message_id: Gmail message ID
        """
        try:
            attachments_dir = output_dir / "attachments" / message_id
            attachments_dir.mkdir(parents=True, exist_ok=True)

            payload = message_data["raw_message"]["payload"]
            self._extract_attachments(payload, attachments_dir, message_id)

        except Exception as attachment_error:
            self.logger.error(f"Error saving attachments for message {message_id}: {attachment_error}")

    def _validate_attachment_safety(self, filename: str, size: int) -> bool:
        """
        Validate attachment is safe to save.

        Args:
            filename: Attachment filename
            size: Attachment size in bytes

        Returns:
            True if attachment is safe to save, False otherwise
        """
        # Check extension against dangerous list
        ext = Path(filename).suffix.lower()
        if ext in self.DANGEROUS_EXTENSIONS:
            self.logger.warning(f"Blocked dangerous file extension: {ext} (filename: {filename})")
            return False

        # Check size limits (100MB max)
        max_safe_size = 100 * 1024 * 1024  # 100MB
        if size > max_safe_size:
            self.logger.warning(f"Blocked oversized attachment: {size} bytes (filename: {filename})")
            return False

        return True

    def _extract_attachments(self, payload: dict[str, Any], attachments_dir: Path, message_id: str) -> None:
        """
        Recursively extract attachments from message payload.

        Args:
            payload: Message payload
            attachments_dir: Directory to save attachments
            message_id: Gmail message ID
        """
        if "parts" in payload:
            for part in payload["parts"]:
                self._extract_attachments(part, attachments_dir, message_id)
        else:
            if payload.get("filename"):
                attachment_id = payload["body"].get("attachmentId")
                if attachment_id:
                    try:
                        # Check attachment size before downloading
                        attachment_size = payload["body"].get("size", 0)
                        if attachment_size > self.config.max_attachment_size:
                            self.logger.warning(
                                f"Skipping attachment {payload['filename']}: size {attachment_size} bytes "
                                f"exceeds limit of {self.config.max_attachment_size} bytes"
                            )
                            return

                        attachment = self._execute_with_retry(
                            lambda: self.service.users()
                            .messages()
                            .attachments()
                            .get(userId="me", messageId=message_id, id=attachment_id)
                            .execute()
                        )

                        file_data = base64.urlsafe_b64decode(attachment["data"])

                        # Double-check actual data size after download
                        if len(file_data) > self.config.max_attachment_size:
                            self.logger.warning(
                                f"Skipping attachment {payload['filename']}: actual size {len(file_data)} bytes "
                                f"exceeds limit of {self.config.max_attachment_size} bytes"
                            )
                            return

                        # Sanitize filename to prevent path traversal
                        safe_filename = sanitize_filename(payload["filename"])

                        # Validate attachment safety (extension and size)
                        if not self._validate_attachment_safety(safe_filename, len(file_data)):
                            self.logger.warning(f"Skipping unsafe attachment: {payload['filename']}")
                            return

                        # Create file path
                        file_path = attachments_dir / safe_filename

                        # Validate path doesn't escape attachments directory
                        try:
                            resolved_path = file_path.resolve()
                            resolved_attachments_dir = attachments_dir.resolve()
                            if not str(resolved_path).startswith(str(resolved_attachments_dir)):
                                self.logger.warning(
                                    f"Attachment path escapes directory: {safe_filename} (resolved to {resolved_path})"
                                )
                                return
                        except (OSError, RuntimeError) as path_error:
                            self.logger.warning(f"Could not validate attachment path: {path_error}")
                            return

                        # Save attachment
                        with open(file_path, "wb") as attachment_file:
                            attachment_file.write(file_data)

                    except Exception as extract_error:
                        self.logger.error(f"Error extracting attachment {payload['filename']}: {extract_error}")

    def _apply_rule_actions(self, message_id: str, actions: list[str]) -> list[str]:
        """
        Apply configured actions to a processed message.

        Args:
            message_id: Gmail message ID
            actions: List of actions to apply

        Returns:
            List of successfully applied actions
        """
        successful_actions = []

        for action in actions:
            try:
                if action == "archive":
                    self._archive_message(message_id)
                elif action == "mark_read":
                    self._mark_message_read(message_id)
                elif action.startswith("label:"):
                    label_name = action[6:]  # Remove "label:" prefix
                    self._add_label_to_message(message_id, label_name)
                elif action.startswith("remove_label:"):
                    label_name = action[13:]  # Remove "remove_label:" prefix
                    self._remove_label_from_message(message_id, label_name)
                elif action == "delete":
                    self._delete_message(message_id, permanent=False)  # Trash by default
                elif action == "delete_permanent":
                    self._delete_message(message_id, permanent=True)  # Permanent delete
                elif action.startswith("forward:"):
                    forward_to = action[8:]  # Remove "forward:" prefix
                    # Use existing forward_email method
                    self.forward_email(
                        message_id=message_id, to=forward_to, additional_body="Auto-forwarded by Gmail collector"
                    )

                # If we get here, the action succeeded
                successful_actions.append(action)

            except Exception as action_error:
                self.logger.error(f"Error applying action '{action}' to message {message_id}: {action_error}")
                # Don't add to successful_actions if it failed

        return successful_actions

    def _archive_message(self, message_id: str) -> None:
        """Archive a message by removing INBOX label."""
        self.logger.info(f"Archiving message {message_id} by removing INBOX label")
        result = self._execute_with_retry(
            lambda: self.service.users()
            .messages()
            .modify(userId="me", id=message_id, body={"removeLabelIds": ["INBOX"]})
            .execute()
        )
        self.logger.info(f"Archive result for {message_id}: {result}")

    def _mark_message_read(self, message_id: str) -> None:
        """Mark a message as read by removing UNREAD label."""
        self._execute_with_retry(
            lambda: self.service.users()
            .messages()
            .modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]})
            .execute()
        )

    def _add_label_to_message(self, message_id: str, label_name: str) -> None:
        """Add a label to a message."""
        label_id = self._get_or_create_label(label_name)
        if label_id:
            self._execute_with_retry(
                lambda: self.service.users()
                .messages()
                .modify(userId="me", id=message_id, body={"addLabelIds": [label_id]})
                .execute()
            )

    def _remove_label_from_message(self, message_id: str, label_name: str) -> None:
        """Remove a label from a message."""
        label_id = self._get_label_id(label_name)
        if label_id:
            self._execute_with_retry(
                lambda: self.service.users()
                .messages()
                .modify(userId="me", id=message_id, body={"removeLabelIds": [label_id]})
                .execute()
            )

    def _delete_message(self, message_id: str, permanent: bool = False) -> None:
        """
        Delete or trash a message.

        Args:
            message_id: Gmail message ID
            permanent: If True, permanently delete; if False, move to trash
        """
        if permanent:
            # Permanently delete (requires gmail.modify scope)
            self._execute_with_retry(
                lambda: self.service.users().messages().delete(userId="me", id=message_id).execute()
            )
        else:
            # Move to trash (can be recovered for 30 days)
            self._execute_with_retry(
                lambda: self.service.users().messages().trash(userId="me", id=message_id).execute()
            )

    def _get_or_create_label(self, label_name: str) -> str | None:
        """Get label ID or create label if it doesn't exist."""
        label_id = self._get_label_id(label_name)
        if label_id:
            return label_id

        try:
            label = self._execute_with_retry(
                lambda: self.service.users().labels().create(userId="me", body={"name": label_name}).execute()
            )
            label_id_result: str = str(label["id"])
            return label_id_result
        except Exception:
            return None

    def _get_label_id(self, label_name: str) -> str | None:
        """Get label ID by name."""
        try:
            labels = self._execute_with_retry(lambda: self.service.users().labels().list(userId="me").execute())
            for label in labels.get("labels", []):
                if label["name"] == label_name:
                    label_id_result: str = str(label["id"])
                    return label_id_result
        except Exception:
            pass
        return None

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: str | None = None,
        from_email: str | None = None,
        cc: str | None = None,
        bcc: str | None = None,
        reply_to: str | None = None,
    ) -> bool:
        """
        Send an email using Gmail API with optional HTML support.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Plain text email body content
            html_body: Optional HTML email body content
            from_email: Sender email (defaults to authenticated account)
            cc: CC recipients (comma-separated)
            bcc: BCC recipients (comma-separated)
            reply_to: Reply-to address

        Returns:
            True if email was sent successfully, False otherwise

        Raises:
            ContentProcessingError: If email sending fails
        """
        try:
            # Create message - use alternative if HTML provided
            if html_body:
                message = MIMEMultipart("alternative")
            else:
                message = MIMEMultipart()

            message["To"] = to
            message["Subject"] = subject

            if from_email:
                message["From"] = from_email
            if cc:
                message["Cc"] = cc
            if bcc:
                message["Bcc"] = bcc
            if reply_to:
                message["Reply-To"] = reply_to

            # Add body parts
            message.attach(MIMEText(body, "plain", "utf-8"))

            if html_body:
                # Add HTML part if provided
                message.attach(MIMEText(html_body, "html", "utf-8"))

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            # Send via Gmail API
            self._execute_with_retry(
                lambda: self.service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
            )

            return True

        except HttpError as api_error:
            raise ContentProcessingError(
                f"Failed to send email to {to}", {"original_error": str(api_error)}
            ) from api_error

    def forward_email(
        self, message_id: str, to: str, additional_body: str | None = None, from_email: str | None = None
    ) -> bool:
        """
        Forward an existing email to a new recipient with HTML support.

        Args:
            message_id: ID of the message to forward
            to: Recipient email address
            additional_body: Additional text to add before forwarded content
            from_email: Sender email (defaults to authenticated account)

        Returns:
            True if email was forwarded successfully, False otherwise

        Raises:
            ContentProcessingError: If forwarding fails
        """
        try:
            # Get original message
            original_message = self._get_message_details(message_id)
            if not original_message:
                raise ContentProcessingError(f"Could not retrieve message {message_id} for forwarding")

            # Create forwarded message as multipart/alternative
            message = MIMEMultipart("mixed")
            message["To"] = to
            message["Subject"] = f"Fwd: {original_message.get('subject', '')}"

            if from_email:
                message["From"] = from_email

            # Create alternative part for plain + HTML
            alternative = MIMEMultipart("alternative")

            # Extract body content
            body_data = original_message.get("body", {})
            plain_body = ""
            html_body = ""

            if isinstance(body_data, dict):
                plain_body = body_data.get("plain", "")
                html_body = body_data.get("html", "")
            else:
                # Handle legacy string format
                plain_body = body_data if isinstance(body_data, str) else ""

            # Create forwarded header info
            forward_header_plain = "---------- Forwarded message ----------\n"
            forward_header_plain += f"From: {original_message.get('from', '')}\n"
            forward_header_plain += f"Date: {original_message['date'].isoformat()}\n"
            forward_header_plain += f"Subject: {original_message.get('subject', '')}\n"
            forward_header_plain += f"To: {original_message.get('to', '')}\n\n"

            forward_header_html = """
<div style="border-left: 2px solid #ccc; padding-left: 10px; margin: 10px 0;">
<p><strong>---------- Forwarded message ----------</strong></p>
<p><strong>From:</strong> {}</p>
<p><strong>Date:</strong> {}</p>
<p><strong>Subject:</strong> {}</p>
<p><strong>To:</strong> {}</p>
</div>
<br/>
""".format(
                original_message.get("from", "").replace("<", "&lt;").replace(">", "&gt;"),
                original_message["date"].isoformat(),
                original_message.get("subject", "").replace("<", "&lt;").replace(">", "&gt;"),
                original_message.get("to", "").replace("<", "&lt;").replace(">", "&gt;"),
            )

            # Build plain text version
            forwarded_plain = ""
            if additional_body:
                forwarded_plain += additional_body + "\n\n"
            forwarded_plain += forward_header_plain + plain_body

            # Add plain text part
            alternative.attach(MIMEText(forwarded_plain, "plain", "utf-8"))

            # Build HTML version if HTML content exists
            if html_body:
                forwarded_html = ""
                if additional_body:
                    # Convert additional body to simple HTML
                    html_additional = f"<p>{additional_body.replace(chr(10), '<br/>')}</p><br/>"
                    forwarded_html += html_additional
                forwarded_html += forward_header_html
                # Wrap original HTML in a container to preserve formatting
                forwarded_html += '<div style="margin-top: 10px;">' + html_body + "</div>"

                # Add HTML part
                alternative.attach(MIMEText(forwarded_html, "html", "utf-8"))
            elif plain_body:
                # Create simple HTML from plain text if no HTML exists
                forwarded_html = ""
                if additional_body:
                    html_additional = f"<p>{additional_body.replace(chr(10), '<br/>')}</p><br/>"
                    forwarded_html += html_additional
                forwarded_html += forward_header_html
                # Convert plain text to simple HTML
                html_plain_body = plain_body.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
                pre_style = "white-space: pre-wrap; font-family: inherit;"
                forwarded_html += (
                    f'<div style="margin-top: 10px;"><pre style="{pre_style}">{html_plain_body}</pre></div>'
                )

                # Add HTML part
                alternative.attach(MIMEText(forwarded_html, "html", "utf-8"))

            # Attach the alternative part to the message
            message.attach(alternative)

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            # Send via Gmail API
            self._execute_with_retry(
                lambda: self.service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
            )

            return True

        except Exception as forward_error:
            raise ContentProcessingError(
                f"Failed to forward message {message_id} to {to}", {"original_error": str(forward_error)}
            ) from forward_error

    def _cleanup_old_state_entries(self, processed_messages: dict[str, Any]) -> dict[str, Any]:
        """
        Clean up old message entries from state to prevent unbounded growth.

        Keeps only the 10,000 most recently processed messages based on timestamp.

        Args:
            processed_messages: Current state dictionary

        Returns:
            Cleaned state dictionary
        """
        if not processed_messages or len(processed_messages) <= 10000:
            return processed_messages

        # Sort by last_processed timestamp (most recent first)
        sorted_items = sorted(processed_messages.items(), key=lambda x: x[1].get("last_processed", ""), reverse=True)

        # Keep only 10k most recent
        cleaned_messages = dict(sorted_items[:10000])
        cleanup_count = len(processed_messages) - len(cleaned_messages)

        if cleanup_count > 0:
            self.logger.info(f"Cleaned up {cleanup_count} old message entries from state")

        return cleaned_messages

    def _load_state_with_validation(self) -> dict[str, Any]:
        """
        Load state with integrity validation and error recovery.

        Returns:
            Dictionary containing validated state data

        Raises:
            ContentProcessingError: If state loading fails critically
        """
        try:
            # Load state using atomic operation
            current_state = self.state_manager.load_state()

            # Validate state structure and integrity
            if not isinstance(current_state, dict):
                self.logger.warning("State file contains invalid data structure, initializing new state")
                return self._create_initial_state()

            # Validate required keys exist and have correct types
            processed_messages = current_state.get("processed_messages")
            if processed_messages is not None:
                if not isinstance(processed_messages, (dict, list)):
                    self.logger.warning("Invalid processed_messages format, initializing new state")
                    return self._create_initial_state()

                # Validate message entries are properly formatted
                if isinstance(processed_messages, dict):
                    invalid_entries = []
                    for msg_id, msg_data in processed_messages.items():
                        if not isinstance(msg_data, dict) or "actions_applied" not in msg_data:
                            invalid_entries.append(msg_id)

                    # Clean up invalid entries
                    if invalid_entries:
                        self.logger.warning(f"Found {len(invalid_entries)} invalid message entries, cleaning up")
                        for invalid_id in invalid_entries:
                            del processed_messages[invalid_id]
                        current_state["processed_messages"] = processed_messages

            # Add checksum for integrity validation
            current_state["_integrity_hash"] = self._calculate_state_hash(current_state)

            return current_state

        except Exception as load_error:
            self.logger.warning(f"Failed to load state file, creating new state: {load_error}")
            return self._create_initial_state()

    def _save_state_with_validation(self, state_data: dict[str, Any]) -> None:
        """
        Save state with integrity validation using atomic operations.

        Args:
            state_data: State data to save

        Raises:
            StateManagementError: If state saving fails
        """
        try:
            # Validate state structure before saving
            self._validate_state_structure(state_data)

            # Add integrity hash
            state_to_save = state_data.copy()
            state_to_save["_integrity_hash"] = self._calculate_state_hash(state_data)
            state_to_save["_last_updated"] = datetime.now().isoformat()

            # Use atomic save operation
            self.state_manager.save_state(state_to_save)

        except Exception as save_error:
            from tools._shared.exceptions import StateManagementError

            raise StateManagementError(
                "Failed to save Gmail collector state",
                {"error_type": type(save_error).__name__, "original_error": str(save_error)},
            ) from save_error

    def _create_initial_state(self) -> dict[str, Any]:
        """
        Create initial state structure.

        Returns:
            Dictionary containing initial state
        """
        initial_state = {"processed_messages": {}, "version": "1.0", "_created": datetime.now().isoformat()}
        initial_state["_integrity_hash"] = self._calculate_state_hash(initial_state)
        return initial_state

    def _validate_state_structure(self, state_data: dict[str, Any]) -> None:
        """
        Validate state data structure.

        Args:
            state_data: State data to validate

        Raises:
            StateManagementError: If state structure is invalid
        """
        if not isinstance(state_data, dict):
            raise StateManagementError("State data must be a dictionary")

        processed_messages = state_data.get("processed_messages")
        if processed_messages is not None:
            if not isinstance(processed_messages, dict):
                raise StateManagementError("processed_messages must be a dictionary")

            # Validate message entry structure
            for msg_id, msg_data in processed_messages.items():
                if not isinstance(msg_id, str):
                    raise StateManagementError(f"Message ID must be string: {type(msg_id)}")
                if not isinstance(msg_data, dict):
                    raise StateManagementError(f"Message data must be dictionary: {type(msg_data)}")
                if "actions_applied" not in msg_data:
                    raise StateManagementError(f"Message data missing actions_applied: {msg_id}")
                if not isinstance(msg_data["actions_applied"], list):
                    raise StateManagementError(f"actions_applied must be list: {msg_id}")

    def _calculate_state_hash(self, state_data: dict[str, Any]) -> str:
        """
        Calculate integrity hash for state data.

        Args:
            state_data: State data to hash (excluding existing hash)

        Returns:
            SHA-256 hash of state data
        """
        import hashlib
        import json

        # Create copy excluding all metadata fields (starting with _) for consistent hashing
        hashable_data = {k: v for k, v in state_data.items() if not k.startswith("_")}

        # Convert to deterministic JSON string
        json_string = json.dumps(hashable_data, sort_keys=True, separators=(",", ":"))

        # Calculate SHA-256 hash
        return hashlib.sha256(json_string.encode("utf-8")).hexdigest()
