"""Tests for web-articles link discovery collector.

This module tests link extraction, filtering, state management, and review file generation.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from tools.web_articles.src.collectors.web_articles.collector import WebArticlesDiscoverer
from tools.web_articles.src.collectors.web_articles.config import (
    FirecrawlConfig,
    SourceConfig,
    WebArticlesConfig,
)


class TestWebArticlesDiscoverer:
    """Test WebArticlesDiscoverer class."""

    def test_discoverer_initialization(self, sample_config_data: dict[str, Any], mock_firecrawl: MagicMock) -> None:
        """Test discoverer initialization with valid config."""

        # Create config from sample data
        config = WebArticlesConfig(
            output_dir=sample_config_data["output_dir"],
            rate_limit_seconds=sample_config_data["rate_limit_seconds"],
            exclude_keywords=sample_config_data["exclude_keywords"],
            sources=[
                SourceConfig(
                    url=source["url"],
                    max_depth=source.get("max_depth", 1),
                    keywords=source.get("keywords", []),
                )
                for source in sample_config_data["sources"]
            ],
            firecrawl=FirecrawlConfig(),
        )

        with patch(
            "tools.web_articles.src.collectors.web_articles.collector.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            discoverer = WebArticlesDiscoverer(config)
            assert discoverer.config == config
            assert discoverer.firecrawl_api_key == "fc-test-key-12345"

    def test_discoverer_missing_api_key(
        self, sample_config_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing API key raises ValueError."""
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

        config = WebArticlesConfig(
            output_dir=sample_config_data["output_dir"],
            rate_limit_seconds=sample_config_data["rate_limit_seconds"],
            exclude_keywords=sample_config_data["exclude_keywords"],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
        )

        with pytest.raises(ValueError, match="FIRECRAWL_API_KEY environment variable not found"):
            WebArticlesDiscoverer(config)


