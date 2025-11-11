"""Tests for web_direct collector."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from tools.web_direct.src.collectors.web_direct.collector import WebDirectCollector
from tools.web_direct.src.collectors.web_direct.config import (
    FilterCriteria,
    SourceConfig,
    WebDirectConfig,
)


class TestWebDirectCollector:
    """Test WebDirectCollector class."""

    def test_collector_initialization(self, sample_config_data: dict[str, Any]) -> None:
        """Test collector initialization with valid config."""
        config = WebDirectConfig(
            output_dir=sample_config_data["output_dir"],
            sources=[SourceConfig(url="https://example.com/blog")],
            state_file=sample_config_data["state_file"],
        )

        collector = WebDirectCollector(config)

        assert collector.config == config
        assert collector.session is not None
        assert collector.state_manager is not None

    def test_merge_filters_both_none(self, sample_config_data: dict[str, Any]) -> None:
        """Test merging filters when both are None."""
        config = WebDirectConfig(
            output_dir=sample_config_data["output_dir"],
            sources=[SourceConfig(url="https://example.com/blog")],
        )

        collector = WebDirectCollector(config)
        result = collector._merge_filters(None, None)

        assert result is None

    def test_merge_filters_default_only(self, sample_config_data: dict[str, Any]) -> None:
        """Test merging filters with only default filters."""
        config = WebDirectConfig(
            output_dir=sample_config_data["output_dir"],
            sources=[SourceConfig(url="https://example.com/blog")],
        )

        collector = WebDirectCollector(config)
        default = FilterCriteria(max_age_days=30, exclude_keywords=["spam"])

        result = collector._merge_filters(default, None)

        assert result == default

    def test_merge_filters_specific_overrides_default(self, sample_config_data: dict[str, Any]) -> None:
        """Test that specific filters override defaults."""
        config = WebDirectConfig(
            output_dir=sample_config_data["output_dir"],
            sources=[SourceConfig(url="https://example.com/blog")],
        )

        collector = WebDirectCollector(config)
        default = FilterCriteria(max_age_days=30, min_content_length=100)
        specific = FilterCriteria(max_age_days=7, include_keywords=["ai"])

        result = collector._merge_filters(default, specific)

        assert result.max_age_days == 7  # Overridden
        assert result.min_content_length == 100  # From default
        assert result.include_keywords == ["ai"]  # From specific

    @patch("tools.web_direct.src.collectors.web_direct.collector.BeautifulSoup")
    @patch("tools.web_direct.src.collectors.web_direct.collector.requests.Session")
    def test_discover_links_success(
        self,
        mock_session_class: MagicMock,
        mock_bs: MagicMock,
        sample_config_data: dict[str, Any],
    ) -> None:
        """Test successful link discovery from index page."""
        # Setup mock HTML response
        mock_response = Mock()
        mock_response.text = "<html><a href='/blog/article-1'>Article 1</a></html>"
        mock_response.raise_for_status = Mock()

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Setup BeautifulSoup mock
        mock_soup = Mock()
        mock_link = Mock()
        mock_link.__getitem__ = Mock(return_value="/blog/article-1")
        mock_soup.find_all.return_value = [mock_link]
        mock_bs.return_value = mock_soup

        config = WebDirectConfig(
            output_dir=sample_config_data["output_dir"],
            sources=[SourceConfig(url="https://example.com/blog")],
            state_file=sample_config_data["state_file"],
        )

        collector = WebDirectCollector(config)
        collector.session = mock_session

        links = collector._discover_links("https://example.com/blog", verbose=False)

        assert isinstance(links, list)
        assert mock_session.get.called

    @patch("tools.web_direct.src.collectors.web_direct.collector.trafilatura")
    @patch("tools.web_direct.src.collectors.web_direct.collector.requests.Session")
    def test_fetch_article_success(
        self,
        mock_session_class: MagicMock,
        mock_trafilatura: MagicMock,
        sample_config_data: dict[str, Any],
        mock_html_response: str,
        mock_markdown_content: str,
    ) -> None:
        """Test successful article fetching."""
        # Setup mocks
        mock_response = Mock()
        mock_response.text = mock_html_response
        mock_response.raise_for_status = Mock()

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        mock_trafilatura.extract.return_value = mock_markdown_content

        # Mock metadata
        mock_metadata = Mock()
        mock_metadata.title = "Test Article Title"
        mock_metadata.author = "Test Author"
        mock_metadata.description = "Test description"
        mock_metadata.date = "2025-01-15"
        mock_trafilatura.extract_metadata.return_value = mock_metadata

        # Create collector
        config = WebDirectConfig(
            output_dir=sample_config_data["output_dir"],
            sources=[SourceConfig(url="https://example.com/blog")],
            state_file=sample_config_data["state_file"],
        )

        collector = WebDirectCollector(config)
        collector.session = mock_session

        # Fetch article
        source = SourceConfig(url="https://example.com/blog")
        result = collector._fetch_article("https://example.com/blog/article", source, verbose=False)

        assert result is not None
        assert isinstance(result, dict)
        assert result["title"] == "Test Article Title"
        assert result["markdown"] == mock_markdown_content
        assert result["author"] == "Test Author"
        assert result["created_date"] == "2025-01-15"

    @patch("tools.web_direct.src.collectors.web_direct.collector.trafilatura")
    @patch("tools.web_direct.src.collectors.web_direct.collector.requests.Session")
    def test_fetch_article_filtered_out(
        self,
        mock_session_class: MagicMock,
        mock_trafilatura: MagicMock,
        sample_config_data: dict[str, Any],
        mock_html_response: str,
    ) -> None:
        """Test article being filtered out."""
        # Setup mocks
        mock_response = Mock()
        mock_response.text = mock_html_response
        mock_response.raise_for_status = Mock()

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Return short content (will be filtered)
        mock_trafilatura.extract.return_value = "Short content."
        mock_trafilatura.extract_metadata.return_value = None

        # Create collector with filters
        config = WebDirectConfig(
            output_dir=sample_config_data["output_dir"],
            sources=[SourceConfig(url="https://example.com/blog")],
            state_file=sample_config_data["state_file"],
            default_filters=FilterCriteria(min_content_length=100),
        )

        collector = WebDirectCollector(config)
        collector.session = mock_session

        # Fetch article
        source = SourceConfig(url="https://example.com/blog")
        result = collector._fetch_article("https://example.com/blog/article", source, verbose=False)

        # Should return tuple indicating filtered with reason
        assert isinstance(result, tuple)
        assert result[0] is None
        assert "too_short" in result[1]

    @patch("tools.web_direct.src.collectors.web_direct.collector.write_markdown_file")
    def test_save_article(
        self,
        mock_write: MagicMock,
        sample_config_data: dict[str, Any],
    ) -> None:
        """Test saving article to file."""
        config = WebDirectConfig(
            output_dir=sample_config_data["output_dir"],
            sources=[SourceConfig(url="https://example.com/blog")],
            state_file=sample_config_data["state_file"],
        )

        collector = WebDirectCollector(config)

        url = "https://example.com/blog/article"
        result = {
            "title": "Test Article",
            "markdown": "# Test\n\nContent",
            "word_count": 50,
            "created_date": "2025-01-15",
            "author": "Test Author",
            "description": "Test description",
        }

        collector._save_article(url, result, verbose=False)

        # Check that write_markdown_file was called
        assert mock_write.called
        call_args = mock_write.call_args

        # Check frontmatter
        frontmatter = call_args[1]["metadata_dict"]
        assert frontmatter["title"] == "Test Article"
        assert frontmatter["url"] == url
        assert frontmatter["source"] == "web_direct"
        assert frontmatter["word_count"] == 50

        # Check state was updated
        assert url in collector.state
        assert collector.state[url]["status"] == "success"

    def test_filter_article_links(self, sample_config_data: dict[str, Any]) -> None:
        """Test filtering of article-like links."""
        config = WebDirectConfig(
            output_dir=sample_config_data["output_dir"],
            sources=[SourceConfig(url="https://example.com/blog")],
        )

        collector = WebDirectCollector(config)

        links = [
            "https://example.com/blog/my-article",  # Should include
            "https://example.com/tag/python",  # Should exclude
            "https://example.com/about",  # Should exclude
            "https://other-site.com/blog/article",  # Should exclude (different domain)
            "https://example.com/news/2024/article",  # Should include (has year)
        ]

        filtered = collector._filter_article_links(links, "https://example.com/blog")

        assert "https://example.com/blog/my-article" in filtered
        assert "https://example.com/news/2024/article" in filtered
        assert "https://example.com/tag/python" not in filtered
        assert "https://example.com/about" not in filtered
        assert "https://other-site.com/blog/article" not in filtered


class TestConfigValidation:
    """Test configuration validation."""

    def test_merge_filters_all_fields(self, sample_config_data: dict[str, Any]) -> None:
        """Test merging filters with all fields."""
        config = WebDirectConfig(
            output_dir=sample_config_data["output_dir"],
            sources=[SourceConfig(url="https://example.com/blog")],
        )

        collector = WebDirectCollector(config)

        default = FilterCriteria(
            max_age_days=365,
            min_content_length=100,
            include_keywords=["default"],
            exclude_keywords=["spam"],
        )

        specific = FilterCriteria(
            max_age_days=30,
            min_content_length=500,
            include_keywords=["specific"],
            exclude_keywords=["ads"],
        )

        result = collector._merge_filters(default, specific)

        assert result.max_age_days == 30
        assert result.min_content_length == 500
        assert result.include_keywords == ["specific"]
        assert result.exclude_keywords == ["ads"]
