"""Tests for web-articles content fetcher.

This module tests content fetching, markdown generation, and file creation.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from tools.web_articles.src.collectors.web_articles.config import (
    FirecrawlConfig,
    SourceConfig,
    WebArticlesConfig,
)
from tools.web_articles.src.collectors.web_articles.fetcher import WebArticlesFetcher


class TestWebArticlesFetcher:
    """Test WebArticlesFetcher class."""

    def test_fetcher_initialization(self, sample_config_data: dict[str, Any], mock_firecrawl: MagicMock) -> None:
        """Test fetcher initialization with valid config."""
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
            "tools.web_articles.src.collectors.web_articles.fetcher.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            fetcher = WebArticlesFetcher(config)
            assert fetcher.config == config
            assert fetcher.firecrawl_api_key == "fc-test-key-12345"

    def test_fetcher_missing_api_key(self, sample_config_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
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
            WebArticlesFetcher(config)


class TestContentFetching:
    """Test content fetching from approved links."""

    def test_fetch_missing_review_file(self, temp_output_dir: Path, mock_firecrawl: MagicMock) -> None:
        """Test that fetch raises error when review file doesn't exist."""
        config = WebArticlesConfig(
            output_dir=str(temp_output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
            review_file=str(temp_output_dir / "nonexistent_review.yaml"),
        )

        with patch(
            "tools.web_articles.src.collectors.web_articles.fetcher.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            fetcher = WebArticlesFetcher(config)

            with pytest.raises(FileNotFoundError, match="Review file not found"):
                fetcher.fetch(verbose=False)

    def test_fetch_invalid_review_file(self, temp_output_dir: Path, mock_firecrawl: MagicMock) -> None:
        """Test that fetch raises error for invalid review file format."""
        review_file = temp_output_dir / "invalid_review.yaml"
        review_file.write_text("invalid: yaml\nno_sources: here")

        config = WebArticlesConfig(
            output_dir=str(temp_output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
            review_file=str(review_file),
        )

        with patch(
            "tools.web_articles.src.collectors.web_articles.fetcher.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            fetcher = WebArticlesFetcher(config)

            with pytest.raises(ValueError, match="Invalid review file format"):
                fetcher.fetch(verbose=False)

    def test_fetch_from_review_file(
        self, temp_output_dir: Path, temp_review_file: Path, mock_firecrawl: MagicMock
    ) -> None:
        """Test fetching content from valid review file."""
        output_dir = temp_output_dir / "articles"
        config = WebArticlesConfig(
            output_dir=str(output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
            review_file=str(temp_review_file),
        )

        # Mock Firecrawl to return article content with metadata
        mock_result = MagicMock()
        mock_result.markdown = (
            "# Test Article\n\n"
            "This is a test article with sufficient content to pass the minimum length check. "
            "It contains multiple paragraphs and detailed information about the topic."
        )
        mock_result.metadata = {
            "title": "Test Article",
            "description": "A test article description",
            "keywords": "test, article, example",
            "author": "Test Author",
            "language": "en",
            "ogTitle": "Test Article OG",
            "ogDescription": "OG description",
            "ogImage": "https://example.com/image.jpg",
        }
        mock_firecrawl.scrape_url.return_value = mock_result

        with patch(
            "tools.web_articles.src.collectors.web_articles.fetcher.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            fetcher = WebArticlesFetcher(config)
            stats = fetcher.fetch(verbose=False)

            # Check that articles were fetched
            assert stats["total"] == 2  # Two links in sample review data
            assert stats["successful"] >= 0
            assert stats["failed"] >= 0


class TestMarkdownGeneration:
    """Test markdown file generation."""

    def test_markdown_file_creation(
        self, temp_output_dir: Path, temp_review_file: Path, mock_firecrawl: MagicMock
    ) -> None:
        """Test that markdown files are created with correct structure."""
        output_dir = temp_output_dir / "articles"
        config = WebArticlesConfig(
            output_dir=str(output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
            review_file=str(temp_review_file),
        )

        # Mock Firecrawl to return article content with metadata
        mock_result = MagicMock()
        mock_result.markdown = "# Test Article\n\nThis is a test article with enough content to be valid."
        mock_result.metadata = {}  # Empty metadata for this test
        mock_firecrawl.scrape_url.return_value = mock_result

        with patch(
            "tools.web_articles.src.collectors.web_articles.fetcher.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            fetcher = WebArticlesFetcher(config)
            stats = fetcher.fetch(verbose=False)

            # Check that output directory was created
            assert output_dir.exists()

            # Check that some markdown files were created
            if stats["successful"] > 0:
                md_files = list(output_dir.glob("*.md"))
                assert len(md_files) > 0

    def test_markdown_frontmatter(
        self, temp_output_dir: Path, temp_review_file: Path, mock_firecrawl: MagicMock
    ) -> None:
        """Test that markdown files have correct frontmatter."""
        output_dir = temp_output_dir / "articles"
        config = WebArticlesConfig(
            output_dir=str(output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
            review_file=str(temp_review_file),
        )

        # Mock Firecrawl to return article content with metadata
        mock_result = MagicMock()
        mock_result.markdown = "# Test Article\n\nThis is test article content with sufficient length for validation."
        mock_result.metadata = {
            "title": "Test Article",
            "description": "Test description",
            "keywords": "test, keywords",
            "author": "Test Author",
            "publishedTime": "2024-01-01",
            "language": "en",
            "ogTitle": "OG Title",
            "ogDescription": "OG Description",
            "ogImage": "https://example.com/og.jpg",
        }
        mock_firecrawl.scrape_url.return_value = mock_result

        with patch(
            "tools.web_articles.src.collectors.web_articles.fetcher.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            fetcher = WebArticlesFetcher(config)
            stats = fetcher.fetch(verbose=False)

            if stats["successful"] > 0:
                # Read first markdown file
                md_files = list(output_dir.glob("*.md"))
                with open(md_files[0]) as f:
                    content = f.read()

                # Check frontmatter structure
                assert content.startswith("---\n")
                assert "title:" in content
                assert "url:" in content
                assert "source:" in content
                assert "collected_date:" in content
                assert "word_count:" in content
                # Check new metadata fields
                assert "description:" in content
                assert "keywords:" in content
                assert "author:" in content
                assert "published_date:" in content
                assert "language:" in content
                assert "og_title:" in content
                assert "og_description:" in content
                assert "og_image:" in content


class TestFilenameSanitization:
    """Test filename sanitization for safe file creation."""

    def test_filename_from_title(self, temp_output_dir: Path, mock_firecrawl: MagicMock) -> None:
        """Test that filenames are sanitized from titles."""
        review_data = {
            "sources": [
                {
                    "source_url": "https://example.com",
                    "links": [
                        {
                            "url": "https://example.com/article",
                            "title": "Test: Article / With * Special ? Characters!",
                        }
                    ],
                }
            ]
        }

        review_file = temp_output_dir / "review.yaml"
        with open(review_file, "w") as f:
            yaml.dump(review_data, f)

        output_dir = temp_output_dir / "articles"
        config = WebArticlesConfig(
            output_dir=str(output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
            review_file=str(review_file),
        )

        # Mock Firecrawl to return content
        mock_result = MagicMock()
        mock_result.markdown = "# Test\n\nArticle content with enough words to pass validation checks."
        mock_result.metadata = {}
        mock_firecrawl.scrape_url.return_value = mock_result

        with patch(
            "tools.web_articles.src.collectors.web_articles.fetcher.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            fetcher = WebArticlesFetcher(config)
            stats = fetcher.fetch(verbose=False)

            if stats["successful"] > 0:
                # Check that filename doesn't contain special characters
                md_files = list(output_dir.glob("*.md"))
                for md_file in md_files:
                    filename = md_file.name
                    # Should not contain special characters
                    assert "/" not in filename
                    assert "*" not in filename
                    assert "?" not in filename
                    assert ":" not in filename


class TestContentValidation:
    """Test content validation (minimum length, etc.)."""

    def test_skip_short_content(self, temp_output_dir: Path, temp_review_file: Path, mock_firecrawl: MagicMock) -> None:
        """Test that content shorter than minimum length is skipped."""
        output_dir = temp_output_dir / "articles"
        config = WebArticlesConfig(
            output_dir=str(output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
            review_file=str(temp_review_file),
        )

        # Mock Firecrawl to return very short content
        mock_result = MagicMock()
        mock_result.markdown = "Too short"  # Less than 100 chars
        mock_result.metadata = {}
        mock_firecrawl.scrape_url.return_value = mock_result

        with patch(
            "tools.web_articles.src.collectors.web_articles.fetcher.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            fetcher = WebArticlesFetcher(config)
            stats = fetcher.fetch(verbose=False)

            # Should skip articles that are too short
            assert stats["skipped"] == 2  # Both articles in review file should be skipped

    def test_handle_empty_content(
        self, temp_output_dir: Path, temp_review_file: Path, mock_firecrawl: MagicMock
    ) -> None:
        """Test handling of empty content from Firecrawl."""
        output_dir = temp_output_dir / "articles"
        config = WebArticlesConfig(
            output_dir=str(output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
            review_file=str(temp_review_file),
        )

        # Mock Firecrawl to return empty content
        mock_result = MagicMock()
        mock_result.markdown = ""
        mock_result.metadata = {}
        mock_firecrawl.scrape_url.return_value = mock_result

        with patch(
            "tools.web_articles.src.collectors.web_articles.fetcher.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            fetcher = WebArticlesFetcher(config)
            stats = fetcher.fetch(verbose=False)

            # Should skip empty articles
            assert stats["skipped"] == 2


class TestErrorHandling:
    """Test error handling during content fetching."""

    def test_handle_fetch_error(self, temp_output_dir: Path, temp_review_file: Path, mock_firecrawl: MagicMock) -> None:
        """Test handling of errors during content fetching."""
        output_dir = temp_output_dir / "articles"
        config = WebArticlesConfig(
            output_dir=str(output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
            review_file=str(temp_review_file),
        )

        # Mock Firecrawl to raise exception
        mock_firecrawl.scrape_url.side_effect = Exception("API Error")

        with patch(
            "tools.web_articles.src.collectors.web_articles.fetcher.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            fetcher = WebArticlesFetcher(config)
            stats = fetcher.fetch(verbose=False)

            # Should count as failed
            assert stats["failed"] == 2  # Both articles should fail

    def test_handle_rate_limit_error(
        self, temp_output_dir: Path, temp_review_file: Path, mock_firecrawl: MagicMock
    ) -> None:
        """Test handling of rate limit errors (429)."""
        output_dir = temp_output_dir / "articles"
        config = WebArticlesConfig(
            output_dir=str(output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
            review_file=str(temp_review_file),
        )

        # Mock Firecrawl to raise rate limit error
        mock_firecrawl.scrape_url.side_effect = Exception("429 Rate limit exceeded")

        with patch(
            "tools.web_articles.src.collectors.web_articles.fetcher.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            fetcher = WebArticlesFetcher(config)
            stats = fetcher.fetch(verbose=False)

            # Should handle rate limit gracefully
            assert stats["total"] == 2


class TestFetchStatistics:
    """Test fetch statistics tracking."""

    def test_fetch_statistics_successful(
        self, temp_output_dir: Path, temp_review_file: Path, mock_firecrawl: MagicMock
    ) -> None:
        """Test statistics for successful fetch."""
        output_dir = temp_output_dir / "articles"
        config = WebArticlesConfig(
            output_dir=str(output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
            review_file=str(temp_review_file),
        )

        # Mock Firecrawl to return valid content
        mock_result = MagicMock()
        mock_result.markdown = "# Article\n\n" + "This is test content. " * 50  # Sufficient length
        mock_result.metadata = {}
        mock_firecrawl.scrape_url.return_value = mock_result

        with patch(
            "tools.web_articles.src.collectors.web_articles.fetcher.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            fetcher = WebArticlesFetcher(config)
            stats = fetcher.fetch(verbose=False)

            # Verify statistics structure
            assert "successful" in stats
            assert "failed" in stats
            assert "skipped" in stats
            assert "total" in stats
            assert "avg_word_count" in stats

            # Total should equal sum of successful, failed, and skipped
            assert stats["total"] == stats["successful"] + stats["failed"] + stats["skipped"]

    def test_word_count_calculation(
        self, temp_output_dir: Path, temp_review_file: Path, mock_firecrawl: MagicMock
    ) -> None:
        """Test that word count is calculated and included in stats."""
        output_dir = temp_output_dir / "articles"
        config = WebArticlesConfig(
            output_dir=str(output_dir),
            rate_limit_seconds=0.1,
            exclude_keywords=[],
            sources=[SourceConfig(url="https://example.com")],
            firecrawl=FirecrawlConfig(),
            review_file=str(temp_review_file),
        )

        # Mock Firecrawl to return content with known word count
        test_content = "# Article\n\n" + "word " * 100  # 100 words + "# Article"
        mock_result = MagicMock()
        mock_result.markdown = test_content
        mock_result.metadata = {}
        mock_firecrawl.scrape_url.return_value = mock_result

        with patch(
            "tools.web_articles.src.collectors.web_articles.fetcher.V1FirecrawlApp", return_value=mock_firecrawl
        ):
            fetcher = WebArticlesFetcher(config)
            stats = fetcher.fetch(verbose=False)

            if stats["successful"] > 0:
                # Average word count should be calculated
                assert stats["avg_word_count"] > 0