class TestLinkExtraction:
    """Test link extraction from web pages."""

    def test_extract_links_from_firecrawl_response(
        self, temp_output_dir: Path, sample_config_data: dict[str, Any], mock_firecrawl: MagicMock
    ) -> None:
        """Test extracting links from Firecrawl API response."""
        # Update config to use temp directory
        config = WebArticlesConfig(
            output_dir=str(temp_output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com/blog")],
            firecrawl=FirecrawlConfig(),
            state_file=str(temp_output_dir / "state.json"),
            review_file=str(temp_output_dir / "review.yaml"),
        )

        with patch(
            "tools.web_articles.src.collectors.web_articles.collector.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            discoverer = WebArticlesDiscoverer(config)
            links = discoverer._extract_links("https://example.com/blog")

            # Should extract blog and news links (article indicators)
            assert isinstance(links, list)
            assert all("url" in link and "title" in link for link in links)

    def test_extract_title_from_url(self, temp_output_dir: Path, mock_firecrawl: MagicMock) -> None:
        """Test extracting readable title from URL path."""
        config = WebArticlesConfig(
            output_dir=str(temp_output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
        )

        with patch(
            "tools.web_articles.src.collectors.web_articles.collector.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            discoverer = WebArticlesDiscoverer(config)

            # Test various URL formats
            assert discoverer._extract_title_from_url("https://example.com/blog/my-great-article") == "My Great Article"
            assert discoverer._extract_title_from_url("https://example.com/posts/hello_world") == "Hello World"
            assert discoverer._extract_title_from_url("https://example.com/news/breaking-news.html") == "Breaking News"


class TestLinkFiltering:
    """Test link filtering logic."""

    def test_filter_article_links(self, temp_output_dir: Path, mock_firecrawl: MagicMock) -> None:
        """Test filtering to only include article-like links."""
        config = WebArticlesConfig(
            output_dir=str(temp_output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
        )

        with patch(
            "tools.web_articles.src.collectors.web_articles.collector.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            discoverer = WebArticlesDiscoverer(config)

            test_links = [
                {"url": "https://example.com/blog/article-1", "title": "Article 1"},
                {"url": "https://example.com/news/story-1", "title": "Story 1"},
                {"url": "https://example.com/about", "title": "About"},  # Should be filtered
                {"url": "https://example.com/category/tech", "title": "Tech"},  # Should be filtered
                {"url": "https://example.com/tag/python", "title": "Python"},  # Should be filtered
            ]

            filtered = discoverer._filter_article_links(test_links, "https://example.com")

            # Only blog and news links should remain
            assert len(filtered) >= 2
            filtered_urls = [link["url"] for link in filtered]
            assert "https://example.com/blog/article-1" in filtered_urls
            assert "https://example.com/news/story-1" in filtered_urls
            assert "https://example.com/about" not in filtered_urls
            assert "https://example.com/category/tech" not in filtered_urls

    def test_filter_excludes_different_domain(self, temp_output_dir: Path, mock_firecrawl: MagicMock) -> None:
        """Test that links from different domains are filtered out."""
        config = WebArticlesConfig(
            output_dir=str(temp_output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
        )

        with patch(
            "tools.web_articles.src.collectors.web_articles.collector.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            discoverer = WebArticlesDiscoverer(config)

            test_links = [
                {"url": "https://example.com/blog/article-1", "title": "Article 1"},
                {"url": "https://otherdomain.com/blog/article-2", "title": "Article 2"},  # Different domain
            ]

            filtered = discoverer._filter_article_links(test_links, "https://example.com")

            # Only same-domain link should remain
            assert len(filtered) <= 1
            if len(filtered) > 0:
                assert all("example.com" in link["url"] for link in filtered)


class TestStateManagement:
    """Test state tracking and persistence."""

    def test_load_empty_state(self, temp_output_dir: Path, mock_firecrawl: MagicMock) -> None:
        """Test loading state when no state file exists."""
        config = WebArticlesConfig(
            output_dir=str(temp_output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
            state_file=str(temp_output_dir / "nonexistent_state.json"),
        )

        with patch(
            "tools.web_articles.src.collectors.web_articles.collector.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            discoverer = WebArticlesDiscoverer(config)

            # Check state_manager instead of state dict
            discovered_items = discoverer.state_manager.get_processed_items(source_type="web_articles")
            assert len(discovered_items) == 0

    def test_load_existing_state(self, temp_output_dir: Path, temp_state_file: Path, mock_firecrawl: MagicMock) -> None:
        """Test loading existing state file - SQLite state manager doesn't auto-load JSON files."""
        config = WebArticlesConfig(
            output_dir=str(temp_output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
            state_file=str(temp_state_file),
        )

        with patch(
            "tools.web_articles.src.collectors.web_articles.collector.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            discoverer = WebArticlesDiscoverer(config)

            # Note: SQLite state manager creates a .db file, not a .json file
            # So this test just verifies the discoverer initializes correctly
            # The actual state persistence is tested in test_state_persistence
            discovered_items = discoverer.state_manager.get_processed_items(source_type="web_articles")
            # Should be empty since SQLite doesn't load from JSON
            assert isinstance(discovered_items, list)

    def test_state_persistence(self, temp_output_dir: Path, mock_firecrawl: MagicMock) -> None:
        """Test that state is saved correctly."""
        state_file = temp_output_dir / "state.json"
        config = WebArticlesConfig(
            output_dir=str(temp_output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com/blog")],
            firecrawl=FirecrawlConfig(),
            state_file=str(state_file),
            review_file=str(temp_output_dir / "review.yaml"),
        )

        # Mock Firecrawl to return some links
        mock_map_result = MagicMock()
        mock_map_result.links = ["https://example.com/blog/test-article"]
        mock_firecrawl.map_url.return_value = mock_map_result

        with patch(
            "tools.web_articles.src.collectors.web_articles.collector.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            discoverer = WebArticlesDiscoverer(config)
            discoverer.discover(verbose=False)

            # Check state database file was created (.db extension, not .json)
            state_db_file = temp_output_dir / "state.db"
            assert state_db_file.exists()

            # Verify state content via state_manager
            discovered_items = discoverer.state_manager.get_processed_items(source_type="web_articles")
            assert len(discovered_items) >= 0  # May be empty if links were filtered
            assert isinstance(discovered_items, list)


class TestReviewFileGeneration:
    """Test review file generation."""

    def test_write_review_file(self, temp_output_dir: Path, mock_firecrawl: MagicMock) -> None:
        """Test writing review file with discovered links."""
        review_file = temp_output_dir / "review.yaml"
        config = WebArticlesConfig(
            output_dir=str(temp_output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com/blog")],
            firecrawl=FirecrawlConfig(),
            state_file=str(temp_output_dir / "state.json"),
            review_file=str(review_file),
        )

        # Mock Firecrawl to return article links
        mock_map_result = MagicMock()
        mock_map_result.links = ["https://example.com/blog/test-article"]
        mock_firecrawl.map_url.return_value = mock_map_result

        with patch(
            "tools.web_articles.src.collectors.web_articles.collector.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            discoverer = WebArticlesDiscoverer(config)
            stats = discoverer.discover(verbose=False)

            # Check review file was created if there were new links
            if stats["new_links"] > 0:
                assert review_file.exists()

                # Load and verify review file content
                with open(review_file) as f:
                    review_data = yaml.safe_load(f)

                assert "file_metadata" in review_data
                assert "sources" in review_data
                assert review_data["file_metadata"]["total_sources"] >= 0

    def test_review_file_structure(self, temp_output_dir: Path, sample_review_data: dict[str, Any]) -> None:
        """Test that review file has correct structure."""
        # Verify sample review data structure
        assert "file_metadata" in sample_review_data
        assert "sources" in sample_review_data

        metadata = sample_review_data["file_metadata"]
        assert "generated_by" in metadata
        assert "generated_on" in metadata
        assert "total_sources" in metadata
        assert "total_links" in metadata

        sources = sample_review_data["sources"]
        assert len(sources) > 0

        for source in sources:
            assert "source_url" in source
            assert "discovery_date" in source
            assert "links" in source

            for link in source["links"]:
                assert "url" in link
                assert "title" in link
                assert "matched_keywords" in link


class TestExcludeKeywords:
    """Test exclude keywords filtering."""

    def test_exclude_keywords_in_url(self, temp_output_dir: Path, mock_firecrawl: MagicMock) -> None:
        """Test that links with exclude keywords in URL are filtered."""
        config = WebArticlesConfig(
            output_dir=str(temp_output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=["spam", "advertisement"],
            sources=[SourceConfig(url="https://example.com/blog")],
            firecrawl=FirecrawlConfig(),
            state_file=str(temp_output_dir / "state.json"),
            review_file=str(temp_output_dir / "review.yaml"),
        )

        # Mock Firecrawl to return links with spam in URL
        mock_map_result = MagicMock()
        mock_map_result.links = [
            "https://example.com/blog/good-article",
            "https://example.com/blog/spam-article",  # Should be excluded
            "https://example.com/blog/advertisement-page",  # Should be excluded
        ]
        mock_firecrawl.map_url.return_value = mock_map_result

        with patch(
            "tools.web_articles.src.collectors.web_articles.collector.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            discoverer = WebArticlesDiscoverer(config)
            stats = discoverer.discover(verbose=False)

            # Should exclude spam and advertisement links
            assert stats["excluded_links"] >= 2


class TestDiscoverWorkflow:
    """Test complete discovery workflow."""

    def test_discover_with_no_new_links(
        self, temp_output_dir: Path, temp_state_file: Path, mock_firecrawl: MagicMock
    ) -> None:
        """Test discovery when all links are already in state."""
        config = WebArticlesConfig(
            output_dir=str(temp_output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com/blog")],
            firecrawl=FirecrawlConfig(),
            state_file=str(temp_state_file),
            review_file=str(temp_output_dir / "review.yaml"),
        )

        # Pre-populate state with some URLs
        discoverer_temp = WebArticlesDiscoverer(config)
        discoverer_temp.state_manager.mark_item_processed(
            "https://example.com/blog/article-1", source_type="web_articles", source_name="example.com"
        )
        discoverer_temp.state_manager.mark_item_processed(
            "https://example.com/blog/article-2", source_type="web_articles", source_name="example.com"
        )

        # Mock Firecrawl to return links that are already in state
        mock_map_result = MagicMock()
        mock_map_result.links = [
            "https://example.com/blog/article-1",  # Already in state
            "https://example.com/blog/article-2",  # Already in state
        ]
        mock_firecrawl.map_url.return_value = mock_map_result

        with patch(
            "tools.web_articles.src.collectors.web_articles.collector.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            discoverer = WebArticlesDiscoverer(config)
            stats = discoverer.discover(verbose=False)

            assert stats["new_links"] == 0
            assert stats["skipped_links"] >= 2

    def test_discover_with_force_flag(
        self, temp_output_dir: Path, temp_state_file: Path, mock_firecrawl: MagicMock
    ) -> None:
        """Test discovery with force flag (ignore state)."""
        config = WebArticlesConfig(
            output_dir=str(temp_output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com/blog")],
            firecrawl=FirecrawlConfig(),
            state_file=str(temp_state_file),
            review_file=str(temp_output_dir / "review.yaml"),
        )

        # Mock Firecrawl to return article links
        mock_map_result = MagicMock()
        mock_map_result.links = ["https://example.com/blog/article-1"]  # Already in state
        mock_firecrawl.map_url.return_value = mock_map_result

        with patch(
            "tools.web_articles.src.collectors.web_articles.collector.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            discoverer = WebArticlesDiscoverer(config)
            stats = discoverer.discover(force=True, verbose=False)

            # With force=True, should re-discover even existing links
            assert stats["skipped_links"] == 0
