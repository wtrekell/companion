"""Pytest configuration and fixtures for web_direct tests."""

import tempfile
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def temp_output_dir() -> Path:
    """Create a temporary output directory for tests.

    Returns:
        Path to temporary directory
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_state_file(temp_output_dir: Path) -> Path:
    """Create a temporary state file path.

    Args:
        temp_output_dir: Temporary output directory

    Returns:
        Path to temporary state file
    """
    return temp_output_dir / "test_state.json"


@pytest.fixture
def sample_config_data(temp_output_dir: Path, temp_state_file: Path) -> dict[str, Any]:
    """Create sample configuration data.

    Args:
        temp_output_dir: Temporary output directory
        temp_state_file: Temporary state file path

    Returns:
        Dictionary with sample config data
    """
    return {
        "output_dir": str(temp_output_dir),
        "rate_limit_seconds": 0.1,
        "state_file": str(temp_state_file),
        "max_retries": 3,
        "timeout_seconds": 30,
        "articles": [
            {"url": "https://example.com/article-1", "title": "Test Article 1"},
            {"url": "https://example.com/article-2"},
        ],
        "default_filters": {
            "max_age_days": 365,
            "min_content_length": 100,
            "exclude_keywords": ["spam"],
        },
    }


@pytest.fixture
def mock_html_response() -> str:
    """Create mock HTML response for testing.

    Returns:
        HTML string
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Article Title</title>
        <meta name="author" content="Test Author">
        <meta name="description" content="Test description">
        <meta name="date" content="2025-01-15">
    </head>
    <body>
        <article>
            <h1>Test Article Title</h1>
            <p>This is the main content of the article. It contains multiple sentences
            to ensure the word count is sufficient for testing. The content extraction
            should work well with this simple HTML structure.</p>
            <p>Another paragraph to add more content and increase the word count.</p>
        </article>
    </body>
    </html>
    """


@pytest.fixture
def mock_markdown_content() -> str:
    """Create mock markdown content for testing.

    Returns:
        Markdown string
    """
    return """# Test Article Title

This is the main content of the article. It contains multiple sentences
to ensure the word count is sufficient for testing. The content extraction
should work well with this simple HTML structure.

Another paragraph to add more content and increase the word count."""
