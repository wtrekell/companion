"""StackExchange content collector for Signal system.

This module provides the main StackExchangeCollector class for collecting questions,
answers, and comments from StackExchange sites via the StackExchange API v2.3.
"""

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests  # type: ignore[import-untyped]

from tools._shared.exceptions import ContentProcessingError, NetworkConnectionError, SSRFError
from tools._shared.filters import apply_content_filter
from tools._shared.http_client import RateLimitedHttpClient
from tools._shared.output import ensure_folder_structure, write_markdown_file
from tools._shared.security import sanitize_filename, sanitize_text_content, validate_url_for_ssrf
from tools._shared.storage import SqliteStateManager

from .config import SiteConfig, StackExchangeCollectorConfig


class StackExchangeCollector:
    """
    StackExchange content collector using the StackExchange API v2.3.
    """

    def __init__(self, collector_config: StackExchangeCollectorConfig):
        """
        Initialize StackExchange collector.

        Args:
            collector_config: Configuration object for the collector

        Raises:
            ContentProcessingError: If initialization fails
        """
        self.config = collector_config
        self.logger = logging.getLogger(__name__)

        # Initialize HTTP client with rate limiting
        rate_limit = 1.0 / collector_config.rate_limit_seconds
        self.http_client = RateLimitedHttpClient(requests_per_second=rate_limit)
        self.http_client.session.headers.update({"User-Agent": collector_config.user_agent})

        # Initialize state manager
        state_db_path = str(Path(collector_config.output_dir) / "stackexchange_state.db")
        try:
            self.state_manager = SqliteStateManager(state_db_path)
        except Exception as state_error:
            raise ContentProcessingError(
                "Failed to initialize StackExchange state manager",
                {"database_path": state_db_path, "error": str(state_error)},
            ) from state_error

        self.logger.info("StackExchange collector initialized successfully")

    def _build_api_url(self, endpoint: str, site_name: str) -> str:
        """
        Build StackExchange API URL with security validation.

        Args:
            endpoint: API endpoint path
            site_name: StackExchange site name

        Returns:
            Complete API URL

        Raises:
            SSRFError: If resulting URL violates SSRF protection
        """
        # Sanitize inputs to prevent injection attacks
        sanitized_endpoint = sanitize_text_content(endpoint.strip("/"))

        # Build the URL path
        base_path = f"/{self.config.api_version}/{sanitized_endpoint}"
        full_url = f"{self.config.base_url}{base_path}"

        # Validate the final URL for SSRF protection
        # Note: base_url is already validated in config, but we validate the final URL too
        if not validate_url_for_ssrf(full_url):
            raise SSRFError(
                f"API URL blocked by SSRF protection: {full_url}",
                context={"endpoint": endpoint, "site": site_name, "blocked_url": full_url},
            )

        return full_url

    def _build_query_parameters(self, site_name: str, additional_params: dict[str, Any]) -> dict[str, Any]:
        """
        Build query parameters for API requests with input sanitization.

        Args:
            site_name: StackExchange site name
            additional_params: Additional parameters to include

        Returns:
            Dictionary of query parameters

        Raises:
            ContentProcessingError: If parameters are invalid
        """
        # Sanitize site name (already validated in config, but double-check at runtime)
        sanitized_site = sanitize_text_content(site_name.strip())
        if not sanitized_site:
            raise ContentProcessingError("Site name cannot be empty", {"original_site_name": site_name})

        # Build base parameters with sanitized values
        params = {
            "site": sanitized_site,
            "pagesize": min(self.config.max_page_size, 100),
            "filter": "withbody",  # Include question and answer bodies
        }

        # Sanitize and validate additional parameters
        for key, value in additional_params.items():
            # Sanitize parameter key
            sanitized_key = sanitize_text_content(str(key).strip())
            if not sanitized_key:
                continue  # Skip empty keys

            # Sanitize parameter value based on type
            if isinstance(value, str):
                sanitized_value = sanitize_text_content(value.strip())
                if sanitized_value:  # Only add non-empty values
                    params[sanitized_key] = sanitized_value
            elif isinstance(value, (int, float, bool)):
                params[sanitized_key] = value
            else:
                # Convert other types to string and sanitize
                sanitized_value = sanitize_text_content(str(value).strip())
                if sanitized_value:
                    params[sanitized_key] = sanitized_value

        # Add API key if configured (already sanitized in config)
        if self.config.api_key:
            params["key"] = self.config.api_key

        return params

    def _make_api_request(self, endpoint: str, site_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Make API request to StackExchange.

        Args:
            endpoint: API endpoint
            site_name: StackExchange site name
            params: Query parameters

        Returns:
            JSON response data

        Raises:
            NetworkConnectionError: If API request fails
        """
        try:
            api_url = self._build_api_url(endpoint, site_name)
            query_params = self._build_query_parameters(site_name, params)

            self.logger.debug(f"Making API request to: {api_url} with params: {query_params}")

            response = self.http_client.get(api_url, params=query_params)

            # Handle API backoff headers
            if "X-RateLimit-Remaining" in response.headers:
                remaining_requests = int(response.headers["X-RateLimit-Remaining"])
                if remaining_requests < 10:
                    self.logger.warning(f"API quota low: {remaining_requests} requests remaining")

            # Parse JSON response
            api_data = response.json()

            # Check for API errors
            if "error_id" in api_data:
                error_message = api_data.get("error_message", "Unknown API error")
                raise NetworkConnectionError(
                    f"StackExchange API error: {error_message}",
                    context={"error_id": api_data["error_id"], "site": site_name},
                )

            return api_data  # type: ignore[no-any-return]

        except requests.RequestException as request_error:
            raise NetworkConnectionError(
                f"Failed to make API request to {endpoint}",
                context={"site": site_name, "error": str(request_error)},
            ) from request_error
        except json.JSONDecodeError as json_error:
            raise NetworkConnectionError(
                f"Failed to parse API response from {endpoint}",
                context={"site": site_name, "error": str(json_error)},
            ) from json_error

    def _get_questions(self, site_config: SiteConfig) -> list[dict[str, Any]]:
        """
        Fetch questions from StackExchange site.

        Args:
            site_config: Site configuration

        Returns:
            List of question data dictionaries
        """
        questions: list[dict[str, Any]] = []
        page = 1
        max_questions = site_config.max_questions

        while len(questions) < max_questions:
            params = {"page": page, "sort": site_config.sort_order, "order": "desc"}

            # Add tag filtering if specified
            if site_config.tags:
                params["tagged"] = ";".join(site_config.tags)

            try:
                api_response = self._make_api_request("questions", site_config.name, params)
                page_questions = api_response.get("items", [])

                if not page_questions:
                    break

                questions.extend(page_questions)

                # Check if we have more pages
                if not api_response.get("has_more", False):
                    break

                page += 1

            except NetworkConnectionError as api_error:
                self.logger.error(f"Failed to fetch questions for {site_config.name}: {api_error}")
                break

        return questions[:max_questions]

    def _get_answers_and_comments(self, question_id: int, site_name: str) -> dict[str, list[dict[str, Any]]]:
        """
        Fetch answers and comments for a question.

        Args:
            question_id: Question ID
            site_name: StackExchange site name

        Returns:
            Dictionary with 'answers' and 'comments' keys
        """
        result: dict[str, list[dict[str, Any]]] = {"answers": [], "comments": []}

        try:
            # Fetch answers
            answers_response = self._make_api_request(
                f"questions/{question_id}/answers", site_name, {"sort": "votes", "order": "desc", "filter": "withbody"}
            )
            result["answers"] = answers_response.get("items", [])

            # Fetch comments for the question
            comments_response = self._make_api_request(
                f"questions/{question_id}/comments", site_name, {"sort": "creation", "order": "desc"}
            )
            result["comments"] = comments_response.get("items", [])

        except NetworkConnectionError as api_error:
            self.logger.warning(f"Failed to fetch answers/comments for question {question_id}: {api_error}")

        return result

    def _apply_filters(self, question_data: dict[str, Any], site_config: SiteConfig) -> bool:
        """
        Apply filtering criteria to a question.

        Args:
            question_data: Question data from API
            site_config: Site configuration with filters

        Returns:
            True if question passes filters, False otherwise
        """
        # Use site-specific filters if available, otherwise use defaults
        filters = site_config.filters or self.config.default_filters

        # Build content data for filtering
        content_data = {
            "title": question_data.get("title", ""),
            "body": question_data.get("body", ""),
            "score": question_data.get("score", 0),
            "created_date": datetime.fromtimestamp(question_data.get("creation_date", 0), tz=UTC),
        }

        # Build filter criteria
        filter_criteria = {
            "max_age_days": filters.max_age_days,
            "min_score": filters.min_score,
            "include_keywords": filters.include_keywords,
            "exclude_keywords": filters.exclude_keywords,
        }

        # Apply basic content filters
        if not apply_content_filter(content_data, filter_criteria):
            return False

        # Apply StackExchange-specific filters
        # Minimum answers filter
        if filters.min_answers is not None:
            answer_count = question_data.get("answer_count", 0)
            if answer_count < filters.min_answers:
                return False

        # Tag filtering
        question_tags = question_data.get("tags", [])

        # Required tags filter
        if filters.required_tags:
            if not any(tag in question_tags for tag in filters.required_tags):
                return False

        # Excluded tags filter
        if filters.excluded_tags:
            if any(tag in question_tags for tag in filters.excluded_tags):
                return False

        return True

    def _should_update_question(
        self, question_id: int, answer_count: int, last_activity_date: int
    ) -> tuple[bool, bool]:
        """
        Check if question should be updated based on answer count or activity changes.

        Args:
            question_id: StackExchange question ID
            answer_count: Current answer count
            last_activity_date: Last activity timestamp

        Returns:
            Tuple of (should_process, is_update) where:
            - should_process: True if question should be processed
            - is_update: True if this is an update to existing question
        """
        # Check if question exists in state
        if not self.state_manager.is_item_processed(str(question_id)):
            return (True, False)  # New question

        # Get stored state to check for changes
        try:
            stored_items = self.state_manager.get_processed_items(source_type="stackexchange")

            # Find this specific question in state
            for item_id, _source_type, _source_name, _timestamp, metadata in stored_items:
                if item_id == str(question_id) and metadata:
                    stored_answer_count = metadata.get("answer_count", 0)
                    stored_activity_date = metadata.get("last_activity_date", 0)

                    # Re-fetch if answer count increased or activity is newer
                    if answer_count > stored_answer_count:
                        self.logger.debug(
                            f"Question {question_id} has new answers: {stored_answer_count} -> {answer_count}"
                        )
                        return (True, True)  # Update: new answers

                    if last_activity_date > stored_activity_date:
                        self.logger.debug(f"Question {question_id} has new activity")
                        return (True, True)  # Update: new activity

                    # No changes detected
                    return (False, False)
        except Exception as e:
            self.logger.warning(f"Error checking question state for {question_id}: {e}")
            # On error, err on the side of processing
            return (True, False)

        # Default: skip if already processed and no changes detected
        return (False, False)

    def _format_question_content(
        self,
        question_data: dict[str, Any],
        answers: list[dict[str, Any]],
        comments: list[dict[str, Any]],
        site_name: str,
    ) -> tuple[str, dict[str, Any]]:
        """
        Format question, answers, and comments as markdown.

        Args:
            question_data: Question data from API
            answers: List of answer data
            comments: List of comment data
            site_name: StackExchange site name

        Returns:
            Tuple of (markdown_content, metadata)
        """
        # Build metadata with sanitized content
        metadata = {
            "title": sanitize_text_content(question_data.get("title", "Untitled Question")),
            "author": sanitize_text_content(question_data.get("owner", {}).get("display_name", "Anonymous")),
            "source": "stackexchange",
            "site": sanitize_text_content(site_name),
            "question_id": question_data.get("question_id"),
            "url": sanitize_text_content(question_data.get("link", "")),
            "tags": [sanitize_text_content(tag) for tag in question_data.get("tags", []) if tag],
            "score": question_data.get("score", 0),
            "answer_count": question_data.get("answer_count", 0),
            "view_count": question_data.get("view_count", 0),
            "created_date": datetime.fromtimestamp(question_data.get("creation_date", 0), tz=UTC).isoformat(),
            "collected_date": datetime.now(tz=UTC).isoformat(),
        }

        # Build markdown content with sanitized text
        content_parts = []

        # Question title and body
        safe_title = sanitize_text_content(question_data.get("title", "Untitled Question"))
        content_parts.append(f"# {safe_title}")
        content_parts.append("")

        if question_data.get("body"):
            safe_body = sanitize_text_content(question_data["body"])
            content_parts.append(safe_body)
            content_parts.append("")

        # Question metadata
        content_parts.append("## Question Details")
        content_parts.append("")
        content_parts.append(f"- **Score**: {question_data.get('score', 0)}")
        content_parts.append(f"- **Views**: {question_data.get('view_count', 0)}")
        content_parts.append(f"- **Answers**: {question_data.get('answer_count', 0)}")

        if question_data.get("tags"):
            tags_formatted = ", ".join(f"`{tag}`" for tag in question_data["tags"])
            content_parts.append(f"- **Tags**: {tags_formatted}")

        content_parts.append("")

        # Comments on question
        if comments:
            content_parts.append("## Comments")
            content_parts.append("")
            for comment in comments:
                author = sanitize_text_content(comment.get("owner", {}).get("display_name", "Anonymous"))
                score = comment.get("score", 0)
                body = sanitize_text_content(comment.get("body", ""))
                content_parts.append(f"**{author}** (score: {score}): {body}")
                content_parts.append("")

        # Answers
        if answers:
            content_parts.append("## Answers")
            content_parts.append("")

            for i, answer in enumerate(answers, 1):
                author = sanitize_text_content(answer.get("owner", {}).get("display_name", "Anonymous"))
                score = answer.get("score", 0)
                is_accepted = answer.get("is_accepted", False)

                accept_marker = " ✓" if is_accepted else ""
                content_parts.append(f"### Answer {i}{accept_marker}")
                content_parts.append("")
                content_parts.append(f"**Author**: {author} | **Score**: {score}")
                content_parts.append("")

                if answer.get("body"):
                    safe_answer_body = sanitize_text_content(answer["body"])
                    content_parts.append(safe_answer_body)
                    content_parts.append("")

        markdown_content = "\n".join(content_parts)
        return markdown_content, metadata

    def _generate_filename(self, question_data: dict[str, Any], site_name: str) -> str:
        """
        Generate secure filename for question markdown file.

        Args:
            question_data: Question data from API
            site_name: StackExchange site name

        Returns:
            Sanitized filename for the markdown file
        """
        question_id = sanitize_text_content(str(question_data.get("question_id", "unknown")))

        # Sanitize title for filename using shared security utility
        title = sanitize_text_content(question_data.get("title", "untitled"))
        clean_title = sanitize_filename(title)[:50]  # Use shared sanitization function

        # Sanitize site name
        clean_site_name = sanitize_filename(site_name)

        # Use creation date for organization
        creation_timestamp = question_data.get("creation_date", time.time())
        try:
            creation_date = datetime.fromtimestamp(creation_timestamp, tz=UTC)
            date_prefix = creation_date.strftime("%Y-%m-%d")
        except (ValueError, OSError):
            # Fallback to current date if timestamp is invalid
            date_prefix = datetime.now(UTC).strftime("%Y-%m-%d")

        # Generate secure filename
        filename_parts = [date_prefix, clean_site_name, clean_title, question_id]
        base_filename = "_".join(part for part in filename_parts if part)

        return sanitize_filename(f"{base_filename}.md")

    def collect_site(self, site_config: SiteConfig) -> dict[str, Any]:
        """
        Collect questions from a specific StackExchange site.

        Args:
            site_config: Site configuration

        Returns:
            Collection statistics
        """
        self.logger.info(f"Starting collection for {site_config.name}")

        stats: dict[str, Any] = {
            "site": site_config.name,
            "questions_processed": 0,
            "questions_saved": 0,
            "questions_updated": 0,
            "questions_skipped": 0,
            "errors": 0,
        }

        try:
            # Fetch questions
            questions = self._get_questions(site_config)
            self.logger.info(f"Fetched {len(questions)} questions from {site_config.name}")

            for question in questions:
                stats["questions_processed"] += 1
                question_id = question.get("question_id")

                if not question_id:
                    self.logger.warning("Question missing ID, skipping")
                    stats["questions_skipped"] += 1
                    continue

                try:
                    # Check if question needs updating
                    answer_count = question.get("answer_count", 0)
                    last_activity_date = question.get("last_activity_date", 0)

                    should_process, is_update = self._should_update_question(
                        question_id, answer_count, last_activity_date
                    )

                    if not should_process:
                        self.logger.debug(f"Question {question_id} already processed and unchanged, skipping")
                        stats["questions_skipped"] += 1
                        continue

                    # Apply filters
                    if not self._apply_filters(question, site_config):
                        self.logger.debug(f"Question {question_id} filtered out")
                        stats["questions_skipped"] += 1
                        continue

                    # Fetch additional data if requested
                    answers = []
                    comments = []

                    if site_config.include_answers or site_config.include_comments:
                        additional_data = self._get_answers_and_comments(question_id, site_config.name)
                        if site_config.include_answers:
                            answers = additional_data["answers"]
                        if site_config.include_comments:
                            comments = additional_data["comments"]

                    # Format content
                    markdown_content, metadata = self._format_question_content(
                        question, answers, comments, site_config.name
                    )

                    # Determine output path
                    output_dir = ensure_folder_structure(self.config.output_dir, "stackexchange", site_config.name)

                    filename = self._generate_filename(question, site_config.name)
                    output_path = output_dir / filename

                    # Check if content changed before writing (like Reddit does)
                    full_content_with_metadata = ""
                    if metadata:
                        frontmatter_lines = ["---"]
                        for key, value in metadata.items():
                            if value is not None:
                                if isinstance(value, str):
                                    frontmatter_lines.append(f'{key}: "{value}"')
                                elif isinstance(value, list):
                                    frontmatter_lines.append(f"{key}: {value}")
                                else:
                                    frontmatter_lines.append(f"{key}: {value}")
                        frontmatter_lines.append("---")
                        full_content_with_metadata = "\n".join(frontmatter_lines) + "\n\n" + markdown_content
                    else:
                        full_content_with_metadata = markdown_content

                    # Only write if content changed
                    from tools._shared.output import update_existing_file

                    if update_existing_file(str(output_path), full_content_with_metadata):
                        write_markdown_file(str(output_path), markdown_content, metadata)
                        self.logger.debug(f"Content changed, writing file: {output_path}")
                    else:
                        self.logger.debug(f"No content changes for: {output_path}")

                    # Mark as processed with tracking metrics
                    self.state_manager.mark_item_processed(
                        str(question_id),
                        "stackexchange",
                        site_config.name,
                        {
                            "title": question.get("title", ""),
                            "score": question.get("score", 0),
                            "answer_count": question.get("answer_count", 0),
                            "last_activity_date": question.get("last_activity_date", 0),
                        },
                    )

                    # Update stats based on whether this is new or updated
                    if is_update:
                        stats["questions_updated"] += 1
                        self.logger.debug(f"Updated question {question_id} at {output_path}")
                    else:
                        stats["questions_saved"] += 1
                        self.logger.debug(f"Saved question {question_id} to {output_path}")

                except Exception as question_error:
                    self.logger.error(f"Error processing question {question_id}: {question_error}")
                    stats["errors"] += 1

        except Exception as site_error:
            self.logger.error(f"Error collecting from site {site_config.name}: {site_error}")
            stats["errors"] += 1

        self.logger.info(f"Completed collection for {site_config.name}: {stats}")
        return stats

    def collect_all_sites(self) -> dict[str, Any]:
        """
        Collect from all configured StackExchange sites.

        Returns:
            Overall collection statistics
        """
        self.logger.info(f"Starting collection from {len(self.config.sites)} sites")

        overall_stats: dict[str, Any] = {
            "sites_processed": 0,
            "total_questions_processed": 0,
            "total_questions_saved": 0,
            "total_questions_updated": 0,
            "total_questions_skipped": 0,
            "total_errors": 0,
            "site_stats": [],
        }

        for site_config in self.config.sites:
            try:
                site_stats = self.collect_site(site_config)
                overall_stats["sites_processed"] += 1
                overall_stats["total_questions_processed"] += site_stats["questions_processed"]
                overall_stats["total_questions_saved"] += site_stats["questions_saved"]
                overall_stats["total_questions_updated"] += site_stats["questions_updated"]
                overall_stats["total_questions_skipped"] += site_stats["questions_skipped"]
                overall_stats["total_errors"] += site_stats["errors"]
                overall_stats["site_stats"].append(site_stats)

            except Exception as site_error:
                self.logger.error(f"Failed to collect from site {site_config.name}: {site_error}")
                overall_stats["total_errors"] += 1

        self.logger.info(f"Collection completed: {overall_stats}")
        return overall_stats

    def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        if hasattr(self, "http_client"):
            self.http_client.close()

    def __enter__(self) -> "StackExchangeCollector":
        """Context manager entry - returns self for use in with statements."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - ensures resources are cleaned up."""
        self.close()
