"""Configuration loading and validation for web-direct collector.

This module provides configuration dataclasses and loading functionality
for the web-direct content collection tool.
"""

from dataclasses import dataclass, field

from tools._shared.config import load_yaml_config


@dataclass
class FilterCriteria:
    """Filter criteria for content filtering."""

    max_age_days: int | None = None
    min_content_length: int | None = None
    include_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)


@dataclass
class SourceConfig:
    """Configuration for a single source (index page) to crawl."""

    url: str
    max_articles: int = 50
    filters: FilterCriteria | None = None


@dataclass
class WebDirectConfig:
    """Complete configuration for web-direct collector."""

    output_dir: str
    sources: list[SourceConfig]
    rate_limit_seconds: float = 2.0
    state_file: str = "tools/web_direct/data/web_direct_state.json"
    default_filters: FilterCriteria | None = None
    max_retries: int = 3
    timeout_seconds: int = 30


def load_web_direct_config(config_path: str) -> WebDirectConfig:
    """Load and validate web-direct configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        WebDirectConfig instance with validated configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If configuration is invalid or missing required fields
    """
    # Load YAML file with secure environment variable substitution
    raw_config = load_yaml_config(config_path)

    if not raw_config:
        raise ValueError("Configuration file is empty")

    # Validate required fields
    if "output_dir" not in raw_config:
        raise ValueError("Missing required field: output_dir")

    if "sources" not in raw_config or not raw_config["sources"]:
        raise ValueError("Missing or empty required field: sources")

    # Parse default filters
    default_filters = None
    if "default_filters" in raw_config and raw_config["default_filters"]:
        filter_data = raw_config["default_filters"]
        default_filters = FilterCriteria(
            max_age_days=filter_data.get("max_age_days"),
            min_content_length=filter_data.get("min_content_length"),
            include_keywords=filter_data.get("include_keywords", []),
            exclude_keywords=filter_data.get("exclude_keywords", []),
        )

    # Parse sources
    sources = []
    for idx, source_data in enumerate(raw_config["sources"]):
        if not isinstance(source_data, dict):
            raise ValueError(f"Source at index {idx} is not a dictionary")

        if "url" not in source_data:
            raise ValueError(f"Source at index {idx} is missing required field: url")

        # Parse source-specific filters
        source_filters = None
        if "filters" in source_data and source_data["filters"]:
            filter_data = source_data["filters"]
            source_filters = FilterCriteria(
                max_age_days=filter_data.get("max_age_days"),
                min_content_length=filter_data.get("min_content_length"),
                include_keywords=filter_data.get("include_keywords", []),
                exclude_keywords=filter_data.get("exclude_keywords", []),
            )

        sources.append(
            SourceConfig(
                url=source_data["url"],
                max_articles=source_data.get("max_articles", 50),
                filters=source_filters,
            )
        )

    # Build final config
    return WebDirectConfig(
        output_dir=raw_config["output_dir"],
        sources=sources,
        rate_limit_seconds=raw_config.get("rate_limit_seconds", 2.0),
        state_file=raw_config.get("state_file", "tools/web_direct/data/web_direct_state.json"),
        default_filters=default_filters,
        max_retries=raw_config.get("max_retries", 3),
        timeout_seconds=raw_config.get("timeout_seconds", 30),
    )
