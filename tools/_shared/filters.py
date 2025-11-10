"""Content filtering utilities for content collectors.

Simplified for personal use - keyword matching and age/score filtering.
No ReDoS protection or field size limits needed.
"""

import fnmatch
import logging
import re
from datetime import UTC, datetime, timedelta
from html import unescape
from typing import Any

logger = logging.getLogger(__name__)


def strip_html_tags(html_content: str) -> str:
    """Strip HTML tags and convert to plain text."""
    if not html_content:
        return ""
    text = re.sub(r"<[^>]+>", " ", html_content)
    text = unescape(text)
    text = " ".join(text.split())
    return text


def matches_keywords(text_content: str, keyword_list: list[str], case_sensitive: bool = False) -> bool:
    """
    Check if text matches any keywords (supports wildcards * and ?).

    Args:
        text_content: Text to search in
        keyword_list: Keywords/patterns to match
        case_sensitive: Case sensitive matching

    Returns:
        True if any keyword matches
    """
    if not text_content or not keyword_list:
        return False

    search_text = text_content if case_sensitive else text_content.lower()

    for keyword in keyword_list:
        if not keyword:
            continue

        pattern = keyword if case_sensitive else keyword.lower()

        # Wildcard or simple substring match
        if "*" in pattern or "?" in pattern:
            if fnmatch.fnmatch(search_text, f"*{pattern}*"):
                return True
        else:
            if pattern in search_text:
                return True

    return False


def matches_keywords_debug(
    text_content: str, keyword_list: list[str], case_sensitive: bool = False
) -> tuple[bool, str | None]:
    """Debug version that returns which keyword matched."""
    if not text_content or not keyword_list:
        return False, None

    search_text = text_content if case_sensitive else text_content.lower()

    for keyword in keyword_list:
        if not keyword:
            continue

        pattern = keyword if case_sensitive else keyword.lower()

        if "*" in pattern or "?" in pattern:
            if fnmatch.fnmatch(search_text, f"*{pattern}*"):
                return True, keyword
        else:
            if pattern in search_text:
                return True, keyword

    return False, None


def apply_content_filter(content_data: dict[str, Any], filter_criteria: dict[str, Any]) -> bool:
    """
    Apply filtering based on age, score, and keywords.

    Args:
        content_data: Content metadata (title, text, score, created_date, etc.)
        filter_criteria: Filtering criteria

    Returns:
        True if content passes all filters
    """
    logger.debug(f"Applying filters: {filter_criteria}")
    logger.debug(f"Content: '{content_data.get('title', '')}'")

    # Build combined text for keyword matching
    text_parts = []
    if content_data.get("title"):
        text_parts.append(str(content_data["title"]))
    if content_data.get("text"):
        text_parts.append(str(content_data["text"]))
    if content_data.get("body"):
        body = content_data["body"]
        if isinstance(body, dict):
            body_text = body.get("html", "") or body.get("plain", "")
            if body.get("html"):
                body_text = strip_html_tags(body_text)
            text_parts.append(body_text)
        else:
            body_str = str(body)
            if "<" in body_str and ">" in body_str:
                body_str = strip_html_tags(body_str)
            text_parts.append(body_str)

    combined_text = " ".join(text_parts)

    # Age filtering
    max_age = filter_criteria.get("max_age_days")
    if max_age is not None and content_data.get("created_date"):
        try:
            created = content_data["created_date"]
            if isinstance(created, str):
                content_date = datetime.fromisoformat(created)
            elif isinstance(created, datetime):
                content_date = created
            else:
                content_date = datetime.fromtimestamp(float(created))

            # Normalize to UTC
            if content_date.tzinfo is None:
                content_date = content_date.replace(tzinfo=UTC)
            else:
                content_date = content_date.astimezone(UTC)

            cutoff = datetime.now(tz=UTC) - timedelta(days=max_age)
            if content_date < cutoff:
                logger.debug("Rejected: too old")
                return False
        except (ValueError, TypeError) as e:
            logger.debug(f"Age filter skipped: {e}")

    # Score filtering
    min_score = filter_criteria.get("min_score")
    if min_score is not None and content_data.get("score") is not None:
        try:
            if float(content_data["score"]) < min_score:
                logger.debug("Rejected: score too low")
                return False
        except (ValueError, TypeError) as e:
            logger.debug(f"Score filter skipped: {e}")

    # Comments filtering (Reddit-specific)
    min_comments = filter_criteria.get("min_comments")
    if min_comments is not None and content_data.get("num_comments") is not None:
        try:
            if int(content_data["num_comments"]) < min_comments:
                logger.debug("Rejected: not enough comments")
                return False
        except (ValueError, TypeError) as e:
            logger.debug(f"Comments filter skipped: {e}")

    # Include keywords (must match at least one)
    include_keywords = filter_criteria.get("include_keywords", [])
    if include_keywords:
        if not matches_keywords(combined_text, include_keywords):
            logger.debug("Rejected: no include keywords matched")
            return False

    # Exclude keywords (must not match any)
    exclude_keywords = filter_criteria.get("exclude_keywords", [])
    if exclude_keywords:
        matched, keyword = matches_keywords_debug(combined_text, exclude_keywords)
        if matched:
            logger.debug(f"Rejected: matched exclude keyword '{keyword}'")
            return False

    logger.debug("Passed all filters")
    return True


# Backwards compatibility alias
apply_content_filter_with_keywords = apply_content_filter
