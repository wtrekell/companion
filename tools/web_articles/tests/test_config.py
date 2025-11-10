"""Tests for web-articles collector configuration module.

This module tests configuration loading, validation, and dataclass structures.
"""

from pathlib import Path

import pytest
import yaml

from tools.web_articles.src.collectors.web_articles.config import (
    FirecrawlConfig,
    SourceConfig,
    WebArticlesConfig,
    load_web_articles_config,
)


class TestSourceConfig:
    """Test SourceConfig dataclass."""

    def test_source_config_defaults(self) -> None:
        """Test default SourceConfig values."""
        source = SourceConfig(url="https://example.com/blog")
        assert source.url == "https://example.com/blog"
        assert source.max_depth == 1
        assert source.keywords == []
        assert source.link_patterns == {}

    def test_source_config_with_values(self) -> None:
        """Test SourceConfig with specific values."""
        source = SourceConfig(
            url="https://example.com/news",
            max_depth=3,
            keywords=["ai", "machine learning"],
            link_patterns={"include": ["*/blog/*"], "exclude": ["*/archive/*"]},
        )
        assert source.url == "https://example.com/news"
        assert source.max_depth == 3
        assert len(source.keywords) == 2
        assert "include" in source.link_patterns
        assert "exclude" in source.link_patterns


class TestFirecrawlConfig:
    """Test FirecrawlConfig dataclass."""

    def test_firecrawl_config_defaults(self) -> None:
        """Test default FirecrawlConfig values."""
        config = FirecrawlConfig()
        assert config.max_pages_per_source == 100
        assert config.timeout_ms == 30000
        assert config.only_main_content is True

    def test_firecrawl_config_with_values(self) -> None:
        """Test FirecrawlConfig with specific values."""
        config = FirecrawlConfig(max_pages_per_source=50, timeout_ms=60000, only_main_content=False)
        assert config.max_pages_per_source == 50
        assert config.timeout_ms == 60000
        assert config.only_main_content is False


class TestWebArticlesConfig:
    """Test WebArticlesConfig dataclass."""

    def test_web_articles_config_required_fields(self) -> None:
        """Test WebArticlesConfig with required fields only."""
        config = WebArticlesConfig(
            output_dir="output/web_articles",
            rate_limit_seconds=7.0,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
        )
        assert config.output_dir == "output/web_articles"
        assert config.rate_limit_seconds == 7.0
        assert config.exclude_keywords == []
        assert len(config.sources) == 1
        assert isinstance(config.firecrawl, FirecrawlConfig)
        # Check default values
        assert config.state_file == "tools/web_articles/data/gatherers_state.json"
        assert config.review_file == "tools/web_articles/data/links_for_review.yaml"

    def test_web_articles_config_all_fields(self) -> None:
        """Test WebArticlesConfig with all fields specified."""
        config = WebArticlesConfig(
            output_dir="custom/output",
            rate_limit_seconds=5.0,
            exclude_keywords=["spam", "ads"],
            sources=[
                SourceConfig(url="https://example.com", keywords=["test"]),
                SourceConfig(url="https://another.com", max_depth=2),
            ],
            firecrawl=FirecrawlConfig(max_pages_per_source=25),
            state_file="custom/state.json",
            review_file="custom/review.yaml",
        )
        assert config.output_dir == "custom/output"
        assert config.rate_limit_seconds == 5.0
        assert len(config.exclude_keywords) == 2
        assert len(config.sources) == 2
        assert config.state_file == "custom/state.json"
        assert config.review_file == "custom/review.yaml"


