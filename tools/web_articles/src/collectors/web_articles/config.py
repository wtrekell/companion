"""Configuration loading and validation for web-articles collector.

This module provides configuration dataclasses and loading functionality
for the web-articles content collection tool.
"""

from dataclasses import dataclass, field

from tools._shared.config import load_yaml_config


@dataclass
class SourceConfig:
    """Configuration for a single content source."""

    url: str
    max_depth: int = 1
    keywords: list[str] = field(default_factory=list)
    link_patterns: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class FirecrawlConfig:
    """Configuration for Firecrawl API behavior."""

    max_pages_per_source: int = 100
    timeout_ms: int = 30000
    only_main_content: bool = True


@dataclass
class WebArticlesConfig:
    """Complete configuration for web-articles collector."""

    output_dir: str
    rate_limit_seconds: float
    exclude_keywords: list[str]
    sources: list[SourceConfig]
    firecrawl: FirecrawlConfig
    state_file: str = "tools/web_articles/data/gatherers_state.json"
    review_file: str = "tools/web_articles/data/links_for_review.yaml"


def load_web_articles_config(config_path: str) -> WebArticlesConfig:
    """Load and validate web-articles configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        WebArticlesConfig instance with validated configuration

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

    # Parse sources
    sources = []
    for idx, source_data in enumerate(raw_config["sources"]):
        if not isinstance(source_data, dict):
            raise ValueError(f"Source at index {idx} is not a dictionary")

        if "url" not in source_data:
            raise ValueError(f"Source at index {idx} is missing required field: url")

        sources.append(
            SourceConfig(
                url=source_data["url"],
                max_depth=source_data.get("max_depth", 1),
                keywords=source_data.get("keywords", []),
                link_patterns=source_data.get("link_patterns", {}),
            )
        )

    # Parse Firecrawl config
    firecrawl_data = raw_config.get("firecrawl", {})
    firecrawl_config = FirecrawlConfig(
        max_pages_per_source=firecrawl_data.get("max_pages_per_source", 100),
        timeout_ms=firecrawl_data.get("timeout_ms", 30000),
        only_main_content=firecrawl_data.get("only_main_content", True),
    )

    # Build final config
    return WebArticlesConfig(
        output_dir=raw_config["output_dir"],
        rate_limit_seconds=raw_config.get("rate_limit_seconds", 7.0),
        exclude_keywords=raw_config.get("exclude_keywords", []),
        sources=sources,
        firecrawl=firecrawl_config,
        state_file=raw_config.get("state_file", "tools/web_articles/data/gatherers_state.json"),
        review_file=raw_config.get("review_file", "tools/web_articles/data/links_for_review.yaml"),
    )
