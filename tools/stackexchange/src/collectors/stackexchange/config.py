"""Configuration classes for StackExchange collector.

This module defines typed configuration structures for StackExchange collection settings.
"""

from dataclasses import dataclass, field

from tools._shared.config import load_yaml_config
from tools._shared.exceptions import ConfigurationValidationError
from tools._shared.security import (
    sanitize_text_content,
    validate_input_length,
    validate_url_for_ssrf,
)


@dataclass
class FilterCriteria:
    """Content filtering criteria for StackExchange questions."""

    max_age_days: int | None = None
    min_score: int | None = None
    min_answers: int | None = None
    include_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    required_tags: list[str] = field(default_factory=list)
    excluded_tags: list[str] = field(default_factory=list)


@dataclass
class SiteConfig:
    """Configuration for a specific StackExchange site."""

    name: str
    tags: list[str] = field(default_factory=list)
    filters: FilterCriteria | None = None
    max_questions: int = 50
    include_answers: bool = True
    include_comments: bool = True
    sort_order: str = "activity"  # activity, votes, creation, relevance


@dataclass
class StackExchangeCollectorConfig:
    """Main configuration for StackExchange collector."""

    output_dir: str
    api_key: str = ""  # Optional for higher quotas
    rate_limit_seconds: float = 1.0
    default_filters: FilterCriteria = field(default_factory=FilterCriteria)
    sites: list[SiteConfig] = field(default_factory=list)

    # StackExchange API settings
    api_version: str = "2.3"
    base_url: str = "https://api.stackexchange.com"
    user_agent: str = "Signal:StackExchange:Collector:v2.0.0"
    max_page_size: int = 100


def _validate_numeric_bounds(value: int | float, field_name: str, min_val: int | float, max_val: int | float) -> None:
    """Validate numeric field is within acceptable bounds."""
    if not isinstance(value, (int, float)):
        raise ConfigurationValidationError(f"{field_name} must be a number")
    if value < min_val or value > max_val:
        raise ConfigurationValidationError(f"{field_name} must be between {min_val} and {max_val}, got {value}")


def _validate_sort_order(sort_order: str) -> str:
    """Validate and sanitize sort order parameter."""
    valid_sorts = {"activity", "votes", "creation", "relevance"}
    sanitized_sort = sanitize_text_content(sort_order.lower().strip())
    if sanitized_sort not in valid_sorts:
        raise ConfigurationValidationError(f"sort_order must be one of {valid_sorts}, got '{sort_order}'")
    return sanitized_sort


def _validate_site_name(site_name: str) -> str:
    """Validate and sanitize StackExchange site name."""
    # StackExchange site names are limited and well-defined
    sanitized_name = sanitize_text_content(site_name.lower().strip())
    sanitized_name = validate_input_length(sanitized_name, 100, "site name")

    # Basic validation - should contain only letters, numbers, dots, hyphens
    import re

    if not re.match(r"^[a-z0-9.-]+$", sanitized_name):
        raise ConfigurationValidationError(
            f"Invalid site name format: '{site_name}'. Should contain only letters, numbers, dots, and hyphens."
        )

    return sanitized_name


def _validate_tags_list(tags: list[str], field_name: str) -> list[str]:
    """Validate and sanitize list of tags."""
    if not isinstance(tags, list):
        raise ConfigurationValidationError(f"{field_name} must be a list")

    validated_tags = []
    for tag in tags:
        if not isinstance(tag, str):
            raise ConfigurationValidationError(f"All {field_name} must be strings")

        sanitized_tag = sanitize_text_content(tag.strip())
        sanitized_tag = validate_input_length(sanitized_tag, 50, f"{field_name} item")

        if sanitized_tag:  # Only add non-empty tags
            validated_tags.append(sanitized_tag)

    return validated_tags