class TestConfigLoading:
    """Test configuration loading from YAML files."""

    def test_load_minimal_config(self, tmp_path: Path) -> None:
        """Test loading minimal valid configuration."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
output_dir: "output/web_articles"
rate_limit_seconds: 7.0
exclude_keywords: []
sources:
  - url: "https://example.com/blog"
        """
        )

        config = load_web_articles_config(str(config_file))
        assert config.output_dir == "output/web_articles"
        assert config.rate_limit_seconds == 7.0
        assert len(config.sources) == 1
        assert config.sources[0].url == "https://example.com/blog"

    def test_load_config_with_multiple_sources(self, tmp_path: Path) -> None:
        """Test loading configuration with multiple sources."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
output_dir: "output/web_articles"
rate_limit_seconds: 7.0
exclude_keywords: ["spam"]
sources:
  - url: "https://example.com/blog"
    max_depth: 1
    keywords: ["python", "ai"]
  - url: "https://another.com/news"
    max_depth: 2
    keywords: ["tech"]
        """
        )

        config = load_web_articles_config(str(config_file))
        assert len(config.sources) == 2
        assert config.sources[0].url == "https://example.com/blog"
        assert config.sources[0].max_depth == 1
        assert len(config.sources[0].keywords) == 2
        assert config.sources[1].url == "https://another.com/news"
        assert config.sources[1].max_depth == 2

    def test_load_config_with_firecrawl_settings(self, tmp_path: Path) -> None:
        """Test loading configuration with Firecrawl settings."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
output_dir: "output/web_articles"
rate_limit_seconds: 5.0
exclude_keywords: []
sources:
  - url: "https://example.com/blog"
firecrawl:
  max_pages_per_source: 50
  timeout_ms: 60000
  only_main_content: false
        """
        )

        config = load_web_articles_config(str(config_file))
        assert config.firecrawl.max_pages_per_source == 50
        assert config.firecrawl.timeout_ms == 60000
        assert config.firecrawl.only_main_content is False

    def test_load_config_with_custom_paths(self, tmp_path: Path) -> None:
        """Test loading configuration with custom state and review file paths."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
output_dir: "output/web_articles"
rate_limit_seconds: 7.0
exclude_keywords: []
state_file: "custom/state.json"
review_file: "custom/review.yaml"
sources:
  - url: "https://example.com/blog"
        """
        )

        config = load_web_articles_config(str(config_file))
        assert config.state_file == "custom/state.json"
        assert config.review_file == "custom/review.yaml"

    def test_load_config_missing_file(self) -> None:
        """Test loading non-existent configuration file."""
        with pytest.raises(FileNotFoundError):
            load_web_articles_config("/nonexistent/config.yaml")

    def test_load_config_empty_file(self, tmp_path: Path) -> None:
        """Test loading empty configuration file."""
        config_file = tmp_path / "empty_config.yaml"
        config_file.write_text("")

        with pytest.raises(ValueError, match="Configuration file is empty"):
            load_web_articles_config(str(config_file))

    def test_load_config_missing_output_dir(self, tmp_path: Path) -> None:
        """Test loading config missing required output_dir field."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
rate_limit_seconds: 7.0
sources:
  - url: "https://example.com/blog"
        """
        )

        with pytest.raises(ValueError, match="Missing required field: output_dir"):
            load_web_articles_config(str(config_file))

    def test_load_config_missing_sources(self, tmp_path: Path) -> None:
        """Test loading config missing required sources field."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
output_dir: "output/web_articles"
rate_limit_seconds: 7.0
        """
        )

        with pytest.raises(ValueError, match="Missing or empty required field: sources"):
            load_web_articles_config(str(config_file))

    def test_load_config_empty_sources(self, tmp_path: Path) -> None:
        """Test loading config with empty sources list."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
output_dir: "output/web_articles"
rate_limit_seconds: 7.0
sources: []
        """
        )

        with pytest.raises(ValueError, match="Missing or empty required field: sources"):
            load_web_articles_config(str(config_file))

    def test_load_config_source_missing_url(self, tmp_path: Path) -> None:
        """Test loading config with source missing URL field."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
output_dir: "output/web_articles"
rate_limit_seconds: 7.0
sources:
  - max_depth: 1
    keywords: ["test"]
        """
        )

        with pytest.raises(ValueError, match="Source at index 0 is missing required field: url"):
            load_web_articles_config(str(config_file))

    def test_load_config_invalid_source_type(self, tmp_path: Path) -> None:
        """Test loading config with invalid source type."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
output_dir: "output/web_articles"
rate_limit_seconds: 7.0
sources:
  - "https://example.com/blog"
        """
        )

        with pytest.raises(ValueError, match="Source at index 0 is not a dictionary"):
            load_web_articles_config(str(config_file))

    def test_load_config_default_rate_limit(self, tmp_path: Path) -> None:
        """Test that default rate limit is applied when not specified."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
output_dir: "output/web_articles"
sources:
  - url: "https://example.com/blog"
        """
        )

        config = load_web_articles_config(str(config_file))
        assert config.rate_limit_seconds == 7.0  # Default value

    def test_load_config_default_exclude_keywords(self, tmp_path: Path) -> None:
        """Test that default exclude keywords is empty list when not specified."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
output_dir: "output/web_articles"
sources:
  - url: "https://example.com/blog"
        """
        )

        config = load_web_articles_config(str(config_file))
        assert config.exclude_keywords == []


class TestConfigValidation:
    """Test configuration validation edge cases."""

    def test_source_url_formats(self, tmp_path: Path) -> None:
        """Test various URL formats are accepted."""
        valid_urls = [
            "https://example.com/blog",
            "http://example.com/news",
            "https://subdomain.example.com/articles",
            "https://example.com:8080/blog",
            "https://example.com/path/to/page",
        ]

        for url in valid_urls:
            config_file = tmp_path / "test_config.yaml"
            config_data = {"output_dir": "output", "sources": [{"url": url}]}

            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

            config = load_web_articles_config(str(config_file))
            assert config.sources[0].url == url

    def test_keywords_as_list(self, tmp_path: Path) -> None:
        """Test that keywords must be a list."""
        config_file = tmp_path / "test_config.yaml"
        config_data = {"output_dir": "output", "sources": [{"url": "https://example.com", "keywords": ["test"]}]}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_web_articles_config(str(config_file))
        assert isinstance(config.sources[0].keywords, list)
        assert config.sources[0].keywords == ["test"]

    def test_max_depth_values(self, tmp_path: Path) -> None:
        """Test various max_depth values are accepted."""
        for depth in [1, 2, 3, 5, 10]:
            config_file = tmp_path / f"test_config_{depth}.yaml"
            config_data = {"output_dir": "output", "sources": [{"url": "https://example.com", "max_depth": depth}]}

            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

            config = load_web_articles_config(str(config_file))
            assert config.sources[0].max_depth == depth
