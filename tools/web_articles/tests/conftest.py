"""Pytest configuration and fixtures for web-articles collector tests.

This module provides shared fixtures and configuration for all web-articles collector tests.
"""

import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture  # type: ignore[misc]
def mock_firecrawl() -> MagicMock:
    """Create a mock Firecrawl API client for testing.

    Returns:
        MagicMock configured with typical Firecrawl API responses
    """
    mock = MagicMock()

    # Mock successful scrape_url response with markdown and links
    mock_scrape_result = MagicMock()
    mock_scrape_result.markdown = "# Test Article\n\nThis is test content from Firecrawl."
    mock_scrape_result.links = [
        "https://example.com/blog/article-1",
        "https://example.com/blog/article-2",
        "https://example.com/news/story-1",
    ]
    mock_scrape_result.metadata = {}

    mock.scrape_url.return_value = mock_scrape_result

    # Mock successful map_url response with list of URLs
    mock_map_result = MagicMock()
    mock_map_result.links = [
        "https://example.com/blog/article-1",
        "https://example.com/blog/article-2",
        "https://example.com/news/story-1",
        "https://example.com/blog/article-3",
    ]

    mock.map_url.return_value = mock_map_result

    return mock


@pytest.fixture  # type: ignore[misc]
def sample_config_data() -> dict[str, Any]:
    """Create sample configuration data for tests.

    Returns:
        Dictionary with valid web-articles configuration
    """
    return {
        "output_dir": "output/web_articles",
        "rate_limit_seconds": 1.0,
        "exclude_keywords": ["spam", "advertisement"],
        "state_file": "tools/web_articles/data/test_state.json",
        "review_file": "tools/web_articles/data/test_review.yaml",
        "firecrawl": {
            "max_pages_per_source": 50,
            "timeout_ms": 30000,
            "only_main_content": True,
        },
        "sources": [
            {
                "url": "https://example.com/blog",
                "max_depth": 1,
                "keywords": ["test", "example", "python"],
            },
            {
                "url": "https://another-site.com/news",
                "max_depth": 2,
                "keywords": ["ai", "machine learning"],
            },
        ],
    }


@pytest.fixture  # type: ignore[misc]
def temp_output_dir() -> Generator[Path, None, None]:
    """Create a temporary output directory for testing.

    Yields:
        Path to temporary directory (cleaned up after test)
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture  # type: ignore[misc]
def temp_config_file(temp_output_dir: Path, sample_config_data: dict[str, Any]) -> Path:
    """Create a temporary configuration file.

    Args:
        temp_output_dir: Temporary directory path
        sample_config_data: Sample configuration data

    Returns:
        Path to temporary config file
    """
    import yaml

    # Update paths to use temp directory
    config_data = sample_config_data.copy()
    config_data["output_dir"] = str(temp_output_dir / "output")
    config_data["state_file"] = str(temp_output_dir / "state.json")
    config_data["review_file"] = str(temp_output_dir / "review.yaml")

    config_file = temp_output_dir / "test_config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    return config_file


@pytest.fixture  # type: ignore[misc]
def sample_state_data() -> dict[str, Any]:
    """Create sample state data for testing.

    Returns:
        Dictionary with state tracking data
    """
    return {
        "discovered_urls": [
            "https://example.com/blog/article-1",
            "https://example.com/blog/article-2",
        ],
        "last_run": "2025-10-27T10:00:00",
        "total_discovered": 2,
    }


@pytest.fixture  # type: ignore[misc]
def temp_state_file(temp_output_dir: Path, sample_state_data: dict[str, Any]) -> Path:
    """Create a temporary state file.

    Args:
        temp_output_dir: Temporary directory path
        sample_state_data: Sample state data

    Returns:
        Path to temporary state file
    """
    import json

    state_file = temp_output_dir / "state.json"
    with open(state_file, "w") as f:
        json.dump(sample_state_data, f, indent=2)

    return state_file


@pytest.fixture  # type: ignore[misc]
def sample_review_data() -> dict[str, Any]:
    """Create sample review file data for testing.

    Returns:
        Dictionary with review file structure
    """
    return {
        "file_metadata": {
            "generated_by": "Link Review File Generator",
            "generated_on": "2025-10-27",
            "total_sources": 1,
            "total_links": 2,
        },
        "sources": [
            {
                "source_url": "https://example.com/blog",
                "discovery_date": "2025-10-27",
                "notes": "Links discovered from https://example.com/blog (2 new)",
                "links": [
                    {
                        "url": "https://example.com/blog/article-1",
                        "title": "Test Article 1",
                        "matched_keywords": ["test", "python"],
                    },
                    {
                        "url": "https://example.com/blog/article-2",
                        "title": "Test Article 2",
                        "matched_keywords": ["example"],
                    },
                ],
            }
        ],
    }


@pytest.fixture  # type: ignore[misc]
def temp_review_file(temp_output_dir: Path, sample_review_data: dict[str, Any]) -> Path:
    """Create a temporary review file.

    Args:
        temp_output_dir: Temporary directory path
        sample_review_data: Sample review data

    Returns:
        Path to temporary review file
    """
    import yaml

    review_file = temp_output_dir / "review.yaml"
    with open(review_file, "w") as f:
        yaml.dump(sample_review_data, f)

    return review_file


@pytest.fixture  # type: ignore[misc]
def sample_scraped_links() -> list[dict[str, str]]:
    """Create sample scraped link data.

    Returns:
        List of link dictionaries as returned by Firecrawl
    """
    return [
        {"url": "https://example.com/blog/article-1", "title": "Test Article 1"},
        {"url": "https://example.com/blog/article-2", "title": "Test Article 2"},
        {"url": "https://example.com/news/story-1", "title": "News Story 1"},
        {"url": "https://example.com/about", "title": "About Us"},  # Should be filtered
        {"url": "https://example.com/category/tech", "title": "Tech Category"},  # Should be filtered
    ]


@pytest.fixture(autouse=True)  # type: ignore[misc]
def clean_test_environment(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Clean test environment before each test.

    Args:
        monkeypatch: Pytest monkeypatch fixture
    """
    # Set mock API key for tests
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test-key-12345")

    yield

    # Cleanup after test
    pass