def load_stackexchange_config(config_path: str) -> StackExchangeCollectorConfig:
    """
    Load StackExchange collector configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Parsed configuration object

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        ConfigurationValidationError: If configuration is invalid
    """
    raw_config = load_yaml_config(config_path)

    # Parse and validate default filters
    default_filters_data = raw_config.get("default_filters", {})

    # Validate numeric filter values
    max_age_days = default_filters_data.get("max_age_days")
    if max_age_days is not None:
        _validate_numeric_bounds(max_age_days, "default_filters.max_age_days", 1, 3650)  # 1 day to 10 years

    min_score = default_filters_data.get("min_score")
    if min_score is not None:
        _validate_numeric_bounds(min_score, "default_filters.min_score", -1000, 10000)

    min_answers = default_filters_data.get("min_answers")
    if min_answers is not None:
        _validate_numeric_bounds(min_answers, "default_filters.min_answers", 0, 1000)

    default_filters = FilterCriteria(
        max_age_days=max_age_days,
        min_score=min_score,
        min_answers=min_answers,
        include_keywords=_validate_tags_list(default_filters_data.get("include_keywords", []), "include_keywords"),
        exclude_keywords=_validate_tags_list(default_filters_data.get("exclude_keywords", []), "exclude_keywords"),
        required_tags=_validate_tags_list(default_filters_data.get("required_tags", []), "required_tags"),
        excluded_tags=_validate_tags_list(default_filters_data.get("excluded_tags", []), "excluded_tags"),
    )

    # Parse and validate site configurations
    sites = []
    for i, site_data in enumerate(raw_config.get("sites", [])):
        if not isinstance(site_data, dict):
            raise ConfigurationValidationError(f"Site at index {i} must be a dictionary")

        # Validate required fields
        if "name" not in site_data:
            raise ConfigurationValidationError(f"Site at index {i} is missing required 'name' field")

        # Validate and sanitize site name
        site_name = _validate_site_name(site_data["name"])

        # Validate numeric site parameters
        max_questions = site_data.get("max_questions", 50)
        _validate_numeric_bounds(max_questions, f"site[{i}].max_questions", 1, 1000)

        # Validate and sanitize tags
        site_tags = _validate_tags_list(site_data.get("tags", []), f"site[{i}].tags")

        # Validate sort order
        sort_order = _validate_sort_order(site_data.get("sort_order", "activity"))

        # Parse site-specific filters if present
        site_filters = None
        if "filters" in site_data:
            filter_data = site_data["filters"]
            if not isinstance(filter_data, dict):
                raise ConfigurationValidationError(f"Site[{i}].filters must be a dictionary")

            # Validate site filter numeric values
            site_max_age = filter_data.get("max_age_days")
            if site_max_age is not None:
                _validate_numeric_bounds(site_max_age, f"site[{i}].filters.max_age_days", 1, 3650)

            site_min_score = filter_data.get("min_score")
            if site_min_score is not None:
                _validate_numeric_bounds(site_min_score, f"site[{i}].filters.min_score", -1000, 10000)

            site_min_answers = filter_data.get("min_answers")
            if site_min_answers is not None:
                _validate_numeric_bounds(site_min_answers, f"site[{i}].filters.min_answers", 0, 1000)

            site_filters = FilterCriteria(
                max_age_days=site_max_age,
                min_score=site_min_score,
                min_answers=site_min_answers,
                include_keywords=_validate_tags_list(
                    filter_data.get("include_keywords", []), f"site[{i}].include_keywords"
                ),
                exclude_keywords=_validate_tags_list(
                    filter_data.get("exclude_keywords", []), f"site[{i}].exclude_keywords"
                ),
                required_tags=_validate_tags_list(filter_data.get("required_tags", []), f"site[{i}].required_tags"),
                excluded_tags=_validate_tags_list(filter_data.get("excluded_tags", []), f"site[{i}].excluded_tags"),
            )

        site_config = SiteConfig(
            name=site_name,
            tags=site_tags,
            filters=site_filters,
            max_questions=max_questions,
            include_answers=bool(site_data.get("include_answers", True)),
            include_comments=bool(site_data.get("include_comments", True)),
            sort_order=sort_order,
        )
        sites.append(site_config)

    # Build and validate main configuration
    # Validate required main config fields
    if "output_dir" not in raw_config:
        raise ConfigurationValidationError("Missing required 'output_dir' field in StackExchange configuration")

    # Validate output directory path
    output_dir = sanitize_text_content(str(raw_config["output_dir"]).strip())
    if not output_dir:
        raise ConfigurationValidationError("output_dir cannot be empty")

    # Validate API configuration
    api_key = sanitize_text_content(raw_config.get("api_key", "").strip())
    if api_key:
        api_key = validate_input_length(api_key, 1000, "api_key")

    # Validate rate limiting
    rate_limit_seconds = raw_config.get("rate_limit_seconds", 1.0)
    _validate_numeric_bounds(rate_limit_seconds, "rate_limit_seconds", 0.1, 300.0)  # 0.1s to 5 min

    # Validate API version
    api_version = sanitize_text_content(raw_config.get("api_version", "2.3").strip())
    if not api_version:
        raise ConfigurationValidationError("api_version cannot be empty")

    # CRITICAL: Validate base URL for SSRF protection
    base_url = raw_config.get("base_url", "https://api.stackexchange.com")
    if not validate_url_for_ssrf(base_url):
        raise ConfigurationValidationError(
            f"base_url '{base_url}' is blocked by SSRF protection. "
            "Only public HTTPS URLs are allowed for StackExchange API endpoints."
        )

    # Validate user agent
    user_agent = sanitize_text_content(raw_config.get("user_agent", "Signal:StackExchange:Collector:v2.0.0"))
    user_agent = validate_input_length(user_agent, 200, "user_agent")

    # Validate page size
    max_page_size = raw_config.get("max_page_size", 100)
    _validate_numeric_bounds(max_page_size, "max_page_size", 1, 100)  # StackExchange API limit

    # Ensure we have at least one site configured
    if not sites:
        raise ConfigurationValidationError("At least one site must be configured")

    config = StackExchangeCollectorConfig(
        output_dir=output_dir,
        api_key=api_key,
        rate_limit_seconds=float(rate_limit_seconds),
        default_filters=default_filters,
        sites=sites,
        api_version=api_version,
        base_url=base_url,
        user_agent=user_agent,
        max_page_size=int(max_page_size),
    )

    return config
